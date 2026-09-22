"""
vault_core.py

The actual encrypt/split and match/reconstruct/decrypt logic, factored
out so both the CLI scripts (vault_create.py, vault_recover.py) and the
GUI (vault_gui.py) call the exact same code paths -- no duplicated
crypto logic between the terminal and windowed versions of this tool.

Functions here raise plain exceptions (ValueError, VaultError) rather
than calling sys.exit, so callers (CLI argparse wrapper, or a Tk
dialog) can present errors however fits their interface.
"""

import base64
import os
import secrets
import string
import tarfile
import tempfile
from datetime import datetime, timezone

from cryptography.exceptions import InvalidTag
from cryptography.hazmat.primitives.ciphers.aead import AESGCM

from gf256_sss import split_secret, reconstruct_secret
from wordgen import estimate_word_entropy_bits, load_dictionary, pick_words, bundled_memorable_wordlist
import kdf as kdfmod
import krypt_container

DEK_LEN = 32
SALT_LEN = 16
NONCE_LEN = 12


class VaultError(Exception):
    """Raised for recoverable, user-facing problems (bad input, wrong
    codewords, corrupted files, missing optional dependency, etc.)."""


def _noop_log(msg: str) -> None:
    pass


def random_filename(n: int = 16) -> str:
    alphabet = string.ascii_lowercase + string.digits
    return "".join(secrets.choice(alphabet) for _ in range(n))


def make_archive(input_path: str, dest_tar_path: str) -> None:
    """Tar (uncompressed) the input file or directory into dest_tar_path."""
    with tarfile.open(dest_tar_path, "w") as tar:
        arcname = os.path.basename(os.path.normpath(input_path))
        tar.add(input_path, arcname=arcname)


def resolve_kdf_params(kdf_method: str, overrides: dict | None = None) -> dict:
    """overrides is a dict of just the keys the caller wants to change
    from kdfmod.default_params(kdf_method)."""
    params = kdfmod.default_params(kdf_method)
    if overrides:
        params.update({k: v for k, v in overrides.items() if v is not None})
    return params


def resolve_word_mode(
    word_length: int | None,
    word_count: int | None,
    dictionary_path: str | None,
    memorable: bool,
    strong_words: bool,
) -> tuple[int | None, int, str | None, bool, int]:
    """
    Resolves the CLI's --word-length/--word-count/--dictionary/
    --memorable/--strong-words flags into what create_vault expects.
    Shared by vault_create.py and vault_create_prime.py so both CLIs
    get identical --memorable behavior.

    Memorable mode triggers on explicit --memorable, OR implicitly
    whenever --word-length is omitted -- that's the new default path:
    a bare `--input --trustees --threshold` invocation (no word length
    given) gets memorable codewords instead of an argparse error
    demanding one. Passing --word-length always keeps the old
    fixed-length behavior, so anything relying on it is unaffected.

    Returns (word_length, word_count, dictionary_path, randomize_case,
    digit_suffix_len) ready to pass straight into create_vault /
    create_vault_prime. Raises ValueError on conflicting flags.
    """
    is_memorable = memorable or word_length is None
    if is_memorable and strong_words:
        raise ValueError(
            "--memorable and --strong-words pull in opposite directions "
            "(memorability vs. density) -- pick one."
        )
    if is_memorable:
        return None, (word_count if word_count is not None else 8), dictionary_path, False, 0

    if word_length < 3:
        raise ValueError("word length should be at least 3")
    return (
        word_length,
        word_count if word_count is not None else 1,
        dictionary_path,
        strong_words,
        3 if strong_words else 0,
    )


def create_vault(
    input_path: str,
    trustees: int,
    threshold: int,
    word_length: int | None,
    word_count: int = 1,
    dictionary_path: str | None = None,
    outdir: str | None = None,
    kdf_method: str = "pbkdf2",
    kdf_params: dict | None = None,
    randomize_case: bool = False,
    digit_suffix_len: int = 0,
    log=_noop_log,
) -> dict:
    """
    Archives `input_path`, encrypts it, splits the DEK into `trustees`
    Shamir shards (threshold `threshold`), protects each shard with a
    codeword, and writes a single .krypt container plus one codeword
    file per trustee.

    Caller is responsible for resolving kdf_method/kdf_params ahead of
    time (including any "argon2 unavailable, fall back?" confirmation)
    -- this function just uses whatever it's given.

    randomize_case/digit_suffix_len are the opt-in stronger-codeword
    mode (see wordgen.py's module docstring) -- both default off.

    word_length=None means memorable mode: dictionary_words (real,
    whole words, no length filter) is used unfiltered -- pass
    dictionary_path=None to fall back to wordgen.bundled_memorable_wordlist().
    Callers doing this should also pass randomize_case=False,
    digit_suffix_len=0, since those actively hurt memorability.

    Returns: {"krypt_path": str, "words_dir": str, "trustee_files": [str, ...],
    "outdir": str, "estimated_word_entropy_bits": float}
    """
    if threshold > trustees:
        raise ValueError("threshold (D) cannot exceed trustees (T)")
    if not (1 <= trustees <= 255):
        raise ValueError("trustees (T) must be between 1 and 255")
    if word_length is not None and word_length < 3:
        raise ValueError("word length should be at least 3")
    if not os.path.exists(input_path):
        raise ValueError(f"input path not found: {input_path}")

    if kdf_params is None:
        kdf_params = kdfmod.default_params(kdf_method)

    outdir = outdir or f"vault_{datetime.now(timezone.utc).strftime('%Y%m%dT%H%M%SZ')}"
    os.makedirs(outdir, exist_ok=True)
    krypt_filename = random_filename(16) + ".krypt"
    krypt_stem = os.path.splitext(krypt_filename)[0]
    words_dir = os.path.join(outdir, f"{krypt_stem}_trustee_words")
    os.makedirs(words_dir, exist_ok=True)

    if word_length is None:
        dictionary_words = load_dictionary(dictionary_path, None) if dictionary_path else bundled_memorable_wordlist()
        source = dictionary_path or "the bundled EFF wordlist"
        log(f"Memorable mode: loaded {len(dictionary_words)} whole, real candidate words from {source}")
    elif dictionary_path:
        dictionary_words = load_dictionary(dictionary_path, word_length)
        log(f"Loaded {len(dictionary_words)} candidate words of length {word_length} from {dictionary_path}")
    else:
        dictionary_words = None
        log("No dictionary supplied; using synthetic pronounceable words.")

    entropy_bits = estimate_word_entropy_bits(
        word_length,
        word_count,
        dictionary_size=len(dictionary_words) if dictionary_words else None,
        randomize_case=randomize_case,
        digit_suffix_len=digit_suffix_len,
    )
    style_bits = []
    if randomize_case:
        style_bits.append("mixed case")
    if digit_suffix_len:
        style_bits.append(f"+{digit_suffix_len} digit suffix")
    style = f" ({', '.join(style_bits)})" if style_bits else ""
    log(
        f"Estimated codeword strength: ~{entropy_bits:.0f} bits combinatorial per "
        f"trustee{style} (before any KDF stretching). Recovery cracks each "
        f"codeword independently, so this per-codeword number -- not a "
        f"{trustees}-trustee total -- is the real security margin; raising "
        f"threshold/trustee counts does not substitute for it."
    )

    with tempfile.TemporaryDirectory() as tmp:
        tar_path = os.path.join(tmp, "archive.tar")
        log(f"Archiving '{input_path}' ...")
        make_archive(input_path, tar_path)
        with open(tar_path, "rb") as f:
            plaintext = f.read()

    dek = secrets.token_bytes(DEK_LEN)
    archive_nonce = secrets.token_bytes(NONCE_LEN)
    ciphertext = AESGCM(dek).encrypt(archive_nonce, plaintext, associated_data=None)

    shards = split_secret(dek, threshold=threshold, total_shards=trustees)
    log(f"Split DEK into {trustees} shards, threshold {threshold}")

    shard_records = []
    trustee_files = []
    for i, (x, y) in enumerate(shards, start=1):
        codeword = pick_words(
            word_length,
            word_count,
            dictionary_words,
            randomize_case=randomize_case,
            digit_suffix_len=digit_suffix_len,
        )
        salt = secrets.token_bytes(SALT_LEN)
        shard_key = kdfmod.derive_key(kdf_method, kdf_params, codeword, salt)
        shard_nonce = secrets.token_bytes(NONCE_LEN)
        payload = bytes([x]) + y
        shard_ct = AESGCM(shard_key).encrypt(shard_nonce, payload, associated_data=None)

        shard_records.append({
            "salt": base64.b64encode(salt).decode(),
            "nonce": base64.b64encode(shard_nonce).decode(),
            "ciphertext": base64.b64encode(shard_ct).decode(),
        })

        trustee_file = os.path.join(words_dir, f"trustee_{i}.txt")
        with open(trustee_file, "w") as f:
            f.write(codeword + "\n")
        trustee_files.append(trustee_file)

    secrets.SystemRandom().shuffle(shard_records)

    metadata = {
        "version": 2,
        "container_format": "krypt1",
        "created_utc": datetime.now(timezone.utc).isoformat(),
        "archive_nonce": base64.b64encode(archive_nonce).decode(),
        "trustees_total": trustees,
        "threshold": threshold,
        "word_length": word_length,
        "word_count": word_count,
        "randomize_case": randomize_case,
        "digit_suffix_len": digit_suffix_len,
        "kdf": kdf_method,
        "kdf_params": kdf_params,
        "salt_len": SALT_LEN,
        "nonce_len": NONCE_LEN,
        "shards": shard_records,
    }
    krypt_path = os.path.join(outdir, krypt_filename)
    krypt_container.write_krypt(krypt_path, metadata, ciphertext)
    log(f"Wrote vault container: {krypt_path} ({os.path.getsize(krypt_path)} bytes)")

    return {
        "krypt_path": krypt_path,
        "words_dir": words_dir,
        "trustee_files": trustee_files,
        "outdir": os.path.abspath(outdir),
        "estimated_word_entropy_bits": entropy_bits,
    }


def peek_metadata(krypt_path: str) -> dict:
    """Read just the metadata of a .krypt file (threshold, trustee count,
    KDF, etc.) without attempting any decryption. Raises VaultError if
    it's a shardic-prime vault (use vault_recover_prime.py for those)."""
    metadata, _ = krypt_container.read_krypt(krypt_path)
    if metadata.get("scheme") == "prime-trustee":
        raise VaultError(
            f"'{krypt_path}' is a shardic-prime vault (scheme='prime-trustee'), "
            "not a plain krypt1 vault. Use vault_recover_prime.py to recover it."
        )
    return metadata


def _resolve_kdf_common(metadata: dict) -> tuple[str, dict]:
    """Shared by vault_core.resolve_kdf and vault_core_prime.resolve_kdf --
    backward compatible with version-1 metadata (PBKDF2 only, flat fields).
    Raises VaultError if the vault needs Argon2id and it's unavailable.
    Does NOT check the scheme tag; callers apply their own scheme guard
    before calling this, since the base scheme rejects prime-trustee
    metadata and the prime scheme requires it."""
    if "kdf_params" in metadata:
        kdf_method = metadata["kdf"]
        kdf_params = metadata["kdf_params"]
    else:
        kdf_method = "pbkdf2"
        kdf_params = {"iterations": metadata["kdf_iterations"]}

    if kdf_method == "argon2id" and not kdfmod.ARGON2_AVAILABLE:
        raise VaultError(
            "This vault's shards are protected with Argon2id, but "
            "'argon2-cffi' isn't installed here. Install it and try "
            "again -- there's no fallback for this, since the KDF "
            "choice was fixed when the vault was created."
        )
    return kdf_method, kdf_params


def resolve_kdf(metadata: dict) -> tuple[str, dict]:
    """Raises VaultError if this is a shardic-prime vault (use
    vault_recover_prime.py for those) -- this is the one choke point both
    vault_recover.py (which reads the container directly, bypassing
    peek_metadata) and the GUI's match_codewords() both pass through, so
    it's checked here too, not just in peek_metadata."""
    if metadata.get("scheme") == "prime-trustee":
        raise VaultError(
            "This is a shardic-prime vault (scheme='prime-trustee'), not a "
            "plain krypt1 vault. Use vault_recover_prime.py to recover it."
        )
    return _resolve_kdf_common(metadata)


def try_match_word(codeword: str, shard_records, kdf_method, kdf_params, used_indices):
    """Try `codeword` against every not-yet-consumed shard record.
    Returns (record_index, x, y) on success, else None."""
    for idx, rec in enumerate(shard_records):
        if idx in used_indices:
            continue
        salt = base64.b64decode(rec["salt"])
        nonce = base64.b64decode(rec["nonce"])
        ct = base64.b64decode(rec["ciphertext"])
        key = kdfmod.derive_key(kdf_method, kdf_params, codeword, salt)
        try:
            payload = AESGCM(key).decrypt(nonce, ct, associated_data=None)
        except InvalidTag:
            continue
        return idx, payload[0], payload[1:]
    return None


def match_codewords(codewords: list[str], metadata: dict) -> tuple[list, list[int]]:
    """
    Try each codeword in `codewords` against the vault's shard records.
    Returns (recovered_shards, unmatched_positions) where recovered_shards
    is a list of (x, y_bytes) and unmatched_positions are indices into
    the input `codewords` list that didn't match anything (skips blanks).
    """
    kdf_method, kdf_params = resolve_kdf(metadata)
    shard_records = metadata.get("shards", metadata.get("shares"))

    recovered = []
    used_indices: set[int] = set()
    unmatched_positions = []

    for pos, word in enumerate(codewords):
        word = word.strip()
        if not word:
            continue
        match = try_match_word(word, shard_records, kdf_method, kdf_params, used_indices)
        if match is None:
            unmatched_positions.append(pos)
            continue
        idx, x, y = match
        used_indices.add(idx)
        recovered.append((x, y))

    return recovered, unmatched_positions


def reconstruct_and_decrypt(
    metadata: dict,
    ciphertext: bytes,
    recovered_shards: list,
    outdir: str | None = None,
    log=_noop_log,
) -> dict:
    """
    Given >= threshold recovered (x, y) shards, reconstructs the DEK,
    decrypts the archive, and extracts it to `outdir`.

    Returns: {"outdir": str}
    """
    threshold = metadata["threshold"]
    if len(recovered_shards) < threshold:
        raise VaultError(
            f"Only {len(recovered_shards)} of the required {threshold} "
            "codewords matched a shard."
        )

    log("Reconstructing DEK from recovered shards ...")
    dek = reconstruct_secret(recovered_shards)
    if len(dek) != DEK_LEN:
        raise VaultError("Reconstructed key has unexpected length -- shards may be inconsistent.")

    log("Decrypting archive ...")
    archive_nonce = base64.b64decode(metadata["archive_nonce"])
    try:
        plaintext = AESGCM(dek).decrypt(archive_nonce, ciphertext, associated_data=None)
    except InvalidTag:
        raise VaultError(
            "Archive decryption failed authentication. This means the "
            "recovered DEK is wrong (mismatched/insufficient shards) or "
            "the ciphertext is corrupted/tampered. No output was written."
        )

    outdir = outdir or f"recovered_{datetime.now(timezone.utc).strftime('%Y%m%dT%H%M%SZ')}"
    os.makedirs(outdir, exist_ok=True)

    with tempfile.NamedTemporaryFile(suffix=".tar", delete=False) as tmp:
        tmp.write(plaintext)
        tmp_path = tmp.name
    try:
        with tarfile.open(tmp_path, "r") as tar:
            tar.extractall(outdir, filter="data")
    finally:
        os.remove(tmp_path)

    log(f"Success. Recovered contents extracted to: {os.path.abspath(outdir)}")
    return {"outdir": os.path.abspath(outdir)}

"""
vault_core_prime.py

"shardic-prime" variant of vault_core.py: same threshold-recoverable
vault, plus one PRIME trustee whose codeword must always be present at
recovery time. The remaining trustees stay a plain interchangeable
k-of-n pool -- see gf256_sss_prime.py for the layered split/reconstruct
construction this is built on.

Deliberately a separate module/CLI/container-format from the base
scheme (container_format "krypt1-prime", not "krypt1", plus a
"scheme": "prime-trustee" metadata tag) rather than a flag on the
original -- so a base-scheme vault can never accidentally be opened
with prime-aware tooling or vice versa, and vault_core.py's plain
uniform scheme stays untouched.

`trustees` (T) and `threshold` (D) here count the prime trustee: T
total participants = 1 prime + (T-1) pool trustees; D codewords
required to recover = the prime's + (D-1) from the pool.

Shard records keep the same opaque {salt, nonce, ciphertext} shape as
the base scheme, and are shuffled together the same way -- so which
record belongs to the prime trustee is not visible from the container
structure either, only from decrypting it with the right codeword.
The encrypted payload carries a one-byte type tag (SHARD_TYPE_PRIME /
SHARD_TYPE_POOL) so a codeword's role is only learned once it matches.
"""

import base64
import os
import secrets
import tarfile
import tempfile
from datetime import datetime, timezone

from cryptography.exceptions import InvalidTag
from cryptography.hazmat.primitives.ciphers.aead import AESGCM

from gf256_sss_prime import split_secret_with_prime, reconstruct_secret_with_prime
from wordgen import estimate_word_entropy_bits, load_dictionary, pick_words, bundled_memorable_wordlist
import kdf as kdfmod
import krypt_container
import vault_core as base

DEK_LEN = base.DEK_LEN
SALT_LEN = base.SALT_LEN
NONCE_LEN = base.NONCE_LEN

VaultError = base.VaultError

SHARD_TYPE_PRIME = 0
SHARD_TYPE_POOL = 1

# Shard-protection mode, per whitepaper §4.8: "kdf" is the traditional
# human-memorized codeword stretched through kdf.derive_key(); "drbg" is
# a full-strength key drawn directly from the OS CSPRNG, used as the
# shard-protection key with no wordlist and no KDF stretching -- because
# neither serves any purpose against a value that's already uniformly
# random across the full key space. A "drbg" credential can't be
# memorized, so callers that choose it must deliver the raw key bytes
# via shardic-envelope (or physical carriage) rather than asking a
# trustee to type anything.
PROTECTION_KDF = "kdf"
PROTECTION_DRBG = "drbg"


def _noop_log(msg: str) -> None:
    pass


def create_vault_prime(
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
    protection_modes: list[str] | None = None,
    log=_noop_log,
) -> dict:
    """
    Like vault_core.create_vault, except one of the `trustees` is a
    PRIME trustee whose codeword is required for every recovery,
    alongside any (threshold - 1) of the remaining (trustees - 1) pool
    trustees.

    `protection_modes`, if given, is a list of length `trustees` (index
    0 = prime, 1..pool_size = pool trustees in split order) of
    PROTECTION_KDF/PROTECTION_DRBG, choosing per-trustee how that
    trustee's shard is protected (see the PROTECTION_* constants).
    Omitting it (the default) protects every trustee with PROTECTION_KDF,
    identical to this function's behavior before this parameter existed
    -- existing callers (the CLI, the GUI) are unaffected.

    Returns the same shape as create_vault, plus "prime_trustee_file"
    and "credentials". "credentials" is the authoritative, per-trustee
    list (prime first, then pool in split order); each entry is either
    {"mode": "kdf", "codeword": str, "file": path} -- same codeword
    also written to that file, as always -- or {"mode": "drbg", "key":
    bytes} for a PROTECTION_DRBG trustee, whose raw key is returned
    directly and never written to disk anywhere, since there is no
    codeword file for it to live in. "trustee_files"/"prime_trustee_file"
    remain populated exactly as before when `protection_modes` is
    omitted; with a mix of modes they cover only the "kdf" subset, in
    trustee order -- callers that need the full picture (e.g. a SPAC
    combiner) should use "credentials" instead.
    """
    if threshold < 2:
        raise ValueError(
            "threshold (D) must be >= 2: 1 mandatory prime codeword + "
            ">= 1 from the pool"
        )
    if trustees < 2:
        raise ValueError("trustees (T) must be >= 2: 1 prime trustee + >= 1 pool trustee")
    if threshold > trustees:
        raise ValueError("threshold (D) cannot exceed trustees (T)")
    if not (2 <= trustees <= 255):
        raise ValueError("trustees (T) must be between 2 and 255")
    if word_length is not None and word_length < 3:
        raise ValueError("word length should be at least 3")
    if not os.path.exists(input_path):
        raise ValueError(f"input path not found: {input_path}")
    if protection_modes is not None:
        if len(protection_modes) != trustees:
            raise ValueError(
                f"protection_modes must have exactly {trustees} entries "
                "(1 prime + pool, in that order)"
            )
        if any(m not in (PROTECTION_KDF, PROTECTION_DRBG) for m in protection_modes):
            raise ValueError(f"protection_modes entries must be {PROTECTION_KDF!r} or {PROTECTION_DRBG!r}")

    pool_size = trustees - 1
    pool_threshold = threshold - 1

    def _mode_for(trustee_index: int) -> str:
        return PROTECTION_KDF if protection_modes is None else protection_modes[trustee_index]

    needs_kdf_credentials = any(_mode_for(i) == PROTECTION_KDF for i in range(trustees))

    if kdf_params is None:
        kdf_params = kdfmod.default_params(kdf_method)

    outdir = outdir or f"vault_{datetime.now(timezone.utc).strftime('%Y%m%dT%H%M%SZ')}"
    os.makedirs(outdir, exist_ok=True)
    krypt_filename = base.random_filename(16) + ".krypt"
    krypt_stem = os.path.splitext(krypt_filename)[0]
    words_dir = os.path.join(outdir, f"{krypt_stem}_trustee_words")
    os.makedirs(words_dir, exist_ok=True)

    dictionary_words = None
    entropy_bits = None
    if needs_kdf_credentials:
        if word_length is None:
            dictionary_words = load_dictionary(dictionary_path, None) if dictionary_path else bundled_memorable_wordlist()
            source = dictionary_path or "the bundled EFF wordlist"
            log(f"Memorable mode: loaded {len(dictionary_words)} whole, real candidate words from {source}")
        elif dictionary_path:
            dictionary_words = load_dictionary(dictionary_path, word_length)
            log(f"Loaded {len(dictionary_words)} candidate words of length {word_length} from {dictionary_path}")
        else:
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
            f"KDF-protected trustee{style} (before any KDF stretching) -- "
            "recovery cracks each codeword independently."
        )
    if any(_mode_for(i) == PROTECTION_DRBG for i in range(trustees)):
        log(
            "DRBG-direct mode: the corresponding trustee credential(s) are drawn "
            "directly from the OS CSPRNG as a full 256-bit key -- no wordlist, "
            "no KDF stretching, and no codeword file is written for them."
        )

    with tempfile.TemporaryDirectory() as tmp:
        tar_path = os.path.join(tmp, "archive.tar")
        log(f"Archiving '{input_path}' ...")
        base.make_archive(input_path, tar_path)
        with open(tar_path, "rb") as f:
            plaintext = f.read()

    dek = secrets.token_bytes(DEK_LEN)
    archive_nonce = secrets.token_bytes(NONCE_LEN)
    ciphertext = AESGCM(dek).encrypt(archive_nonce, plaintext, associated_data=None)

    mask, pool_shards = split_secret_with_prime(dek, pool_threshold=pool_threshold, pool_size=pool_size)
    log(
        f"Split DEK into 1 prime shard + {pool_size} pool shards, pool "
        f"threshold {pool_threshold} (total required to recover: {threshold})"
    )

    def _seal_kdf(codeword: str, payload: bytes) -> dict:
        salt = secrets.token_bytes(SALT_LEN)
        shard_key = kdfmod.derive_key(kdf_method, kdf_params, codeword, salt)
        shard_nonce = secrets.token_bytes(NONCE_LEN)
        shard_ct = AESGCM(shard_key).encrypt(shard_nonce, payload, associated_data=None)
        return {
            "protection": PROTECTION_KDF,
            "salt": base64.b64encode(salt).decode(),
            "nonce": base64.b64encode(shard_nonce).decode(),
            "ciphertext": base64.b64encode(shard_ct).decode(),
        }

    def _seal_drbg(payload: bytes) -> tuple[dict, bytes]:
        shard_key = secrets.token_bytes(32)
        shard_nonce = secrets.token_bytes(NONCE_LEN)
        shard_ct = AESGCM(shard_key).encrypt(shard_nonce, payload, associated_data=None)
        record = {
            "protection": PROTECTION_DRBG,
            "nonce": base64.b64encode(shard_nonce).decode(),
            "ciphertext": base64.b64encode(shard_ct).decode(),
        }
        return record, shard_key

    def _issue(trustee_index: int, file_stem: str, payload: bytes) -> dict:
        """Seals `payload` under whichever protection mode this trustee_index
        was assigned, and returns its "credentials" entry (see docstring)."""
        if _mode_for(trustee_index) == PROTECTION_KDF:
            codeword = pick_words(
                word_length, word_count, dictionary_words,
                randomize_case=randomize_case, digit_suffix_len=digit_suffix_len,
            )
            shard_records.append(_seal_kdf(codeword, payload))
            file_path = os.path.join(words_dir, f"{file_stem}.txt")
            with open(file_path, "w") as f:
                f.write(codeword + "\n")
            trustee_files.append(file_path)
            return {"mode": PROTECTION_KDF, "codeword": codeword, "file": file_path}
        record, raw_key = _seal_drbg(payload)
        shard_records.append(record)
        return {"mode": PROTECTION_DRBG, "key": raw_key}

    shard_records = []
    trustee_files = []
    credentials = []

    prime_cred = _issue(0, "trustee_prime", bytes([SHARD_TYPE_PRIME]) + mask)
    credentials.append(prime_cred)
    prime_file = prime_cred.get("file")

    for i, (x, y) in enumerate(pool_shards, start=1):
        pool_cred = _issue(i, f"trustee_{i}", bytes([SHARD_TYPE_POOL, x]) + y)
        credentials.append(pool_cred)

    secrets.SystemRandom().shuffle(shard_records)

    metadata = {
        "version": 1,
        "container_format": "krypt1-prime",
        "scheme": "prime-trustee",
        "created_utc": datetime.now(timezone.utc).isoformat(),
        "archive_nonce": base64.b64encode(archive_nonce).decode(),
        "trustees_total": trustees,
        "threshold": threshold,
        "pool_size": pool_size,
        "pool_threshold": pool_threshold,
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
        "prime_trustee_file": prime_file,
        "credentials": credentials,
        "outdir": os.path.abspath(outdir),
        "estimated_word_entropy_bits": entropy_bits,
    }


def peek_metadata(krypt_path: str) -> dict:
    """Read just the metadata of a shardic-prime .krypt file, without
    attempting any decryption. Raises VaultError if it isn't one."""
    metadata, _ = krypt_container.read_krypt(krypt_path)
    if metadata.get("scheme") != "prime-trustee":
        raise VaultError(
            f"'{krypt_path}' is not a shardic-prime vault "
            f"(scheme={metadata.get('scheme')!r}). Use vault_recover.py "
            "for plain krypt1 vaults."
        )
    return metadata


def resolve_kdf(metadata: dict) -> tuple[str, dict]:
    """Raises VaultError if this isn't a shardic-prime vault (use
    vault_recover.py for plain krypt1 vaults) -- mirrors peek_metadata's
    guard, and is the choke point vault_recover_prime.py's main() passes
    through (it reads the container directly, bypassing peek_metadata)."""
    if metadata.get("scheme") != "prime-trustee":
        raise VaultError(
            f"This is not a shardic-prime vault (scheme={metadata.get('scheme')!r}), "
            "not 'prime-trustee'. Use vault_recover.py for plain krypt1 vaults."
        )
    return base._resolve_kdf_common(metadata)


def try_match_word_prime(codeword: str, shard_records, kdf_method, kdf_params, used_indices):
    """Like vault_core.try_match_word, but decodes the type-tagged
    payload used by the prime-trustee scheme. Only tries PROTECTION_KDF
    records -- a PROTECTION_DRBG record has no salt to derive against
    and no codeword was ever issued for it (see try_match_key_prime).

    Returns (record_index, kind, value) where kind is "prime" and
    value is the mask bytes, or kind is "pool" and value is
    (x, y_bytes). Returns None if no untried record matches.
    """
    for idx, rec in enumerate(shard_records):
        if idx in used_indices:
            continue
        if rec.get("protection", PROTECTION_KDF) != PROTECTION_KDF:
            continue
        salt = base64.b64decode(rec["salt"])
        nonce = base64.b64decode(rec["nonce"])
        ct = base64.b64decode(rec["ciphertext"])
        key = kdfmod.derive_key(kdf_method, kdf_params, codeword, salt)
        try:
            payload = AESGCM(key).decrypt(nonce, ct, associated_data=None)
        except InvalidTag:
            continue

        shard_type = payload[0]
        if shard_type == SHARD_TYPE_PRIME:
            return idx, "prime", payload[1:]
        if shard_type == SHARD_TYPE_POOL:
            return idx, "pool", (payload[1], payload[2:])
        continue
    return None


def try_match_key_prime(key: bytes, shard_records, used_indices):
    """PROTECTION_DRBG counterpart to try_match_word_prime: `key` is the
    raw shard-protection key a trustee already holds (delivered via
    shardic-envelope or physical carriage, never typed), tried directly
    against every not-yet-matched PROTECTION_DRBG record -- no salt, no
    KDF, since the key is already the AES-256-GCM key itself.

    Returns (record_index, kind, value), same shape as
    try_match_word_prime. Returns None if no untried record matches.
    """
    for idx, rec in enumerate(shard_records):
        if idx in used_indices:
            continue
        if rec.get("protection", PROTECTION_KDF) != PROTECTION_DRBG:
            continue
        nonce = base64.b64decode(rec["nonce"])
        ct = base64.b64decode(rec["ciphertext"])
        try:
            payload = AESGCM(key).decrypt(nonce, ct, associated_data=None)
        except InvalidTag:
            continue

        shard_type = payload[0]
        if shard_type == SHARD_TYPE_PRIME:
            return idx, "prime", payload[1:]
        if shard_type == SHARD_TYPE_POOL:
            return idx, "pool", (payload[1], payload[2:])
        continue
    return None


def match_codewords_prime(codewords: list[str], metadata: dict):
    """
    Try each codeword in `codewords` against the vault's shard records.

    Returns (mask, pool_shards, unmatched_positions):
      mask is the prime trustee's mask bytes, or None if not found.
      pool_shards is a list of (x, y_bytes) from matched pool trustees.
      unmatched_positions are indices into `codewords` that matched nothing.
    """
    kdf_method, kdf_params = resolve_kdf(metadata)
    shard_records = metadata.get("shards", metadata.get("shares"))

    mask = None
    pool_shards = []
    used_indices: set[int] = set()
    unmatched_positions = []

    for pos, word in enumerate(codewords):
        word = word.strip()
        if not word:
            continue
        match = try_match_word_prime(word, shard_records, kdf_method, kdf_params, used_indices)
        if match is None:
            unmatched_positions.append(pos)
            continue
        idx, kind, value = match
        used_indices.add(idx)
        if kind == "prime":
            mask = value
        else:
            pool_shards.append(value)

    return mask, pool_shards, unmatched_positions


def reconstruct_and_decrypt_prime(
    metadata: dict,
    ciphertext: bytes,
    mask,
    pool_shards: list,
    outdir: str | None = None,
    log=_noop_log,
) -> dict:
    """
    Given the prime trustee's mask and >= pool_threshold recovered
    pool (x, y) shards, reconstructs the DEK, decrypts the archive,
    and extracts it to `outdir`.

    Returns: {"outdir": str}
    """
    pool_threshold = metadata["pool_threshold"]
    if mask is None:
        raise VaultError(
            "The prime trustee's codeword was not among those entered -- "
            "this vault cannot be recovered without it, no matter how "
            "many pool codewords are supplied."
        )
    if len(pool_shards) < pool_threshold:
        raise VaultError(
            f"Only {len(pool_shards)} of the required {pool_threshold} pool "
            "codewords matched a shard (plus the prime trustee's)."
        )

    log("Reconstructing DEK from the prime mask and recovered pool shards ...")
    dek = reconstruct_secret_with_prime(mask, pool_shards)
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

"""
kdf.py

Key derivation for shard protection. Two supported methods:

  - "pbkdf2"   : PBKDF2-HMAC-SHA256 via `cryptography` (already a
                 required dependency of this project, zero extra
                 install).
  - "argon2id" : Argon2id via the optional `argon2-cffi` package.
                 Memory-hard, so it resists GPU/ASIC-parallel offline
                 guessing much better than PBKDF2 does for the same
                 wall-clock cost -- worth it if you're worried about
                 someone brute-forcing a leaked metadata.json.

Design point: vault_create.py records which method AND which exact
parameters (iterations, or time/memory/parallelism cost) were used,
inside metadata.json. vault_recover.py reads that back and derives
keys the same way automatically -- it never needs to be told which
KDF a given vault used. That's what keeps both programs standalone:
metadata.json + the .crypt file + the codewords is always enough,
regardless of which KDF choice was made at creation time.
"""

import sys

from cryptography.hazmat.primitives.kdf.pbkdf2 import PBKDF2HMAC
from cryptography.hazmat.primitives import hashes

KEY_LEN = 32

try:
    from argon2.low_level import hash_secret_raw, Type as _Argon2Type
    from argon2.low_level import ffi as _argon2_ffi, lib as _argon2_lib, core as _argon2_core
    from argon2.exceptions import HashingError as _Argon2HashingError
    ARGON2_AVAILABLE = True
except ImportError:
    ARGON2_AVAILABLE = False

# Argon2's output depends on the number of lanes (`parallelism`), never on
# how many threads compute them. hash_secret_raw sets threads = lanes, which
# fails with "Threading failure" where there are no threads (Pyodide in a
# browser). There, compute the same lanes on one thread instead; the key is
# bit-identical, so a vault made either way recovers on the other.
ARGON2_THREADS_AVAILABLE = sys.platform != "emscripten"

METHODS = ("argon2id", "pbkdf2")

DEFAULT_PBKDF2_ITERATIONS = 400_000
DEFAULT_ARGON2_TIME_COST = 4
DEFAULT_ARGON2_MEMORY_COST_KIB = 262144  # 256 MiB
DEFAULT_ARGON2_PARALLELISM = 4
MIN_ARGON2_SALT_LEN = 8


def default_params(method: str) -> dict:
    if method == "pbkdf2":
        return {"iterations": DEFAULT_PBKDF2_ITERATIONS}
    if method == "argon2id":
        return {
            "time_cost": DEFAULT_ARGON2_TIME_COST,
            "memory_cost_kib": DEFAULT_ARGON2_MEMORY_COST_KIB,
            "parallelism": DEFAULT_ARGON2_PARALLELISM,
        }
    raise ValueError(f"Unknown KDF method: {method!r}. Choose one of {METHODS}.")


def derive_key(method: str, params: dict, passphrase: str, salt: bytes) -> bytes:
    if method == "pbkdf2":
        kdf = PBKDF2HMAC(
            algorithm=hashes.SHA256(),
            length=KEY_LEN,
            salt=salt,
            iterations=params["iterations"],
        )
        return kdf.derive(passphrase.encode("utf-8"))

    if method == "argon2id":
        if not ARGON2_AVAILABLE:
            raise RuntimeError(
                "This vault's shards are protected with Argon2id, but the "
                "'argon2-cffi' package isn't installed here. Run:\n"
                "    pip install argon2-cffi\n"
                "then try recovery again. (Nothing else about the vault is "
                "affected -- this is purely a missing local dependency.)"
            )
        if len(salt) < MIN_ARGON2_SALT_LEN:
            raise ValueError("Argon2id salt too short")
        if not ARGON2_THREADS_AVAILABLE:
            return _argon2id_single_thread(
                passphrase.encode("utf-8"),
                salt,
                time_cost=params["time_cost"],
                memory_cost_kib=params["memory_cost_kib"],
                parallelism=params["parallelism"],
            )
        return hash_secret_raw(
            secret=passphrase.encode("utf-8"),
            salt=salt,
            time_cost=params["time_cost"],
            memory_cost=params["memory_cost_kib"],
            parallelism=params["parallelism"],
            hash_len=KEY_LEN,
            type=_Argon2Type.ID,
        )

    raise ValueError(f"Unknown KDF method: {method!r}. Choose one of {METHODS}.")


def _argon2id_single_thread(secret: bytes, salt: bytes, time_cost: int,
                            memory_cost_kib: int, parallelism: int) -> bytes:
    """Argon2id with lanes = parallelism computed on one thread, through
    argon2-cffi's low-level core(). Same output as hash_secret_raw with the
    same parameters (see ARGON2_THREADS_AVAILABLE)."""
    out = _argon2_ffi.new("uint8_t[]", KEY_LEN)
    pwd = _argon2_ffi.new("uint8_t[]", secret)
    slt = _argon2_ffi.new("uint8_t[]", salt)
    ctx = _argon2_ffi.new("argon2_context *", dict(
        out=out, outlen=KEY_LEN,
        pwd=pwd, pwdlen=len(secret),
        salt=slt, saltlen=len(salt),
        secret=_argon2_ffi.NULL, secretlen=0,
        ad=_argon2_ffi.NULL, adlen=0,
        t_cost=time_cost, m_cost=memory_cost_kib,
        lanes=parallelism, threads=1,
        version=_argon2_lib.ARGON2_VERSION_NUMBER,
        allocate_cbk=_argon2_ffi.NULL, free_cbk=_argon2_ffi.NULL,
        flags=_argon2_lib.ARGON2_DEFAULT_FLAGS,
    ))
    rc = _argon2_core(ctx, _Argon2Type.ID.value)
    if rc != _argon2_lib.ARGON2_OK:
        raise _Argon2HashingError(_argon2_ffi.string(_argon2_lib.argon2_error_message(rc)).decode("ascii"))
    return bytes(_argon2_ffi.buffer(out, KEY_LEN))

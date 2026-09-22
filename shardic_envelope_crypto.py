"""
shardic_envelope_crypto.py

Pubkey-envelope primitives for shardic-envelope (see
docs/pubkey-envelope-plugin.md and docs/keycloak-credential-lookup.md --
those docs are the design rationale; this module is the first real code).
Purely additive: wraps/unwraps opaque byte payloads (a codeword, or a
recovered unsealed shard) to a recipient's X25519 public key. Never touches
gf256_sss_prime.py's split/reconstruct math or vault_core_prime.py's
KDF/shard logic -- those stay exactly as they are.

Construction: ephemeral X25519 ECDH + HKDF-SHA256 + AES-256-GCM (a
standard ECIES-style hybrid encryption), using the `cryptography` library
already required by kdf.py -- no new crypto dependency.

Two of these functions (serialize_unsealed_shard/deserialize_unsealed_shard)
aren't crypto at all -- they're the byte encoding for a
vault_core_prime.try_match_word_prime result (an "unsealed shard": the
prime trustee's mask, or a pool trustee's (x, y) point) so it can pass
through wrap()/unwrap() as an opaque payload. They
live here rather than being duplicated in both the combiner and trustee
demo apps, per the same "don't duplicate crypto-adjacent logic across
frontends" reasoning as the rest of this project's core modules.
"""

import base64
import os
import secrets

from cryptography.exceptions import InvalidTag
from cryptography.hazmat.primitives import hashes, serialization
from cryptography.hazmat.primitives.asymmetric.x25519 import X25519PrivateKey, X25519PublicKey
from cryptography.hazmat.primitives.ciphers.aead import AESGCM
from cryptography.hazmat.primitives.kdf.hkdf import HKDF

ALGORITHM_TAG = "x25519-hkdf-sha256-aes256gcm"
_HKDF_INFO = b"shardic-envelope-v1"
_NONCE_LEN = 12  # matches vault_core.NONCE_LEN's convention
_KEY_LEN = 32

UNSEALED_SHARD_KIND_PRIME = "prime"
UNSEALED_SHARD_KIND_POOL = "pool"


class EnvelopeError(Exception):
    """Raised on a malformed envelope, algorithm mismatch, or failed
    decryption (wrong key or tampered ciphertext)."""


def generate_keypair() -> tuple[bytes, bytes]:
    """Returns (private_key_raw_32B, public_key_raw_32B)."""
    private_key = X25519PrivateKey.generate()
    return _private_key_to_raw(private_key), _public_key_to_raw(private_key.public_key())


def public_key_from_private(private_key_raw: bytes) -> bytes:
    """Re-derive the public key from a stored private key."""
    private_key = X25519PrivateKey.from_private_bytes(private_key_raw)
    return _public_key_to_raw(private_key.public_key())


def load_or_create_keypair(key_dir: str) -> tuple[bytes, bytes]:
    """Reads {key_dir}/private.key + {key_dir}/public.key if both exist;
    otherwise generates a fresh keypair and persists it there (private
    key written with mode 0600). Used identically by the combiner and
    every trustee container against their own docker volume, so identity
    survives a container restart within a demo session."""
    os.makedirs(key_dir, exist_ok=True)
    priv_path = os.path.join(key_dir, "private.key")
    pub_path = os.path.join(key_dir, "public.key")

    if os.path.exists(priv_path) and os.path.exists(pub_path):
        with open(priv_path, "rb") as f:
            private_key_raw = f.read()
        with open(pub_path, "rb") as f:
            public_key_raw = f.read()
        return private_key_raw, public_key_raw

    private_key_raw, public_key_raw = generate_keypair()
    fd = os.open(priv_path, os.O_WRONLY | os.O_CREAT | os.O_TRUNC, 0o600)
    with os.fdopen(fd, "wb") as f:
        f.write(private_key_raw)
    with open(pub_path, "wb") as f:
        f.write(public_key_raw)
    return private_key_raw, public_key_raw


def fingerprint(public_key_raw: bytes) -> str:
    """SHA-256 of the raw public key, hex, grouped in 4-char blocks for
    display/log output. Not used for any programmatic trust decision in
    the demo -- purely a human-readable identity check."""
    digest = hashes.Hash(hashes.SHA256())
    digest.update(public_key_raw)
    hex_digest = digest.finalize().hex()
    return ":".join(hex_digest[i:i + 4] for i in range(0, len(hex_digest), 4))


def wrap(plaintext: bytes, recipient_public_key_raw: bytes) -> dict:
    """ECIES-style hybrid encrypt of `plaintext` to the recipient's
    X25519 public key. Returns a JSON-serializable dict:
      {"alg": ALGORITHM_TAG, "ephemeral_pub": b64, "nonce": b64, "ciphertext": b64}
    The ephemeral private key is used once and discarded."""
    recipient_public_key = X25519PublicKey.from_public_bytes(recipient_public_key_raw)
    ephemeral_private_key = X25519PrivateKey.generate()
    ephemeral_public_raw = _public_key_to_raw(ephemeral_private_key.public_key())

    shared_secret = ephemeral_private_key.exchange(recipient_public_key)
    aes_key = _derive_key(shared_secret)

    nonce = secrets.token_bytes(_NONCE_LEN)
    ciphertext = AESGCM(aes_key).encrypt(nonce, plaintext, associated_data=None)

    return {
        "alg": ALGORITHM_TAG,
        "ephemeral_pub": base64.b64encode(ephemeral_public_raw).decode("ascii"),
        "nonce": base64.b64encode(nonce).decode("ascii"),
        "ciphertext": base64.b64encode(ciphertext).decode("ascii"),
    }


def unwrap(envelope: dict, recipient_private_key_raw: bytes) -> bytes:
    """Inverse of wrap(). Raises EnvelopeError on algorithm mismatch,
    a malformed envelope, or failed decryption (wrong key / tampered
    envelope)."""
    if envelope.get("alg") != ALGORITHM_TAG:
        raise EnvelopeError(f"unsupported envelope algorithm: {envelope.get('alg')!r}")
    try:
        ephemeral_public_raw = base64.b64decode(envelope["ephemeral_pub"])
        nonce = base64.b64decode(envelope["nonce"])
        ciphertext = base64.b64decode(envelope["ciphertext"])
    except (KeyError, ValueError) as e:
        raise EnvelopeError(f"malformed envelope: {e}") from e

    recipient_private_key = X25519PrivateKey.from_private_bytes(recipient_private_key_raw)
    try:
        ephemeral_public_key = X25519PublicKey.from_public_bytes(ephemeral_public_raw)
    except ValueError as e:
        raise EnvelopeError(f"malformed ephemeral public key: {e}") from e

    shared_secret = recipient_private_key.exchange(ephemeral_public_key)
    aes_key = _derive_key(shared_secret)

    try:
        return AESGCM(aes_key).decrypt(nonce, ciphertext, associated_data=None)
    except InvalidTag as e:
        raise EnvelopeError("decryption failed -- wrong private key or tampered envelope") from e


def serialize_unsealed_shard(kind: str, value) -> bytes:
    """Encodes a vault_core_prime.try_match_word_prime() result as
    opaque bytes, so it can pass through wrap()/unwrap() without either
    container reimplementing matching/reconstruction logic.
      kind == "prime": b"P" + mask               (1 + 32 = 33 bytes)
      kind == "pool":  b"L" + bytes([x]) + y_bytes (1 + 1 + 32 = 34 bytes)
    """
    if kind == UNSEALED_SHARD_KIND_PRIME:
        return b"P" + value
    if kind == UNSEALED_SHARD_KIND_POOL:
        x, y_bytes = value
        return b"L" + bytes([x]) + y_bytes
    raise ValueError(f"unknown unsealed shard kind: {kind!r}")


def deserialize_unsealed_shard(data: bytes) -> tuple[str, object]:
    """Inverse of serialize_unsealed_shard()."""
    if not data:
        raise ValueError("empty unsealed shard payload")
    tag, rest = data[0:1], data[1:]
    if tag == b"P":
        return UNSEALED_SHARD_KIND_PRIME, rest
    if tag == b"L":
        if len(rest) < 1:
            raise ValueError("truncated pool unsealed shard payload")
        return UNSEALED_SHARD_KIND_POOL, (rest[0], rest[1:])
    raise ValueError(f"unknown unsealed shard tag: {tag!r}")


def _derive_key(shared_secret: bytes) -> bytes:
    return HKDF(algorithm=hashes.SHA256(), length=_KEY_LEN, salt=None, info=_HKDF_INFO).derive(shared_secret)


def _private_key_to_raw(private_key: X25519PrivateKey) -> bytes:
    return private_key.private_bytes(
        encoding=serialization.Encoding.Raw,
        format=serialization.PrivateFormat.Raw,
        encryption_algorithm=serialization.NoEncryption(),
    )


def _public_key_to_raw(public_key: X25519PublicKey) -> bytes:
    return public_key.public_bytes(encoding=serialization.Encoding.Raw, format=serialization.PublicFormat.Raw)


if __name__ == "__main__":
    # quick self-test
    import shutil
    import tempfile

    # wrap/unwrap round-trip
    recipient_priv, recipient_pub = generate_keypair()
    plaintext = b"correct-horse-battery-staple-codeword-demo"
    envelope = wrap(plaintext, recipient_pub)
    assert unwrap(envelope, recipient_priv) == plaintext

    # wrong private key must fail, not silently return garbage
    wrong_priv, _ = generate_keypair()
    try:
        unwrap(envelope, wrong_priv)
        raise AssertionError("unwrap with the wrong private key should have raised EnvelopeError")
    except EnvelopeError:
        pass

    # tampered ciphertext must fail
    tampered = dict(envelope)
    tampered_bytes = bytearray(base64.b64decode(tampered["ciphertext"]))
    tampered_bytes[0] ^= 0xFF
    tampered["ciphertext"] = base64.b64encode(bytes(tampered_bytes)).decode("ascii")
    try:
        unwrap(tampered, recipient_priv)
        raise AssertionError("unwrap of tampered ciphertext should have raised EnvelopeError")
    except EnvelopeError:
        pass

    # unsealed shard serialization round-trip: prime
    mask = secrets.token_bytes(32)
    encoded = serialize_unsealed_shard("prime", mask)
    assert deserialize_unsealed_shard(encoded) == ("prime", mask)

    # unsealed shard serialization round-trip: pool
    y_bytes = secrets.token_bytes(32)
    encoded = serialize_unsealed_shard("pool", (7, y_bytes))
    kind, value = deserialize_unsealed_shard(encoded)
    assert kind == "pool" and value == (7, y_bytes)

    # load_or_create_keypair persists across calls
    tmp_dir = tempfile.mkdtemp()
    try:
        priv1, pub1 = load_or_create_keypair(tmp_dir)
        priv2, pub2 = load_or_create_keypair(tmp_dir)
        assert (priv1, pub1) == (priv2, pub2)
        assert public_key_from_private(priv1) == pub1
    finally:
        shutil.rmtree(tmp_dir)

    # fingerprint is deterministic and differs across keys
    _, other_pub = generate_keypair()
    assert fingerprint(recipient_pub) == fingerprint(recipient_pub)
    assert fingerprint(recipient_pub) != fingerprint(other_pub)

    print("shardic_envelope_crypto self-test passed")

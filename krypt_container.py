"""
krypt_container.py

Defines the single-file .krypt container: metadata and ciphertext
bundled together so a vault is one file to copy/email/upload, instead
of a ciphertext file plus a separate metadata.json that have to travel
together and never get separated.

Layout (all integers big-endian):

    +----------------+---------------------------------------------+
    | 8 bytes        | magic: b"KRYPTv1\n"                          |
    | 4 bytes        | metadata length, uint32                     |
    | N bytes        | metadata, UTF-8 JSON                        |
    | remaining bytes| raw AES-256-GCM ciphertext of the archive    |
    +----------------+---------------------------------------------+

The ciphertext is stored raw (not base64-wrapped inside the JSON) so
the file doesn't pay a ~33% size penalty for embedding it as text.
Metadata stays JSON because it's small and benefits from being easy
to inspect (`head -c 2000 file.krypt` is readable).
"""

import json
import struct

MAGIC = b"KRYPTv1\n"
_LEN_STRUCT = struct.Struct(">I")  # unsigned 32-bit big-endian


def write_krypt(path: str, metadata: dict, ciphertext: bytes) -> None:
    meta_bytes = json.dumps(metadata).encode("utf-8")
    if len(meta_bytes) > 0xFFFFFFFF:
        raise ValueError("metadata too large for container format")
    with open(path, "wb") as f:
        f.write(MAGIC)
        f.write(_LEN_STRUCT.pack(len(meta_bytes)))
        f.write(meta_bytes)
        f.write(ciphertext)


def read_krypt(path: str):
    """Returns (metadata: dict, ciphertext: bytes)."""
    with open(path, "rb") as f:
        magic = f.read(len(MAGIC))
        if magic != MAGIC:
            raise ValueError(
                f"'{path}' doesn't look like a .krypt file (bad magic header). "
                "Was it truncated or corrupted in transit?"
            )
        len_bytes = f.read(_LEN_STRUCT.size)
        if len(len_bytes) != _LEN_STRUCT.size:
            raise ValueError(f"'{path}' is truncated (missing metadata length field)")
        (meta_len,) = _LEN_STRUCT.unpack(len_bytes)
        meta_bytes = f.read(meta_len)
        if len(meta_bytes) != meta_len:
            raise ValueError(f"'{path}' is truncated (metadata block cut short)")
        try:
            metadata = json.loads(meta_bytes.decode("utf-8"))
        except json.JSONDecodeError as e:
            raise ValueError(f"'{path}' has corrupted metadata JSON: {e}") from e
        ciphertext = f.read()
    if not ciphertext:
        raise ValueError(f"'{path}' has no ciphertext after the metadata block")
    return metadata, ciphertext

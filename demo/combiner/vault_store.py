"""
vault_store.py -- pluggable storage for the combiner's .krypt bytes.

Implements the `VaultStore` interface sketched in
docs/vault-storage-backend.md: a filesystem-backed reference
implementation, keyed by an opaque vault_id, with a store()-must-not-
overwrite guarantee mirroring EnvelopeDropPoint.deposit()'s own
non-overwrite semantics (docs/envelope-delivery.md).

This is the only backend v1.0 ships. SQL/NoSQL support is a
config-selected alternate implementation of the same interface, added
later as a fast-follow -- not bundled or operated by shardic itself.
See docs/vault-storage-backend.md for why.
"""

import os
from typing import Protocol


class VaultStoreError(Exception):
    """Base class for VaultStore errors."""


class VaultAlreadyExistsError(VaultStoreError):
    """Raised by store() when vault_id already has a live record."""


class VaultNotFoundError(VaultStoreError):
    """Raised by retrieve() when vault_id has no stored record."""


class VaultStore(Protocol):
    def store(self, vault_id: str, krypt_bytes: bytes) -> None:
        """Persist a .krypt container's raw bytes, keyed by vault_id.
        Raises VaultAlreadyExistsError if a live record already exists
        for vault_id -- storage must not silently overwrite an
        existing vault."""
        ...

    def retrieve(self, vault_id: str) -> bytes:
        """Return the stored .krypt bytes for vault_id. Raises
        VaultNotFoundError if none exist."""
        ...


class FilesystemVaultStore:
    """Reference VaultStore implementation: one file per vault_id,
    named "{vault_id}.krypt", under base_dir."""

    def __init__(self, base_dir: str):
        self._base_dir = base_dir

    def _path(self, vault_id: str) -> str:
        return os.path.join(self._base_dir, f"{vault_id}.krypt")

    def store(self, vault_id: str, krypt_bytes: bytes) -> None:
        os.makedirs(self._base_dir, exist_ok=True)
        path = self._path(vault_id)
        if os.path.exists(path):
            raise VaultAlreadyExistsError(f"a vault already exists for vault_id {vault_id!r}")
        # Write-to-temp-then-rename so a crash mid-write can never leave
        # a partially-written file at the real path.
        tmp_path = path + ".tmp"
        with open(tmp_path, "wb") as f:
            f.write(krypt_bytes)
            f.flush()
            os.fsync(f.fileno())
        os.replace(tmp_path, path)

    def retrieve(self, vault_id: str) -> bytes:
        path = self._path(vault_id)
        if not os.path.exists(path):
            raise VaultNotFoundError(f"no vault stored for vault_id {vault_id!r}")
        with open(path, "rb") as f:
            return f.read()


if __name__ == "__main__":
    import shutil
    import tempfile

    tmp_dir = tempfile.mkdtemp(prefix="vault_store_selftest_")
    try:
        store = FilesystemVaultStore(tmp_dir)
        vault_id = "11111111-1111-1111-1111-111111111111"
        payload = b"pretend .krypt bytes"

        store.store(vault_id, payload)
        assert store.retrieve(vault_id) == payload
        print("store/retrieve round-trip: OK")

        try:
            store.store(vault_id, b"different bytes")
        except VaultAlreadyExistsError:
            print("store() rejects overwrite of an existing vault_id: OK")
        else:
            raise AssertionError("store() silently overwrote an existing vault_id")

        try:
            store.retrieve("no-such-vault-id")
        except VaultNotFoundError:
            print("retrieve() raises for an unknown vault_id: OK")
        else:
            raise AssertionError("retrieve() did not raise for an unknown vault_id")

        print("All vault_store.py self-tests passed.")
    finally:
        shutil.rmtree(tmp_dir)

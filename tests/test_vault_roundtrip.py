"""Create -> recover round trips for plain and prime .krypt vaults, plus
corruption handling. Small Argon2id parameters keep it fast; the
cross-path test creates with threads and recovers on one thread, as a
browser (Pyodide) recovering a CLI-made vault would."""
import filecmp
import os
import secrets

import pytest

import kdf
import krypt_container
import vault_core
import vault_core_prime

FAST = {"time_cost": 1, "memory_cost_kib": 8192, "parallelism": 1}
FAST_P4 = {"time_cost": 1, "memory_cost_kib": 8192, "parallelism": 4}


def _input(tmp_path):
    src = tmp_path / "input"
    (src / "sub").mkdir(parents=True)
    (src / "a.bin").write_bytes(secrets.token_bytes(3000))
    (src / "sub" / "b.txt").write_text("shardic\n")
    return src


def _same_tree(a, b):
    def ok(c):
        if c.left_only or c.right_only or c.diff_files or c.funny_files:
            return False
        if not all(filecmp.cmp(os.path.join(c.left, n), os.path.join(c.right, n), shallow=False)
                   for n in c.common_files):
            return False
        return all(ok(s) for s in c.subdirs.values())
    return ok(filecmp.dircmp(a, b))


def _create_plain(tmp_path, params=FAST, trustees=4, threshold=3):
    src = _input(tmp_path)
    res = vault_core.create_vault(str(src), trustees, threshold, word_length=None, word_count=4,
                                  outdir=str(tmp_path / "out"), kdf_method="argon2id", kdf_params=params)
    words = [open(p).read().strip() for p in res["trustee_files"]]
    return src, res["krypt_path"], words


def test_plain_roundtrip_any_d(tmp_path):
    src, krypt, words = _create_plain(tmp_path)
    meta, ct = krypt_container.read_krypt(krypt)
    shards, unmatched = vault_core.match_codewords(words[1:], meta)
    assert unmatched == []
    vault_core.reconstruct_and_decrypt(meta, ct, shards, outdir=str(tmp_path / "rec"))
    assert _same_tree(src, tmp_path / "rec" / "input")


def test_plain_d_minus_1_refused(tmp_path):
    _, krypt, words = _create_plain(tmp_path)
    meta, ct = krypt_container.read_krypt(krypt)
    shards, _ = vault_core.match_codewords(words[:2], meta)
    with pytest.raises(vault_core.VaultError, match="Only 2 of the required 3"):
        vault_core.reconstruct_and_decrypt(meta, ct, shards, outdir=str(tmp_path / "rec"))
    assert not (tmp_path / "rec").exists()


@pytest.mark.skipif(kdf.ARGON2_THREADS_AVAILABLE is False, reason="needs the threaded path to create")
def test_threaded_create_single_thread_recover(tmp_path, monkeypatch):
    src, krypt, words = _create_plain(tmp_path, params=FAST_P4)
    monkeypatch.setattr(kdf, "ARGON2_THREADS_AVAILABLE", False)
    meta, ct = krypt_container.read_krypt(krypt)
    shards, unmatched = vault_core.match_codewords(words[:3], meta)
    assert unmatched == []
    vault_core.reconstruct_and_decrypt(meta, ct, shards, outdir=str(tmp_path / "rec"))
    assert _same_tree(src, tmp_path / "rec" / "input")


def test_wrong_codeword_does_not_match(tmp_path):
    _, krypt, words = _create_plain(tmp_path)
    meta, _ = krypt_container.read_krypt(krypt)
    _, unmatched = vault_core.match_codewords([words[0], "not a real codeword"], meta)
    assert unmatched == [1]


def test_ciphertext_tamper_detected(tmp_path):
    _, krypt, words = _create_plain(tmp_path)
    meta, ct = krypt_container.read_krypt(krypt)
    bad = bytearray(ct)
    bad[len(bad) // 2] ^= 0x01
    shards, _ = vault_core.match_codewords(words[:3], meta)
    with pytest.raises(vault_core.VaultError, match="failed authentication"):
        vault_core.reconstruct_and_decrypt(meta, bytes(bad), shards, outdir=str(tmp_path / "rec"))
    assert not (tmp_path / "rec").exists()


def test_shard_record_tamper_unmatches_only_that_codeword(tmp_path):
    _, krypt, words = _create_plain(tmp_path)
    meta, _ = krypt_container.read_krypt(krypt)
    import base64
    for rec in meta["shards"]:
        raw = bytearray(base64.b64decode(rec["ciphertext"]))
        raw[0] ^= 0x01
        rec["ciphertext"] = base64.b64encode(bytes(raw)).decode()
    shards, unmatched = vault_core.match_codewords(words, meta)
    assert shards == [] and unmatched == [0, 1, 2, 3]


def test_metadata_records_no_trustee_mapping(tmp_path):
    """Invariant: shard records carry only salt/nonce/ciphertext, nothing naming a trustee."""
    _, krypt, _ = _create_plain(tmp_path)
    meta, _ = krypt_container.read_krypt(krypt)
    for rec in meta["shards"]:
        assert set(rec) == {"salt", "nonce", "ciphertext"}


def test_prime_roundtrip_and_prime_required(tmp_path):
    src = _input(tmp_path)
    res = vault_core_prime.create_vault_prime(str(src), 5, 3, word_length=None, word_count=4,
                                              outdir=str(tmp_path / "out"),
                                              kdf_method="argon2id", kdf_params=FAST)
    words = [c["codeword"] for c in res["credentials"]]  # prime first
    meta, ct = krypt_container.read_krypt(res["krypt_path"])

    mask, pool, unmatched = vault_core_prime.match_codewords_prime([words[0], words[2], words[4]], meta)
    assert unmatched == []
    vault_core_prime.reconstruct_and_decrypt_prime(meta, ct, mask, pool, outdir=str(tmp_path / "rec"))
    assert _same_tree(src, tmp_path / "rec" / "input")

    mask2, pool2, _ = vault_core_prime.match_codewords_prime(words[1:], meta)
    assert mask2 is None
    with pytest.raises(vault_core.VaultError, match="prime trustee"):
        vault_core_prime.reconstruct_and_decrypt_prime(meta, ct, mask2, pool2, outdir=str(tmp_path / "rec2"))

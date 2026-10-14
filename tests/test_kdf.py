"""kdf.py: known-answer tests for both Argon2id paths and PBKDF2.

The Argon2id vectors were produced by argon2-cffi's threaded
hash_secret_raw and independently confirmed with hash-wasm 4.12.0 (a
separate Argon2 implementation), except `empty_p3`, which hash-wasm
refuses (empty password); that one is checked against argon2-cffi only.
Salt for every vector: bytes(range(16)).
"""
import secrets
import sys

import pytest
from argon2.exceptions import HashingError

import kdf

SALT = bytes(range(16))
IN_PYODIDE = sys.platform == "emscripten"

ARGON2ID_KAT = {
    # name: (passphrase, time_cost, memory_cost_kib, parallelism, key hex)
    "default": ("correct horse battery staple", 4, 262144, 4,
                "a45342f708de9426cdad16317518e6cc4c0f05b9c57615f5e9eb1d00a8e85357"),
    "small_p4": ("correct horse battery staple", 3, 32768, 4,
                 "ee2dfb135998b02926082487668738142ee9525c4864b1178b474976ed30033a"),
    "p1": ("shardic", 2, 16384, 1,
           "1a86914ec48d6b6aa556048ba7e628697f794d5b56be60c2b1a34f99e1b9f444"),
    "unicode_p2": ("ünïcödé 🔑", 2, 16384, 2,
                   "d464619858c951f0ff8434086fc9977e94c66c36f7f289ba9b43a18e1ac6ba58"),
    "empty_p3": ("", 1, 8192, 3,
                 "6e23dc9bf252fa706630ca93e29674386bff41691ab3223a619925e9c2ca8660"),
}

PBKDF2_KAT = ("correct horse battery staple", 400_000,
              "d91e3759b6fcb4df9c277c789ab319e9543d0c028ae55e7b784ecbe2149c34eb")


@pytest.fixture(params=[True, False], ids=["threaded", "single-thread"])
def argon2_path(request, monkeypatch):
    """Run a test under both Argon2id paths; single-thread is what Pyodide uses."""
    if request.param and IN_PYODIDE:
        pytest.skip("no threads under Pyodide")
    monkeypatch.setattr(kdf, "ARGON2_THREADS_AVAILABLE", request.param)
    return request.param


def test_threads_flag_matches_platform():
    assert kdf.ARGON2_THREADS_AVAILABLE is (not IN_PYODIDE)


@pytest.mark.parametrize("name", ARGON2ID_KAT)
def test_argon2id_known_answers(name, argon2_path):
    pw, t, m, p, expected = ARGON2ID_KAT[name]
    params = {"time_cost": t, "memory_cost_kib": m, "parallelism": p}
    assert kdf.derive_key("argon2id", params, pw, SALT).hex() == expected


def test_default_params_match_default_kat():
    """The 'default' vector really is the project's default Argon2id parameters."""
    pw, t, m, p, _ = ARGON2ID_KAT["default"]
    assert kdf.default_params("argon2id") == {"time_cost": t, "memory_cost_kib": m, "parallelism": p}


@pytest.mark.skipif(IN_PYODIDE, reason="no threaded path to compare against under Pyodide")
@pytest.mark.parametrize("parallelism", [1, 2, 3, 4, 7, 8])
def test_single_thread_equals_threaded_random(parallelism, monkeypatch):
    params = {"time_cost": 2, "memory_cost_kib": 8 * parallelism * 4, "parallelism": parallelism}
    for _ in range(3):
        pw = secrets.token_urlsafe(12)
        salt = secrets.token_bytes(16)
        monkeypatch.setattr(kdf, "ARGON2_THREADS_AVAILABLE", True)
        threaded = kdf.derive_key("argon2id", params, pw, salt)
        monkeypatch.setattr(kdf, "ARGON2_THREADS_AVAILABLE", False)
        assert kdf.derive_key("argon2id", params, pw, salt) == threaded


def test_pbkdf2_known_answer():
    pw, iterations, expected = PBKDF2_KAT
    assert kdf.derive_key("pbkdf2", {"iterations": iterations}, pw, SALT).hex() == expected


def test_short_salt_rejected(argon2_path):
    with pytest.raises(ValueError, match="salt too short"):
        kdf.derive_key("argon2id", kdf.default_params("argon2id"), "pw", b"1234567")


def test_invalid_params_raise_hashing_error(argon2_path):
    # Argon2 requires at least 8 KiB per lane.
    bad = {"time_cost": 1, "memory_cost_kib": 8, "parallelism": 4}
    with pytest.raises(HashingError):
        kdf.derive_key("argon2id", bad, "pw", SALT)


def test_unknown_method_rejected():
    with pytest.raises(ValueError, match="Unknown KDF method"):
        kdf.derive_key("scrypt", {}, "pw", SALT)

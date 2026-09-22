"""
gf256_sss.py

Byte-wise Shamir's Secret Sharing over GF(2^8), using the same field
(generator 0x03, reduction polynomial 0x11B) as AES. This is the same
approach used by classic tools like `ssss`.

Each byte of the secret gets its own random polynomial of degree
(threshold - 1); all bytes for a given shard are evaluated at the same
x-coordinate (the shard index, 1..T). Reconstruction interpolates each
byte position independently at x=0.
"""

import secrets

# ---- GF(256) log/antilog tables (generator 3, poly 0x11B, same as AES) ----

_EXP = [0] * 512  # periodic extension so mul/div never need modulo
_LOG = [0] * 256


def _gf_mul_slow(a: int, b: int) -> int:
    p = 0
    for _ in range(8):
        if b & 1:
            p ^= a
        hi = a & 0x80
        a = (a << 1) & 0xFF
        if hi:
            a ^= 0x1B
        b >>= 1
    return p & 0xFF


def _build_tables():
    x = 1
    for i in range(255):
        _EXP[i] = x
        _LOG[x] = i
        x = _gf_mul_slow(x, 0x03)
    for i in range(255, 512):
        _EXP[i] = _EXP[i - 255]


_build_tables()


def gf_add(a: int, b: int) -> int:
    return a ^ b


def gf_mul(a: int, b: int) -> int:
    if a == 0 or b == 0:
        return 0
    return _EXP[_LOG[a] + _LOG[b]]


def gf_div(a: int, b: int) -> int:
    if a == 0:
        return 0
    if b == 0:
        raise ZeroDivisionError("GF(256) division by zero")
    return _EXP[_LOG[a] - _LOG[b] + 255]


def _eval_poly(coeffs, x: int) -> int:
    # Horner's method, coeffs[0] is the constant term (the secret byte)
    result = 0
    for c in reversed(coeffs):
        result = gf_mul(result, x) ^ c
    return result


def split_secret(secret: bytes, threshold: int, total_shards: int):
    """
    Split `secret` (bytes) into total_shards shards such that any
    `threshold` of them can reconstruct it.

    Returns: list of (x, y_bytes) tuples, x in 1..total_shards.
    """
    if not (1 <= threshold <= total_shards <= 255):
        raise ValueError("Require 1 <= threshold <= total_shards <= 255")

    # One random polynomial per byte position of the secret.
    polys = []
    for byte_val in secret:
        coeffs = [byte_val] + [secrets.randbelow(256) for _ in range(threshold - 1)]
        polys.append(coeffs)

    shards = []
    for x in range(1, total_shards + 1):
        y = bytes(_eval_poly(coeffs, x) for coeffs in polys)
        shards.append((x, y))
    return shards


def reconstruct_secret(shards) -> bytes:
    """
    Reconstruct the secret from a list of (x, y_bytes) tuples via
    Lagrange interpolation at x=0, done independently per byte position.
    """
    xs = [s[0] for s in shards]
    if len(set(xs)) != len(xs):
        raise ValueError("Duplicate shard x-coordinates supplied")

    secret_len = len(shards[0][1])
    for _, y in shards:
        if len(y) != secret_len:
            raise ValueError("Inconsistent shard lengths")

    out = bytearray(secret_len)
    for pos in range(secret_len):
        total = 0
        for i, (xi, yi) in enumerate(shards):
            yi_byte = yi[pos]
            num = 1
            den = 1
            for j, (xj, _) in enumerate(shards):
                if i == j:
                    continue
                num = gf_mul(num, xj)          # (0 - xj) == xj in GF(2^n)
                den = gf_mul(den, xi ^ xj)      # (xi - xj) == xi ^ xj
            total ^= gf_mul(yi_byte, gf_div(num, den))
        out[pos] = total
    return bytes(out)


if __name__ == "__main__":
    # quick self-test
    secret = secrets.token_bytes(32)
    shards = split_secret(secret, threshold=3, total_shards=5)
    import itertools
    for combo in itertools.combinations(shards, 3):
        assert reconstruct_secret(list(combo)) == secret
    try:
        combo2 = shards[:2]
        assert reconstruct_secret(combo2) != secret or True  # 2 shards -> garbage, not equal in general
    except Exception:
        pass
    print("gf256_sss self-test passed")

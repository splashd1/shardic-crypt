"""
gf256_sss_prime.py

"shardic-prime" variant of the Shamir split: exactly one trustee (the
PRIME trustee) must always be present at recovery time, in addition to
any `pool_threshold`-sized subset of the remaining, fully
interchangeable pool trustees. Built entirely on top of the existing
byte-wise GF(256) SSS in gf256_sss.py -- no new field math.

Construction (a one-time-pad mask layered over an ordinary Shamir
split):

    mask          = random bytes, same length as the secret
    masked_secret = secret XOR mask
    pool_shards   = split_secret(masked_secret, pool_threshold, pool_size)

The prime trustee's codeword protects `mask` directly -- there's no
polynomial for the prime slot, it's an all-or-nothing pad. Recovery
needs `mask` AND any `pool_threshold` of the pool shards:

    masked_secret = reconstruct_secret(pool_shards)
    secret        = masked_secret XOR mask

Without `mask`, no amount of pool shards (even all of them) reveals
anything about `secret` -- `masked_secret` is uniformly random without
it. Without at least `pool_threshold` pool shards, `mask` alone
reveals nothing either. That's what makes the prime trustee essential
while leaving the pool a plain interchangeable k-of-n, with the same
information-theoretic guarantee as the base scheme on each side of the
layering.
"""

import secrets

from gf256_sss import split_secret, reconstruct_secret


def split_secret_with_prime(secret: bytes, pool_threshold: int, pool_size: int):
    """
    Returns (mask, pool_shards):
      mask        -- bytes, same length as secret; goes to the prime trustee.
      pool_shards -- list of (x, y_bytes) tuples as returned by
                     gf256_sss.split_secret; any pool_threshold of
                     these, together with mask, reconstruct `secret`.
    """
    if pool_threshold < 1:
        raise ValueError(
            "pool_threshold must be >= 1 (with no pool required, this is "
            "just single-key encryption -- use gf256_sss.split_secret directly)"
        )
    mask = secrets.token_bytes(len(secret))
    masked_secret = bytes(a ^ b for a, b in zip(secret, mask))
    pool_shards = split_secret(masked_secret, threshold=pool_threshold, total_shards=pool_size)
    return mask, pool_shards


def reconstruct_secret_with_prime(mask: bytes, pool_shards) -> bytes:
    """Inverse of split_secret_with_prime. `pool_shards` must contain
    at least pool_threshold consistent (x, y_bytes) tuples."""
    masked_secret = reconstruct_secret(pool_shards)
    if len(masked_secret) != len(mask):
        raise ValueError("mask/pool shard length mismatch")
    return bytes(a ^ b for a, b in zip(masked_secret, mask))


if __name__ == "__main__":
    # quick self-test
    import itertools

    secret = secrets.token_bytes(32)
    mask, pool_shards = split_secret_with_prime(secret, pool_threshold=3, pool_size=5)

    for combo in itertools.combinations(pool_shards, 3):
        assert reconstruct_secret_with_prime(mask, list(combo)) == secret

    # Below pool_threshold, or without the mask at all, reconstruction
    # must not silently succeed with the right answer.
    short_combo = pool_shards[:2]
    assert reconstruct_secret_with_prime(mask, short_combo) != secret

    print("gf256_sss_prime self-test passed")

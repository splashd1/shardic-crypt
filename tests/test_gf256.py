"""GF(256) Shamir: any D of T reconstructs; D-1 does not."""
import itertools
import secrets

import pytest

from gf256_sss import reconstruct_secret, split_secret
from gf256_sss_prime import reconstruct_secret_with_prime, split_secret_with_prime

CASES = [(2, 2), (2, 3), (3, 5), (4, 6), (5, 7), (5, 20)]


@pytest.mark.parametrize("threshold,total", CASES)
def test_any_d_of_t_reconstructs(threshold, total):
    secret = secrets.token_bytes(32)
    shards = split_secret(secret, threshold=threshold, total_shards=total)
    assert len(shards) == total
    combos = list(itertools.combinations(shards, threshold))
    for combo in combos[:200]:
        assert reconstruct_secret(list(combo)) == secret


@pytest.mark.parametrize("threshold,total", CASES)
def test_d_minus_1_does_not_reconstruct(threshold, total):
    secret = secrets.token_bytes(32)
    shards = split_secret(secret, threshold=threshold, total_shards=total)
    for combo in list(itertools.combinations(shards, threshold - 1))[:200]:
        assert reconstruct_secret(list(combo)) != secret


def test_more_than_d_also_reconstructs():
    secret = secrets.token_bytes(32)
    shards = split_secret(secret, threshold=3, total_shards=6)
    assert reconstruct_secret(shards) == secret


@pytest.mark.parametrize("pool_threshold,pool_size", [(1, 1), (1, 3), (2, 4), (4, 19)])
def test_prime_plus_any_pool_threshold_reconstructs(pool_threshold, pool_size):
    secret = secrets.token_bytes(32)
    mask, pool = split_secret_with_prime(secret, pool_threshold=pool_threshold, pool_size=pool_size)
    for combo in list(itertools.combinations(pool, pool_threshold))[:200]:
        assert reconstruct_secret_with_prime(mask, list(combo)) == secret


def test_pool_without_prime_does_not_reconstruct():
    secret = secrets.token_bytes(32)
    mask, pool = split_secret_with_prime(secret, pool_threshold=2, pool_size=4)
    # All pool shards, no mask: plain Shamir reconstruction gives the masked value, not the secret.
    assert reconstruct_secret(pool) != secret
    assert mask != secret

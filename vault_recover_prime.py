#!/usr/bin/env python3
"""
vault_recover_prime.py

shardic-prime variant of vault_recover.py. Given a .krypt file created
by vault_create_prime.py, the prime trustee's codeword, and >=
pool_threshold pool codewords, reconstructs the DEK and decrypts the
archive. See vault_core_prime.py for the construction.

Codewords can be entered in any order -- this program doesn't need to
be told in advance which one is the prime trustee's. Each codeword is
tried against every unmatched shard record the same way
vault_recover.py does it; the type-tagged payload says whether it
turned out to be the prime shard or a pool shard only once it
successfully decrypts.

Usage:
  python3 vault_recover_prime.py VAULT.krypt [--outdir DIR]
  python3 vault_recover_prime.py --vault-dir DIR [--outdir DIR]

If codewords aren't passed via --word (repeatable), you'll be prompted
interactively until the prime codeword plus enough pool codewords are
recovered.
"""

import argparse
import getpass
import glob
import importlib.util
import os
import sys

if importlib.util.find_spec("cryptography") is None:
    sys.exit(
        "error: this program requires the 'cryptography' package, which isn't "
        "installed here.\n"
        "  Run: pip install cryptography\n"
        "then try again."
    )

import krypt_container
import vault_core_prime


def load_from_vault_dir(vault_dir: str):
    krypt_candidates = sorted(glob.glob(os.path.join(vault_dir, "*.krypt")))
    if not krypt_candidates:
        sys.exit(f"error: no .krypt file found in {vault_dir}")
    if len(krypt_candidates) > 1:
        print(f"[i] Multiple .krypt files found in {vault_dir}; using {krypt_candidates[0]}")
    return krypt_container.read_krypt(krypt_candidates[0])


def load_source(args):
    """Resolve (metadata, ciphertext) from whichever input args were given."""
    if args.krypt_file:
        if not os.path.exists(args.krypt_file):
            sys.exit(f"error: .krypt file not found: {args.krypt_file}")
        return krypt_container.read_krypt(args.krypt_file)

    if args.input:
        if os.path.isdir(args.input):
            return load_from_vault_dir(args.input)
        if args.input.endswith(".krypt"):
            if not os.path.exists(args.input):
                sys.exit(f"error: .krypt file not found: {args.input}")
            return krypt_container.read_krypt(args.input)
        sys.exit(
            f"error: don't know how to read '{args.input}' -- expected a "
            ".krypt file or a vault directory."
        )

    if args.vault_dir:
        return load_from_vault_dir(args.vault_dir)

    sys.exit(
        "error: supply a .krypt file (positional argument or --krypt-file), "
        "or a --vault-dir."
    )


def main():
    ap = argparse.ArgumentParser(
        description="Recover and decrypt a shardic-prime vault (1 mandatory prime codeword + D-1 pool codewords)."
    )
    ap.add_argument("input", nargs="?", default=None, help="A .krypt file, or a vault directory")
    ap.add_argument("--krypt-file", default=None, help="Explicit path to a .krypt container")
    ap.add_argument("--vault-dir", default=None, help="Directory containing a .krypt file")
    ap.add_argument("--word", action="append", default=[], help="A codeword phrase. Repeatable. If omitted, you'll be prompted.")
    ap.add_argument("--outdir", default=None, help="Directory to extract the recovered archive into")
    args = ap.parse_args()

    metadata, ciphertext = load_source(args)
    if metadata.get("scheme") != "prime-trustee":
        sys.exit(
            "error: this .krypt file wasn't created by vault_create_prime.py "
            f"(scheme={metadata.get('scheme')!r}). Use vault_recover.py instead."
        )

    try:
        kdf_method, kdf_params = vault_core_prime.resolve_kdf(metadata)
    except vault_core_prime.VaultError as e:
        sys.exit(f"error: {e}")

    threshold = metadata["threshold"]
    pool_threshold = metadata["pool_threshold"]
    shard_records = metadata.get("shards", metadata.get("shares"))

    print(
        f"[i] This vault requires the prime trustee's codeword plus "
        f"{pool_threshold} of {metadata['pool_size']} pool codewords "
        f"({threshold} total, of {metadata['trustees_total']} trustees)."
    )
    print(f"[i] Shard protection KDF: {kdf_method}")

    mask = None
    pool_shards = []
    used_indices = set()

    codewords_queue = list(args.word)
    while mask is None or len(pool_shards) < pool_threshold:
        total_have = (1 if mask is not None else 0) + len(pool_shards)
        if codewords_queue:
            word = codewords_queue.pop(0)
        else:
            word = getpass.getpass(
                f"Enter codeword {total_have + 1}/{threshold}: "
            ).strip()
            if not word:
                print("  (empty input, try again)")
                continue

        match = vault_core_prime.try_match_word_prime(word, shard_records, kdf_method, kdf_params, used_indices)
        if match is None:
            print("  [-] That codeword doesn't match any remaining shard. Try again.")
            continue

        idx, kind, value = match
        used_indices.add(idx)
        if kind == "prime":
            mask = value
            print("  [+] Prime trustee's codeword accepted.")
        else:
            pool_shards.append(value)
            print(f"  [+] Pool codeword accepted ({len(pool_shards)}/{pool_threshold}).")

    try:
        vault_core_prime.reconstruct_and_decrypt_prime(
            metadata, ciphertext, mask, pool_shards, outdir=args.outdir,
            log=lambda msg: print(f"[*] {msg}"),
        )
    except vault_core_prime.VaultError as e:
        sys.exit(f"error: {e}")


if __name__ == "__main__":
    main()

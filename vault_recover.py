#!/usr/bin/env python3
"""
vault_recover.py

Given a .krypt file and >= threshold codewords, reconstructs the DEK
via Shamir interpolation and decrypts the archive.

How a codeword finds "its" shard (the indexing mechanism):
  The container's metadata stores, per shard, only an opaque
  (salt, nonce, ciphertext) tuple -- nothing says which trustee or
  word it belongs to. For each codeword entered, this program tries
  deriving a key against every not-yet-matched shard record and
  attempts an AES-GCM decrypt. AES-GCM's authentication tag means
  only the correct (codeword, shard record) pairing succeeds; every
  wrong pairing fails loudly and cheaply. With T typically in the
  tens, this brute trial is effectively instant, and it means the
  metadata itself reveals no assignment information even if it leaks.

This is a thin CLI wrapper around vault_core; the same core functions
are used by vault_gui.py, so both frontends share one implementation
of the actual crypto.

Usage:
  python3 vault_recover.py VAULT.krypt [--outdir DIR]
  python3 vault_recover.py --vault-dir DIR [--outdir DIR]
  python3 vault_recover.py --crypt-file X.crypt --metadata metadata.json [--outdir DIR]   # legacy split-file vaults

If codewords aren't passed via --word (repeatable), you'll be
prompted interactively until enough valid, distinct shards are
recovered.
"""

import argparse
import getpass
import glob
import importlib.util
import json
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
import vault_core


def load_from_vault_dir(vault_dir: str):
    """A vault dir may hold a new-style .krypt container, or an old-style
    metadata.json + <name>.crypt pair. Prefer the former if both exist."""
    krypt_candidates = sorted(glob.glob(os.path.join(vault_dir, "*.krypt")))
    if krypt_candidates:
        if len(krypt_candidates) > 1:
            print(f"[i] Multiple .krypt files found in {vault_dir}; using {krypt_candidates[0]}")
        return krypt_container.read_krypt(krypt_candidates[0])

    metadata_path = os.path.join(vault_dir, "metadata.json")
    if not os.path.exists(metadata_path):
        sys.exit(f"error: no .krypt file or metadata.json found in {vault_dir}")
    with open(metadata_path) as f:
        metadata = json.load(f)
    crypt_path = os.path.join(vault_dir, metadata["crypt_file"])
    if not os.path.exists(crypt_path):
        sys.exit(f"error: metadata.json refers to missing ciphertext file: {crypt_path}")
    with open(crypt_path, "rb") as f:
        ciphertext = f.read()
    return metadata, ciphertext


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

    if args.crypt_file and args.metadata:
        if not os.path.exists(args.crypt_file):
            sys.exit(f"error: crypt file not found: {args.crypt_file}")
        if not os.path.exists(args.metadata):
            sys.exit(f"error: metadata file not found: {args.metadata}")
        with open(args.metadata) as f:
            metadata = json.load(f)
        with open(args.crypt_file, "rb") as f:
            ciphertext = f.read()
        return metadata, ciphertext

    sys.exit(
        "error: supply a .krypt file (positional argument or --krypt-file), "
        "a --vault-dir, or a legacy --crypt-file + --metadata pair."
    )


def main():
    ap = argparse.ArgumentParser(description="Recover and decrypt a vault from D codewords.")
    ap.add_argument("input", nargs="?", default=None, help="A .krypt file, or a vault directory")
    ap.add_argument("--krypt-file", default=None, help="Explicit path to a .krypt container")
    ap.add_argument("--vault-dir", default=None, help="Directory containing a .krypt file (or legacy metadata.json + <name>.crypt)")
    ap.add_argument("--crypt-file", default=None, help="Legacy: explicit path to a .crypt file (use with --metadata)")
    ap.add_argument("--metadata", default=None, help="Legacy: explicit path to metadata.json (use with --crypt-file)")
    ap.add_argument("--word", action="append", default=[], help="A codeword phrase. Repeatable. If omitted, you'll be prompted.")
    ap.add_argument("--outdir", default=None, help="Directory to extract the recovered archive into")
    args = ap.parse_args()

    metadata, ciphertext = load_source(args)
    if metadata.get("scheme") == "prime-trustee":
        sys.exit(
            "error: this .krypt file was created by vault_create_prime.py "
            "(scheme='prime-trustee', a mandatory-prime-trustee vault) -- "
            "use vault_recover_prime.py instead."
        )

    try:
        kdf_method, kdf_params = vault_core.resolve_kdf(metadata)
    except vault_core.VaultError as e:
        sys.exit(f"error: {e}")

    threshold = metadata["threshold"]
    shard_records = metadata.get("shards", metadata.get("shares"))

    print(f"[i] This vault requires {threshold} of {metadata['trustees_total']} codewords to recover.")
    print(f"[i] Shard protection KDF: {kdf_method}")

    recovered = []
    used_indices = set()

    codewords_queue = list(args.word)
    while len(recovered) < threshold:
        if codewords_queue:
            word = codewords_queue.pop(0)
        else:
            word = getpass.getpass(
                f"Enter codeword {len(recovered) + 1}/{threshold}: "
            ).strip()
            if not word:
                print("  (empty input, try again)")
                continue

        match = vault_core.try_match_word(word, shard_records, kdf_method, kdf_params, used_indices)
        if match is None:
            print("  [-] That codeword doesn't match any remaining shard. Try again.")
            continue

        idx, x, y = match
        used_indices.add(idx)
        recovered.append((x, y))
        print(f"  [+] Codeword accepted ({len(recovered)}/{threshold}).")

    try:
        vault_core.reconstruct_and_decrypt(
            metadata, ciphertext, recovered, outdir=args.outdir,
            log=lambda msg: print(f"[*] {msg}"),
        )
    except vault_core.VaultError as e:
        sys.exit(f"error: {e}")


if __name__ == "__main__":
    main()

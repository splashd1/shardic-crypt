#!/usr/bin/env python3
"""
vault_create_prime.py

shardic-prime variant of vault_create.py: same threshold-recoverable
encrypted vault, except one trustee is the PRIME trustee -- their
codeword must be present at every recovery, in addition to any
(threshold - 1) of the remaining (trustees - 1) pool trustees, who
stay fully interchangeable among themselves.

See vault_core_prime.py / gf256_sss_prime.py for the construction.
This is a separate scheme and container format from vault_create.py
-- vaults created here can only be recovered with vault_recover_prime.py.

Outputs:
  <vault_dir>/<random16>.krypt                                - single-file container
  <vault_dir>/<random16>_trustee_words/trustee_prime.txt       - the mandatory codeword
  <vault_dir>/<random16>_trustee_words/trustee_N.txt           - pool codewords (interchangeable)
  (the trustee_words directory name is keyed to the .krypt filename
  above, so repeated runs into the same <vault_dir> never collide)

Usage:
  python3 vault_create_prime.py --input PATH --trustees T --threshold D \
      --word-length N [--word-count K] [--dictionary FILE] \
      [--outdir DIR] [--kdf {argon2id,pbkdf2}] [--strong-words]

  T counts the prime trustee (1 prime + T-1 pool). D counts the prime
  trustee's codeword (1 mandatory + D-1 from the pool).
"""

import argparse
import importlib.util
import sys

if importlib.util.find_spec("cryptography") is None:
    sys.exit(
        "error: this program requires the 'cryptography' package, which isn't "
        "installed here.\n"
        "  Run: pip install cryptography\n"
        "then try again."
    )

import kdf as kdfmod
import vault_core
import vault_core_prime


def main():
    ap = argparse.ArgumentParser(
        description="Create a threshold-recoverable encrypted vault with one mandatory prime trustee."
    )
    ap.add_argument("--input", required=True, help="File or directory to archive & encrypt")
    ap.add_argument("--trustees", "-T", type=int, required=True,
                     help="Total trustees INCLUDING the prime trustee (T)")
    ap.add_argument("--threshold", "-D", type=int, required=True,
                     help="Codewords required to recover, INCLUDING the prime trustee's (D)")
    ap.add_argument("--word-length", "-N", type=int, default=None,
                     help="Character length of each codeword. Omit for --memorable mode (the default "
                          "when this is left out): whole real words of varying length instead.")
    ap.add_argument("--word-count", type=int, default=None,
                     help="Words per trustee codeword phrase (default: 8 in --memorable mode, else 1; "
                          "use >1 for real entropy margin)")
    ap.add_argument("--dictionary", default=None,
                     help="Wordlist file (one word per line). In --memorable mode, defaults to the bundled "
                          "EFF wordlist; otherwise falls back to synthetic pronounceable words if omitted.")
    ap.add_argument("--memorable", action="store_true",
                     help="Optimize for a trustee being able to recall their codeword instead of writing "
                          "it down: whole, real dictionary words (bundled EFF wordlist by default), no "
                          "length filtering, no case randomization, no digit suffixes. This is also the "
                          "default whenever --word-length is omitted; pass this explicitly for clarity in "
                          "scripts, or to force it even if --word-length is also given (which is then "
                          "ignored). Mutually exclusive with --strong-words.")
    ap.add_argument("--strong-words", action="store_true",
                     help="Opt-in higher-entropy codewords: randomize letter case and append a "
                          "3-digit suffix to each word. Only worth it if codewords will be "
                          "typed/pasted rather than read aloud or handwritten. Mutually exclusive "
                          "with --memorable, since case/digit noise undermines memorability.")
    ap.add_argument("--outdir", default=None, help="Output directory (default: ./vault_<timestamp>)")
    ap.add_argument("--kdf", choices=list(kdfmod.METHODS), default=None,
                     help="KDF for shard protection. Default: argon2id if argon2-cffi is installed, else pbkdf2.")
    ap.add_argument("--pbkdf2-iterations", type=int, default=None, help="Override PBKDF2 iteration count")
    ap.add_argument("--argon2-time-cost", type=int, default=None, help="Override Argon2id time_cost (default 4)")
    ap.add_argument("--argon2-memory-cost-kib", type=int, default=None, help="Override Argon2id memory cost in KiB (default 262144 = 256 MiB)")
    ap.add_argument("--argon2-parallelism", type=int, default=None, help="Override Argon2id parallelism (default 4)")
    ap.add_argument("--yes", "-y", action="store_true", help="Assume yes to any confirmation prompts (e.g. proceeding without Argon2id)")
    args = ap.parse_args()

    # --- Resolve KDF method + params (recorded in metadata, so recovery is self-describing) ---
    if args.kdf is None:
        if kdfmod.ARGON2_AVAILABLE:
            kdf_method = "argon2id"
        else:
            print("[!] WARNING: 'argon2-cffi' is not installed, so Argon2id (the")
            print("    stronger, memory-hard KDF) isn't available. Shard protection")
            print("    would fall back to PBKDF2-HMAC-SHA256, which is weaker against")
            print("    GPU/ASIC-parallel offline guessing of your codewords.")
            print("    For stronger protection, install it and re-run:")
            print("        pip install argon2-cffi")
            if args.yes:
                print("    --yes supplied; proceeding with the PBKDF2 fallback.")
            elif not sys.stdin.isatty():
                sys.exit(
                    "error: refusing to silently fall back to PBKDF2 in a "
                    "non-interactive run. Re-run with --yes to accept the "
                    "fallback, install argon2-cffi, or pass --kdf pbkdf2 "
                    "explicitly."
                )
            else:
                answer = input("    Proceed with the PBKDF2 fallback anyway? [y/N]: ").strip().lower()
                if answer not in ("y", "yes"):
                    sys.exit("Aborted. Install argon2-cffi and re-run, or pass --kdf pbkdf2 explicitly.")
            kdf_method = "pbkdf2"
    elif args.kdf == "argon2id" and not kdfmod.ARGON2_AVAILABLE:
        sys.exit(
            "error: --kdf argon2id requested but argon2-cffi isn't installed.\n"
            "  Run: pip install argon2-cffi\n"
            "  ...or drop --kdf to auto-select, or pass --kdf pbkdf2."
        )
    else:
        kdf_method = args.kdf

    kdf_overrides = {}
    if kdf_method == "pbkdf2":
        kdf_overrides["iterations"] = args.pbkdf2_iterations
    else:
        kdf_overrides["time_cost"] = args.argon2_time_cost
        kdf_overrides["memory_cost_kib"] = args.argon2_memory_cost_kib
        kdf_overrides["parallelism"] = args.argon2_parallelism
    kdf_params = vault_core.resolve_kdf_params(kdf_method, kdf_overrides)

    print(f"[i] Shard protection KDF: {kdf_method} {kdf_params}")

    if args.memorable and args.word_length is not None:
        print(f"[i] --memorable set: ignoring --word-length {args.word_length} (using whole real words instead).")

    try:
        word_length, word_count, dictionary_path, randomize_case, digit_suffix_len = vault_core.resolve_word_mode(
            word_length=args.word_length,
            word_count=args.word_count,
            dictionary_path=args.dictionary,
            memorable=args.memorable,
            strong_words=args.strong_words,
        )
    except ValueError as e:
        sys.exit(f"error: {e}")

    if word_length is None and args.word_length is None and not args.memorable:
        print("[i] No --word-length given: defaulting to --memorable mode (whole real words).")

    try:
        result = vault_core_prime.create_vault_prime(
            input_path=args.input,
            trustees=args.trustees,
            threshold=args.threshold,
            word_length=word_length,
            word_count=word_count,
            dictionary_path=dictionary_path,
            outdir=args.outdir,
            kdf_method=kdf_method,
            kdf_params=kdf_params,
            randomize_case=randomize_case,
            digit_suffix_len=digit_suffix_len,
            log=lambda msg: print(f"[*] {msg}"),
        )
    except (ValueError, vault_core.VaultError) as e:
        sys.exit(f"error: {e}")

    pool_size = args.trustees - 1
    pool_threshold = args.threshold - 1
    print()
    print(f"[+] Wrote {len(result['trustee_files'])} trustee codeword files to: {result['words_dir']}/")
    print("    trustee_prime.txt is MANDATORY -- recovery always needs it.")
    print(f"    trustee_1.txt..trustee_{pool_size}.txt are the interchangeable pool; any "
          f"{pool_threshold} of them, plus the prime codeword, recover the vault "
          f"({args.threshold} total).")
    print("    Distribute each file to exactly one trustee (out of band, e.g. in")
    print("    person or over a channel they individually control), then DELETE")
    print("    these files from this machine.")
    print()
    print(f"Vault output directory: {result['outdir']}")


if __name__ == "__main__":
    main()

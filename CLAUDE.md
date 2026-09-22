# shardic — Project Memory

## What this is

A two-frontend (CLI + GUI), threshold-recoverable encrypted vault.
Encrypts a file/folder with AES-256-GCM under a random DEK, splits the
DEK via Shamir's Secret Sharing (GF(256), byte-wise) into T shards with
threshold D, and protects each shard with a codeword. Recovery needs
any D of T codewords — no single party (including the creator) can
decrypt alone once the codewords are distributed.

Read `README.md` first — it's the full spec of behavior, CLI flags,
build steps, and design rationale. This file is for the things a new
Claude Code session needs to *not re-derive from scratch* or
*re-break by accident*.

## Architecture (don't duplicate crypto logic across frontends)

- `gf256_sss.py` — Shamir split/reconstruct over GF(256). Self-tests
  at the bottom of the file (`python3 gf256_sss.py`).
- `wordgen.py` — codeword generation (dictionary or synthetic
  pronounceable words).
- `kdf.py` — PBKDF2 / Argon2id, `ARGON2_AVAILABLE` flag, `default_params()`.
- `krypt_container.py` — the `.krypt` single-file format: magic header
  + length-prefixed JSON metadata + raw ciphertext (not base64 — avoid
  the size penalty if you're tempted to "simplify" this).
- `vault_core.py` — **the actual crypto orchestration**
  (`create_vault`, `match_codewords`, `reconstruct_and_decrypt`, etc.).
  `vault_create.py`, `vault_recover.py`, and `vault_gui.py` are all
  thin frontends over this. **If you're changing encrypt/decrypt/split
  behavior, change it here once — do not patch it separately in the
  CLI or the GUI.** They intentionally share this module so the three
  frontends can't drift apart.
- `vault_create.py` / `vault_recover.py` — CLI (argparse), including
  interactive prompts (KDF fallback confirmation, codeword entry).
- `vault_gui.py` — Tkinter GUI, two tabs, background-thread execution
  with a `queue.Queue` log sink polled via `root.after()`. Don't call
  Tk widget methods directly from the worker thread — only from the
  `self.after(0, ...)` callback.

## Key design decisions (rationale, so they don't get "fixed" by accident)

- **Indexing shards without a mapping table**: metadata never records
  which codeword unlocks which shard. Recovery brute-trials each
  entered codeword against every unmatched shard record; AES-GCM's
  auth tag is the correctness check. This is deliberate — it's what
  keeps the `.krypt` file safe to store/share without leaking
  trustee-to-shard assignment. Don't add a mapping field "for
  efficiency" — T is small (tens), the trial cost is negligible.
- **Argon2id is optional, PBKDF2 is the zero-dependency fallback.**
  Creating a vault: if Argon2id is unavailable, warn + require
  confirmation (`--yes` for non-interactive CLI, a Yes/No dialog in
  the GUI) before silently downgrading security. Recovering a vault:
  no fallback is offered — the KDF was fixed at creation time, so
  print/show an "install argon2-cffi" message and stop.
- **`.krypt` is one file on purpose.** Earlier version had a separate
  `.crypt` + `metadata.json`; that got merged per explicit request so
  there's nothing to accidentally separate when sharing a vault.
  Legacy split-file vaults are still readable (`vault_recover.py`
  auto-detects `.krypt` vs `metadata.json` in a `--vault-dir`) — keep
  that backward compat if touching `load_source`/`load_from_vault_dir`.
- **Uncompressed tar** (mode `"w"` not `"w:gz"`) deliberately, so
  ciphertext size doesn't leak plaintext compressibility. Don't
  "optimize" this to gzip without flagging the tradeoff.
- **PyInstaller, not a different bundler** — chosen because it handles
  `cryptography`'s OpenSSL bindings and `argon2-cffi`'s C extension
  via existing hooks with zero manual `--hidden-import` fuss (verified
  during build). AppImage wraps the PyInstaller binaries; don't
  conflate the two build steps.

## Build & test

- CLI dev loop: `python3 vault_create.py --input testdata --trustees 3
  --threshold 2 --word-length 6 --outdir /tmp/v && python3
  vault_recover.py /tmp/v/*.krypt --outdir /tmp/r --word ... --word
  ...` then `diff -r testdata /tmp/r/testdata`.
- GUI dev loop needs a display. Headless testing used Xvfb
  (`Xvfb :99 -screen 0 1024x768x24 &`, `export DISPLAY=:99`) plus
  driving the Tk widgets programmatically through a real
  `root.mainloop()` (not manual `root.update()` polling — that breaks
  `.after()` scheduling from worker threads with a "main thread is not
  in main loop" error).
- `./build_appimage.sh` builds both `VaultTool-x86_64.AppImage` (CLI)
  and `VaultToolGUI-x86_64.AppImage` (GUI). Needs `python3-tk` on the
  build machine for the GUI half.
- `build_windows.bat` — **written but never run/tested** (no Windows
  machine was available when this was built). Same PyInstaller
  invocations as the tested Linux build. Flag/fix anything that
  doesn't match once it's actually run.
- `.github/workflows/build.yml` — CI builds both platforms on push to
  `main`; this is how a real Windows `.exe` gets produced without a
  local Windows machine.

## Open items / known gaps

- Windows build is unverified (see above).
- AppImage is x86-64 only; no aarch64 build has been produced.
- No automated test suite exists yet — all verification so far has
  been manual round-trip scripts (create -> recover -> `diff -r`) run
  ad hoc. Worth adding `pytest` coverage for `gf256_sss.py` (property
  tests: any D-of-T subset reconstructs, D-1 doesn't) and
  `krypt_container.py` (round-trip, truncation/corruption handling)
  if this grows.

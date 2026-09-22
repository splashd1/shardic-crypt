# Threshold-Recoverable Encrypted Vault

Two CLI programs, a GUI, and shared library modules.

This tool gives an operator the ability to encrypt data such that
exposure is entrusted to a defined pool of T trustees, requiring a
minimum subset of D of them to actively agree — each by supplying
their individual codeword — before the plaintext can be recovered.
No single party, including whoever created the vault, can decrypt it
alone; any group smaller than D learns nothing about the data even if
they pool what they have (see "How the design works" below).

**Example: break-glass access to critical infrastructure.** A company
locks a root CA private key, a production database master key, or a
SCADA override credential in a vault with, say, `T=7` trustees (a mix
of senior engineers, security officers, and an executive) and a
`D=4` threshold. Day to day, nobody has access to the key at all — it
only gets reconstructed for a genuine emergency (an incident, an
outage, an urgent access-revocation). When that happens, no single
person, including whoever's holding the `.krypt` file, can unlock it
unilaterally: four of the seven trustees each have to independently
choose to supply their codeword. That gives the organization a
credential that's recoverable under real emergency conditions while
staying resistant to misuse by any one insider or one compromised
account — with a built-in record of exactly which trustees
participated in each recovery.

**Example: diceware-style memorable codewords.** A family estate plan
splits access to a password manager's master vault among five
relatives (`T=5`, `D=3`) — but unlike the infrastructure case above,
each trustee needs to actually *memorize* their codeword rather than
store a file; nobody wants it written on a sticky note. This is
`--memorable` mode — in fact it's the default, so just omitting
`--word-length` gets it: `python3 vault_create.py --input ...
--trustees 5 --threshold 3` builds each codeword out of whole, real
words from the bundled EFF long wordlist instead of synthetic
strings — the classic diceware approach, much easier to commit to
memory and recall correctly than an equivalent-strength random string.
Unlike the fixed-length `--dictionary` mode, memorable mode doesn't
filter the wordlist down to one length, so it draws from the full
7,772-word pool (~12.9 bits/word) rather than whatever subset happens
to share one length — see "Codeword modes" below for the full picture.

These two are just illustrations — see [Other potential use
cases](#other-potential-use-cases) below for a broader list spanning
government and business scenarios.

## Files
- `vault_create.py` — CLI Program 1: archive → encrypt → split into trustee codewords → single `.krypt` file
- `vault_recover.py` — CLI Program 2: recover DEK from D codewords → decrypt → extract
- `vault_gui.py` — GUI (Tkinter): same two operations as tabs in a windowed app, with form fields instead of flags
- `vault_core.py` — shared library: the actual encrypt/split and match/reconstruct/decrypt logic; both CLIs and the GUI call this, so there's exactly one implementation of the crypto behind three frontends
- `gf256_sss.py` — shared library: byte-wise Shamir's Secret Sharing over GF(256)
- `wordgen.py` — shared library: codeword generation (memorable, dictionary, or synthetic)
- `kdf.py` — shared library: key derivation (PBKDF2 or Argon2id), self-describing via metadata
- `krypt_container.py` — shared library: the single-file `.krypt` container format
- `wordlists/eff_large_wordlist.txt` — the EFF long wordlist (7,776
  words, one per line), source-of-truth copy for `--dictionary`-based
  diceware-style codewords; see "Example: diceware-style memorable
  codewords" above. Published by the Electronic Frontier Foundation
  (<https://www.eff.org/dice>) under CC BY 3.0 US; reformatted here
  from EFF's original tab-separated `<dice-roll>\t<word>` file to one
  word per line, since that's the format `wordgen.load_dictionary()`
  expects. A handful of entries with punctuation (`drop-down`,
  `felt-tip`, `t-shirt`, `yo-yo`) get silently excluded by the
  `isalpha()` filter both this and the module below apply — expected,
  negligible.
- `eff_wordlist_words.py` — the same wordlist, embedded as a plain
  Python tuple, used by `--memorable` mode (`wordgen.bundled_memorable_wordlist()`)
  instead of reading the `.txt` file at runtime. This is what actually
  ships in the standalone `.exe`/`.AppImage` builds below — PyInstaller
  onefile bundles only get built by following Python imports, not by
  picking up loose data files like `wordlists/*.txt`, so a real .py
  module is what makes memorable mode work in the packaged binaries
  without extra `--add-data` wiring in `build_appimage.sh`/`build_windows.bat`.
- `build_appimage.sh` — builds standalone Linux binaries + `.AppImage` packages (CLI and GUI)
- `build_windows.bat` — builds standalone Windows `.exe` files (run on Windows; see below)
- `.github/workflows/build.yml` — GitHub Actions workflow that builds Windows + Linux executables in CI, and publishes a GitHub Release with all of them attached when a `v*` tag is pushed
- `vault_create_prime.py` / `vault_recover_prime.py` / `vault_core_prime.py` / `gf256_sss_prime.py` — the **shardic-prime** variant: adds a mandatory "prime trustee" on top of the base scheme. See "shardic-prime" below. Available both as CLI scripts and as a "Shardic-Prime" tab (with its own Create/Recover sub-tabs) in `vault_gui.py`.
- `shardic_envelope_crypto.py` — shared library implementing **shardic-envelope** (wrap/unwrap a codeword under a trustee's public key instead of requiring memorization); used by `demo/trustee/app.py` and `demo/combiner/app.py`. See `docs/pubkey-envelope-plugin.md` below for the design.
- `docs/pubkey-envelope-plugin.md` — **shardic-envelope**, a design proposal (not yet implemented) for a bolt-on plugin that wraps each trustee's codeword under their own public key, trading memorability for arbitrarily larger/higher-entropy codewords protected by a keypair instead of memory.
- [`docs/keycloak-credential-lookup.md`](docs/keycloak-credential-lookup.md) — a Keycloak-backed `CredentialLookup` for shardic-envelope: selecting trustees from a Keycloak group, an OIDC-authenticated client-side-only key registration flow, and the `shardic-operator` role that authenticates and authorizes privileged combiner actions. **The operator role (identity, authorization, and separation-of-duties) is implemented and verified in `demo/`**; the trustee key-registration flow itself is still a design proposal.
- [`docs/portable-trustee-client.md`](docs/portable-trustee-client.md) — a design proposal (not yet implemented) for a browser-based trustee app (registration, key custody, ceremony participation) replacing today's per-trustee Docker container: WebCrypto X25519 keypair generation, non-extractable-key custody, device-bound portability (re-register on device loss, no export path), and the accepted browser-XSS residual risk this trades for.
- [`docs/ceremony-formation.md`](docs/ceremony-formation.md) — **implemented and verified end-to-end in `demo/`**: how one specific ceremony gets formed from the registered candidate directory — operator-initiated T/D selection with an ordered backup list, per-trustee invitations, and automatic race-safe backfill when a slot is declined or times out.
- [`docs/envelope-delivery.md`](docs/envelope-delivery.md) — a design proposal (not yet implemented) for getting a wrapped envelope from a shardic-envelope wrap event to the right trustee: a pull-based, single-read drop point modeled on Vault-style response-wrapping, authenticated by the same OIDC session as registration.
- [`docs/notification-channel-concept.md`](docs/notification-channel-concept.md) — a concept paper (one step earlier than a design proposal — no channel chosen yet) laying out the need, options, and design-choice drivers for the trustee-facing "go pull your envelope" ping and the operator-facing "unredeemed drop expired" alert that `envelope-delivery.md` left open.
- [`docs/notification-channels.md`](docs/notification-channels.md) — **implemented and verified in `demo/`**: a single pluggable, admin-configurable `NotificationChannel` interface (log-line/webhook/email, fan-out delivery) resolving the concept paper above. Wired into ceremony invitations only — the other two event types this doc names (envelope-ready ping, drop-expired alert) await `envelope-delivery.md`'s still-unbuilt drop point.
- [`docs/vault-storage-backend.md`](docs/vault-storage-backend.md) — **implemented in `demo/`**: a pluggable `VaultStore` interface behind the combiner's `.krypt` storage, replacing the old hardcoded filesystem path — filesystem-backed by default in v1.0, SQL/NoSQL as a still-unbuilt config-selected alternate implementation, no bundled database.

  Together, these seven documents describe one proposed operational
  lifecycle for shardic-envelope. Three full pieces are implemented and
  verified against the real `demo/` stack — **form** (including its
  notification channel), and the `.krypt` storage behind **wrap** — the
  rest remain design proposals: **register** (trustee generates a
  keypair client-side, via `portable-trustee-client.md`, and registers
  the public half per `keycloak-credential-lookup.md`, once, ahead of
  any ceremony) → **form** (an authenticated operator initiates a
  specific ceremony and invites T trustees from the directory, per
  `ceremony-formation.md`, notified via `notification-channels.md`'s
  pluggable interface) → **wrap** (operator runs shardic-envelope per
  `pubkey-envelope-plugin.md`, which looks up each trustee's public key
  via the same registry; the resulting `.krypt` bytes are persisted via
  `vault-storage-backend.md`'s `VaultStore`) → **deliver** (each
  envelope lands in the drop point from `envelope-delivery.md` for the
  trustee to pull, notified via the same shared channel interface, once
  that drop point exists) → **recover** (trustee decrypts locally and
  types the resulting codeword into `vault_recover.py`/the GUI,
  unchanged from today).
- [`docs/shardic-envelope-explainer.html`](docs/shardic-envelope-explainer.html) — a static, illustrated walkthrough of the shardic-envelope ceremony's four phases (Formation, Protected & Dormant, Threshold-Proof, Finalize & Verify), for anyone who can't run the live `demo/` stack. Open it directly in a browser.
- [`docs/nomenclature.md`](docs/nomenclature.md) — the canonical glossary and lifecycle-state vocabulary for shardic's domain objects (vault, shard, unsealed shard, trustee, combiner, etc.), grounded in actual code usage. Also available as a Claude Code skill (`.claude/skills/shardic-nomenclature/`) that loads automatically for naming-sensitive work.
- [`docs/sss_explained_for_shardic.md`](docs/sss_explained_for_shardic.md) — a standalone, complete explainer of Shamir's Secret Sharing: the geometric intuition, the precise polynomial construction, why the arithmetic runs over GF(256), and how shardic builds on it. The white paper's §1.4 gives a shorter in-context version of the same intuition before §3.2's mechanics; this is the full reference.
- [`docs/shardic_white_paper.v3.2.md`](docs/shardic_white_paper.v3.2.md) — the shardic white paper: motivation, operator walkthroughs, the underlying cryptographic mechanics, and a security discussion of trade-offs (including shardic-envelope's impact). Rendered `.docx`/`.html` twins live alongside it; superseded drafts (v1.2 through v3.1) are kept in `docs/archive/` for history.
- [`docs/feedback-on-v3.2.md`](docs/feedback-on-v3.2.md) — section-by-section accuracy/formatting/readability review of the v3.2 draft against v3.1.
- [`docs/sss_explained_for_shardic.md`](docs/sss_explained_for_shardic.md)'s companion: [`docs/gf256-field-construction.md`](docs/gf256-field-construction.md) — supplemental detail on why GF(256) uses reduction polynomial `0x11B` and generator `3` specifically, referenced from `gf256_sss.py`'s docstring.
- [`docs/shardic-cryptographic-path.md`](docs/shardic-cryptographic-path.md) (+ `.docx`/`.html` twins) — a code-grounded reference walking DEK formation through recovery at the level of actual function names and data shapes, across the base scheme, shardic-prime, and shardic-envelope; complements the white paper's conceptual Appendix A rather than duplicating it.
- [`docs/spac-concept.md`](docs/spac-concept.md) — design proposal (early brainstorm, nothing implemented): generalizing shardic's protected value beyond file decryption to any protected action.
- [`docs/embedment-manual.md`](docs/embedment-manual.md) — **adopted design doc**: the fork-tree of hardware-embedment options for carrying an unsealed shard (fleet-scale, cohort granularity, etc.); determines the *inputs* a wire-format contract needs rather than fixing one.
- [`docs/icd-wire-format-draft.md`](docs/icd-wire-format-draft.md) — design proposal, unimplemented review draft: the actual wire-format contract at the shardic client-module boundary that `embedment-manual.md` leaves open.
- [`docs/shardware-token.md`](docs/shardware-token.md), [`docs/shardware-token-embed-extract.md`](docs/shardware-token-embed-extract.md), [`docs/shardware-token-key-custody.md`](docs/shardware-token-key-custody.md) — design proposals (nothing implemented): a family of hardware-token alternatives to a memorized codeword — physical carriage, PUF-sealed embed/extract with vault-signed authorization, and hardware-backed key custody, respectively.
- [`docs/dlt-integration-brainstorm.md`](docs/dlt-integration-brainstorm.md) — **tabled**: an unscoped, uncommitted brainstorm on blockchain/hashgraph integration, kept only so the idea isn't lost.
- `docs/shardic_deck_v3_2.pptx` — the current companion slide deck, realigned to the v3.2 whitepaper. No markdown source; edited directly as OOXML (see the `shardic-doc-pipeline` Claude Code skill's pptx XML-surgery workflow).
- `docs/archive/` — superseded whitepaper drafts (v1.2–v3.1jd) and old deck/presentation files, kept for history but out of the live document set.
- `docs/media/` — figures embedded in the whitepaper and other docs; `docs/tools/fix_docx.py` — post-processes pandoc's docx output to fix two recurring regen bugs (dangling Word styles, duplicated embedded media) — see the `shardic-doc-pipeline` Claude Code skill.
- `demo/` — a live, containerized shardic-prime + shardic-envelope stack (Keycloak-backed combiner/trustee services, docker-compose); see [`demo/README.md`](demo/README.md) for setup and the full walkthrough.
- `graphics/` — shardic branding artwork (logo, banner images); not currently embedded in any doc.
- `CLAUDE.md` — Claude Code project memory: architecture map and design decisions not to accidentally re-break, for any Claude Code session working in this repo.
- `notes.md` — running cross-session dev log, synced via the `shardic-sync` Claude Code skill so a session on a different machine can pick up context.

## Requirements (running from source)
```
pip install cryptography
pip install argon2-cffi   # optional, but strongly recommended (see below)
```
The GUI additionally needs Tkinter, which ships with most Python
installs; on some minimal Linux distros it's a separate package
(`sudo apt install python3-tk` on Debian/Ubuntu). Windows and macOS
python.org installers include it by default.

Python 3.9+ (3.12 recommended; `filter="data"` extraction requires 3.12,
or 3.11.4+ — on older versions drop that argument from `tar.extractall(...)`
in vault_recover.py / vault_core.py).

**All three frontends check for `cryptography` before doing anything else**
and, if it's missing, show the exact `pip install` command to run instead
of a raw traceback — a dialog box in the GUI's case, since it may not even
have a terminal to print to.

`argon2-cffi` is optional. If it's installed, vault creation prefers
Argon2id; if it isn't:
- **CLI**: prints a warning and prompts `Proceed with the PBKDF2 fallback
  anyway? [y/N]` (or aborts safely if non-interactive and `--yes` wasn't
  passed).
- **GUI**: shows the same warning as a Yes/No dialog before proceeding.

Recovery has no fallback either way — the KDF choice was fixed when the
vault was created, so both frontends just show a clear "install
argon2-cffi" message if a vault needs it and it's missing.

## Quick start (CLI)

Create a vault from a file or directory, 5 trustees, 3 needed to recover.
Leaving out `--word-length` gets you the default: **memorable mode**
(`--memorable`) — whole, real words from the bundled EFF wordlist, 8
per trustee, ~103 bits of entropy, meant to actually be remembered
rather than written down:
```
python3 vault_create.py --input ./my_directory \
    --trustees 5 --threshold 3 \
    --outdir vault_out
```
Outputs into `vault_out/`:
- `<random16>.krypt` — **single file** containing both the metadata
  (everything needed to recover, except the codewords) and the encrypted
  archive. This is the one file you back up or share.
- `<random16>_trustee_words/trustee_1.txt` ... `trustee_5.txt` — one
  codeword each, e.g. `desktop-anaconda-upstroke-paralegal-survivor`.
  The directory name is keyed to the `.krypt` filename above (same
  random16), so creating multiple vaults into the same `--outdir`
  never overwrites an earlier run's trustee codewords.

Pass `--word-length` (e.g. `--word-length 8 --word-count 2`) to get the
old fixed-length behavior instead — see "Codeword modes" below for the
full picture (memorable / dictionary / synthetic / `--strong-words`).

Distribute each `trustee_N.txt` to one trustee out-of-band, then delete
them from this machine. The `.krypt` file can be stored, emailed, or
uploaded anywhere — it leaks no information about which codeword belongs
to which shard (see "Indexing without a mapping table" below).

Recover (interactive prompt for 3 codewords):
```
python3 vault_recover.py vault_out/xxxxxxxxxxxxxxxx.krypt --outdir recovered
```
Or non-interactively:
```
python3 vault_recover.py vault_out/xxxxxxxxxxxxxxxx.krypt --outdir recovered \
    --word "word-one" --word "word-two" --word "word-three"
```
`--vault-dir vault_out` also works and will find the `.krypt` file inside
automatically (and still understands older split-file vaults — see below).

### Choosing / tuning the KDF

```
--kdf {argon2id,pbkdf2}          # default: argon2id if available, else prompts to fall back
--yes / -y                       # auto-accept the PBKDF2 fallback warning, no prompt
--pbkdf2-iterations N            # default 400000
--argon2-time-cost N             # default 4
--argon2-memory-cost-kib N       # default 262144 (256 MiB)
--argon2-parallelism N           # default 4
```

### Codeword modes

Four ways to generate codewords, all going through the same
KDF+AES-GCM per-shard protection and all reported with an estimated
combinatorial-entropy figure (in bits) so you can compare them
directly. Pick one — `--memorable` and `--strong-words` are mutually
exclusive, since they optimize for opposite things.

- **Memorable (`--memorable`, and the default whenever `--word-length`
  is omitted)**: whole, real dictionary words — the bundled EFF long
  wordlist (`eff_wordlist_words.py`, 7,772 words) unless `--dictionary`
  points somewhere else — with no length filtering, no case
  randomization, no digit suffixes. Default word count is 8
  (~103 bits with the bundled list). This is the recommended default:
  real words engage semantic memory in a way random syllables and
  mixed-case/digit noise don't, so a trustee has a real shot at
  recalling their codeword without writing it down. Passing
  `--word-length` always opts back into one of the modes below (fully
  backward compatible with anything that already specified it).
  ```
  python3 vault_create.py --input ./my_directory \
      --trustees 5 --threshold 3 --memorable --word-count 6 \
      --outdir vault_out
  ```
- **Dictionary (`--dictionary FILE --word-length N`)**: words of
  exactly length N pulled from a file you supply. Useful if you want
  every codeword the same visible length/shape; costs you most of the
  dictionary's candidates to the length filter, so it's usually lower
  entropy per word than memorable mode off the same file.
- **Synthetic (`--word-length N`, no `--dictionary`)**: the default
  before this scheme existed — pronounceable random syllables
  (alternating consonant/vowel) of exact length N. Denser
  bits-per-character than real words, but the syllables don't mean
  anything, so they're harder to actually remember. Prefer memorable
  mode unless codewords are going to be stored rather than memorized.
- **`--strong-words`** (stacks with dictionary/synthetic modes, not
  memorable mode): randomizes the case of each generated letter and
  appends a 3-digit suffix to every word, e.g. `bAfOgE472` instead of
  `bafoge`. Same length/word-count settings, meaningfully more
  entropy — randomized case is +1 bit/char for free (doubles the
  alphabet at every position), the digit suffix adds ~3.32 bits/char.
  Only turn this on if codewords will be typed or copy-pasted rather
  than read aloud or handwritten — case is the first thing lost in
  dictation or sloppy transcription.
  ```
  python3 vault_create.py --input ./my_directory \
      --trustees 5 --threshold 3 \
      --word-length 8 --word-count 2 --strong-words \
      --outdir vault_out
  ```

All of this is purely a generation-time choice — recovery just tries
whatever string a trustee enters against each shard's KDF+AES-GCM
check (see `vault_core.try_match_word`), so none of it touches the
`.krypt` format or breaks compatibility with codewords generated
under a different mode before these flags existed.

## GUI

```
python3 vault_gui.py
```
Three tabs:
- **Create Vault** — pick a file/folder, fill in trustee count,
  threshold, a "Memorable codewords" checkbox (checked by default —
  see `--memorable` under "Codeword modes" above), codeword
  length/count, a "Strong words" checkbox (see `--strong-words`
  above), output folder, and a KDF option (Auto / Argon2id / PBKDF2),
  then click Create. Memorable and Strong words are mutually
  exclusive — checking one unchecks and disables the other, and the
  codeword-length field is disabled while Memorable is checked, since
  it's ignored in that mode. A "Customize Argon2id cost (advanced)"
  checkbox under the KDF option is unchecked by default, so the raised
  defaults (`time_cost=4`, `memory_cost=256 MiB`, `parallelism=4`,
  same as the CLI's `--argon2-*` flags — see "Choosing / tuning the
  KDF" above) apply with no extra fields shown; checking it reveals
  time-cost/memory-cost/parallelism entry fields to override them —
  lower for faster recovery on constrained hardware, or raise further
  for more margin. Progress and log output stream into the window,
  including an estimated codeword-entropy figure; a completion dialog
  shows where the `.krypt` file and trustee codeword files landed.
- **Recover Vault** — pick the `.krypt` file and click "Load Vault
  Info" to see how many codewords are needed; that many password-style
  entry fields appear automatically. Fill in the codewords, pick an
  output folder, click Recover.
- **Shardic-Prime** — the mandatory-prime-trustee variant (see below),
  as its own Create/Recover sub-tabs mirroring the two above (Create
  has the same Memorable/Strong-words checkboxes). Trustee count (T)
  and threshold (D) here include the prime trustee; on Recover,
  codewords can be entered in any order, since which one turns out to
  be the prime trustee's is only known once it decrypts.

The GUI runs the actual crypto work on a background thread so the
window stays responsive, and streams log lines back to the main thread
safely via a queue — long Argon2id derivations or large archives won't
freeze the UI.

## Portable builds (no Python/pip needed on the target machine)

### Linux: `build_appimage.sh`

Builds two `.AppImage` files — self-contained Linux executables that
bundle a Python interpreter plus `cryptography` and `argon2-cffi`, so
end users need nothing installed beyond the AppImage file itself. Both
were built and tested (including the GUI, screenshot-verified) in an
environment with no Python, no Tk, no pip packages, and no
`argon2-cffi` present at all.

```
./build_appimage.sh
```
Output:
- `dist/VaultTool-x86_64.AppImage` — CLI, `create`/`recover` subcommands
  (`encrypt`/`decrypt` also work as aliases)
- `dist/VaultToolGUI-x86_64.AppImage` — GUI, double-click or run it

```
./VaultTool-x86_64.AppImage create --input ./my_directory --trustees 5 --threshold 3 --word-length 8 --word-count 2
./VaultTool-x86_64.AppImage recover VAULT.krypt
./VaultToolGUI-x86_64.AppImage
```
If FUSE isn't available on the target machine (common in containers/CI),
add `--appimage-extract-and-run` right after the AppImage path — tested
and works identically for both.

How it's built: **PyInstaller** (`--onefile`, `--windowed` for the GUI)
compiles each script plus its full dependency closure — including
`cryptography`'s OpenSSL bindings, `argon2-cffi`'s C extension, and for
the GUI, Tkinter/Tcl/Tk — into one self-extracting ELF binary per
program. Those binaries get wrapped in a minimal AppDir (`AppRun`
dispatcher + `.desktop` file + icon) and packaged with `appimagetool`
into the familiar single-file AppImage format: `chmod +x` and run, no
installation, no `sudo`.

### Windows: `build_windows.bat`

**Must be run on an actual Windows machine** — PyInstaller does not
cross-compile, so there is no way to produce a working Windows `.exe`
from Linux or macOS. Copy all the `.py` files plus `build_windows.bat`
onto a Windows machine with Python 3.9+ installed (python.org installer,
with "Add to PATH" checked), then run:
```
build_windows.bat
```
Output in `dist\`:
- `VaultTool-GUI.exe` — double-click, opens the windowed GUI (includes the Shardic-Prime tab)
- `vault-create.exe`, `vault-recover.exe` — CLI equivalents
- `vault-create-prime.exe`, `vault-recover-prime.exe` — shardic-prime CLI equivalents

These run standalone on any Windows 10/11 x64 machine: no Python, no
pip packages, nothing else needs installing there. (I built and tested
the Linux binaries and AppImages directly in this environment; the
Windows build script uses the identical PyInstaller invocations, but I
have no Windows machine here to run it on, so it's untested by me —
flag anything odd if it comes up.)

### Don't have a Windows machine? Use GitHub Actions (`.github/workflows/build.yml`)

This workflow is already wired up in this repo and builds both Windows
and Linux executables on GitHub's own runners — a real Windows `.exe`,
built on real Windows, without you needing to own one. Every push to
`main` builds fresh binaries and uploads them as downloadable,
workflow-run artifacts (`VaultTool-windows-x64`, `VaultTool-linux-x64`)
on that run's **Actions** summary page — but those expire and aren't
versioned.

**To publish a proper Release** (all four binaries — both `.exe`s and
both AppImages — attached to a permanent, versioned download page),
push a tag matching `v*`:
```
git tag v1.0.0
git push --tags
```
That triggers the same Windows/Linux builds, then a `release` job
downloads their outputs and runs `gh release create` to publish them
as a GitHub Release named after the tag, with auto-generated release
notes from the commits since the previous tag. Ordinary pushes to
`main` (no new tag) never create a Release — only tag pushes do.

To use this workflow in a *different* repo from scratch, put the
`.py` files, `build_appimage.sh`, and this file at
`.github/workflows/build.yml`, then push.

## Legacy split-file vaults

Vaults created by an earlier version of these scripts (a separate
`metadata.json` + `<name>.crypt` in a directory) still recover fine:
```
python3 vault_recover.py --vault-dir old_vault_dir --outdir recovered
```
or explicitly:
```
python3 vault_recover.py --crypt-file old.crypt --metadata metadata.json --outdir recovered
```
`vault_create.py` only ever produces the new single-file `.krypt` format
going forward.

## How the design works

1. **Archive**: `tar` bundles the file/directory into one blob so any
   input shape works uniformly.
2. **DEK + AES-256-GCM**: a random 32-byte key encrypts the archive
   once. GCM gives you both confidentiality and tamper detection.
3. **Shamir split (GF(256), byte-wise)**: same construction as the
   classic `ssss` tool — each byte of the DEK gets an independent
   random polynomial of degree `D-1`; each shard evaluates all 32
   polynomials at the same x-coordinate. Any `D` shards reconstruct
   the DEK via Lagrange interpolation; any `D-1` reveal *nothing*
   (information-theoretic security, not just computational).
4. **Per-shard protection**: each shard is itself AES-256-GCM
   encrypted under a key derived from a random codeword, using
   either Argon2id (preferred, memory-hard) or PBKDF2-HMAC-SHA256
   (zero extra dependency fallback) — see `kdf.py`.
5. **Single-file container**: metadata and ciphertext are bundled into
   one `.krypt` file — an 8-byte magic header, a length-prefixed JSON
   metadata block, then the raw ciphertext bytes (not base64-wrapped, so
   there's no ~33% size penalty). See `krypt_container.py`. There's
   nothing to accidentally separate or lose track of anymore.
6. **Indexing without a mapping table**: the metadata stores each shard
   as an opaque `{salt, nonce, ciphertext}` triple — nothing ties a
   record to a trustee or a word. On recovery, each entered codeword is
   tried against every not-yet-matched record; GCM's authentication tag
   means only the correct pairing decrypts successfully, everything else
   fails fast. With T in the tens this is instant, and it means the
   `.krypt` file by itself reveals zero assignment information even if
   someone else gets hold of it.

## shardic-prime: a mandatory prime trustee variant

The base scheme treats every trustee identically: any `D` of `T`
codewords recover the vault, full stop. **shardic-prime** is a
separate variant (own CLI scripts, own `.krypt` container format) that
adds one *essential* trustee on top of that: the **prime trustee**'s
codeword must be among the ones entered, no matter what — the
remaining trustees stay a plain interchangeable pool for the rest of
the threshold. Useful when one specific person (e.g. the estate's
executor, the org's security lead) must always sign off, while backup
signers around them can be any mix.

`T` and `D` now count the prime trustee: `T` total trustees = 1 prime
+ `(T-1)` pool trustees; `D` codewords required = the prime's +
`(D-1)` from the pool.

```
python3 vault_create_prime.py --input ./my_directory \
    --trustees 4 --threshold 3 --word-length 6 --word-count 2
```
creates 1 prime trustee + 3 pool trustees; recovery needs the prime
codeword plus any 2 of the 3 pool codewords. All `4` of the pool
codewords together, *without* the prime one, recover nothing — see
"How it works" below for why that's mathematically guaranteed, not
just enforced by the CLI.

```
python3 vault_recover_prime.py VAULT.krypt
```
prompts for codewords in any order — you don't say up front which one
is the prime trustee's; it's identified automatically once it
decrypts successfully.

**How it works**: a random mask the same length as the DEK is
generated. The prime trustee's codeword protects that mask directly
(a one-time pad, not a Shamir shard). The DEK, XORed with the mask, is
then split with the ordinary `gf256_sss` scheme into the pool shards
(threshold `D-1`, count `T-1`). Recovery needs the mask *and*
`D-1` pool shards to reconstruct the masked DEK and unmask it — without
the mask, the pool shards alone (even all of them) are information-
theoretically indistinguishable from random. See `gf256_sss_prime.py`
for the full construction and `vault_core_prime.py` for how it's wired
into vault creation/recovery. Shard records keep the base scheme's
"opaque `{salt, nonce, ciphertext}`, shuffled, no mapping table"
property — which record is the prime one isn't visible from the
`.krypt` file's structure, only by decrypting it with the right
codeword.

**Not interchangeable with the base scheme.** A shardic-prime vault
carries `"scheme": "prime-trustee"` and `"container_format":
"krypt1-prime"` in its metadata specifically so it's never confused
with a base `vault_create.py` vault — `vault_recover_prime.py` refuses
to open a base-scheme `.krypt` file and vice versa. Always pair
`vault_create_prime.py` output with `vault_recover_prime.py`, and
plain `vault_create.py` output with plain `vault_recover.py`.

## Things worth knowing before you rely on this

- **Entropy of the codewords is the real security bottleneck.**
  A single word — from `--memorable` mode, a fixed-length `--dictionary`,
  or the built-in synthetic generator — is much weaker than the
  AES-256/Shamir math around it on its own. `--memorable` mode's
  unfiltered 7,772-word pool (~12.9 bits/word) is the strongest
  per-word source of the three; a `--dictionary` filtered to a fixed
  `--word-length` is usually much smaller (often hundreds to
  low-thousands of candidates, ~8–11 bits/word), and the synthetic
  generator (`--word-length` with no `--dictionary`) has a larger space
  per length than that but no semantic meaning to help recall it. In
  every mode, `--word-count` is what actually gets you into a real
  security range — each extra word roughly multiplies the search
  space, so aim for the default of 8 in memorable mode, or 2–3+ in the
  other modes. `--strong-words` (see "Codeword modes" above, only
  available outside memorable mode) raises the bits-per-character of
  each word without adding length, if codewords will be typed/pasted
  rather than spoken or handwritten. Note that because each shard is
  cracked independently (see "Indexing without a mapping table"
  above), a higher threshold `D` does *not* let you get away with
  weaker codewords — every codeword individually needs to carry real
  entropy, regardless of `T`.
- **Argon2id vs. PBKDF2**: Argon2id's memory-hardness is what raises
  the cost of an attacker running many parallel guesses on GPUs/ASICs
  against a leaked `.krypt` file — PBKDF2 is cheap to parallelize by
  comparison at equivalent wall-clock cost. The defaults (`time_cost=4`,
  `memory_cost=256 MiB`, `parallelism=4`) are deliberately raised past a
  bare-minimum balance to give real margin against large-scale offline
  guessing without materially slowing down a legitimate recovery; lower
  `--argon2-memory-cost-kib`/`--argon2-time-cost` (CLI) or check
  "Customize Argon2id cost" (GUI) if you need faster recovery on
  constrained hardware, or raise them further for even more margin.
- **Threshold security is information-theoretic; codeword security is
  not.** Getting `D-1` shards gives an attacker literally zero bits
  about the DEK regardless of computing power. Getting a codeword
  right is a matter of guessing effort — that's the piece to size
  according to your threat model (word length, word count, and KDF
  cost together).
- **Back up the `.krypt` file durably** — losing it makes the vault
  unrecoverable regardless of how many codewords you have. Since it's
  a single file now, this is simpler than before, but still worth
  saying out loud.
- Uncompressed `tar` is used deliberately (mode `"w"` not `"w:gz"`) so
  ciphertext size doesn't vary with plaintext compressibility any
  more than necessary; switch to `"w:gz"` in `make_archive()` if you
  want compression and don't mind that leak.

## Other potential use cases

Beyond the two worked examples above, threshold-recoverable encryption
generally fits situations where a policy or legal requirement says "no
single party should be able to unilaterally decrypt this," and access
is rare/high-stakes rather than continuous.

**Government**
- **Two-person-rule systems, generalized to N-of-M** — e.g. "any 3 of
  7 officials," which tolerates absence/incapacitation without
  weakening the no-lone-actor requirement of the classic two-key model.
- **Escrowed decryption keys for classified/lawful-intercept archives**,
  split across officials from different branches/agencies so no single
  agency — or a rogue insider within one — can unilaterally decrypt.
- **Continuity-of-government credentials** that must survive the loss
  of some custodians but still require majority agreement to invoke.
- **Election-system key management** — tabulation-system decryption
  keys split among representatives of multiple parties/observers.
- **Diplomatic/intelligence material** where the "no mapping table"
  property matters most: seizing several codewords in one raid still
  reveals nothing about who holds the rest.

**Business**
- **M&A / escrow and dispute-resolution vaults** — deal terms or
  sensitive documents split among board members, outside counsel, and
  an escrow agent, released only by quorum.
- **Cryptocurrency/treasury cold storage** — an offline way to split
  the root key material behind a multisig wallet among founders/board,
  so no single executive can move funds alone (trustees here often
  already custody a hardware key or keypair — see `docs/pubkey-envelope-plugin.md`, proposed).
- **"Break-glass" access to root credentials** — CA keys, database
  master keys, infrastructure override codes — day-to-day access
  requires zero people, emergency access requires several specific
  people to jointly agree, with an audit trail per trustee (a strong
  fit for existing keypairs too — see `docs/pubkey-envelope-plugin.md`, proposed).
- **Whistleblower/source-protection archives** for journalism or legal
  teams, releasable only if a threshold of editors/lawyers agree.
- **Estate planning / key-person risk** — a founder's critical
  passwords or IP split among heirs, a lawyer, and a business partner.
- **Regulated data with separation-of-duties requirements** (SOX,
  HIPAA "minimum necessary" contexts) — a technical enforcement of an
  existing compliance control rather than just a policy on paper.

**Where this tool fits best:** rare, high-stakes, offline "break
glass" access with a small (tens, not thousands), semi-static trustee
set, where the vault file itself needs to be safely storable/shareable
with zero metadata leakage about who holds what. It's a poor fit for
frequent/live authorization, revoking a single trustee without a full
re-split, or online multi-party protocols — that's the domain of
proper threshold-signature schemes (e.g. FROST) or HSM-backed
multisig, which support key rotation and live quorum that this
static, split-once design doesn't.

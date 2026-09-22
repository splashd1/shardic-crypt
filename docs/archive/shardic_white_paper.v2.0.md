**SHARDIC**

Sharded Encryption for Threshold-Recoverable Vaults — and Protected-Action Ceremonies

*Enforcing Multi-Person Integrity for High-Stakes Data Recovery and Capability Authorization*

**White Paper — Version 2.0**

July 2026

Project repository: github.com/splashd1/shardic

---

# Abstract

Conventional file encryption is monolithic: whoever holds the key, or
controls the system that holds it, controls access to the plaintext —
permanently and unilaterally. **shardic** replaces that single point of
control with a **threshold-recoverable** model. A file or directory is
encrypted once under a randomly generated data encryption key (DEK), and
that DEK is then split — using Shamir's Secret Sharing over GF(256) —
into T shares distributed to T independent trustees. No fewer than a
threshold of D trustees, each supplying an individually held codeword,
can ever reconstruct the key. Below that threshold, the remaining shares
carry *zero* information about the key — a guarantee that holds
regardless of computing power, not merely one that is expensive to
break.

This version extends the paper past that starting point. shardic's
threshold-recovery mechanism was never intrinsically about *files* — it
is a mechanism for enforcing that no single party can unilaterally
invoke something. Sections 1–3 describe the mature, largely-implemented
core exactly as before: the operational need, the CLI walkthrough, and
the cryptographic mechanics, updated to reflect that shardic-envelope
and ceremony formation have since moved from proposed design to running
code. Sections 4–5 are new: they generalize the protected value from "a
file" to a **shardic protected action code (SPAC)** — any enabling
value for a protected capability, not only a decryption target — and
walk two notional missions through the full ceremony lifecycle this
generalization makes possible. Section 6 extends the security
discussion to the new material; Section 7 restates what this design
guarantees and what remains explicitly open.

Read end to end, the design is best understood as four layers, each
built on top of the last without altering what the layer below it
guarantees: sharded protection, shardic-envelope, ceremony formation,
and SPAC. §1.6 states that stack explicitly before the paper works
through it section by section.

Everything described from Section 4 onward is a **design proposal**,
not shipped functionality — flagged as such throughout, in the same
spirit as §3.6/§3.7 flagged shardic-envelope before it shipped.

# 1. The Need for Threshold-Recoverable Protection

## 1.1 Conventional Data Encryption: Monolithic, Single-Point Control

The standard model of symmetric encryption is simple: a key is
generated, data is encrypted under it, and the key is stored or shared
so that plaintext can later be recovered from the ciphertext. That
simplicity is also the model's structural weakness. Whoever possesses
the key — a person, a process, a single server — has **complete and
unilateral** power over the data it protects. Access is a binary,
anonymous fact: either you hold the key, or you don't. There is no way,
within the cryptography itself, to require that access be a *joint*
decision, or to prove after the fact who authorized a given recovery.

This single-point-of-control property persists even when the key
management around it becomes more sophisticated. Wrapping a symmetric
key with a public key so it can only be unwrapped by whoever holds the
matching private key changes *who* the single point of control is, but
not *that* there is one — the private key becomes the new monolithic
secret. Locking a key inside an HSM, a safe, or a physically secured
server changes *where* the single point of control lives, but a single
compromised operator, a single coerced administrator, or a single stolen
credential is still sufficient to defeat it. None of these supplements
change the underlying shape of the trust model: one secret, one holder,
one point of failure.

For routine data protection this is an acceptable, even desirable,
trade-off — simplicity and low friction usually outweigh the risk. It
becomes a liability precisely in the cases organizations care about
most: root credentials, master keys, and archives whose disclosure or
misuse by a single rogue, insider threat, or compromised party would be
catastrophic.

## 1.2 Sharded Encryption: Enforcing Multi-Person Integrity

Sharded, threshold-recoverable encryption addresses this by removing the
single point of control from the cryptography itself, rather than
relying on policy or process to compensate for it. Instead of one key
held by one party, the key is mathematically split into T pieces
("shares"), distributed to T independent trustees, with a threshold D
set below T. Recovering the plaintext requires at least D trustees to
each independently choose to participate. Critically, this is not merely
operationally enforced (e.g. by requiring D signatures at an application
layer) — it is **information-theoretically enforced**: with the
underlying Shamir's Secret Sharing construction, any collection of fewer
than D shares carries mathematically zero information about the key, no
matter how much computing power is applied against it.

The practical effect is that:

- No single trustee — including whoever originally created the vault —
  can ever recover the data alone.
- A rogue insider, a coerced employee, or a single compromised account
  is insufficient to cause disclosure; a collusion of at least D
  independent parties is required.
- The trustee pool can absorb the loss or unavailability of up to T − D
  trustees without losing recoverability — unlike a strict N-of-N or
  two-person rule, which has no slack.
- Every recovery event has a natural audit trail: the specific set of
  trustees who each chose to supply a codeword.

This shifts data protection from "who holds the key" — a fact about
custody — to "who agreed to unlock it" — a fact about consent,
distributed across independent parties who cannot individually override
the group.

## 1.3 Representative Use Cases

Threshold-recoverable encryption is the right tool wherever policy,
regulation, or risk tolerance already implies that no single party
should be able to unilaterally decrypt something, and where access is
rare and high-stakes rather than continuous and routine. Representative
examples include:

#### Break-glass access to critical infrastructure

A root certificate-authority private key, a production database master
key, or a SCADA override credential is locked in a vault with, say, T=7
trustees — a mix of senior engineers, security officers, and an
executive — and a D=4 threshold. Day to day, *nobody* has access to the
key at all. It is reconstructed only for a genuine emergency, and only
if four of the seven trustees each independently agree to participate.

#### Diceware-style estate and succession planning

A family or founder splits access to a password manager's master vault,
or other key-person credentials, among relatives, a lawyer, and a
business partner (T=5, D=3), using memorable, whole-word codewords that
trustees can actually commit to memory rather than write down.

#### Government and public-sector applications

- Generalized two-person-rule systems ("any 3 of 7 officials") that
  tolerate absence or incapacitation without weakening the no-lone-actor
  requirement of the classic two-key model.
- Escrowed decryption keys for classified or lawful-intercept archives,
  split across officials from different branches or agencies so that no
  single agency — or a rogue insider within one — can unilaterally
  decrypt.
- Continuity-of-government credentials that must survive the loss of
  some custodians while still requiring majority agreement to invoke.
- Election-system tabulation keys split among representatives of
  multiple parties or observers.

#### Business and regulated-industry applications

- M&A escrow and dispute-resolution vaults — deal terms or sensitive
  documents released only by quorum of board members, outside counsel,
  and an escrow agent.
- Cryptocurrency or treasury cold storage — splitting root key material
  behind a multisig wallet among founders or board members so no single
  executive can move funds alone.
- Whistleblower or source-protection archives, releasable only if a
  threshold of editors or lawyers agree.
- Regulated data with explicit separation-of-duties requirements (e.g.
  SOX, HIPAA "minimum necessary" contexts) — a technical enforcement of
  an existing compliance control rather than a policy statement alone.

*Where this approach fits best:* rare, high-stakes, offline
"break-glass" access with a small, semi-static trustee set, where the
vault file itself must be safely storable and shareable without leaking
metadata about who holds what. It is a poor fit for frequent or live
authorization, for revoking a single trustee without a full re-split, or
for online multi-party protocols — those are better served by
threshold-signature schemes (e.g. FROST) or HSM-backed multisig, which
support key rotation and live quorum that this static, split-once design
does not attempt to provide. §4 revisits this boundary once the
protected value stops being assumed to be a file.

## 1.4 How Threshold Secret Sharing Works, Conceptually

Section 3.2 gives the precise, byte-by-byte construction. Before that,
it's worth building the intuition for *why* a threshold scheme works at
all — because the obvious first guess at how to "split a key into
pieces" is not what shardic does, and doesn't have the properties §1.2
just promised.

**The obvious guess, and why it falls short.** Imagine cutting the
32-byte DEK into four 8-byte chunks and handing one chunk to each of
four trustees — or the slightly cleverer version, XOR-splitting, where
each share is random and the last one is defined so that all of them
XOR back to the key. Both can be made information-theoretically sound
in the narrow sense that holding fewer than all the pieces reveals
nothing. But both share the same structural flaw: they are
**all-or-nothing** schemes. Reconstruction needs every single piece,
with no way to ask for "any D of T." Lose one trustee, permanently, and
the key is gone forever — exactly the fragility §1.2 said threshold
recovery exists to avoid.

**The actual idea: hide the secret as a point only enough hints can
locate.** Picture the DEK not as a string of bytes but as a single
point on a graph — specifically, where a straight line crosses the
vertical axis. Draw that line so it also happens to pass through T
other points, one assigned to each trustee. Handing a trustee "their"
point tells them nothing on its own: infinitely many different lines
pass through any single point, each crossing the axis somewhere
completely different, so *every* possible secret remains equally
possible. But hand over any **two** trustees' points together, and
there is exactly one straight line that passes through both of them —
which means there is exactly one place it crosses the axis. Two points
determine a line; that's what makes D = 2 work.

Raise the threshold to three, and the trick generalizes: instead of a
straight line, use a curve with one more bend (a parabola), which takes
three points to pin down uniquely rather than two. One or two points
still leave every possible secret equally plausible — the curve simply
isn't determined yet. This is the general pattern: a threshold of D is
implemented as a curve that requires exactly D points to fix, with T
points handed out, one per trustee, all lying on that same curve.
Because the curve only needs *any* D of its T points — not a
particular D, and not all T — the scheme absorbs losing up to T − D
trustees exactly as §1.2 described, something an all-or-nothing chunk
or XOR split can never offer.

> **Why partial progress isn't a thing here.** A combination lock
> rewards partial knowledge — get two of three digits right and you
> are, in a real sense, close. A threshold secret share does not work
> that way. One trustee's point, or even D − 1 of them together,
> doesn't narrow the secret down to a short list of likely candidates;
> it leaves *every* possible value exactly as plausible as before.
> There is no partial credit, no "getting warmer," and no way to make
> attempts and rule out candidates one collusion at a time — the Dth
> point doesn't refine the answer, it is the precise moment the answer
> springs into existence.

shardic's actual implementation replaces "a line" or "a curve on a
graph" with a polynomial of degree D − 1 evaluated over a finite field,
applied independently to each byte of the DEK — the same idea above,
made precise and computable. §3.2 picks up exactly there. For a
complete, standalone treatment — including the exact polynomial
construction and why the arithmetic runs over GF(256) instead of real
numbers — see Appendix A.

## 1.5 From Data to Capability: A Preview

Everything above frames the protected value as a file — an archive
recovered, once, into plaintext on disk. That framing was never load-
bearing for the underlying guarantee: what threshold recovery actually
enforces is that a secret value comes into existence only when D
independent parties each choose to contribute toward it. A file's
plaintext is one instance of "a secret value" — not the only one.
Section 4 makes that generalization explicit and names it: **a shardic
protected action code (SPAC)** is any enabling value for a protected
capability — financial access, a physical safety interlock, a sensitive
document, an account credential — of which "decrypt this archive" is
the narrowest possible case. Sections 2–3 describe the mature core
exactly as it exists today; readers only interested in the file-vault
tool can stop at the end of §3.

## 1.6 The Capability Stack: How the Layers Build on Each Other

It's worth naming the stack explicitly before working through it
section by section, since each layer changes what's actually possible
without invalidating anything the layer beneath it guarantees:

1. **Sharded protection** (§1–§3.5, implemented). The core guarantee: a
   secret is split so that no fewer than D of T independently held
   shares can ever reconstruct it, and below that threshold, zero
   information about the secret exists to extract. This alone is
   sufficient for the personal, estate, and business scenarios in
   §1.3 — a family splitting a password manager's master key, a
   company escrowing a root credential — using the three codeword
   modes described in §6.2.
2. **shardic-envelope** (§3.6, implemented). Wraps each trustee's
   codeword in public-key encryption under a keypair the trustee
   already controls, removing the human-memorability ceiling that
   otherwise caps how strong an individual codeword can practically be
   (§6.2 revisits what this changes about codeword mode selection in
   §6.4).
3. **Ceremony formation** (§3.7, implemented). Turns "who holds a
   codeword" from an ad hoc, once-per-vault trust decision into a
   tracked, repeatable process: candidate trustees are registered
   against an identity provider, a specific quorum is selected and
   invited for a given vault, declined or timed-out slots backfill
   automatically, and delivery of each wrapped codeword is a
   single-read, addressed event rather than an out-of-band handoff.
4. **SPAC** (§4–§5, design proposal). Generalizes the protected value
   itself from "a file's plaintext" to any enabling code for a
   protected capability, and generalizes the ceremony from one fixed
   shape into something tailorable per deployment — which trustees,
   which local-unlock factors, which RTO — to fit the CONOPS and
   embedment environment of a specific client system.

Each layer is a strict superset of the guarantees below it: nothing at
layer 2 weakens layer 1's information-theoretic threshold, and nothing
at layer 4 weakens layer 2 or 3's already-implemented mechanics. A
deployment can stop at any layer and still have a complete, sound
system — layer 4 is simply where this paper's remaining open work
lives.

# 2. Concept of Operations

This section walks through the tool exactly as an operator experiences
it: first the encryption (vault creation) sequence, then the decryption
(recovery) sequence, using the command-line interface. The GUI exposes
the same two operations through the same underlying library, so the
sequence of decisions is identical — only the interaction surface
changes.

## 2.1 Operator Walkthrough: Creating a Vault

An operator with a directory of sensitive files decides on two numbers
before doing anything else: how many trustees (T) will hold a codeword,
and how many of them (D) must agree to recover the data. In this
walkthrough, five trustees are established with a threshold of three:

```
$ python3 vault_create.py \
    --input ./secret_docs \
    --trustees 5 --threshold 3 \
    --word-count 3
```

Left at its defaults, the tool:

1. Reports which key-derivation function will protect each share
   (Argon2id if available, otherwise PBKDF2), since this affects
   recovery speed and offline-guessing resistance.
2. Defaults to `--memorable` mode when no fixed word length is given,
   drawing codewords from the bundled EFF long wordlist rather than
   synthetic strings.
3. Reports its own combinatorial strength estimate for a single
   trustee's codeword phrase, so the operator can judge — before
   distributing anything — whether the chosen word count is adequate
   for the stakes involved.
4. Archives the input into a single blob, generates a random 256-bit
   data encryption key, and encrypts the archive under it.
5. Splits that key into the requested number of Shamir shares and
   protects each one under its own randomly generated codeword.
6. Writes one self-contained `.krypt` file, plus one text file per
   trustee containing only that trustee's codeword.

The actual output of the run above:

```
[i] Share protection KDF: pbkdf2 {'iterations': 400000}
[i] No --word-length given: defaulting to --memorable mode (whole real words).
[*] Memorable mode: loaded 7772 whole, real candidate words from the bundled EFF wordlist
[*] Estimated codeword strength: ~39 bits combinatorial per trustee (before any KDF
    stretching). Recovery cracks each codeword independently, so this per-codeword
    number -- not a 5-trustee total -- is the real security margin; raising
    threshold/trustee counts does not substitute for it.
[*] Archiving 'secret_docs' ...
[*] Split DEK into 5 shares, threshold 3
[*] Wrote vault container: vault_out/ce28by1pn9z8wib2.krypt (11388 bytes)
[+] Wrote 5 trustee codeword files to: vault_out/trustee_words/
    Distribute each trustee_N.txt to exactly one trustee (out of band, e.g. in person
    or over a channel they individually control), then DELETE these files from this
    machine. Recovery needs only the single .krypt file + any 3 of the 5 codewords.
```

The operator's remaining job at this point is entirely procedural, not
cryptographic: distribute each `trustee_N.txt` to exactly one trustee,
out of band, over a channel that trustee individually controls — and
then delete the local copies. The tool deliberately does not automate
distribution; who receives which codeword, and how, is a trust decision
that belongs to the operator, not the software.

## 2.2 Operator Walkthrough: Recovering a Vault

At recovery time, any three of the five trustees supply their codewords
— the operator does not need to know or specify which three:

```
$ python3 vault_recover.py vault_out/ce28by1pn9z8wib2.krypt \
    --word "broadside-repulsion-subway" \
    --word "valuables-repeater-oversleep" \
    --word "winking-portly-diffusion"
```

Actual output:

```
[i] This vault requires 3 of 5 codewords to recover.
[i] Share protection KDF: pbkdf2
[+] Codeword accepted (1/3).
[+] Codeword accepted (2/3).
[+] Codeword accepted (3/3).
[*] Reconstructing DEK from recovered shares ...
[*] Decrypting archive ...
[*] Success. Recovered contents extracted to: /tmp/wp_demo/recovered_out
```

Two operational details are worth calling out. First, codewords can be
entered in **any order** — recovery does not ask "which trustee are
you," it simply tries each supplied codeword against every
not-yet-matched share until one authenticates (see §3.4). Second, if
fewer than D codewords match, or any of them are wrong, the tool reports
how many were accepted and stops — it never writes partial or
best-guess output.

## 2.3 shardic-prime: A Mandatory-Trustee Variant

The base scheme treats every trustee identically — any D of T codewords
recover the vault, full stop. **shardic-prime** is a separate variant,
with its own CLI tools and its own container format, that adds one
*essential* trustee on top of the base scheme: the **prime trustee's**
codeword must always be among those supplied, no matter how many other
codewords are gathered. The remaining trustees form an ordinary
interchangeable pool for the rest of the threshold.

This fits situations where one specific role — an estate's executor, an
organization's security lead — must always sign off, while the people
backing them up can be any qualifying subset. In T=4, D=3 prime-trustee
terms, that means 1 prime trustee plus 3 pool trustees, and recovery
needs the prime's codeword plus any 2 of the 3 pool codewords:

```
$ python3 vault_create_prime.py --input ./my_directory \
    --trustees 4 --threshold 3 \
    --word-length 6 --word-count 2
$ python3 vault_recover_prime.py VAULT.krypt
```

All three pool codewords, gathered without the prime trustee's, recover
nothing — a property guaranteed by the construction itself (§3.5), not
merely enforced by the CLI. As with the base scheme, recovery does not
require the operator to say in advance which supplied codeword belongs
to the prime trustee; it is identified automatically once decryption
succeeds. **§4 revisits the prime trustee's role directly** — it turns
out to generalize to a hardware-embodied instance without requiring any
new mathematics at all.

# 3. Technical Mechanics

This section describes how the `.krypt` container actually protects
data: how the data encryption key is generated, how Shamir's Secret
Sharing protects its recovery, how each individual share is, in turn,
protected by a codeword-derived key, and how the scheme has since
extended into public-key-wrapped delivery and multi-party ceremony
formation.

## 3.1 Archive and Data Encryption Key

Vault creation proceeds in a fixed sequence:

1. The input file or directory is bundled with `tar` into a single
   blob, so any input shape — one file or an entire directory tree —
   is handled uniformly. The archive is deliberately left uncompressed
   (mode `"w"`, not `"w:gz"`) so ciphertext size does not vary with
   plaintext compressibility any more than strictly necessary —
   compression can otherwise leak information about content through
   size alone.
2. A random 256-bit data encryption key (DEK) is generated using a
   cryptographically secure random source (`secrets.token_bytes`).
3. The archive is encrypted exactly once, under that DEK, using
   AES-256-GCM with a randomly generated 96-bit nonce. GCM provides
   both confidentiality and built-in tamper detection: any modification
   to the ciphertext causes authentication to fail rather than silently
   decrypting to garbage.

At this point, the DEK is the single piece of secret material standing
between the ciphertext and the plaintext — exactly as in conventional
symmetric encryption. What differs from the conventional model is what
happens to that key next.

## 3.2 Shamir's Secret Sharing over GF(256)

Rather than being stored or handed to a single custodian, the DEK is
split using a byte-wise implementation of Shamir's Secret Sharing (SSS)
over the finite field GF(2⁸) — the same construction used by classic
tools such as `ssss`, and the same field arithmetic AES itself uses
(generator 3, reduction polynomial 0x11B).

The construction, applied independently to each of the DEK's 32 bytes:

- Each byte of the secret becomes the constant term of a random
  polynomial of degree D − 1, with the remaining coefficients drawn
  uniformly at random.
- Each of the T shares is that polynomial evaluated at a distinct
  x-coordinate (1 through T), across all 32 byte positions
  simultaneously.
- Reconstruction takes any D shares and applies Lagrange interpolation
  at x = 0, independently per byte position, to recover the original
  secret byte.

> **Why this is information-theoretic, not merely computational.** A
> polynomial of degree D − 1 is uniquely determined by any D points on
> it — but with only D − 1 points, *every* possible value of the
> constant term (the secret byte) remains equally consistent with those
> points. An attacker holding D − 1 shares therefore learns exactly
> zero bits about the DEK, regardless of computing power, time, or
> future cryptanalytic advances against AES itself. This is the
> property that separates threshold recovery from key-splitting
> schemes built on secret-sharing-flavored encryption tricks that are
> only computationally, not information-theoretically, hard to break
> below threshold. "Information-theoretic" security means a guarantee
> that holds regardless of computing power — not because breaking it
> is *hard*, but because the information needed to break it simply
> isn't *there*.

## 3.3 Codeword-Derived Key Protection of Shares

A raw Shamir share is still just data — if written to disk unprotected,
whoever possesses D of them could reconstruct the DEK without any
trustee's cooperation at all. Each share is therefore itself
individually encrypted before being placed in the vault:

1. A random, human-typeable codeword is generated for the share (see
   §5's mission vignettes and §6.2 for the available modes: memorable,
   dictionary, and synthetic).
2. A random salt is generated, and a 256-bit key is derived from the
   codeword and salt using one of two supported key-derivation
   functions: PBKDF2-HMAC-SHA256 (400,000 iterations by default — a
   zero-extra-dependency baseline) or Argon2id (`time_cost=4`,
   `memory_cost=256 MiB`, `parallelism=4` by default — memory-hard,
   and preferred when the optional `argon2-cffi` package is available,
   since memory-hardness raises the cost of large-scale parallel
   GPU/ASIC guessing far more than an equivalent-wall-clock PBKDF2
   setting does).
3. The share (its x-coordinate plus its 32 y-bytes) is encrypted with
   AES-256-GCM under that derived key, using its own random nonce.

The vault records, per share, only an opaque triple: `{salt, nonce,
ciphertext}`. Which KDF method and parameters were used are recorded
once in the container's metadata — self-describing, so recovery never
needs to be told out-of-band which settings a given vault used.

## 3.4 The .krypt Container and Zero-Leakage Indexing

All of the above — metadata and ciphertext — is bundled into a single
`.krypt` file: an 8-byte magic header, a length-prefixed JSON metadata
block, and the raw AES-GCM ciphertext of the archive (stored as raw
bytes, not base64-encoded, avoiding a ~33% size penalty). This is
deliberate: there is exactly one file to copy, email, or upload, with
nothing to accidentally separate from a companion metadata file.

The metadata's list of protected shares carries **no mapping** from
record to trustee, and no mapping from record to codeword — each entry
is simply an opaque `{salt, nonce, ciphertext}` triple, and the order of
entries in the file is randomly shuffled at creation time. Recovery
works by **trial matching**: each codeword the operator supplies is
tried, via its derived AES-GCM key, against every not-yet-matched share
record in the vault. GCM's authentication tag makes this a reliable
oracle — the correct pairing decrypts successfully, and every incorrect
pairing fails fast with an authentication error rather than producing
plausible-looking garbage.

With T in the tens, this exhaustive trial is effectively instantaneous,
and it has a meaningful security consequence: the `.krypt` file,
examined on its own, reveals nothing about which share belongs to which
trustee, or how many codewords would need to be compromised together to
threaten a specific subset of the data. Seizing the file, or several
codewords, in isolation yields no assignment information beyond what
successful decryption itself reveals.

## 3.5 How shardic-prime Varies

shardic-prime layers a one-time-pad mask over the ordinary Shamir
construction described above, rather than introducing new field
arithmetic. Given the DEK as the secret:

```
mask          = random bytes, same length as the DEK
masked_secret = DEK XOR mask
pool_shares   = split_secret(masked_secret, pool_threshold, pool_size)
```

The prime trustee's codeword protects `mask` directly — an
all-or-nothing pad, not a point on a Shamir polynomial. Recovery
requires both `mask` and at least `pool_threshold` pool shares:

```
masked_secret = reconstruct_secret(pool_shares)
DEK           = masked_secret XOR mask
```

Without `mask`, the pool shares — even *all* of them — reconstruct only
`masked_secret`, which is uniformly random and indistinguishable from
noise without the mask to remove. Without at least `pool_threshold`
pool shares, `mask` alone reveals nothing either. Both halves of the
construction retain the same information-theoretic guarantee as the
base scheme; layering them is what makes the prime trustee
mathematically essential rather than merely conventionally required.

A shardic-prime vault is tagged in its own metadata (`"scheme":
"prime-trustee"`) specifically so it can never be opened by, or
confused with, the base scheme's recovery tool, and vice versa — the
two container formats are deliberately incompatible rather than
silently cross-readable.

This one-time-pad construction turns out to be the load-bearing piece
of everything in §4: because `mask` is *just a value*, nothing about
`reconstruct_secret_with_prime()` requires that value to be held by a
human. §4.2 reuses this exact code, unmodified, to bind the same
mathematics to a piece of hardware instead.

## 3.6 shardic-envelope: Public-Key-Wrapped Codewords (Implemented)

Every codeword mode described in §6.2 — memorable, dictionary,
synthetic — ultimately protects a share with something a human being
can recall or transcribe, and §6.1 establishes that this individual
codeword strength, not the Shamir/AES layer, is the design's real
computational bottleneck. **shardic-envelope** removes that ceiling
entirely for trustees willing to hold a cryptographic keypair, by
wrapping each trustee's codeword in public-key encryption under a key
*they* already control — rather than under a memory limit. As of this
writing, shardic-envelope is implemented and demonstrated end-to-end
(`shardic_envelope_crypto.py`, `demo/combiner/app.py`), not merely
proposed — the design intent below is now running code.

- Operates strictly on the *output* of vault creation — the plaintext
  files a trustee would otherwise have received — rather than
  modifying `vault_core.py` itself, so the existing encrypt/split/KDF
  path is untouched and the base scheme's guarantees are unaffected.
- Wraps each codeword in a hybrid, ECIES-style envelope (X25519 ECDH +
  HKDF-SHA256 + AES-256-GCM), deliberately shaped to mirror the vault's
  existing `{salt, nonce, ciphertext}` share-record convention rather
  than inventing a new format.
- The **combiner** — the service that holds `.krypt` ciphertext and
  every wrapped envelope, and orchestrates registration and recovery —
  never receives a plaintext codeword at any point, only shards derived
  locally by each trustee and re-wrapped for the combiner's own public
  key on the way back.

Recovery is unchanged from a trustee's point of view in the base
scheme: they still supply a plaintext codeword or its derived shard.
What changes is *provisioning* — the trustee's own device decrypts an
envelope locally, once, to obtain the value they would otherwise have
had to memorize or write down themselves.

## 3.7 Ceremony Formation, Credentials, and Delivery (Implemented)

§3.6 raises two questions that a follow-on design phase answers with
running code, not just a sketch: how does a trustee's public key get
established and trusted in the first place, and how does an operator
convene a specific quorum of trustees for a given vault rather than
improvising trust decisions ad hoc each time?

- **Registration.** Candidate trustees are drawn from a dedicated
  Keycloak group, queried via a read-only service account scoped to
  that group. Each trustee's keypair is generated **client-side only**
  — the private key never transits, or is even briefly held by, any
  server shardic controls. This deliberately keeps identity/selection
  (Keycloak's job) cleanly separated from key custody (never Keycloak's
  job) — a compromised or unavailable identity provider can block
  registration, but cannot on its own expose a DEK, forge a share, or
  weaken the D-of-T guarantee.
- **Ceremony formation.** An operator (authenticated via a dedicated
  `shardic-operator` realm role, replacing an earlier shared static
  admin token) selects T primary trustees plus an ordered backup list
  from the registered candidate pool, and issues invitations. Declined
  or timed-out invitations **backfill automatically** from the ordered
  backup list — race-safe, so a late acceptance from an
  already-backfilled slot is rejected rather than silently double-
  filling it. A ceremony is `formed` once every slot is accepted, or
  `failed` if the backup list is exhausted first. An explicit
  separation-of-duties check blocks the operator who forms a ceremony
  from also self-selecting as one of its trustees.
- **Delivery.** Wrapped envelopes are deposited at an authenticated,
  single-read drop point, addressed by trustee identity rather than a
  contact channel. The trustee fetches their own envelope themselves,
  once. "Exactly once" redemption functions as a *detection* mechanism
  — a second read attempt on an already-claimed envelope is a signal
  something is wrong, not a guarantee nothing can go wrong.
- **Recover.** Unaffected. §2.2's walkthrough describes the same
  underlying act either way.

The organizing principle across all of this: **identity and selection
stay cleanly separated from key custody, and both stay separated from
the offline, fail-closed recovery math** described in §3.1–§3.4. A
compromised identity provider or a stalled ceremony can block
*provisioning*; neither can, on its own, weaken the D-of-T guarantee
itself. §4 builds directly on top of this ceremony-formation machinery
— it is reused unmodified for the pool-trustee side of a SPAC ceremony.

# 4. The SPAC Ecosystem: Extending shardic Beyond File Decryption

**Status: design proposal.** shardic's protection can be extended beyond the demonstrated file protection and supporting shardic-envelope ceremony that has been fielded to deliver a much more critical level of protection at system level.This section, moves beyond the fielded capabiility of §1–§3. shardic Protected Action Code (SPAC) describes a proposed extension that is targeting the flexibility to be embeddable in a variety of clients. As such there is no reference implementation yet —`docs/spac-concept.md`, `docs/shardware-token.md`, and`docs/shardware-token-embed-extract.md` in the project repository are
the design record this section distills into narrative form. Nothing
here is a claim about present functionality.

## 4.1 From Data to Capability: PT SPAC and CT SPAC

§1.5 previewed the reframe; here is the full statement of it. The
plaintext shardic protects has never had to be a file — it is, more
generally, the *enabling value for some protected action*: gaining
financial access, arming a safety-critical system, unlocking a
sensitive document, or granting account access, wherever "the right
D-of-T parties agreed" should be the actual gate on the action, not
merely a procedural approval layered on top of it. A **shardic
protected action code (SPAC)** names that enabling value; **PT SPAC**
and **CT SPAC** name its plaintext and ciphertext forms, in exactly the
same relationship as any other plaintext/ciphertext pair in this
project. "Decrypt this file" is simply the special case where the
protected action is "the codeword holder gets to read the plaintext" —
the same mechanism, applied to the narrowest possible action.

This reframe has real precedent outside cryptography. **Permissive
Action Links (PAL)** — a code required to authorize a safety-critical
action, withheld until an authorized multi-party release procedure
completes — is the closest existing analog for gating a *capability*
rather than merely data. **Two-Person Integrity / the Two-Man Rule**
(the doctrinal basis for "no single individual can access or execute X
alone") is the vocabulary for what the trustee threshold, plus the
separation-of-duties enforcement already described in §3.7, already
implement. Both sit alongside, not instead of, the commercial patterns
already used throughout this design — HSM M-of-N quorum authorization,
FIDO2, TPM sealing — which answer *how* to build the mechanics once the
*why* is established.

## 4.2 The Shardic Client Module and the Fielded Prime Element

A consuming system — the thing that actually executes the protected
action — is built with a "plugin" at the critical-path point where the
PT SPAC is needed. During development and test, the real PT SPAC sits
in that pipeline directly, so the system can be validated end-to-end.
Before fielding, PT SPAC is swapped for a CT SPAC embedded in a
**shardic client module** at that same plugin point — the consuming
system's analog of the trustee apps and combiner described in §3.6–3.7,
except this one lives inside somebody else's execution pipeline rather
than being shardic's own frontend. The interface between the client
module and the shardic ceremony infrastructure is treated as a formal
contract (an Interface Control Document, in the sense that term is used
in systems engineering) rather than an informal library call, given
what is plugged into it.

The discipline already established in §3.6 — never persist a secret
value longer than strictly necessary — extends past the combiner into
this new boundary: PT SPAC should exist in the client module's memory
only long enough to hand off to (or itself trigger) the protected
action, then be zeroized. This is a new boundary for an existing
invariant, not a new invariant.

**Fielded-system binding** is the property that makes this safe to
field at all: a copied CT SPAC, combined with a fully legitimate D-of-T
trustee quorum, must not be sufficient to arm the protected action on a
*different* instance of the client module than the one it was emplaced
into. This needs no new cryptography — it reuses §3.5's mask/pool
one-time-pad construction unmodified, with one substitution: the
fielded system's own hardware-sealed secret stands in for `mask`. The
device performing this role is named a **Fielded Prime Element** — a
hardware-embodied instance of the prime-trustee role from §2.3/§3.5,
just as a `shardware-token` (§4.3) is the device and a shard is the
value it carries, a Fielded Prime Element is the device and `mask` is
the value it holds:

```
mask        = the fielded system's own hardware-sealed secret
              (PUF/secure-element, non-extractable, generated once at
              emplacement, never leaves this hardware, never typed by
              a human, never a codeword)
pool_shares = ordinary trustee shares, delivered by shardware-token or
              network exactly as in §3.6-3.7
DEK         = reconstruct_secret_with_prime(mask, pool_shares)  -- unmodified
CT_SPAC     = AES-256-GCM(PT_SPAC, DEK)                         -- unmodified
```

Copy `CT_SPAC` to different hardware and bring a full legitimate
trustee quorum along; reconstruction still fails, because `mask` is
bound to one specific piece of silicon and was never extractable from
it. This design is deliberately scoped to **one specific piece of
hardware, full stop** — no multi-unit redundancy. If the fielded
hardware is replaced, `mask` is gone with it; there is no export path,
matching the position this project already takes on a lost trustee
device (re-provision, don't migrate the secret).

## 4.3 shardware-token: Hardware-Based Ceremony Variants

Two variants exist for how a physical hardware token participates in a
ceremony, differing in how much trust the token itself has to carry:

**Physical carriage.** A hardware token can simply be the *transport*
for an already-wrapped shard, replacing a network hop with a
courier, hand-off, or safe-deposit retrieval — useful for a
ceremony that wants to run entirely air-gapped past registration. The
token itself can be genuinely dumb storage: since the shard is already
public-key-wrapped before it ever reaches the token, there is nothing
unencrypted on it to protect. The open question this variant leaves is
identity — without a live authenticated session, "whose shard is this"
needs either an attesting operator or a trustee-held signing key.

**PUF-sealed embed/extract.** A hardened variant answers that question
cryptographically instead. The token generates its own keypair locally
at "embed" time (vault creation), receives a shard wrapped to that
keypair, and seals it into PUF/secure-element-backed storage that
requires a matching physical measurement of the chip itself to ever
reproduce the storage key — the standard "fuzzy extractor" construction
used by real hardware such as SRAM-PUF and ring-oscillator-PUF secure
elements. At "extract" time (recovery), the token only releases its
shard against a vault-signed **extraction grant**: a short-lived,
token-bound, nonce-fresh authorization, chained back to a rarely-touched
root signing key through an intermediate that is rotated on a policy
schedule rather than touched per ceremony. A single, live, human
operator authorizes each grant — sufficient because the operator can
only approve or deny a request a genuine physical token already
originated; the real multi-party control is the trustee-token
convening itself, not the operator headcount.

Both variants keep the underlying confidentiality guarantee identical
to §3.6's network path — physical carriage changes *what carries* a
value, never *what protects* it.

## 4.4 Roles and Governance

A SPAC ceremony introduces roles beyond the trustee/operator pair
already established in §3.7, each answering a distinct question and
each deliberately kept separate from the others so that no single
compromised role can undermine the whole ceremony:

| Role | Answers | Held by |
|---|---|---|
| **Trustee** (pool) | Who must jointly agree to recover? | Ordinary shardic-envelope trustees, unchanged from §3.6–3.7 |
| **Fielded Prime Element** | What binds recovery to one specific piece of fielded hardware? | The fielded system's own sealed secret — never a party at all |
| **Local custodian** | Who is physically present to authorize the fielded hardware's own local unseal? | Whoever holds the deployment's chosen possessed (key/token) or known (PIN/passphrase) factor — a role, not an identity, so it transfers across shift changes without re-provisioning |
| **Operator** | Who authorizes a given extraction request? | A single, on-call `shardic-operator`-equivalent role, barred from authorizing a grant naming their own token |
| **Approver** | Who attests that the value being protected is the correct, tested one? | An authority independent of whoever performs the wrap/emplacement step, holding a distinct signing key from the extraction-grant chain |

The Approver's role deserves particular emphasis because it closes a
gap that is easy to miss: AES-256-GCM already guarantees that a CT SPAC
decrypts to *exactly* what was originally encrypted, or fails loudly —
but it says nothing about whether what was encrypted was *correct* in
the first place. An accidental stale value, or a malicious substitution
at wrap time, would otherwise sail through untouched. The Approver
signs a commitment to the validated PT SPAC at approval time,
independent of the wrap operator; that commitment is checked once,
slowly and thoroughly, at emplacement, and again, cheaply and quickly,
at every arming event via a fast wrapped-MAC derived from the same
approval — so verifying authenticity never has to trade away
timeliness.

## 4.5 Availability, Latency, and CONOPS Trade-offs

Not every SPAC deployment has the same tolerance for how long a
ceremony takes. Recovering a file vault comfortably tolerates a slow,
deliberate, hours-long process; releasing time-critical financial
access or a safety-critical authorization plausibly cannot. Rather than
impose one universal answer, this design treats the target **RTO**
(recovery time objective) as a per-deployment parameter, driven by the
actual **CONOPS** — the concept of operations describing who the
trustees, operator, and custodians really are, how they are staffed,
and what infrastructure already exists to reach them.

Three points in a ceremony drive nearly all of the achievable latency,
and each is a real trade against resistance to unauthorized access, not
merely a performance knob:

- **Convening the quorum.** Pre-forming a ceremony ahead of the moment
  of need (§3.7's ceremony-formation machinery, reused unmodified)
  converts "select, invite, wait for acceptance" into a one-time setup
  cost paid before the RTO clock starts — the single largest lever
  available. An ad hoc, cold-start convening can take hours; a
  pre-formed, on-call quorum can respond in seconds to minutes.
- **Share delivery.** A network path is near-instant; physical
  carriage (§4.3) is inherently minutes to days, depending on
  distance and custody logistics. Air-gap independence and a tight RTO
  are largely mutually exclusive properties — a deployment chooses the
  one it actually needs.
- **Endgame unlock.** A single operator and a single local custodian
  are each fast, cryptographically sufficient decisions — but a lone
  authorized person who cannot be reached is a single point of
  *availability* failure, distinct from being a single point of
  *authorization*. An on-call backup roster for both roles, modeled on
  §3.7's ordered-backup-list mechanism, protects availability without
  weakening the one-authorizer, one-custodian property at all.

None of these levers ever reduce how many independent parties are
cryptographically required — every latency improvement here comes from
pre-positioning and parallelizing already-required inputs, never from
requiring fewer of them. A fast, pre-formed, networked, single-tap
ceremony is genuinely fast, but a coerced or compromised set of
already-standing parties moves through it just as fast; a slow,
physically-carried, dual-custodian ceremony is genuinely slow, but that
same friction is often a deliberate deterrent that creates real-world
opportunities for something to be noticed before completion. Stating a
target RTO is therefore also, implicitly, stating how much of that
friction a given mission is willing to trade away — a decision the
CONOPS has to make on purpose, not something this design should default
on its behalf. §5 walks two notional missions through exactly this
trade.

# 5. Notional Missions and Ceremony Lifecycle

**Status: illustrative, notional.** Both vignettes below are
constructed examples, not descriptions of any real system or
deployment. They're intended to walk the full SPAC lifecycle — approval,
emplacement, fielded operation, ceremony formation, and arming — against
a concrete "as-is" baseline. Numeric trustee counts and thresholds are
for illustration.

## 5.1 Vignette A: Escrowed Authorization of a High-Value Treasury Disbursement

**Mission.** A financial institution's treasury system can execute wire
disbursements above a defined threshold only with genuine, non-
bypassable multi-party authorization, replacing a conventional
dual-control approval workflow.

**As-is baseline.** Two named officers each approve a pending
disbursement in a web application. The control is enforced entirely by
application logic and an audit log: a single compromised administrator
account, a shared or hijacked session, or two coerced approvers acting
under common pressure can produce two valid-looking approvals with no
cryptographic guarantee that either approval reflects genuine
independent intent. The audit trail records that two accounts clicked
"approve" — it cannot prove that two independent human decisions
actually occurred.

**Notional shardic-SPAC design.**

- PT SPAC: the treasury system's high-privilege disbursement-signing
  credential.
- T=5 pool trustees (treasury officers), D=3 pool threshold, plus one
  Fielded Prime Element embedded in the treasury platform's own
  HSM-backed appliance — the disbursement can never be signed on any
  other machine, even by the same five officers.
- Approver: the controller function, independent of whoever operates
  vault creation, cryptographically attesting that the wrapped
  credential is the correct, currently-authorized signing key.
- Ceremony formation: a standing, pre-formed quorum of treasury
  officers with an ordered backup list, per §3.7 — no ad hoc
  convening required at disbursement time.
- Operator: a compliance officer, authorizing each extraction request;
  barred from also being one of the five treasury-officer trustees.
- Local custodian: a data-center technician holding a physical
  key-switch at the appliance itself.
- Delivery and RTO: network share delivery (§4.3), targeting an RTO of
  minutes — appropriate for time-sensitive treasury operations, at the
  cost of the air-gap property a slower design could otherwise offer.

**Lifecycle walkthrough.** *Approval* — the controller validates the
signing credential in a test environment and signs a commitment to it.
*Emplacement* — the credential is wrapped as CT SPAC, split across the
five officer-trustees and the appliance's Fielded Prime Element, and
destroyed everywhere else. *Fielded operation* — the appliance runs
normally, holding only CT SPAC. *Ceremony* — a disbursement above
threshold triggers a notification to the standing quorum; three of five
officers respond, the compliance officer authorizes the extraction
grant, the on-site custodian's key-switch unlocks the Fielded Prime
Element locally. *Arming* — DEK reconstructs, the fast wrapped-MAC
check confirms the credential matches the controller's original
approval, the disbursement executes, and every secret value involved is
zeroized immediately after.

| Dimension | As-is (dual-control app logic) | shardic-SPAC |
|---|---|---|
| Protection | Enforced by software/process; bypassable by whoever administers it | Enforced by mathematics; below-threshold shares carry zero information regardless of administrator access |
| Safety | Silent failure modes possible if application logic has a bug | Fail-loud: AES-GCM authentication rejects any incorrect or tampered value outright |
| Assurance | Audit log proves which *accounts* clicked approve, not which *people* independently chose to | Non-repudiable: reconstruction is only possible if D independent trustees each supplied a genuine share |

## 5.2 Vignette B: Notional Safety-Interlock Release Authorization

**Mission.** A notional platform's safety interlock must transition from
a safed to an operational state only upon a release-enable value
becoming available, and only through the deliberate, independent
agreement of multiple authorized parties — the same organizational
problem Permissive Action Links (§4.1) solve, described here purely at
the level of the authorization ceremony, with no operational or
technical detail about any actual system.

**As-is baseline.** A physical lock or sealed code, held by a single
on-duty officer, released under a procedural two-person-rule enforced
by human witnessing rather than any cryptographic mechanism. A single
coerced or compromised individual with physical access, acting alone,
can potentially defeat a procedural control; there is no
mathematically non-repudiable record of which specific individuals
authorized a given release, only paper logs and witness attestations
that can themselves be falsified or coerced.

**Notional shardic-SPAC design.**

- PT SPAC: the notional release-enable value.
- T=5 pool trustees (a qualified duty crew), D=3 pool threshold, plus a
  Fielded Prime Element embedded in the platform's own secure-element
  hardware.
- Local custodian factor: **dual** key-switches (the "two local
  factors" option from §4.4), reflecting that a safety-critical
  interlock plausibly warrants the strongest available local control
  rather than the single-custodian default.
- Approver: an independent technical authority, distinct from the
  operational chain, attesting that the embedded value is the
  correctly certified one — not a stale or substituted version.
- Ceremony formation: a standing, pre-formed, on-alert quorum, targeting
  an RTO of seconds to low minutes.
- Operator: a command-authority representative, authorizing the
  extraction grant as the cryptographic analog of an authorized release
  order.

**Lifecycle walkthrough.** *Approval* — the technical authority
validates and signs a commitment to the release-enable value.
*Emplacement* — the value is wrapped as CT SPAC and split across the
duty crew and the platform's Fielded Prime Element; the plaintext is
destroyed everywhere else. *Fielded operation* — the platform holds
only CT SPAC, indefinitely, with no live dependency on the crew, the
operator, or the network. *Ceremony* — an authorized release order
triggers convening of the standing duty crew; three of five respond,
the command-authority operator authorizes the extraction grant, both
local key-switches turn simultaneously. *Arming* — DEK reconstructs,
the fast integrity check confirms the value matches the technical
authority's original certification, the interlock transitions state,
and every secret value is zeroized immediately after.

| Dimension | As-is (procedural two-person rule) | shardic-SPAC |
|---|---|---|
| Protection | A single coerced/compromised individual with physical access is a structural risk | Mathematically requires genuine independent agreement from D distinct trustees, not merely two people in a room |
| Safety | A wrong or substituted code may not be detected until use | Fail-loud at multiple points: AES-GCM authentication, plus an independent approver-signed integrity check before the value is trusted |
| Assurance | Paper logs and witness statements, alterable or coercible after the fact | A ceremony's participant set is a fact about which independent parties each supplied a genuine cryptographic contribution — not a claim resting on anyone's later testimony |

# 6. Security Discussion

§6.1–§6.3 below characterize codeword strength as it applies to the
base, human-facing shardic tools described in §1–§3.5 — the case where
a trustee actually generates, recalls, or transcribes their own
codeword by hand, and where this analysis stays directly relevant for
anyone using the base scheme on its own. Once a deployment adopts
shardic-envelope, ceremony formation, or SPAC (§3.6 onward), this line
of discussion becomes largely moot: an envelope-delivered codeword is
never memorized, so it can be generated with entropy on par with
ordinary cryptographic key material rather than being bounded by what
a human can recall. §6.1–§6.3 are retained here because the base
scheme remains a fully supported, standalone capability in its own
right; §6.4 states the envelope-era amplification explicitly.

## 6.1 Two Different Kinds of Strength: Key Length vs. Trustee Threshold

It is worth being explicit about which parts of this design are
information-theoretically secure and which are only computationally
secure, because they respond to completely different levers.

- The 256-bit DEK, and the Shamir split protecting it, are effectively
  unconditional: below the threshold D, shares carry zero information
  about the key regardless of an attacker's computing power, and
  AES-256 itself has no known practical cryptanalytic shortcut.
  Raising T or D changes *how many independent parties* must collude,
  not how hard any individual share is to attack directly — each is
  already effectively unbreakable on its own.
- Each individual codeword, by contrast, is only as strong as its own
  guessing space and KDF cost — this is ordinary computational
  security, and it is squarely the operator's responsibility to size
  correctly. Because shares are trial-matched independently (§3.4), a
  higher threshold D does *not* compensate for weak codewords: an
  attacker only ever needs to crack D individual codewords, each on its
  own merits, never the full set at once, and never in combination.

*In short:* raising trustee counts strengthens the collusion
requirement; it does nothing for a codeword that is individually too
weak. The two knobs must both be tuned, and neither substitutes for the
other.

## 6.2 Codeword Modes: Security and Usability Trade-offs

Three codeword generation modes are available, trading recall
difficulty against density of entropy per character. This trade-off is
the original underpinning of codeword-based share protection, and it
remains exactly the right toolkit for the personal and business
scenarios in §1.3, where a trustee is genuinely expected to memorize or
hand-transcribe their own codeword. §6.4 revisits which mode is the
better default once that assumption no longer holds.

#### Memorable mode (default)

Draws whole, real, unfiltered-by-length words from a dictionary — the
bundled EFF long wordlist (7,772 words, ~12.9 bits/word) by default.
This is the classic diceware approach: real words engage semantic
memory in a way synthetic syllables do not, so a trustee can actually
recall a phrase rather than needing to store it. It is also, per word,
the **strongest** of the three sources — a larger, unfiltered candidate
pool beats a length-filtered one.

#### Dictionary mode

Words of exactly a specified length are drawn from a supplied wordlist
file. Useful when every codeword should have a uniform visible shape,
but filtering a natural-language dictionary down to one length
typically leaves only hundreds to low thousands of candidates —
roughly 8–11 bits per word, meaningfully weaker than memorable mode's
unfiltered pool.

#### Synthetic mode

Pronounceable random words are generated from an alternating
consonant/vowel pattern at a specified length, with no dictionary at
all. This produces far more combinations per length than a
natural-language dictionary can (roughly 3.36 bits per character from
the base alphabet sizes), but the syllables carry no meaning, making
them denser but harder to actually remember than real words of
equivalent length.

In every mode, word **count** is what actually establishes a real
security margin — each additional word roughly multiplies the guessing
space.

## 6.3 Tuning Options

Beyond codeword mode and count, two further levers match protection
strength to threat model and operating constraints: KDF selection and
cost (Argon2id's memory-hardness resists parallel GPU/ASIC offline
guessing far better than PBKDF2 at equivalent wall-clock cost), and
trustee count and threshold (raising T − D increases tolerance for
unavailable or lost trustees; raising D relative to T raises the bar
for collusion at the cost of requiring more participants for every
legitimate recovery). Because the KDF choice is fixed at creation time
and recorded in the vault's own metadata, recovery always applies
exactly the settings the vault was created with — no fallback,
negotiation, or downgrade attack against the KDF is possible after the
fact.

## 6.4 Impact of shardic-envelope and Ceremony Formation

Because §3.6's construction changes what protects a codeword — a
private key instead of human memory — it changes the analysis in this
section rather than sitting outside it.

The direct security benefit is removing the memorability ceiling that
shapes §6.2 entirely: a codeword that only needs to survive one local
decryption, immediately before use, can be made arbitrarily long and
high-entropy with no usability penalty at all, pushing each individual
codeword's computational security arbitrarily close to §6.1's
information-theoretic guarantee. Because memorability was the *only*
reason §6.2 traded density for recall, that trade stops applying the
moment a codeword is never recalled by a human at all: **synthetic
mode — the densest bits-per-character of the three, and previously the
least usable — becomes the natural baseline for any envelope-provisioned
trustee.** Memorable and dictionary mode remain the correct choice
specifically where a human still holds their own codeword in their
head or on paper — the standard personal and business deployments of
§1.3 — but they are no longer the default assumption once §3.6 is in
play; mnemonic effort simply stops being a variable worth optimizing
for. That gain relocates rather than eliminates the trust dependency:
the trustee's private key becomes a new single point of failure per
share, and credential resolution introduces a new trust boundary of
its own. Ceremony formation's
separation-of-duties enforcement (§3.7) directly mitigates one specific
instance of this: an operator who forms a ceremony cannot also
self-select as one of its trustees, closing off the most direct form of
operator self-dealing.

## 6.5 Security Considerations Specific to SPAC

The SPAC extension in §4–§5 introduces failure modes that have no
analog in the file-vault core, each addressed by a specific design
choice rather than left to policy:

- **Fielded-system binding.** Without §4.2's Fielded Prime Element
  construction, a copied CT SPAC and a legitimate trustee quorum would
  be sufficient to arm the protected action anywhere, not only on the
  intended hardware. Binding is enforced by reusing §3.5's
  one-time-pad mathematics unmodified — an algebraic guarantee, not a
  policy one.
- **Content authenticity versus ciphertext integrity.** AES-GCM
  guarantees a CT SPAC decrypts to exactly what was encrypted; it says
  nothing about whether what was encrypted was *correct*. The
  Approver role (§4.4) closes this gap with an independently signed
  commitment, checked at both emplacement and arming.
- **Single-operator and single-custodian sufficiency.** Neither role
  being singular weakens the overall guarantee, because neither can
  originate a ceremony action alone — an operator can only approve or
  deny a request a genuine physical or cryptographic event already
  triggered. This is a sufficiency argument, not an availability one;
  §4.5's on-call backup rosters address availability separately,
  without reintroducing a second decision-maker into any single step.
- **RTO as a stated trade, not a free variable.** §4.5 makes explicit
  that faster ceremonies are not free — every latency reduction is
  pre-positioning of already-required inputs, and a CONOPS that
  chooses a fast, networked, pre-formed ceremony is choosing a
  different resistance profile against unauthorized access than a
  slow, physically-carried, dual-custodian one, on purpose.

# 7. Summary

## 7.1 What Sets This Apart From Conventional Symmetric Encryption

Conventional symmetric file encryption answers the question "how do we
keep this secret?" shardic answers a different question: "how do we
ensure no single party can unilaterally expose this secret — or invoke
this capability?" The cryptographic primitives underneath —
AES-256-GCM, a KDF, random key material — are entirely standards-based
and standard. What is different is the **structure of control** imposed
on top of them: the protected value never exists in a form any one
party can extract, because it is never stored whole in the first place.
It exists only fleetingly, in memory, at the moment enough independent
parties have each chosen to contribute their share of it — whether that
value decrypts a file, as in §1–§3, or arms a protected action, as in
§4–§5.

Math beats policies and permissions for enforcement. This is a
categorically stronger guarantee than access-control policies,
multi-approval workflows, or organizational procedure layered on top of
ordinary encryption — those are enforced by software or process and can
be bypassed by whoever administers them. Threshold recovery below D
trustees is enforced by mathematics and cannot be bypassed by any
administrator, insider, or software defect in the recovery tool itself.

## 7.2 Advantages

- No lone-actor risk: recovery is mathematically impossible below the
  trustee threshold, not just procedurally discouraged.
- Graceful tolerance of trustee loss: any D of T is sufficient, so the
  design survives unavailable, incapacitated, or non-cooperating
  trustees up to T − D of them.
- Zero metadata leakage: the vault file alone reveals no
  trustee-to-share mapping, even under direct inspection or partial
  compromise.
- Self-describing recovery: KDF method and parameters travel with the
  vault, so recovery never depends on external configuration matching
  what was used at creation.
- A mandatory-signer variant (shardic-prime) is available without
  weakening the underlying guarantees, for cases where one specific
  role must always participate — and, per §4, that role generalizes to
  a hardware-embodied Fielded Prime Element with no new mathematics
  required.
- Fail-closed behavior throughout: insufficient or incorrect
  codewords, unavailable KDF dependencies, or corrupted containers are
  reported explicitly and stop the operation — the design contains no
  silent-degradation path that would produce partial or misleading
  output.
- Generalizes past file decryption entirely: the same guarantee that
  protects a vault's plaintext can, per §4–§5, gate an arbitrary
  protected action, with the fielded-system-binding and approver
  mechanisms needed to do so safely already designed.

## 7.3 Limitations and Mitigations

- Codeword strength is the real bottleneck for the base scheme. The
  Shamir/AES layer is effectively unbreakable; an individual codeword
  is only as strong as its generation mode, length, and count.
  *Mitigation:* use adequate word count, prefer Argon2id where
  available, and adopt shardic-envelope (§3.6) for trustees who can
  bear key custody.
- This is a static, split-once design at its core. Revoking or
  replacing a single trustee requires a full re-split and
  re-distribution of a new vault; there is no live key-rotation or
  online quorum protocol. *Mitigation:* this tool is intentionally
  scoped to rare, high-stakes, offline "break-glass" access and
  deliberate-ceremony SPAC arming; frequent or live multi-party
  authorization should instead use threshold-signature schemes (e.g.
  FROST) or HSM-backed multisig.
- The `.krypt` container, and by extension a CT SPAC bundle, is a
  single point of *availability* failure even though it is not a
  single point of *access* failure. *Mitigation:* back up the
  container durably; there is only one artifact to protect.
- It doesn't scale limitlessly — the system is implemented with a
  ceiling at 255 shares, and makes practical sense for double-digit
  trustee counts. *Mitigation:* use it where it fits; the ceiling is
  an operational-practicality boundary, not a cryptographic one.
- The SPAC extension (§4–§5) is, as stated throughout, an unimplemented
  design. Several parameters remain explicitly open rather than
  decided: the concrete `LocalUnlockFactor` category for a given
  deployment, the specific PUF/secure-element hardware to target, and
  the wire format for extraction-grant certificates. *Mitigation:*
  none of these gaps weaken the cryptographic core described in
  §3.1–§3.5, which every SPAC construction reuses unmodified — they
  are integration and deployment decisions, not open cryptographic
  questions.
- The Windows build path has not yet been verified against a real
  Windows environment as of this writing. *Mitigation:* Linux CLI,
  GUI, and AppImage builds have been independently verified; Windows
  verification is tracked as an open item.

Taken together, these limitations describe the boundary of the problem
this design is built to solve — rare, high-stakes recovery and
authorization requiring genuine multi-party agreement — rather than
deficiencies within that boundary. Within it, the core guarantee stands
on solid ground, whether what it protects is a file's plaintext or a
protected action's enabling code: no fewer than D independently held
contributions will ever bring that value into existence, and that
guarantee does not degrade, weaken, or silently fail under any of the
failure modes considered in its design.

# Appendix A: Shamir's Secret Sharing, Explained

§1.4 and §3.2 walk through Shamir's Secret Sharing (SSS) at the depth
needed to follow the rest of this paper. This appendix is the complete,
standalone treatment those sections point to — the same source
document maintained in the project repository as
[`docs/sss_explained_for_shardic.md`](sss_explained_for_shardic.md),
reproduced here in full so the paper is self-contained.

## A.1 The Problem It Solves

Say you have a secret — a key, a password, a number — and you want to split it among several people so that:

- Any **D** of them together can reconstruct it exactly.
- Any group of fewer than **D** learns *nothing* about it, not even a probabilistic edge.

That's a **(D, T) threshold scheme**: T total shares, D required to recover. Shamir's Secret Sharing (SSS), published by Adi Shamir in 1979, solves this using a simple fact from algebra: **a polynomial of degree D−1 is uniquely determined by D points, and completely undetermined by any fewer.**

## A.2 The Intuition, Before the Math

It's worth seeing *why* this works before the formula, because the obvious first guess at "splitting a secret into pieces" isn't it, and doesn't have the properties above.

**The obvious guess, and why it falls short.** Imagine cutting a secret key into equal chunks and handing one chunk to each trustee — or the slightly cleverer version, XOR-splitting, where each share is random and the last one is defined so that all of them XOR back to the key. Both can be made information-theoretically sound in the narrow sense that holding fewer than all the pieces reveals nothing. But both share the same structural flaw: they are **all-or-nothing** schemes. Reconstruction needs every single piece, with no way to ask for "any D of T." Lose one trustee, permanently, and the secret is gone forever — exactly the fragility a threshold scheme exists to avoid.

**The actual idea: hide the secret as a point only enough hints can locate.** Picture the secret not as a string of bytes but as a single point on a graph — specifically, where a straight line crosses the vertical axis. Draw that line so it also happens to pass through T other points, one assigned to each trustee. Handing a trustee "their" point tells them nothing on its own: infinitely many different lines pass through any single point, each crossing the axis somewhere completely different, so *every* possible secret remains equally possible. But hand over any **two** trustees' points together, and there is exactly one straight line that passes through both of them — which means there is exactly one place it crosses the axis. Two points determine a line; that's what makes D = 2 work.

Raise the threshold to three, and the trick generalizes: instead of a straight line, use a curve with one more bend (a parabola), which takes three points to pin down uniquely rather than two. One or two points still leave every possible secret equally plausible — the curve simply isn't determined yet. This is the general pattern: a threshold of D is implemented as a curve that requires exactly D points to fix, with T points handed out, one per trustee, all lying on that same curve. Because the curve only needs *any* D of its T points — not a particular D, and not all T — the scheme absorbs losing up to T − D trustees, something an all-or-nothing chunk or XOR split can never offer.

That curve is a polynomial. The next section makes it precise.

## A.3 The Precise Construction

You already know the geometric version from precalculus: two points determine a line (degree 1), three points determine a parabola (degree 2). In general, **D points determine a unique polynomial of degree D−1** — no more, no fewer. Shamir's insight is to hide the secret as the *constant term* of such a polynomial, then hand out points on its curve as shares.

1. To split a secret `S` into T shares with threshold D, build a polynomial of degree D−1:

   `f(x) = S + a₁x + a₂x² + ... + a_(D-1)x^(D-1)`

   where `a₁, ..., a_(D-1)` are **random coefficients**, and the constant term is the secret: `f(0) = S`.

2. Generate T shares by evaluating this polynomial at T distinct nonzero x-values:

   `share_i = (i, f(i))` for `i = 1, 2, ..., T`

3. Distribute one `(x, f(x))` point to each of the T trustees.

**Reconstruction:** given any D of these points, you can fit the unique degree-(D−1) polynomial that passes through them, using **Lagrange interpolation**, and evaluate it at `x = 0` to recover `f(0) = S`.

## A.4 Why Fewer Than D Shares Reveal Nothing

This is the part that separates SSS from "encryption" in the usual sense — it's not computationally hard to break with fewer shares, it's **information-theoretically impossible**.

With only D−1 points, there are infinitely many degree-(D−1) polynomials passing through them — one for *every possible value* of `f(0)`. Each candidate secret is equally consistent with the data you have. You haven't narrowed the search space at all; you've learned literally zero bits about `S`. This is a much stronger guarantee than most cryptography offers, where security rests on a hard computational problem (factoring, discrete log) that could in principle be broken by a smarter algorithm or bigger computer. Here, there's no algorithm to break — the information simply isn't present in D−1 shares.

It also means there's no such thing as partial progress. A combination lock rewards partial knowledge — get two of three digits right and you are, in a real sense, close. A threshold secret share does not work that way. D−1 points together don't narrow the secret down to a short list of likely candidates; they leave *every* possible value exactly as plausible as before. There's no "getting warmer," and no way to make attempts and rule out candidates one collusion at a time — the D<sup>th</sup> point doesn't refine the answer, it's the precise moment the answer springs into existence.

## A.5 Why GF(256) Instead of Real Numbers

If you did this arithmetic over the real numbers, you'd run into two problems: fractions creep into Lagrange interpolation, and floating-point rounding would silently corrupt the secret. So SSS is done instead over a **finite field** — a closed, exact number system with no rounding.

Shardic uses **GF(256)**, the finite field with 256 elements, which conveniently maps one field element to exactly one byte (2⁸ = 256). Every arithmetic operation — polynomial evaluation, interpolation — is closed within this system, so shares and reconstructed secrets are exact bytes with no precision loss. This is also *why* GF(256) has a hard structural ceiling: with only 256 possible nonzero x-coordinates (well, 255, since 0 is reserved for the secret's evaluation point), you can't hand out more than 255 distinct shares without either colliding x-values or moving to a bigger field (GF(2¹⁶)) or a prime-field construction. It's not a tunable setting — it's the size of the number system itself.

## A.6 How This Becomes Shardic

Shardic doesn't split your *file* with SSS — it splits the **encryption key**.

1. Your file is encrypted with **AES-256-GCM** under a randomly generated **Data Encryption Key (DEK)**. This is fast, standard symmetric encryption — SSS is never applied to bulk data because polynomial math over GF(256) doesn't scale to megabytes efficiently.
2. That 256-bit DEK is the "secret" `S` fed into Shamir's construction, split into T shares under threshold D — i.e., any D trustees can reconstruct the DEK; fewer cannot, even in principle.
3. Each share is further protected by a memorable **codeword**, run through a KDF (Argon2id or PBKDF2) so that possessing the raw share bytes isn't enough — you also need the human-memorized word.
4. At recovery time, once D correct codewords unlock D shares, Lagrange interpolation reconstructs the DEK, and AES-GCM decrypts the file.

So the security model has two independent layers stacked: **AES-GCM** protects the bulk data computationally (hard to break, but not impossible in principle), while **Shamir's Secret Sharing** protects the *key itself* information-theoretically (impossible to break with insufficient shares, full stop, regardless of computing power).

## A.7 Where Shardic Extends the Textbook Scheme

A few things shardic adds on top of vanilla SSS that are worth knowing, since they're not part of Shamir's original 1979 construction:

- **Zero-leakage indexing**: normally you'd store metadata mapping "codeword A → share 3" for lookup convenience. Shardic doesn't — it brute-trials each entered codeword against all unmatched share records, using the AES-GCM authentication tag as a correctness oracle. This means the metadata file itself leaks no information about which codeword belongs to which share, closing a side-channel that a naive implementation would otherwise expose.
- **shardic-prime**: a variant that designates exactly one trustee as the *mandatory prime trustee* — reconstruction fails without their codeword specifically, no matter how many of the remaining pool trustees are gathered. This isn't native to pure threshold SSS (which treats all D-of-T combinations as equally valid) and requires an additional constraint — a one-time-pad-style mask layered over the ordinary Shamir split — on top of the polynomial construction.
- **Entropy transparency**: the system warns rather than silently degrades if your chosen KDF parameters or codeword strength fall below a safe threshold — a UX layer around the crypto, not a change to the math itself.

## A.8 The One-Sentence Summary

Shamir's Secret Sharing turns "split a secret among T people, any D of whom can recover it" into a simple geometry fact — a degree-(D−1) polynomial needs exactly D points to pin down — and shardic uses that fact to protect not your file directly, but the single key that unlocks it, so that reconstructing access requires genuine cooperation among trustees rather than trusting any single point of failure.

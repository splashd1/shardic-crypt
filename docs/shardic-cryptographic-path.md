# The shardic Cryptographic Path: DEK Formation Through Recovery

**Status: reference document, grounded directly in the current code**
(`gf256_sss.py`, `gf256_sss_prime.py`, `vault_core.py`,
`vault_core_prime.py`, `kdf.py`, `krypt_container.py`,
`shardic_envelope_crypto.py`, `demo/combiner/app.py`). Written as a
standalone explainer; drafted with an eye toward reuse as a white
paper appendix (alongside Appendix A's SSS explainer) and as source
material for a companion slide. Where content describes a **design
proposal** rather than shipped code, it's flagged explicitly, matching
the white paper's own Implemented/Design Proposal convention.

This document complements rather than duplicates the white paper's
**Appendix A** (`docs/shardic_white_paper.v4.1.md` /
`docs/sss_explained_for_shardic.md`): Appendix A stays at the
conceptual level (why SSS works, no code); this document covers the
same ground plus shardic-envelope and SPAC at the level of actual
function names, data shapes, and line-level detail from the current
implementation.

This document answers one question precisely: **what cryptographic
operation happens at each step, on which value, and why** — from DEK
formation through recovery, across the base scheme, shardic-prime, and
shardic-envelope, and into SPAC's reuse of that same math.

---

## 1. The Base Scheme: File Vault Encryption and Recovery

### 1.1 DEK formation

```python
dek = secrets.token_bytes(32)   # DEK_LEN
```

A fresh 256-bit key, drawn directly from the OS CSPRNG for every
vault. It does not derive from a password, a codeword, or anything
else — it exists purely as random bytes for the lifetime of vault
creation, and again briefly during recovery.

### 1.2 Encrypting the archive under the DEK

The input file or directory is archived **uncompressed** (`tarfile`,
mode `"w"`, not `"w:gz"` — deliberately, so ciphertext size never
leaks plaintext compressibility), then encrypted once:

```python
archive_nonce = secrets.token_bytes(12)
ciphertext = AESGCM(dek).encrypt(archive_nonce, plaintext, associated_data=None)
```

AES-256-GCM under the DEK, with a fresh random 96-bit nonce. GCM's
authentication tag (appended to the ciphertext) is what makes every
later decryption **fail loud** on any wrong key or tampering — never a
garbage-plaintext output, only a clean success or a hard failure.

At this point the DEK is the single value standing between anyone and
the plaintext. Every remaining step exists to ensure no one party ever
holds it intact.

### 1.3 Splitting the DEK: the SSS secret *is* the DEK

```python
shards = split_secret(dek, threshold=threshold, total_shards=trustees)
```

`gf256_sss.py` implements byte-wise Shamir's Secret Sharing over
GF(2⁸) — the same field AES itself uses (generator `3`, reduction
polynomial `0x11B`). The DEK is exactly 32 bytes; each byte position
gets its own independent random polynomial of degree `D − 1`, with
that DEK byte as the constant term:

```python
coeffs = [byte_val] + [secrets.randbelow(256) for _ in range(threshold - 1)]
```

Each trustee's index `x` (1..T) yields a 32-byte vector
`y = (p₀(x), …, p₃₁(x))` — the value of every one of those 32
polynomials at that trustee's x-coordinate. The pair `(x, y)` is the
trustee's **shard**.

This is where the Shamir guarantee applies directly to the DEK: any
`D` shards uniquely determine all 32 constant terms via Lagrange
interpolation; any `D − 1` leave every possible byte value equally
likely — genuinely zero information, not merely expensive to break.
**There is no key-encryption key here.** Wrapping the DEK under a
separate key before splitting *that* key would only relocate the
single point of control (exactly the failure mode the white paper's
§1.1 argues against in general) — splitting the DEK itself is what
actually removes it.

### 1.4 Protecting each shard with a codeword

A shard is useless to whoever holds only the `.krypt` container — it
also needs its owning trustee's codeword:

```python
salt = secrets.token_bytes(16)
shard_key = kdfmod.derive_key(kdf_method, kdf_params, codeword, salt)   # PBKDF2-HMAC-SHA256 or Argon2id
shard_nonce = secrets.token_bytes(12)
payload = bytes([x]) + y
shard_ct = AESGCM(shard_key).encrypt(shard_nonce, payload, associated_data=None)
```

The codeword (memorable, dictionary, or synthetic mode) is stretched
through a KDF — PBKDF2-HMAC-SHA256 at 400,000 iterations by default,
or Argon2id (256 MiB / t=4 / p=4) if available — into a 256-bit
`shard_key`, independently salted per shard. That key AES-256-GCM
encrypts the shard's `(x, y)` payload. A shard is therefore protected
twice over: it exists only inside ciphertext that itself requires a
KDF-stretched codeword to open.

Shard records are then randomly shuffled
(`secrets.SystemRandom().shuffle`) before being written — nothing in
the container ties a given encrypted shard to a given trustee or
codeword. That property is what makes the trial-matching recovery step
below necessary, not incidental.

### 1.5 Packaging: the `.krypt` container

Metadata (KDF method/params, `T`, `D`, the shuffled shard records, the
archive's nonce) and the raw archive ciphertext are written as one
file: magic header, length-prefixed JSON metadata, raw ciphertext — no
base64 (avoids the ~33% size penalty), nothing to accidentally
separate.

### 1.6 Recovery

A trustee supplies their codeword. For **every** still-unmatched shard
record, the recovery path re-derives a candidate key from that
codeword against that record's own stored salt, and attempts a
decrypt:

```python
key = kdfmod.derive_key(kdf_method, kdf_params, codeword, salt)
payload = AESGCM(key).decrypt(nonce, ct, associated_data=None)   # InvalidTag on any wrong guess
```

GCM's tag is the correctness oracle — there is no lookup table, no
"which record is mine," just trial and error with a hard yes/no per
attempt. Whichever record's tag validates is that trustee's actual
shard; its first byte is `x`, the rest is `y`.

Once `D` shards are recovered, Lagrange interpolation at `x = 0`,
performed independently per byte position, recombines them:

```python
dek = reconstruct_secret(recovered_shards)
```

For each byte position: for every recovered shard `i`, multiply its
`y` byte by `∏(xⱼ) / ∏(xᵢ ⊕ xⱼ)` across all other recovered shards
`j`, then XOR the 32 per-shard contributions together. Repeat for all
32 positions and the original DEK falls out exactly.

```python
plaintext = AESGCM(dek).decrypt(archive_nonce, ciphertext, associated_data=None)
```

If the recombined DEK is wrong — insufficient shards, mismatched
shards, tampering — this raises `InvalidTag` and stops outright, never
producing a partial or corrupted extraction. On success, the tar is
extracted and the vault is recovered.

### 1.7 Two key layers, not one

| Layer | Protects | Key type | Held by |
|---|---|---|---|
| Archive encryption | The user's actual data | The DEK — **this is the SSS secret itself** | Nobody, post-split; reconstructed only transiently at recovery |
| Shard protection | One SSS shard (a point on the DEK's Shamir polynomial, not a fragment of the DEK's bytes) | A per-trustee key derived from a codeword via PBKDF2/Argon2id | Implicitly, via the trustee's held codeword |

---

## 2. shardic-prime: A Mandatory Trustee

**Status: implemented.** A separate module (`gf256_sss_prime.py`) and
container format (`krypt1-prime`, `scheme: "prime-trustee"`) from the
base scheme, so a base-scheme vault can never be opened with
prime-aware tooling or vice versa.

### 2.1 The construction: a one-time pad layered over ordinary SSS

Where the base scheme splits the DEK directly, shardic-prime XORs it
with a random mask first, then splits the *masked* value:

```python
mask = secrets.token_bytes(32)                 # same length as the DEK
masked_secret = bytes(a ^ b for a, b in zip(dek, mask))
pool_shards = split_secret(masked_secret, threshold=pool_threshold, total_shards=pool_size)
```

The **prime trustee**'s codeword protects `mask` directly — there is
no polynomial for the prime slot; it's an all-or-nothing pad, not a
Shamir point. Every other trustee is an ordinary **pool trustee**,
interchangeable among themselves the same way base-scheme trustees
are. `T` and `D` count the prime trustee: `pool_size = T − 1`,
`pool_threshold = D − 1`.

Without `mask`, no number of pool shards — even all of them — reveals
anything about the DEK: `masked_secret` is uniformly random without
it. Without at least `pool_threshold` pool shards, `mask` alone
reveals nothing either. Both halves keep the base scheme's
information-theoretic guarantee; the pad is what makes the prime
trustee's participation non-negotiable rather than merely encouraged.

### 2.2 Shard sealing and container differences

Each value — `mask` for the prime trustee, `(x, y)` for each pool
trustee — is sealed exactly like a base-scheme shard: a per-record
salt, a codeword run through the same KDF choice, AES-256-GCM. A
one-byte type tag (`SHARD_TYPE_PRIME` / `SHARD_TYPE_POOL`) rides
inside the encrypted payload itself, not in the container's visible
structure, so a codeword's role — prime or pool — is only learned once
it actually matches a record. Records are shuffled together the same
way as the base scheme.

### 2.3 Recovery

Trial-matching proceeds exactly as in §1.6, except a successful match
now also reveals whether the matched record was the prime's `mask` or
a pool `(x, y)` point. Reconstruction requires the prime's `mask`
**and** at least `pool_threshold` pool shards:

```python
masked_secret = reconstruct_secret(pool_shards)      # ordinary Lagrange interpolation, §1.6
dek = bytes(a ^ b for a, b in zip(masked_secret, mask))
```

Missing the prime trustee's codeword, no quantity of pool codewords —
even all of them — recovers the vault. This is the mechanism, not a
policy layered on top of it.

---

## 3. shardic-envelope: A Public-Key Delivery Layer

**Status: implemented** (`shardic_envelope_crypto.py`,
`demo/combiner/app.py`, `demo/trustee/app.py`).

### 3.1 What it is

An ECIES-style hybrid encryption construction — ephemeral X25519 ECDH
+ HKDF-SHA256 + AES-256-GCM — that wraps an arbitrary opaque byte
payload to a recipient's public key:

```python
shared_secret = ephemeral_private_key.exchange(recipient_public_key)
aes_key = HKDF(algorithm=SHA256(), length=32, salt=None, info=b"shardic-envelope-v1").derive(shared_secret)
ciphertext = AESGCM(aes_key).encrypt(nonce, plaintext, associated_data=None)
```

The ephemeral private key is used once and discarded. `unwrap()` is
the inverse: the recipient's stored private key regenerates the same
shared secret via its own ECDH exchange, and AES-GCM's tag rejects a
wrong key or tampering the same way every other layer in this project
does.

### 3.2 What it wraps — two different payloads, two different directions

Critically, shardic-envelope wraps **two distinct things at two
distinct moments**, never confuse them:

**Codeword envelope (combiner → trustee), at vault creation.** The
combiner still generates a plain-text codeword and runs
`create_vault_prime()` exactly as in §2 — nothing about DEK splitting
or shard sealing changes. What changes is delivery: instead of an
operator handing that codeword to a trustee out of band, the combiner
wraps it to the trustee's already-registered public key —
`shardic_envelope_crypto.wrap(codeword.encode(), recipient_pub)` — and
the trustee retrieves it by polling
`GET /trustees/pending-envelope`. The combiner never persists a
plaintext codeword once this happens.

**Unsealed shard envelope (trustee → combiner), at recovery.** The
trustee unwraps their codeword envelope locally, then runs the *same*
trial-matching logic from §1.6/§2.3
(`try_match_word_prime`) against their own copy of the vault to derive
their **unsealed shard** — the prime's `mask`, or a pool trustee's
`(x, y)` point. An unsealed shard only exists after a codeword has
already matched a shard; it is a *result*, never a delivery mechanism,
and never a codeword itself. That unsealed shard is serialized —

```python
b"P" + mask                    # prime unsealed shard: 33 bytes
b"L" + bytes([x]) + y_bytes    # pool unsealed shard: 34 bytes
```

— and wrapped back to the combiner's public key, which the trustee
already has: it rides along in the same API response as the codeword
envelope (`combiner_pub`), so no separate lookup is needed for the
reply. The combiner unwraps and deserializes it, and by construction
**never sees a plaintext codeword at any point** — only an unsealed
shard, already matched, already reduced to exactly the bytes needed
for reconstruction.

### 3.3 What shardic-envelope deliberately does not change

Straight from the module's own docstring: it "never touches
`gf256_sss_prime.py`'s split/reconstruct math or `vault_core_prime.py`'s
KDF/shard logic — those stay exactly as they are." Envelope is a
transport-confidentiality layer composed *on top of* shardic-prime in
the current implementation, not a fourth, independent way of splitting
or protecting the DEK. The `.krypt` container's shard records are
still codeword-KDF-AES-GCM-sealed exactly as in §2.2; envelope only
changes how the codeword reaches the trustee and how the resulting
unsealed shard gets back, never what's stored at rest.

### 3.4 Identity, not secrecy: `fingerprint()`

`fingerprint()` (a SHA-256 hash of a raw public key, hex, grouped for
display) exists purely for a human to visually cross-check "is this
really the trustee/combiner I think it is" — it plays no role in any
cryptographic matching or wrapping decision.

---

## 4. SPAC Cryptographic Operation Options

**Status: design proposal** (white paper §4 onward) — SPAC generalizes
the *protected value* (from "a file's DEK" to "any enabling value for
a protected action," a **PT SPAC**/**CT SPAC** pair mirroring
plaintext/ciphertext) without introducing new field math. Every
operation below is the same GF(2⁸) SSS, the same one-time-pad-over-SSS
construction, and the same envelope primitive already described in
§1–§3.

### 4.1 Fielded Prime Element: hardware-sourced `mask`

A **fielded prime element** is shardic-prime's `mask` (§2.1), sourced
from a fielded system's own PUF- or secure-element-sealed secret
instead of a human-held codeword — `reconstruct_secret_with_prime()`
runs completely unmodified. Non-extractable, generated once at
emplacement, never typed by a human, never leaves the hardware. A
copied `CT SPAC` plus a full legitimate trustee quorum still can't arm
a *different* fielded instance, because that instance's `mask` never
travels with the ciphertext — it's the algebraic property from §2.1,
applied to a device rather than a person.

### 4.2 Choosing how a SPAC trustee's own shard is protected

This is the operation §4.7/§4.8 of the white paper are actually about,
and the source of the original question this document grew out of.
Nothing here is a new cryptographic primitive — it's two **independent**
choices, applied to a SPAC trustee's shard or mask, each drawing on a
mechanism already described above:

- **Delivery axis (§4.7)** — does the protection value reach the
  trustee memorized, or shardic-envelope-wrapped?
- **Entropy-source axis (§4.8)** — where does that value *come from* in
  the first place: generated as a human-shaped codeword and stretched
  through a KDF, or drawn directly from a DRBG as a full-strength key
  with no wordlist step and no KDF stretching at all?

#### 4.2.1 Delivery axis: memorized vs. shardic-envelope

| Option | Mechanism | Status | When it applies |
|---|---|---|---|
| Memorized (opt-out) | The value is held/typed by the trustee directly, never wrapped | Implemented (mechanism) | Field/communications-denied deployments — a device holding a wrapped credential is itself a seizable artifact; a memorized value is not |
| shardic-envelope (default) | §3's codeword-envelope delivery + unsealed-shard-envelope reply, wrapping the trustee's protection value to a keypair they already hold | Implemented (mechanism) / proposed as SPAC's default (§4.7) | Default for SPAC ceremonies |

#### 4.2.2 Entropy-source axis: codeword+KDF (baseline) vs. DRBG-direct (SPAC default)

| Option | Mechanism | Status | When it applies |
|---|---|---|---|
| Codeword + KDF (baseline / opt-out) | §1.4/§2.2's codeword → KDF (PBKDF2/Argon2id) → AES-256-GCM, exactly as the base/prime schemes already implement and as `demo/combiner/app.py` runs today (`create_vault_prime(..., word_count=1, kdf_method="pbkdf2")`) | Implemented | Named, deliberate opt-out for SPAC too — no persistent key material to seize, no credential-lookup trust boundary, no private-key custody burden, relayable over any channel, no cryptographic-tooling bar for the trustee population, minimal setup friction |
| DRBG-direct (SPAC default) | A full 256-bit key drawn straight from the same CSPRNG class as the DEK/masks/nonces, used **directly** as the AES-256-GCM shard-protection key — no `pick_words()`, no KDF stretching, because stretching only compensates for a human-chosen secret's narrower guessing space | Design proposal (§4.8) — no code path exists yet; `demo/combiner/app.py` does not currently generate or seal a value this way | Standard SPAC default — gives shard protection genuine bit-parity with the 256-bit DEK it protects |

Illustrative contrast with §1.4's actual codeword-sealing code — the
DRBG-direct path would replace the KDF step outright, not merely swap
which KDF runs:

```python
# §1.4, today (codeword + KDF, baseline/opt-out):
shard_key = kdfmod.derive_key(kdf_method, kdf_params, codeword, salt)

# §4.8, proposed (DRBG-direct, SPAC default) -- not implemented:
shard_key = secrets.token_bytes(32)   # no codeword, no wordlist, no KDF
```

A DRBG-direct key can't be memorized, so it necessarily forces
envelope (or shardware-token) delivery — but choosing envelope
delivery does *not* require a DRBG-direct key; a normally generated
codeword can still be envelope-wrapped for transport confidentiality
alone, exactly as the current implementation does. The two axes are
independent but not symmetric.

Every combination of the two axes still terminates in the exact same
`reconstruct_secret[_with_prime]` call — the choice only changes how a
shard/mask is protected and delivered before it ever reaches that
step, never what the reconstruction math does with it.

### 4.3 shardware-token variants (design proposals, no new field math)

Two hardware-carriage variants, both explicitly out of scope for any
new cryptographic construction:

- **Physical carriage** — a token transports an already
  `shardic-envelope`-wrapped unsealed shard (§3.2's unsealed shard
  envelope) in place of a network hop; nothing on the token is ever
  unencrypted, and `submit_shard_reply()`/`unwrap()` are reused
  unmodified.
- **PUF-sealed embed/extract** — a token generates its own X25519
  keypair locally, seals a wrapped shard behind PUF/secure-element
  storage, and releases it only against a vault-signed extraction
  grant. Still an X25519 keypair and the same `wrap()`/`unwrap()`
  primitive from §3.1 — the hardware changes *when and how* the
  private key is used, not the wrapping construction itself.

---

## 5. Summary Comparison

| | Base scheme | shardic-prime | shardic-envelope | SPAC / Fielded Prime Element |
|---|---|---|---|---|
| **Status** | Implemented | Implemented | Implemented | Design proposal |
| **What's split** | The DEK, directly | DEK ⊕ random mask (the masked value is split) | *(not a splitting scheme — a delivery layer, composed on top of prime)* | Same as shardic-prime; DEK generalizes to any PT SPAC-enabling value |
| **Mandatory participant** | None — any `D` of `T` peers | The prime trustee, always | N/A | The fielded prime element, always |
| **Per-shard protection at rest** | Codeword → KDF → AES-256-GCM | Same, plus a type tag (prime/pool) inside the sealed payload | Unchanged — envelope wraps the codeword/unsealed shard in transit, not the stored record | Codeword → KDF (baseline/opt-out, implemented) *or* DRBG-direct key with no KDF (proposed default, §4.8); `mask` sourced from hardware, not memory, in the Fielded Prime Element case |
| **Container format tag** | `krypt1` | `krypt1-prime` | *(inherits whichever container it's layered on — `krypt1-prime` in the current demo)* | Not yet a concrete container format — design proposal |
| **What crosses the wire during recovery** | Nothing — codewords are typed locally by whoever runs `vault_recover.py` | Same as base scheme | A codeword envelope out, an unsealed shard envelope back — never a plaintext codeword | Same envelope pattern, or a physically-carried wrapped unsealed shard (shardware-token) |

---

## 6. Notes for Reuse

**As a white paper appendix.** This slots naturally as **Appendix B**,
immediately after Appendix A's SSS explainer (which this document
assumes as background rather than re-deriving — §1.3's Lagrange
interpolation step is deliberately terse here for that reason).
Sections 1–3 correspond to the paper's §3.1–§3.7; §4 corresponds to
§4.2/§4.7/§4.8. Status badges above use the same
Implemented/Design-Proposal language the paper already uses throughout.

**As a slide.** The natural split is two slides, matching the existing
deck's per-topic granularity (one concept per slide, not one section
per slide):

- *Slide A — "One Value, Two Ways to Protect It"*: §1.3/§1.4's split
  diagram (DEK → SSS → shards → codeword-sealed) as the base pattern,
  with §2's one-time-pad-over-SSS shown as a light variant (a mask
  layered on top, prime trustee mandatory).
- *Slide B — "Two Payloads, Two Directions"*: §3.2's codeword-envelope
  vs. unsealed-shard-envelope distinction as a two-card, opposite-arrow
  layout (combiner → trustee / trustee → combiner) — this is the piece
  most prone to being flattened into "envelope wraps the codeword" in
  informal summaries, so a slide that visually separates the two
  directions earns its keep.
- *Slide C — "Two Independent Axes for a SPAC Trustee's Shard"*:
  §4.2.1/§4.2.2's delivery axis (memorized vs. envelope) crossed with
  the entropy-source axis (codeword+KDF vs. DRBG-direct) as a 2×2 grid
  — the natural home for the asymmetry callout (DRBG forces envelope
  delivery; envelope doesn't force DRBG) and for flagging DRBG-direct
  as still a design proposal, not shipped code.

**Terminology.** This document follows the project's
shard-vs-unsealed-shard distinction precisely (see
`.claude/skills/shardic-nomenclature/SKILL.md`): *shard* is the
at-rest, pre-match value inside a `.krypt` container; *unsealed shard*
is the post-match, in-motion value that only exists in
shardic-envelope's recovery leg. Carry that distinction into any
appendix or slide text built from this document — it's easy to flatten
by accident, and the project has already had that collision once.

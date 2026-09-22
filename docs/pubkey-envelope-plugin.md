# shardic-envelope: a public-key codeword envelope (proposed, unimplemented)

**Status: design proposal.** Nothing described here exists in the
codebase yet — `vault_core.py`, `wordgen.py`, and the four CLI/GUI
frontends are all unchanged by this document. This is a design for a
**bolt-on plugin** that would operate entirely on the *output* of
vault creation (the `<random16>_trustee_words/trustee_N.txt` files), not a
modification to the encrypt/split/KDF logic described in the main
[README](../README.md#how-the-design-works). It's written to be
revised as the real implementation takes shape — treat the interfaces
below as the current best guess at the seams, not a frozen spec.

## The problem this solves

From the README's "Things worth knowing" section:

> Entropy of the codewords is the real security bottleneck ... aim for
> the default of 8 [words] in memorable mode, or 2–3+ in the other
> modes.

That ceiling exists because a human has to actually memorize the
codeword — `--memorable` mode is already a compromise between entropy
and recallability, and every mode's practical word count is bounded by
what a trustee can realistically carry in their head (or is willing to
write on paper, which the whole design tries to avoid encouraging).

**shardic-envelope removes that ceiling for trustees willing to trade
"memorize it" for "protect it with a keypair I already control."**
Each trustee's codeword gets generated as large as you like — 16
memorable words, a 256-bit synthetic string, whatever — then
immediately wrapped in a public-key envelope under *that trustee's
own* public key. The trustee never memorizes anything; they store the
encrypted envelope (on their laptop, phone, hardware key, wherever)
and decrypt it locally with their private key only when they're
actually participating in a recovery. The bottleneck moves from "how
much can a human remember" to "how well does this one trustee protect
their own private key" — which is a problem trustees already have
tooling and habits for (password managers, hardware security keys,
GPG/age identities), unlike memorizing five random words.

This composes with either the base scheme or [shardic-prime](../README.md#shardic-prime-a-mandatory-prime-trustee-variant):
the plugin only ever looks at `<random16>_trustee_words/trustee_N.txt`-shaped
output, and both `vault_create.py` and `vault_create_prime.py` produce
that shape.

## Where it sits in the architecture

```
vault_create.py / vault_create_prime.py
        │
        ▼
<random16>_trustee_words/trustee_1.txt ... trustee_T.txt   (plaintext codewords, as today)
        │
        ▼
   ┌─────────────────────────────┐
   │   shardic-envelope plugin   │   ← everything new lives here
   │  (runs as a separate,       │
   │   opt-in post-processing    │
   │   step, not inside          │
   │   vault_core.py)            │
   └─────────────────────────────┘
        │
        ▼
trustee_1.txt.envelope ... trustee_T.txt.envelope   (PK-wrapped)
        + plaintext originals securely destroyed
```

Keeping this a separate stage (rather than a `create_vault()` flag)
means:
- The core crypto in `vault_core.py` — the piece the README's security
  claims rest on — stays untouched and doesn't take on a dependency on
  however key lookup ends up being implemented.
- It's opt-in per trustee, not per vault: a vault could reasonably
  have some trustees who memorize a normal-sized codeword and others
  who get the long/wrapped kind, mixed freely, since `vault_recover.py`
  doesn't care how a trustee arrived at the string they type in — it
  just tries it against the shard records.
- shardic-prime's prime-trustee codeword and pool codewords are both
  just files in `<random16>_trustee_words/` too, so the plugin needs no
  awareness of which scheme produced its input.

## The credential lookup: a pluggable interface, not a database design

The plugin needs, for each trustee, a way to go from "trustee
identifier" to "their current public key + which algorithm it's for."
This document deliberately does **not** design that store — it
defines the minimal contract the plugin depends on, and treats
whatever satisfies it as pluggable:

```python
class CredentialLookup(Protocol):
    def get_public_key(self, trustee_id: str) -> PublicKeyRecord:
        """Raises KeyNotFoundError if trustee_id has no credential on file."""

@dataclass
class PublicKeyRecord:
    trustee_id: str
    algorithm: str        # e.g. "x25519", "rsa-oaep-4096" — carried per-record so
                           # trustees can use different key types/ages
    public_key_bytes: bytes
    fingerprint: str       # for the printed confirmation step, see below
```

A real deployment might back this with a flat JSON file, an
organization's existing PKI/LDAP directory, a hardware-token registry,
whatever already exists for that org's identity management — that's
an integration decision for whoever deploys the plugin, not something
shardic should own or ship an opinion on. The plugin's job stops at
"call `get_public_key(trustee_id)` and get back a key + algorithm
tag or a clear error."

`trustee_id` needs to be *decided* by the plugin's caller at the point
codewords are generated — most naturally the same `trustee_1`,
`trustee_2`, ... labels already used for filenames, or a real name if
the credential store is keyed that way. Either way, that mapping
(which numbered trustee is which real person) is exactly the kind of
information the base scheme's "[indexing without a mapping
table](../README.md#indexing-without-a-mapping-table)" property
deliberately keeps out of the `.krypt` file — this plugin's mapping
lives entirely in its own local run, never touches the vault
container, and should be discarded (not just the plaintext codewords)
once wrapping completes.

## The envelope construction

Per trustee, a hybrid (ECIES-style) envelope, algorithm chosen per the
`PublicKeyRecord.algorithm` tag so trustees aren't forced onto one key
type:

- **X25519 trustee keys**: generate an ephemeral X25519 keypair,
  perform ECDH against the trustee's public key, run the shared secret
  through HKDF to derive an AES-256-GCM key, encrypt the codeword under
  that key. Ephemeral public key + nonce + ciphertext ship together;
  the ephemeral private key is discarded immediately after use.
- **RSA trustee keys**: RSA-OAEP wraps a random AES-256 key, which then
  encrypts the codeword under AES-256-GCM (plain RSA-OAEP of the
  codeword directly would work for short codewords but caps message
  size and loses the uniform "always AES-GCM at the end" shape).

Both land in the same envelope shape: `{algorithm, ephemeral_key_or_wrapped_dek,
nonce, ciphertext}` — deliberately mirroring the
`{salt, nonce, ciphertext}` shape `vault_core.py` already uses for
shard records, so the plugin's output format doesn't invent a
gratuitously different convention. Serialize it the same
length-prefixed-JSON-then-bytes way `krypt_container.py` frames the
`.krypt` file, or reuse that module directly if the shape ends up
close enough — TBD once real code is written.

This is deliberately **not** "shell out to `age`/`gpg`" — building the
envelope construction directly (as above) keeps shardic in control of
the exact primitives and avoids a runtime dependency on an external
binary being installed and on `$PATH`. Revisit this if that tradeoff
stops making sense — `age`'s format is a reasonable fallback algorithm
tag to support alongside the native construction, not mutually
exclusive with it.

## Secure destruction of the plaintext intermediates

This is the part that actually delivers the "protect them with their
own private keys from disclosure" property — an envelope sitting next
to an undeleted plaintext copy protects nothing. Proposed sequencing:

1. Generate all `T` codewords and write all `T` envelopes to their
   final destinations first. **Do not delete anything until every
   trustee that's opting into wrapping has a successfully written
   envelope on disk**, `fsync`'d. A partial run that deletes some
   plaintexts before all envelopes exist risks stranding a trustee
   with neither a plaintext codeword nor a working envelope if the
   process dies partway through.
2. Only after every envelope write is confirmed (file exists, expected
   size, re-parses as a well-formed envelope — this checks the
   *envelope's* integrity, not that the intended trustee can actually
   decrypt it, since the plugin never holds a private key and
   structurally can't verify that) does destruction of the plaintext
   `trustee_N.txt` files begin.
3. Destruction should go beyond `os.remove()` — overwrite the file's
   contents before unlinking, then remove it. **Be explicit in the
   implementation and its docs that this is best-effort, not a
   guarantee**: on SSDs (wear-leveling remaps writes instead of
   overwriting in place), copy-on-write filesystems (Btrfs, ZFS,
   APFS), journaling filesystems that may have already written the
   original bytes to a journal, or any filesystem snapshot/backup
   system, "overwrite then delete" does not reliably erase the
   original bytes. The honest guarantee this step provides is "no
   plaintext file remains at the expected path under normal
   filesystem operation" — not "these bytes are cryptographically
   unrecoverable from the underlying storage." Say this out loud in
   whatever CLI output/GUI dialog triggers the destruction step, the
   same way the README is upfront about the `--strong-words` /
   memorable-mode tradeoffs rather than overselling them.
4. Log (to the same `log()` callback pattern `vault_core.py` already
   uses) exactly which trustee files were destroyed and which envelope
   each was replaced by, so there's an audit trail of the handoff —
   consistent with the base scheme's existing "record of exactly which
   trustees participated" framing for recovery.

## Recovery-time flow

Nothing in `vault_recover.py`/`vault_recover_prime.py` changes. A
trustee holding a `.envelope` file:

1. Decrypts it locally, on their own device, with their own private
   key — entirely outside shardic, using whatever tool implements this
   envelope format (a small `shardic-envelope decrypt` helper, most
   likely, mirroring the wrap side).
2. Gets back the plaintext codeword string.
3. Enters that string into `vault_recover.py`/the GUI exactly as any
   other trustee would today.

shardic's recovery path is unaware any of this happened — it just
matches a string against shard records as it always has. This is
important: **the vault operator running `vault_recover.py` never sees
a trustee's private key, and ideally never sees their plaintext
codeword either** (the trustee decrypts locally and types the result
in themselves, the same way they'd type in a memorized word today).

## New threat-model considerations this introduces

Worth documenting explicitly since they're genuinely new failure modes
relative to the memorized-codeword model, not just restatements of
existing ones:

- **A trustee's private key becomes a single point of failure for
  their shard.** Lose the private key (no backup) and that trustee's
  codeword is gone as surely as if they'd forgotten a memorized one —
  except there's no "try to recall it" fallback. Whoever deploys this
  needs their own private-key backup story (hardware key duplication,
  Shamir-split the private key itself, whatever); that's out of scope
  for shardic to prescribe.
- **The base scheme's information-theoretic guarantee about
  individual shards is unaffected.** A compromised trustee private key
  exposes exactly that one trustee's codeword — same blast radius as
  that trustee writing their memorized codeword on a sticky note and
  losing it. Below the threshold `D`, this is still just one point
  among many that reveals nothing on its own; see the README's
  ["Threshold security is information-theoretic; codeword security is
  not"](../README.md#things-worth-knowing-before-you-rely-on-this)
  note, which still holds.
- **The credential lookup is a new trust boundary.** If whatever backs
  `CredentialLookup.get_public_key()` is compromised or spoofed —
  returns an attacker's public key instead of the real trustee's — the
  plugin would faithfully wrap a high-entropy codeword to the
  attacker's key while destroying the only plaintext copy, which is
  strictly worse than doing nothing. The plugin should refuse to
  proceed on any lookup ambiguity, and printing/confirming the
  `fingerprint` from `PublicKeyRecord` against something the operator
  can verify out-of-band (voice confirmation with the trustee, a
  pre-published fingerprint list, etc.) before wrapping is a real
  mitigation worth building in, not an optional nicety — this is the
  step doing the actual authentication work the credential store
  itself doesn't provide.

## Open questions / TBD before real implementation

- Concrete algorithm defaults (X25519 vs. RSA as the "if the trustee
  hasn't chosen" default; whether to support post-quantum KEMs given
  the "persistent" framing in the original ask — a long-lived envelope
  has a longer harvest-now-decrypt-later exposure window than a
  vault meant for rare, ad hoc use).
- Exact envelope container format/versioning (own tiny format vs.
  reusing `krypt_container.py`'s framing).
- CLI/GUI surface: a standalone `shardic_envelope.py` script analogous
  to the existing `vault_create*.py` pattern, vs. a flag/tab bolted
  onto the existing Create flow. Given this document's premise (bolt-
  on plugin, not a core change), a standalone script seems the better
  fit, but this is worth revisiting once the credential-lookup story
  is concrete.
- Key rotation / re-wrapping: if a trustee's keypair is later rotated,
  does the plugin support re-wrapping their existing plaintext... but
  the plaintext is destroyed by design. This likely means rotation
  requires that trustee to decrypt their old envelope (with their old
  key) and immediately re-wrap under the new one — a "rewrap" mode
  the plugin should probably support explicitly rather than leaving
  operators to reconstruct the flow ad hoc.
- Whether destruction (see above) should default on or require an
  explicit `--confirm-destroy`-style opt-in the first time this is
  used, given how irreversible it is and how new the trust-the-
  filesystem-scrub-worked assumption is compared to the rest of this
  tool's conservative-by-default posture.

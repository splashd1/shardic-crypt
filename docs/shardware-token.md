# shardware-token, part 1: physical carriage of an unsealed shard (proposed, unimplemented)

**Status: design proposal.** Nothing described here exists in the
codebase yet.

"shardware-token" names a family of hardware-based alternatives to the
network path a shardic-envelope ceremony normally uses. Two distinct
ideas share the name and are covered in separate docs:

1. **Physical carriage** (this doc) — a hardware token *is* the
   transport: a trustee's derived unsealed shard travels to the
   combiner on the token itself instead of over the network, for
   ceremonies that want an air-gapped or courier-based delivery step.
2. **Hardware-backed key custody** — a token (smartcard, FIDO2/WebAuthn
   authenticator) holds the trustee's private key and performs
   unwrap/derive on-device; the network path
   (`/trustees/pending-envelope`, `/trustees/shard-reply`) is
   unchanged. [portable-trustee-client.md](portable-trustee-client.md#browser-xss-residual-risk-resolved-web-is-the-default-documented-risk-with-an-opt-in-alternative)
   already flagged this as an opt-in hardening option; designed in
   [shardware-token-key-custody.md](shardware-token-key-custody.md).
3. **PUF-sealed embed/extract** — a hardened evolution of (1): the
   token is no longer dumb storage but a PUF/secure-element-backed
   device that generates its own keypair, seals the unsealed shard
   non-extractably, and only releases it against a vault-signed
   extraction grant. Designed in
   [shardware-token-embed-extract.md](shardware-token-embed-extract.md) —
   it supersedes this doc's ["identity without a live
   session"](#the-real-open-problem-identity-without-a-live-session)
   open question with a third, stronger answer.

This doc designs (1) only.

## The problem this solves

Every existing recovery path — base/prime CLI codewords, and
shardic-envelope's `shard_envelope` (an unsealed shard envelope) POST
to `/trustees/shard-reply` —
assumes a live channel at recovery time: either a human typing a
codeword into a prompt, or a trustee's device reaching the combiner
over the network. Some ceremonies can't or won't accept that
assumption — an air-gapped combiner, a trustee who doesn't want their
device to touch the network during recovery, or a ceremony where
physical chain-of-custody (a courier, a safe-deposit box, a hand-off
at a meeting) is itself part of the trust model the organization
already relies on for other secrets. shardware-token gives that case a
defined path instead of leaving it as "figure it out with a USB stick
and no guarantees."

## Key design insight: this needs no new crypto

A `shard_envelope` (an unsealed shard envelope) is already `wrap()`-ed (X25519 ECDH + HKDF +
AES-256-GCM, per `shardic_envelope_crypto.py`) to the **combiner's**
public key before it goes anywhere. That confidentiality guarantee has
never depended on the transport — `pubkey-envelope-plugin.md`'s
construction was designed to be safe sitting on an untrusted relay.
Physical carriage doesn't change what gets protected or how; it only
changes what carries the already-wrapped bytes from the trustee's
device to the combiner. The hardware token itself can be genuinely
dumb storage — it never needs to be a secure element, because there's
nothing unencrypted on it to protect.

This also means `submit_unsealed_shard_reply()` (`demo/combiner/app.py:609`)
doesn't need to change at all. It already takes plain
`(sub, session_id, shard_envelope)` — nothing about it is HTTP-specific.
What's missing is only an **ingestion adapter** that reads those three
values off a physical token instead of a Flask request body, and an
answer to where `sub` comes from without a live OIDC bearer token (see
below — this is the actual open design problem, not the crypto).

## Where it sits in the architecture

```
Trustee's device (unchanged):
  fetch pending codeword_envelope -- OVER THE NETWORK, registration-time
  unwrap locally, run try_match_word_prime() -- unchanged
  derive unsealed shard, serialize_unsealed_shard(), wrap() to combiner_pub -- unchanged
        │
        │   <-- this is the only step that changes -->
        │
        ▼
   ┌───────────────────────────────────────┐
   │  Write {sub, session_id, shard_envelope}│
   │  to shardware-token storage             │
   └───────────────────────────────────────┘
        │
        ▼   physically carried (trustee, courier, safe hand-off)
        │
        ▼
   ┌───────────────────────────────────────┐
   │  Ingestion adapter (new, this doc)      │
   │  reads token, calls submit_unsealed_shard_reply│
   │  exactly as trustees_shard_reply() does │
   └───────────────────────────────────────┘
        │
        ▼
finalize_recovery() / verify_recovery() -- unchanged
```

## Physical medium options

| Medium | Carries | Notes |
|---|---|---|
| **USB mass storage** | JSON file: `{sub, session_id, shard_envelope}` | Simplest to implement — any machine can read/write it, no special reader hardware. Bearer risk: whoever holds the drive holds the (still-encrypted) payload. |
| **Smartcard / CCID applet** | Same JSON, or a compact binary encoding, in an applet's data object | Needs a card reader at both ends; buys a PIN gate on read/write that a bare USB drive doesn't have, at real implementation cost (applet development, reader driver support). |
| **NFC tag** | Same JSON, size-permitting (typical NTAG21x: ~144–888 bytes — an unsealed shard envelope plus session_id/sub comfortably fits) | Tap-to-write/tap-to-read UX, no cable; more exotic reader requirement on the combiner side than USB. |
| **Printed QR code** | Base64/JSON payload, if it fits QR's capacity | Arguably not "hardware" at all, but worth naming — a printed code is the *auditable-by-eye* extreme of this same idea (see chain-of-custody note below), and needs no device at all beyond a printer and a camera. |

Recommendation: **USB mass storage as the reference implementation.**
It requires no new reader hardware on either end and the least new
code (write a JSON file; read a JSON file). Smartcard/NFC are real
future options once there's an actual deployment asking for the PIN
gate or tap UX — nothing about the ingestion adapter below is
medium-specific, so adding a second medium later is additive, not a
redesign.

## The real open problem: identity without a live session

The network path's `sub` doesn't come from the envelope — it comes
from a verified Keycloak bearer token, checked at the HTTP layer
before `submit_unsealed_shard_reply()` is ever called
(`app.py`'s route handler, not shown to the trustee-facing crypto at
all). `wrap()`/`unwrap()` themselves authenticate *nothing* about the
sender — an envelope only proves it was encrypted to the combiner's
public key, never who encrypted it. Take away the live bearer-token
session, and **there is currently no cryptographic assertion of "this
unsealed shard came from trustee X" left at all** — physical carriage would be
trading a real authentication mechanism for an implicit one (whoever
carried the token said whose it was), unless something replaces it.

Two ways to replace it, neither implemented here, both worth deciding
between before this ships:

1. **Operator-attested chain of custody.** The `shardic-operator` who
   physically receives the token asserts the `sub` themselves (e.g.
   picks the trustee from the candidate directory in an admin UI) as
   part of ingesting it — the same trust the organization already
   places in physical hand-off for other secrets, made explicit rather
   than assumed. Cheapest to build; the security property is only as
   good as the physical hand-off itself, which is a property of the
   ceremony's real-world logistics, not of any code in this repo.
2. **Trustee-signed manifest.** Add an Ed25519 signing keypair
   alongside each trustee's existing X25519 envelope keypair (X25519 is
   Diffie-Hellman only — it cannot sign), and have the token carry a
   signature over `{sub, session_id, shard_envelope}` that the
   ingestion adapter verifies against the trustee's already-registered
   public key material. This restores a real cryptographic assertion,
   at the cost of a second keypair per trustee and a signing step that
   doesn't exist anywhere in the pipeline today.

Leaning toward (1) for a first cut — it matches the "dumb storage,
recovery is safe because it doesn't need to be more than that" framing
above, and physical chain-of-custody is arguably the entire point of
choosing this path over the network one. (2) is the more rigorous
answer and should stay on the table if a ceremony operator wants a
transport that doesn't reduce to "the operator's word for it."

**Superseded by a third option**, if the token stops being dumb
storage:
[shardware-token-embed-extract.md](shardware-token-embed-extract.md)
designs a PUF-sealed token that authenticates an extraction request
cryptographically against a vault-issued grant, rather than relying on
either operator say-so or a trustee signing keypair. Read this doc's
remaining sections as the baseline for the "dumb medium" case; the
embed/extract doc is the answer once the medium is smarter.

## What this gains and what it gives up, versus the network path

- **Gains:** the combiner and the trustee's device never need to be
  online at the same time, or online at all, during recovery. A
  ceremony can run entirely air-gapped past the registration step.
- **Gives up:** `envelope-delivery.md`'s exactly-once **redemption**
  guarantee was a property of a *server* enforcing single-read on a
  drop point it controls — that doesn't exist for a physical medium
  nobody's server holds. What *does* still hold, unchanged: `session["replied"]`
  in `submit_unsealed_shard_reply()` already makes a second submission for the
  same `sub` an idempotent no-op, so a duplicate or re-copied token
  can't double-count — that guarantee is at the combiner's ingestion
  step, not the medium, so it survives regardless of which physical
  medium carries the bytes.
- **Gives up (pending a choice above):** live sender authentication,
  unless/until identity option (1) or (2) is chosen and built. This is
  the one gap that must be closed before this is safe to actually use
  for a real ceremony — everything else in this doc is a transport
  swap with no new crypto risk; this is the one place where "no new
  crypto needed" stops being true if the answer is (2).

## Open questions / TBD

- Which identity option (operator-attested vs. trustee-signed) to
  build first — affects whether this needs a new keypair type at all.
- Concrete on-token encoding: plain JSON (simplest, matches every other
  wire format in this project) vs. a compact binary format (matters
  more for NFC's tighter capacity than for USB).
- Whether `session_id` staleness needs an explicit expiry check at
  ingestion (a token written for a since-abandoned recovery session
  attempting to feed a *new* session) — `submit_unsealed_shard_reply()` already
  rejects a `session_id` mismatch against the current session, so this
  may already be covered; worth a test to confirm rather than assuming.
- Whether the ingestion adapter is a CLI (`shardware_ingest.py
  /path/to/mount`) or a new `/admin/recovery/ingest-token` route taking
  a file upload — a CLI keeps a truly air-gapped combiner air-gapped
  (no HTTP surface needed at all for this path); an admin route fits
  better if the combiner is already reachable but the *trustee* is the
  one who wanted to stay offline. Likely both are legitimate for
  different ceremony shapes; not deciding here.

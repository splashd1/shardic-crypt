# Portable trustee client: browser-based registration, custody, and ceremony participation (proposed, unimplemented)

**Status: design proposal.** Nothing described here exists in the
codebase yet. This consolidates decisions reached across several
design-only sessions (not previously written to any `docs/` file) into
one durable record: how a trustee's device-side app — registration,
key custody, and shard derivation/submission during recovery — becomes
portable, while Keycloak, the combiner, and the vault repo stay
centralized and containerized as they are today.

## What's in scope and what isn't

- **Centralized, containerized, unchanged:** Keycloak/IAM, the
  combiner, the vault repo.
- **Portable, this doc's subject:** the trustee-side app covering
  registration (keypair generation, per
  [keycloak-credential-lookup.md](keycloak-credential-lookup.md#registration-flow-oidc-authenticated-client-side-key-generation-only))
  and ceremony participation (shard derivation + delivery to the
  combiner, per
  [ceremony-formation.md](ceremony-formation.md#ephemeral-per-trustee-invitations)),
  replacing today's per-trustee Docker container
  (`demo/trustee/app.py`).

The bottleneck for portability is Keycloak (JVM, ~800MB image, slow
cold start) plus Docker orchestration (8 containers in the current
demo) — not the crypto core, which is already portable, pure-Python.

## Why web (browser) over a native app

Leaning **web-based (PWA/SPA)** over a PyInstaller native app,
contingent on secure in-browser keypair custody — which checks out:

- WebCrypto's `SubtleCrypto` natively supports **X25519**
  (`generateKey`/`deriveBits`) across major browsers as of 2026 (W3C
  Secure Curves API) — matching `shardic_envelope_crypto.py`'s existing
  algorithm exactly. No crypto-primitive change, just a JS port of the
  ~190-line wrap/unwrap wire format.
- A **non-extractable `CryptoKey`**, persisted in IndexedDB, gives
  device-local key custody comparable to the container's isolated
  volume today — private key material never becomes readable JS
  memory.

## Auth: Authorization Code + PKCE

Replaces today's demo shortcut (Direct Access Grant / ROPC, password
in `.env` — `demo/README.md` already documents this as deliberately
demo-only). Keycloak already supports Authorization Code + PKCE with
no client secret required, matching a public browser client.

## Device portability (resolved: device-bound, re-register on loss)

**No export path exists at all.** A trustee's private key never
leaves the device it was generated on — not to a backup, not to a
passphrase-wrapped file, not anywhere. If a trustee loses or wipes
their device, they simply re-enroll with a fresh keypair through the
same registration flow already specified in
[keycloak-credential-lookup.md](keycloak-credential-lookup.md#registration-flow-oidc-authenticated-client-side-key-generation-only)
before being eligible for future ceremonies again. This is literally
the same mechanism that doc already specifies for **rotation** — a
lost device is just an unplanned rotation, not a new case needing its
own design.

This was chosen over two alternatives considered and rejected:

- **Passphrase-wrapped exportable backup** — lets a trustee back up an
  encrypted export, but reopens the exact "protect a secret" problem
  shardic-envelope exists to avoid: the passphrase becomes a new
  single point of failure, no better than a codeword the pubkey-
  envelope design was built specifically to replace.
- **Hardware-backed roaming credential (passkey-style sync)** — no
  export ever happens under shardic's control, but portability then
  depends entirely on the authenticator vendor's own roaming feature,
  outside this project's ability to reason about or guarantee.

The tradeoff accepted here: "portable app, no install" (this doc's
subject) and "identity roams across a trustee's devices" are
different asks, and this design deliberately answers only the first —
losing a device costs a trustee their standing invitation eligibility
until they re-register, not their private key material's safety.

## Browser XSS residual risk (resolved: web is the default, documented risk, with an opt-in alternative)

**Web registration/participation is the default path.** The residual
risk is stated plainly rather than glossed over: a non-extractable
`CryptoKey` can't be *exported* by injected script, but live XSS
during an active session could still *invoke* it on the attacker's
behalf (sign or derive using the key without ever seeing its bytes) —
a real gap the isolated-container model doesn't have, since a
container has no script-injection surface at all. This is the same
posture already taken elsewhere in this design set — e.g. the
[hijacked-OIDC-session risk](keycloak-credential-lookup.md#new-threat-model-considerations)
is documented plainly rather than implying the mitigations already in
place "solve" it outright.

**CLI or hardware-token (WebAuthn) registration remains available as
an explicit, opt-in security option alongside the web default** — not
a replacement for it, an escape hatch for trustees or deployments that
want to avoid the browser attack surface entirely. This generalizes
[keycloak-credential-lookup.md's existing recommendation of
hardware-backed generation](keycloak-credential-lookup.md#registration-flow-oidc-authenticated-client-side-key-generation-only)
— there, it was framed as the better accessibility answer for
less-technical trustees; here, it's the same mechanism offered more
broadly as a hardening choice for anyone who wants it, web remaining
the default for everyone else.

## Remaining real porting cost: GF(256) field math

The one piece of this with genuine correctness risk, not just
wrapping/transport: `gf256_sss_prime.py`'s field math
(`try_match_word_prime`) needs a JS or WASM port for the browser client
to derive a shard locally. Worth scoping as its own work item before
touching auth or UI, with unit tests mirrored from the existing
`gf256_sss*.py` self-tests (`python3 gf256_sss.py`) — this is Shamir
arithmetic, not a formatting detail, and deserves the same test
rigor as the Python original.

## Combiner changes needed

- **CORS must be enabled** on the Flask combiner (currently none) —
  needed once the client is hosted from a different origin than the
  combiner API itself. Concrete allowed-origins/credentials-mode
  policy is deferred to whatever hosting story the client ends up
  with; not decided here.

## How this connects to the rest of the design set

This client is the thing a trustee actually runs for: registration
(per `keycloak-credential-lookup.md`), responding to a ceremony
invitation and submitting a shard (per `ceremony-formation.md`), and —
unchanged — typing the eventual recovered codeword into
`vault_recover.py`/the GUI exactly as today. This doc ties those
threads together at the client level; it doesn't redesign any of them.

## Open questions / TBD before real implementation

- CORS policy specifics (allowed origins, credentials mode) once a
  real hosting story for the static client exists.
- Whether the registration UI and the ceremony-response UI ship as one
  app or stay split.
- GF(256) JS/WASM port: scope, chosen approach (hand-written JS vs.
  compiling the existing Python via WASM), and test-parity plan against
  the Python self-tests.

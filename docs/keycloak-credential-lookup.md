# shardic-envelope credential lookup: a Keycloak-backed trustee directory (proposed, unimplemented)

**Status: design proposal.** Nothing described here exists in the
codebase yet. This document designs one concrete implementation of the
`CredentialLookup` Protocol left deliberately open-ended in
[pubkey-envelope-plugin.md](pubkey-envelope-plugin.md#the-credential-lookup-a-pluggable-interface-not-a-database-design):
Keycloak as the trustee *directory* (who's a candidate trustee), paired
with a small separate key *registry* (what's their public key),
bridged by an OIDC-authenticated, client-side-only registration flow.
Treat the interfaces below as a starting point, not a frozen spec.

## The problem this solves

`pubkey-envelope-plugin.md` intentionally stopped at the `Protocol`
boundary: "that's an integration decision for whoever deploys the
plugin, not something shardic should own or ship an opinion on." This
doc takes that decision for one concrete case — an org that already
runs Keycloak for SSO and wants to pick vault trustees from its
existing user base rather than maintaining a separate list.

That splits into two distinct problems, which this design deliberately
keeps separate rather than solving with one Keycloak feature:

1. **Selection** — who are the candidate trustees? Keycloak is good at
   this; it already knows the org's people and groups.
2. **Custody** — what's each trustee's public key, and how do we know
   it really belongs to them? Keycloak is *not* built for this — it
   has no native concept of a user's encryption keypair, and stretching
   its user-attribute system to hold one would put key material behind
   a broader read scope (anyone with Admin-API user-read access) than
   it needs.

## Where it sits in the architecture

```
vault_create.py / vault_create_prime.py picks trustees
        │
        ▼
Trustee picker UI  ──queries──▶  Keycloak Admin API
        │                        (scoped to a dedicated group,
        │                         e.g. "shardic-trustees";
        │                         read-only service account)
        ▼
trustee_id = Keycloak `sub` claim for each selected trustee
        │
        ▼
shardic-envelope plugin's CredentialLookup.get_public_key(trustee_id)
        │
        ▼
Local key registry (flat JSON / SQLite, keyed by `sub`)
   — populated ahead of time by the registration flow below,
     NOT queried against Keycloak itself
```

Keeping the registry separate from Keycloak means wrap-time only ever
depends on a local store, consistent with
[keeping the OAuth dependency scoped to registration](#keeping-the-oauth-dependency-scoped-to-registration-only)
below. The registry's records are exactly the `PublicKeyRecord` shape
already defined in
[pubkey-envelope-plugin.md](pubkey-envelope-plugin.md#the-credential-lookup-a-pluggable-interface-not-a-database-design) —
this doc doesn't redefine that contract, only how it gets populated.

## Trustee selection via the Keycloak Admin API

The picker queries `GET /admin/realms/{realm}/groups/{group-id}/members`
(or equivalent) for a dedicated group, not the full user list. Two
reasons to scope it this way rather than querying all realm users:

- It keeps "who can be picked as a trustee" an explicit, auditable
  membership decision (adding someone to `shardic-trustees`) rather
  than an implicit "everyone with an SSO account" default.
- The service account backing this query only needs `view-users`
  scoped to that group, not realm-wide read — least privilege matters
  here because a compromised picker credential lets an attacker
  enumerate (though not impersonate — see
  [threat model](#new-threat-model-considerations) below) trustees.

## Key custody: a separate registry, not Keycloak user attributes

Rejected: storing the public key as a Keycloak custom user attribute.
It's tempting (one less moving part) but wrong for this data:

- Keycloak user attributes have no key-specific validation, versioning,
  or rotation semantics — they're free-text fields.
- Read access to user attributes tracks Keycloak's user-read
  permission model, which is broader than "should be able to see
  trustee key fingerprints."

Instead: a small local registry (flat JSON or SQLite is enough to
start), keyed by the trustee's Keycloak `sub` claim, storing
`PublicKeyRecord`s. This is deliberately unglamorous — the design
goal is that this store is easy to reason about and audit, not that it
scales past what a threshold-crypto vault tool actually needs.

## Registration flow: OIDC-authenticated, client-side key generation only

This is the piece that actually populates the registry, and the part
worth being most careful about.

1. Trustee authenticates to Keycloak via OIDC (standard login). The
   registration tool now holds a token with a verified `sub` and
   display-name-ish claims.
2. **The keypair is generated entirely on the trustee's own device —
   never by shardic infrastructure, not even momentarily.** In a
   browser: `SubtleCrypto` (WebCrypto) generates the keypair in-page;
   the private key is exported straight to a local download and never
   transmitted. As a CLI equivalent: a local `shardic-envelope
   register` command, run on the trustee's own machine, mirroring the
   existing `vault_create*.py` pattern of local-only execution.
3. The client submits only: the public key, its algorithm tag, and a
   signature over a server-issued nonce (proof of possession) — signed
   with the newly generated private key, authenticated by the OIDC
   token from step 1.
4. The registry verifies the signature (rejects on mismatch — this
   catches a malformed or unmatched submission, not a hijacked
   session, see threat model), stamps the record with the verified
   `sub`, and stores it.

**Server-side keypair generation with a one-time "copy window" handover
was considered and rejected.** The reasoning, in short: shardic-envelope's
entire value proposition is that the private key is protected by
something *only the trustee* ever holds. Generating it on infrastructure
shardic controls — even for a few seconds, even if shown once and
never persisted — recreates exactly the centralized-custody exposure
window the plugin exists to eliminate: the key transits a network
response, briefly exists in a server process's memory, and gets
rendered through a clipboard/DOM path that's a genuinely worse
exfiltration surface (syncing clipboard managers, extensions, crash
recovery, screen capture) than "it was never anywhere but the
trustee's device." A partial failure mid-handover (crashed tab, dropped
connection) also reproduces the same "did this complete correctly"
fragility that
[secure destruction of plaintext intermediates](pubkey-envelope-plugin.md#secure-destruction-of-the-plaintext-intermediates)
already has to reason about for codewords — no reason to introduce a
second version of that problem for key material when it's avoidable
entirely by not generating server-side in the first place.

For trustees without existing key-management habits (the
`pubkey-envelope-plugin.md` threat model assumes "password managers,
hardware security keys, GPG/age identities" — not a safe assumption for
every trustee), the better accessibility answer is **hardware-backed
generation**, not software generation with a copy window: a WebAuthn
platform authenticator or a hardware token generates the keypair
on-device, non-extractable by construction. There's no handover step
to secure because the private key is never in a form that could be
copied at all. Worth building as the recommended path for
less-technical trustees, ahead of any softer fallback.

Rotation reuses this same flow with a fresh keypair; the registry
record is superseded by the new one. This still leaves open the
"rewrap already-wrapped codewords after rotation" question
`pubkey-envelope-plugin.md` already flags as TBD.

This same rotation mechanism is also the resolved answer to
**device-loss portability**: there is no separate export/backup path
for a trustee's private key. A lost or wiped device is just an
unplanned rotation — see
[portable-trustee-client.md](portable-trustee-client.md#device-portability-resolved-device-bound-re-register-on-loss)
for the full reasoning and the alternatives considered and rejected.

## Keeping the OAuth dependency scoped to registration only

Wrap-time (`vault_create*.py` → shardic-envelope) and recovery-time
(`vault_recover*.py`) must not require Keycloak or any IdP to be
reachable. Both operate against the local key registry, populated
ahead of time by the registration flow above. This matters
specifically because recovery tends to happen under exactly the
conditions where "is the IdP up" is a bad bet — the same offline-first
posture the base scheme already commits to. OIDC's role stays confined
to the one occasional action (register/rotate a key) where verifying
identity is actually the point.

## The operator role

**Status: implemented** — `demo/combiner/app.py`'s `_require_operator()`,
`demo/combiner/keycloak_client.py`'s `user_has_realm_role()`, and a
`shardic-operator` realm role + dedicated `shardic-operator-client`
OIDC client in `demo/keycloak/realm-export.json`. Verified end-to-end
against the real demo stack: an operator token is accepted and audited
by username, a valid-but-unauthorized trustee token is correctly
rejected 403, and a missing token is rejected 401.

**Before this**, every privileged action in `demo/combiner/app.py` —
vault create, recovery start/finalize/verify, even Keycloak
group-membership reads — was gated by one static shared bearer token
(`COMBINER_ADMIN_TOKEN`). There was no identity behind it and no audit
trail: anyone holding the token could do anything, and the combiner
couldn't distinguish one operator from another or record who did what.

**What was built:** the operator is promoted to a real
Keycloak-authenticated role, `shardic-operator`, in the same realm as
the trustee directory but with its own OIDC client
(`shardic-operator-client`) and its own `OPERATOR_OIDC_ISSUER`/
`OPERATOR_REALM` env vars — kept as separately named settings from day
one, even though they resolve to the same Keycloak URL/realm as the
trustee directory today. That's deliberate: the whole point of a
distinct config knob is that splitting operators into their own
realm later (a plausible real-world requirement — operators and
trustees are different trust roles) becomes a config change, not a
re-architecture. Authorization is by role claim (`shardic-operator`
membership), checked via the Admin API using the combiner's own
existing service-account credential (the same trust model already
used for `get_group_members()` — see
[keycloak_client.py's module docstring](../demo/combiner/keycloak_client.py)
for why role claims are never trusted directly out of the caller's own
token). This is the same "scope by group/role, not by bare realm
identity" pattern this doc already uses for trustee selection (see
["Trustee selection via the Keycloak Admin
API"](#trustee-selection-via-the-keycloak-admin-api) above).

**A real environmental gotcha surfaced and fixed during verification:**
Keycloak's `start-dev` mode derives the token issuer from whichever
hostname a request arrives on by default — a token an operator fetches
via `localhost:8080` (from the host, the natural thing for a human to
do) got a different `iss` claim than what the combiner computed
verifying it via `keycloak:8080` (the container-internal address),
causing every operator request to fail userinfo verification with a
401 that had nothing to do with authorization. Trustee auth never hit
this because trustees fetch and present their own tokens entirely
within the container network. Fixed by pinning `KC_HOSTNAME` to a
single fixed value in `demo/docker-compose.yml` so the issuer no
longer varies by request path — worth remembering for any future
route that, like this one, is the first to have a human (not a
container) as the token-fetching party.

### Separation of duties: implemented

An operator can never self-select as one of the T selected trustees
(primaries or backups) for a ceremony they themselves initiate —
`initiate_ceremony()` in `demo/combiner/app.py` compares the operator's
authenticated `sub` against every named primary *and* every name on the
ordered backup list, not just the initial T, before a ceremony is
allowed to form. Verified live: an operator attempting to name
themselves anywhere in either list gets a 403, not a silent
acceptance. This was blocked on
[ceremony-formation.md](ceremony-formation.md#the-operator-role)'s T/D
selection step, which is now implemented — see that doc for the full
ceremony-formation design this check is part of.

## New threat-model considerations

- **Service-account compromise (picker side).** A compromised
  Keycloak service account with `view-users` on the trustee group lets
  an attacker enumerate group membership. It does not let them forge a
  registered key — that requires compromising the OIDC session used at
  registration (below) — so this is a confidentiality/enumeration risk,
  not a key-substitution one. Mitigate with the least-privilege scoping
  already described.
- **A hijacked OIDC session at registration time is a real residual
  risk.** Proof-of-possession (step 3 above) proves the submitted
  public key matches the submitted private key — it does *not* prove
  the session belongs to the claimed trustee if their Keycloak session
  itself has been hijacked. This is the same class of risk as any
  OIDC-authenticated action anywhere, not something specific to
  shardic-envelope, but worth stating plainly rather than implying
  OIDC login "solves" identity binding outright.
- **The registry remains a trust boundary**, exactly as
  `pubkey-envelope-plugin.md`'s
  ["credential lookup is a new trust boundary"](pubkey-envelope-plugin.md#new-threat-model-considerations-this-introduces)
  section already says: if the registry is tampered with post-hoc
  (key substituted after legitimate registration), wrapping would
  faithfully encrypt to the attacker's key. The fingerprint-confirmation
  step that doc recommends still applies here as defense in depth —
  OIDC-verified registration narrows *who could have submitted* a key,
  it doesn't replace verifying the registry wasn't altered afterward.

## Open questions / TBD before real implementation

- Registry backing store: flat JSON is enough for small trustee counts;
  worth deciding the threshold where SQLite (or something with actual
  access control) becomes necessary.
- Proof-of-possession nonce: needs expiry/replay protection, not fully
  specified here.
- Whether to build the WebAuthn/hardware-token path in the first
  version or treat it as a fast-follow after browser/CLI software
  generation ships.
- Registration surface: browser flow vs. CLI-first — CLI matches this
  repo's existing pattern most closely, but a browser flow may be
  necessary if trustees aren't expected to have a local Python/CLI
  environment.
- Whether picker UI and registration tool ship as one `shardic_envelope.py`-adjacent
  script or stay split, mirroring the still-open "CLI/GUI surface"
  question in `pubkey-envelope-plugin.md`.
- ~~Combiner/vault-holder discovery and registration initiation~~ —
  **resolved by splitting it into two separate events, each with its
  own answer** (see below); this was previously one open question
  conflating two different problems.

### Combiner discovery (resolved)

This doc (and the working `demo/` implementation) previously assumed a
trustee already knows which combiner to register with — in the demo
that's a hardcoded `COMBINER_URL` env var per container. The original
open question bundled two distinct problems together; resolving them
separately is what unblocked it:

1. **Directory registration** (this doc, above) is **self-service / pull**:
   once a candidate is added to the `shardic-trustees` group, they
   register their persistent keypair once, ahead of any ceremony,
   against the org's known enrollment endpoint. This event is
   decoupled from any specific ceremony — the resulting pubkey is
   reusable across every future ceremony that selects this trustee.
2. **Ceremony participation** is a separate, later event, and it's
   **push / invitation-driven**: at ceremony-initiation time, an
   operator issues an ephemeral, per-trustee invitation that names
   which combiner/vault-holder instance is running *this specific
   ceremony* and where to send an unsealed shard. The invitation doubles as
   discovery (which instance) and a fresh liveness/proof-of-possession
   check, without requiring a second registration event or a fresh
   keypair. See [ceremony-formation.md](ceremony-formation.md) for the
   full ceremony-initiation and invitation design.

Conflating these two was what made the question feel unresolvable —
"self-service risks landing at the wrong instance" is only a problem
for the ceremony-participation half, which is now push/invitation-based
specifically to close that gap; directory registration staying self-service
is fine because it isn't tied to any one ceremony's combiner instance
in the first place.

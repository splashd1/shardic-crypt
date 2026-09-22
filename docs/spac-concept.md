# SPAC: generalizing shardic's protected value beyond file decryption (proposed, unimplemented)

**Status: design proposal, early brainstorm.** Nothing described here
exists in the codebase, and unlike the other `docs/*.md` proposals
this one isn't scoped to a single mechanism -- it's a reframing of what
shardic ultimately protects, which the rest of this project's design
docs should be read against once it stabilizes.

> **Note on downstream sync:** [embedment-manual.md](embedment-manual.md)
> synthesizes a fork/decision tree from this doc (SPAC bundles, cohort
> framing, key-custody options). It's a snapshot, not generated —
> changes here that affect Fork 1/2/3's shape won't auto-propagate.
> If you revise this doc in ways that touch that framing, check
> whether embedment-manual.md needs a matching update.

## The reframe

Everything shipped or designed so far treats the protected value as
*a file* -- `vault_core.py` encrypts a plaintext archive under a DEK,
splits the DEK, and recovery hands back the archive. **SPAC (shardic
protected action code)** names the more general case this is actually
an instance of: the plaintext shardic protects isn't the end goal, it's
the *enabling value for some protected action* -- gaining financial
access, arming a weapon, unlocking a sensitive file, account access,
or any other capability where "the right D-of-T parties agreed" should
be the gate. "Decrypt this file" is the special case where the
protected action is exactly "the codeword holder gets to read the
plaintext" -- the same mechanism, applied to the narrowest possible
action.

**PT SPAC** / **CT SPAC** name the plaintext/ciphertext pair in this
broader frame -- same relationship as any other plaintext/ciphertext
in this project, just not assumed to be a file.

## Design priorities

Security and trustworthiness are the top priority throughout this
design set -- no large or critical gap is acceptable, and every open
question in this doc and its companions gets resolved (or explicitly
flagged unresolved) rather than quietly assumed away. A close second,
not an afterthought: **the ceremony spanning SPAC protection,
emplacement, and authorized access/execution should stay low-friction
to actually run.** A mechanism nobody can operate without odious
overhead doesn't get used correctly, or gets worked around -- which is
itself a security failure, just a slower-motion one. Every design
choice in this doc set should be read against both priorities at once:
prefer the option that doesn't add friction to the *frequent* path
(arming/recovery) even if it costs a little more at the *rare* one
(creation/approval/rotation) -- the single-operator and single-local-
custodian decisions elsewhere in this design set, and the amortized
approval cost in ["PT/CT swap
integrity"](#pt-ct-swap-integrity) below, both follow this rule.

## Prior art: this has a name outside shardic already

- **Permissive Action Links (PAL)** -- the closest real precedent: a
  code required to arm a weapon, withheld until an authorized
  multi-party release procedure completes. This is "arming a weapon"
  as a protected action, gated by multi-party agreement, which is
  exactly SPAC's shape for that example.
- **Two-Person Integrity / Two-Man Rule** (DoD 5210.41-series) -- the
  doctrinal language for "no single individual can access or execute X
  alone." This is the vocabulary for what the trustee threshold plus
  the operator separation-of-duties check
  (`initiate_ceremony()`, and reused in
  [shardware-token-embed-extract.md](shardware-token-embed-extract.md#why-single-operator-authorization-is-sufficient))
  already implement, just not previously named that way in this
  project's docs.
- Sits alongside, not instead of, the commercial analogs already used
  elsewhere in this design set -- HSM M-of-N quorum auth, FIDO2,
  GlobalPlatform SCP, TPM sealing. PAL/TPI answer "why gate a
  *capability*, not just data"; the commercial analogs answer "how do
  you actually build the mechanics."

## Architecture: the shardic client module

A consuming system is built with a "plugin" at the critical-path point
where the PT SPAC is needed. During development and test, the real PT
SPAC sits in that pipeline directly, so the system can be validated
end-to-end. Before fielding, PT SPAC is swapped for a CT SPAC embedded
in a **shardic client module** at that same plugin point -- the
consuming system's analog of the trustee apps and combiner this
project already has, except this one lives inside somebody else's
execution pipeline rather than being shardic's own frontend.

The interface between the client module and "the shardic service" --
what this project's other docs would call an API, what the user
framing this doc originated from called an **ICD (Interface Control
Document)** -- isn't designed here. Worth treating as a formal contract
rather than an informal library call, given what's plugged into it.

**Ephemeral-at-point-of-use has to extend past the combiner.** This
project already treats "never persist the plaintext longer than
necessary" as load-bearing -- `_secure_delete` after wrapping
(`app.py:496`), no server-side unsealed shard persistence in the
`shardware-token` designs. The same discipline now has to reach into
the *consuming* system: PT SPAC should exist in the client module's
memory only long enough to hand off to (or itself trigger) the
protected action, then get zeroized. Otherwise all the threshold-
recovery rigor upstream is undone by a careless integration downstream
-- this is a new boundary for an existing invariant, not a new
invariant.

## Fielded-system binding

The open problem this doc actually resolves: a copied CT SPAC blob,
combined with a legitimate D-of-T trustee quorum, shouldn't be
sufficient to arm the protected action on a *different* instance of
the client module than the one it was emplaced into.

**This needs no new crypto.** `gf256_sss_prime.py` already implements
exactly the required property, just for a human prime trustee:

```python
# gf256_sss_prime.py:51-54
mask = secrets.token_bytes(len(secret))
masked_secret = bytes(a ^ b for a, b in zip(secret, mask))
pool_shards = split_secret(masked_secret, threshold=pool_threshold, total_shards=pool_size)
```

`reconstruct_secret_with_prime()` (same file, lines 57-63) is the exact
inverse: Shamir-reconstruct `masked_secret` from any
`pool_threshold`-of-`pool_size` shards, then XOR against `mask`. Neither
the mask alone nor the pool shards alone reconstruct anything -- an
algebraic guarantee, not a policy one, already implemented and
self-tested (`gf256_sss_prime.py:66-79`) and already wired through
`vault_core_prime.py`'s `try_match_word_prime`/
`reconstruct_and_decrypt_prime`.

**The fielded system's hardware is a `Fielded Prime Element`** -- a
hardware-embodied instance of the prime-trustee role, standing in for
a human prime trustee:

```
mask        = the fielded system's own hardware-sealed secret
              (PUF/secure-element, same non-extractable property as
              a shardware-token -- see
              shardware-token-embed-extract.md's "Token-side
              possession factor" -- generated once at emplacement,
              never leaves this hardware, never typed by a human,
              never a codeword). A separate X25519 keypair
              (field_pubkey/field_privkey), unrelated to mask and
              used only to receive a wrapped MAC key, is introduced
              later in this doc -- see "PT/CT swap integrity"'s Key
              sources.
pool_shards = ordinary trustee shards, pool_threshold-of-(T-1),
              delivered by shardware-token or network exactly as
              already designed elsewhere in this project
DEK         = reconstruct_secret_with_prime(mask, pool_shards)   -- unmodified
CT_SPAC     = AES-256-GCM(PT_SPAC, DEK)                          -- unmodified vault_core.py path
```

Copy `CT_SPAC` to different hardware, bring a full legitimate trustee
quorum along -- reconstruction still fails, because `mask` is bound to
one specific piece of silicon and was never extractable from it. The
only new component is a client module that (a) unseals `mask` locally
at arming time, (b) collects `pool_threshold` pool shards from human
trustees, and (c) calls the existing reconstruction function. Nothing
in `vault_core_prime.py` or `krypt_container.py` changes.

**Naming this role**: a `Fielded Prime Element` is the device, `mask`
is the value it holds -- the same device/value split already used for
`shardware-token`/`unsealed shard` elsewhere in this project. "Prime trustee"
in `docs/nomenclature.md` stays the human case by default; a
`Fielded Prime Element` is the hardware-embodied instance of that same
role, named distinctly rather than stretching "trustee" (which reads
as a human party throughout the rest of this project's vocabulary) to
also mean a piece of silicon.

### Where DEK reconstruction must happen

Only holds if reconstruction happens **inside the fielded system's own
boundary** -- it acts as its own combiner for this ceremony, receiving
pool unsealed shards directly (network or physical presentation) rather than a
separate combiner reconstructing DEK and shipping it (or the decrypted
PT SPAC) onward afterward. The latter reintroduces a transport hop for
a live secret and doubles the attack surface for no benefit; avoid it
unless the fielded system genuinely can't host combiner logic itself.

### Scope, settled: one specific piece of hardware, full stop

No multi-unit redundancy in this design. If the fielded hardware is
replaced, `mask` is gone with it -- there's no export path, matching
the stance `portable-trustee-client.md` already took for a lost
trustee device (re-enroll, don't migrate the secret). Re-arming on
replacement hardware means re-running the embed/emplacement sequence
against the new hardware's own `mask`, not "recovering" the old
binding. Multi-unit redundancy (a DR site, backup hardware for the
same protected action) is explicitly out of scope for this version --
if it becomes a real requirement, it needs its own design (likely a
separate `CT_SPAC` wrap per unit's own mask, decided at creation time),
not an extension bolted onto this one.

## Fielded-system local-unlock factor

`mask` being non-extractable from its hardware isn't quite enough on
its own: a *stolen fielded unit*, run through its own legitimate local
unseal interface, shouldn't yield `mask` either, independent of
whether any trustee or operator is involved at all. This needs a
second, local input in addition to the hardware seal itself -- the
same `LocalUnlockFactor` Protocol defined in
[shardware-token-embed-extract.md](shardware-token-embed-extract.md#token-side-possession-factor),
reused here rather than given a second, parallel definition: a
discrete, role-transferable possessed (physical key/token) or known
(PIN/passphrase) input, with identity-bound biometric available as a
legitimate but tradeoff-aware choice for a fixed, non-rotating
custodian.

One local custodian is sufficient as designed here, for the same
structural reason a single remote operator was sufficient for the
extraction grant
([shardware-token-embed-extract.md](shardware-token-embed-extract.md#why-single-operator-authorization-is-sufficient)):
the remote operator and the local custodian are already two
independent parties covering two different attack surfaces (logical/
remote vs. physical/local), which is real two-party control before
either individual step requires more than one person. That said, "one"
here is a configuration choice, not an architectural ceiling -- nothing
prevents a deployment from requiring two local factors (e.g. two
key-switches, PAL/launch-console style) if it wants stronger local
control than this default.

## PT/CT swap integrity

Two different guarantees are easy to conflate here, and only one of
them already exists.

**Ciphertext integrity** (already have, free): AES-256-GCM's auth tag
guarantees `CT_SPAC` decrypts to *exactly* what was originally
encrypted, or fails loudly -- existing `vault_core.py`/
`krypt_container.py` machinery already gives this. **Content
authenticity relative to approval** (the actual gap): nothing today
confirms that what got encrypted was the *correct, tested, approved*
`PT_SPAC` in the first place. AES-GCM will happily and correctly
decrypt a wrongly- or maliciously-substituted value right back out --
it only promises "you get back what was put in," never "what was put
in was right." An accidental stale value, or a malicious insider swap
at wrap time, sails through untouched without a second, independent
check.

### The fix: a commitment, checked twice

At approval time, once `PT_SPAC` is validated in the real dev/test
critical-path pipeline:

```
salt       = random(16-32 bytes)
commitment = KDF(salt, PT_SPAC)   -- kdf.py's existing Argon2id/PBKDF2
                                      selection, NOT a bare hash --
                                      PT_SPAC may be as low-entropy as
                                      a short arming code, same reason
                                      codewords never get bare-hashed
                                      elsewhere in this project
```

`{salt, commitment}` is safe to store non-secretly -- it doesn't leak
`PT_SPAC`, the same assumption every codeword-derived KDF output in
this project already relies on.

Checked at two separate points, but not with the same mechanism -- the
frequent one has to be cheap:

1. **At emplacement** (pre-wrap, by the wrap operator, once per
   `PT_SPAC` version): verify `KDF(salt, PT_SPAC) == commitment` and
   `Ed25519_Verify(approver_pubkey, approval_cert)` before producing
   `CT_SPAC = AES-256-GCM(PT_SPAC, DEK)`. Refuse to wrap on mismatch --
   catches an accidental or malicious substitution at the moment it
   would happen. Argon2id is deliberately slow/memory-hard (why it's
   the right choice for a possibly-low-entropy `PT_SPAC`), which is
   fine here since this runs once per version, never once per arming.
2. **At arming** (post-decrypt, inside the fielded client module,
   *every ceremony* -- on the [latency-sensitive
   path](#availability-and-latency-rto)): re-running the same slow KDF
   and signature check on every arming event would fight the RTO
   directly, so this step uses a **fast MAC** derived and wrapped at
   emplacement time instead:

```
-- at emplacement (Phase 2, wrap operator, after step 1's KDF/
-- signature check already passed):
mac_key         = random(32 bytes)
tag             = HMAC-SHA256(mac_key, PT_SPAC)
wrapped_mac_key = shardic_envelope_crypto.wrap(mac_key, field_pubkey)
-- {tag, wrapped_mac_key} joins the emplacement bundle; mac_key itself
-- never travels unwrapped, so nobody holding just the bundle -- only
-- the fielded system's own private key -- can forge a new tag for a
-- substituted PT_SPAC

-- at arming (Phase 3, fielded client module, every ceremony):
mac_key = shardic_envelope_crypto.unwrap(wrapped_mac_key, field_privkey)
assert HMAC-SHA256(mac_key, decrypted_PT_SPAC) == tag   -- refuse to arm on mismatch
```

This still catches what this check exists for -- anything that changed
*between* emplacement and the real ceremony, such as a compromised
build pipeline re-wrapping a different `CT_SPAC` afterward, which
AES-GCM's own integrity check can't see since a re-wrap with a
different plaintext is still a perfectly valid ciphertext -- at
ECIES-unwrap-plus-HMAC cost (milliseconds) instead of an Argon2id cost
on every arming event. The slow KDF/signature check from step 1 stays
available as a periodic, out-of-band audit (not on the arming critical
path) for anyone who wants belt-and-suspenders reassurance that
nothing has drifted since approval.

Fail loudly on either mismatch -- refuse to arm, don't silently
proceed -- matching this project's existing posture (AES-GCM auth-tag
failures, `envelope-delivery.md`'s "loud, not silent" re-redemption
stance).

### Who signs the commitment, and why it can't be the wrap operator

`{salt, commitment}` alone only helps if it's trustworthy -- if
whoever performs the wrap step can also freely mint a new commitment
to match whatever they're substituting, the check is circular. This
needs an **Approver**, a role independent of whoever operates the
wrap/emplacement step -- the same separation-of-duties instinct used
for the operator/trustee split elsewhere in this design set.

**Actors:**

| Actor | Role | Distinct from |
|---|---|---|
| **Approver** | Validates `PT_SPAC` in the real dev/test pipeline, then commits and signs off on it | The wrap operator -- this separation is the entire point |
| **Wrap/emplacement operator** | Runs vault creation: generates `DEK`, does the prime/pool split, produces `CT_SPAC` | The Approver, and the `shardic-operator` who later authorizes extraction grants during recovery |

**Protocol, phased:**

```
Phase 1 -- Approval (Approver, independent of wrap operator, once per
            PT_SPAC value/version -- not once per arming event, so
            this cost is paid at the rare step, not the frequent one):

  salt          = random(16-32 bytes)
  commitment    = KDF(salt, PT_SPAC)
  approval_cert = Ed25519_Sign(
      approver_privkey,
      {salt, commitment, pt_spac_id/version, timestamp}
  )

  -- the version/timestamp in the signed payload matters beyond the
  -- commitment itself: it stops an old, otherwise-valid approval_cert
  -- from being paired with an unrelated later wrap event.
  -- approval_cert (never PT_SPAC itself) is the durable artifact that
  -- crosses to the wrap operator; if PT_SPAC also has to physically
  -- cross that boundary, that hand-off should go through the existing
  -- shardic_envelope_crypto.wrap() machinery, not a new transport.

Phase 2 -- Vault creation / CT_SPAC generation (wrap operator):

  1. Verify Ed25519_Verify(approver_pubkey, approval_cert) -- refuse on failure
  2. Verify KDF(salt, PT_SPAC) == commitment                -- refuse on failure
  3. DEK = random(32 bytes)
  4. mask, pool_shards = split_secret_with_prime(DEK, pool_threshold, pool_size)  -- unmodified
  5. CT_SPAC = AES-256-GCM(PT_SPAC, DEK)                                          -- unmodified
  6. mac_key = random(32 bytes)
     tag = HMAC-SHA256(mac_key, PT_SPAC)
     wrapped_mac_key = shardic_envelope_crypto.wrap(mac_key, field_pubkey)  -- unmodified wrap()
  7. Emplace {CT_SPAC, salt, commitment, approval_cert, tag, wrapped_mac_key}
     as one bundle (all non-secret except CT_SPAC and wrapped_mac_key's
     sealed contents, safe to travel together)
  8. Destroy PT_SPAC, DEK, mac_key, and any wrap-time copy immediately --
     extends the existing _secure_delete discipline

Phase 3 -- Arming (fielded client module, every ceremony -- fast path,
            per "Availability and latency (RTO)" below):

  1. DEK = reconstruct_secret_with_prime(mask, pool_shards)      -- unmodified
  2. candidate_PT_SPAC = AES-256-GCM_decrypt(CT_SPAC, DEK)
  3. mac_key = shardic_envelope_crypto.unwrap(wrapped_mac_key, field_privkey)
  4. Verify HMAC-SHA256(mac_key, candidate_PT_SPAC) == tag       -- refuse to arm on mismatch
  5. Hand off candidate_PT_SPAC to the protected action, then
     zeroize mac_key and candidate_PT_SPAC immediately

  (the slow KDF/signature re-check from Phase 2 stays available as a
   periodic, out-of-band audit -- not on this path)
```

### Key sources

- **Approver's Ed25519 signing keypair** -- a genuinely new key type
  (Ed25519 specifically, since X25519 -- used everywhere else in this
  project -- is DH-only and can't sign). Touched rarely (once per
  `PT_SPAC` approval/rotation), so it fits the same low-frequency/
  high-value tier as `vault_root_key` -- HSM/TPM-sealed, or a
  human-held smartcard signing key, reusing the same hardware category
  already canvassed for shardware-tokens rather than inventing new
  key-custody infrastructure.
- **`DEK`** -- ephemeral, unchanged from today's model.
- **`mask`** -- the fielded system's own hardware-sealed secret,
  unchanged from the fielded-system-binding design above.
- **Fielded system's X25519 keypair (`field_pubkey`/`field_privkey`)**
  -- a new, minimal addition alongside `mask`: generated at the same
  emplacement bootstrap moment, using the same
  `shardic_envelope_crypto.generate_keypair()` already used by every
  other party in this project. Its only job is receiving
  `wrapped_mac_key`; it plays no role in DEK reconstruction, which
  stays exclusively `mask`'s job.
- **`mac_key`** -- ephemeral, generated fresh per `CT_SPAC`/version at
  emplacement, destroyed at the wrap operator immediately after use,
  re-derived locally (via `unwrap`) by the fielded system at every
  arming and zeroized after use.
- **Trustee keypairs (X25519)** -- unchanged.
- **`vault_root_key`/`vault_intermediate_key`** (the extraction-grant
  chain from `shardware-token-embed-extract.md`) -- **kept deliberately
  separate from the Approver's key**, even though both are rarely
  touched and high-value. They answer different questions:
  `vault_root_key` governs *when pool unsealed shards get released* during
  recovery; the Approver's key governs *whether the right thing was
  ever wrapped in the first place*. Sharing one key across both would
  quietly merge two authorities that should stay independent -- the
  same separation-of-duties instinct as everywhere else in this
  design set, just applied to keys instead of people.

Procedural alternative, if a cryptographic Approver key isn't worth
standing up yet: a witnessed, logged approval record substitutes for
`Ed25519_Sign`/`Ed25519_Verify` -- weaker, cheaper, the same
cryptographic-vs-procedural choice already offered for trustee
identity in `shardware-token.md`.

## Availability and latency (RTO)

"Unlock a sensitive file" tolerates a slow, deliberate, hours-long
ceremony; "arm a weapon" or "in-the-moment financial access" plausibly
can't. Rather than pick one universal answer, a SPAC deployment should
declare its own target **RTO** (recovery time objective) and choose
from the options below accordingly -- the same pluggable-per-
deployment pattern as `LocalUnlockFactor` and the physical-medium table
in `shardware-token.md`.

Three points in the ceremony drive almost all of the variance. None of
the mitigations below reduce `pool_threshold`, `D`, or how many
independent inputs are cryptographically required -- every lever here
is about pre-positioning and parallelizing already-required inputs,
never about requiring fewer of them, per this doc's [design
priorities](#design-priorities).

### Convening the quorum

Driver: whether the ceremony was **pre-formed** ahead of the RTO clock
starting (`ceremony-formation.md`) versus formed ad hoc; trustees'
on-call posture; the notification mechanism; whether trustees are
co-located or dispersed.

| Option | Mechanics | Accessibility | Automation | Rough time |
|---|---|---|---|---|
| Pre-formed standing ceremony, push notification, one-tap response | Trustees already accepted invitations in advance; alert via push/SMS; single tap derives + submits the unsealed shard | High -- anywhere with a data signal | High | seconds to ~10 min, bounded mostly by human reaction time |
| Ad hoc formed ceremony, phone-tree/manual notification | No pre-forming; each trustee located and contacted individually, logs in and submits manually | Depends entirely on reachability at that moment | Low | tens of minutes to several hours (longer if unreachable) |
| Co-located duty crew, in-person physical action | Trustees already physically present, act at a console or insert a shardware-token | High only within the facility | Low (physical), but fast -- remote reachability isn't a variable | seconds to a couple minutes, bounded by walk-to-station time |

`ceremony-formation.md`'s existing selection/invitation/backfill
machinery is the biggest lever here and needs no modification --
pre-forming the ceremony converts "select, invite, wait for accept"
into a one-time setup cost paid before the RTO clock starts.

### Unsealed shard delivery

Driver: transport medium -- network versus physical -- and for
physical, distance/custody logistics; for network, whether the
trustee's device is already authenticated.

| Option | Mechanics | Accessibility | Automation | Rough time |
|---|---|---|---|---|
| Direct network submission | Already-authenticated device POSTs `shard_envelope` to the combiner | Anywhere with network | High | sub-second to a few seconds |
| Local physical carriage | USB/smartcard token hand-carried a short distance within one facility, read by the ingestion adapter | Single-site only | Low | a few minutes to tens of minutes, facility-size dependent |
| Long-haul physical carriage | Courier, safe-deposit retrieval, cross-site hand-off | Anywhere, but slow | Minimal, deliberately | hours to days |

Air-gap/no-network-dependency and tight RTO are largely **mutually
exclusive properties** -- a deployment picks the one it actually needs;
this design doesn't provide both for free.

### Endgame unlock (operator grant + local-custodian factor)

Driver: whether the operator/custodian are pre-positioned (on-call)
versus paged cold; the mechanics of the local factor; whether the
extraction-grant path is live-per-request or pre-authorized in batch;
and -- the one place actual *compute* latency rather than human/
logistics latency matters -- the swap-integrity check's own cost,
resolved by the fast MAC in ["PT/CT swap
integrity"](#pt-ct-swap-integrity) above.

| Option | Mechanics | Accessibility | Automation | Rough time |
|---|---|---|---|---|
| Operator + custodian both on-call, PIN/key-switch, fast-tag swap check | Pre-positioned humans, near-instant local actions, cheap crypto check | High if the on-call roster is staffed | High | single-digit seconds to under a minute |
| Remote operator paged on demand, on-site custodian | Operator located, logs into admin console, reviews, approves over network | Moderate -- depends on response time | Moderate | a few minutes to ~30 min |
| Dual local custodian (two key-switches, PAL-style), no live remote step | Two people coordinate a simultaneous local action, possibly against a pre-authorized grant batch | High if both already briefed/co-located | Low, deliberately manual | tens of seconds to a few minutes if present; longer if summoned |

A single operator and single local custodian being *cryptographically
sufficient*
([shardware-token-embed-extract.md](shardware-token-embed-extract.md#why-single-operator-authorization-is-sufficient),
["Fielded-system local-unlock
factor"](#fielded-system-local-unlock-factor)) doesn't make either one
*available* -- a lone authorized person who can't be reached at 3am is
a single point of failure for latency, separate from being a single
point of authorization. Fix: extend `ceremony-formation.md`'s ordered-
backup-list/backfill mechanism to the operator and local-custodian
roles too -- an on-call roster, not a ceremony-trustee list. This
doesn't weaken the security property at all: exactly one operator
still authorizes any given grant, exactly one custodian still supplies
the local factor -- the backup list only widens *who's eligible* to be
that one person when the primary is unreachable.

### CONOPS drives the choice, traded against unauthorized-access resistance

None of the tables above name a winner. The concrete choice at each of
the three points is a CONOPS decision -- who the trustees/operator/
custodians actually are, how they're staffed, what notification
infrastructure exists, and what RTO the deployment has committed to.
Each choice is also a real trade against unauthorized-access
resistance, not just speed: a pre-formed, pre-positioned, networked,
single-tap ceremony is fast, but a coerced or compromised set of
already-standing, already-authenticated parties moves through it just
as fast. Physical carriage, ad hoc paging, and dual-custodian
coordination are slow, but that same friction is often a deliberate
deterrent -- courier custody logs, two people having to physically
coordinate -- that creates more real-world opportunities for something
to be noticed before completion. RTO is one half of a trade the CONOPS
has to state on purpose against unauthorized-access resistance, not
something this design should default on its behalf.

## Open questions / TBD

- **Concrete `LocalUnlockFactor` choice**: which category (possessed,
  known, or identity-bound) to actually build for a given fielded
  deployment is deliberately left unpicked -- see
  ["Fielded-system local-unlock
  factor"](#fielded-system-local-unlock-factor) above.

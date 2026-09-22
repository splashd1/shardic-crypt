# ICD wire format: the shardic client module boundary contract (proposed, unimplemented, review draft)

**Status: draft for review, not committed.** Follows on from
`embedment-manual.md`'s fork tree, which determines *what* an ICD
needs to carry for a given deployment but explicitly stops short of
designing the contract itself
(`spac-concept.md#architecture-the-shardic-client-module`). This draft
takes that next step. Nothing here is implemented; nothing here is
adopted.

## Scope: which boundary this actually designs

Two different boundaries get called "the interface" in this project's
docs, and they are not the same thing:

1. **Consuming system ↔ shardic client module.** This is the ICD, per
   `embedment-manual.md`'s own diagram — the arrow labeled `◀── ICD`
   sits between the "critical-path point" and the `[shardic client
   module]` box, both *inside* the consuming system.
2. **Client module ↔ combiner/trustees.** Already designed elsewhere —
   `shardic-envelope`, `ceremony-formation.md`, `envelope-delivery.md`,
   `shardware-token-embed-extract.md`. Nothing here changes any of it.

This draft is (1) only. Everything the client module does on the
combiner/trustee side to actually produce an unlock value — grant
chains, quorum collection, commitment checks — stays exactly as
already designed; it becomes internal plumbing the ICD boundary hides,
not something this contract re-exposes.

## Settled scoping decision: local, trusted-boundary contract, not a network API

The client module is *embedded in* the consuming system by definition
— that's what "embedment" names. This draft treats the ICD as a call
across a boundary that is already inside one physical or logical trust
enclosure (same host, same fielded enclosure, or equivalent) — not a
network call to a remote peer that needs its own authentication story.
If a real deployment ever wants the consuming system and the client
module on separate hosts, that reintroduces exactly the kind of
transport-hop-for-a-live-secret problem
`spac-concept.md#where-dek-reconstruction-must-happen` already argues
against for the combiner case, and would need its own design pass, not
a quiet assumption bolted onto this one.

## Call shape: one request, one response, no session

A single discrete call — `ArmRequest` in, `ArmResponse` out — not a
persistent session or a multi-step handshake. Matches the "low-friction
for the frequent path" priority `spac-concept.md` sets as a co-equal
goal to security: the consuming system's critical-path code shouldn't
need to manage ICD-side state, only make one call and get one answer.

### `ArmRequest` (consuming system → client module)

```
ArmRequest {
  schema_version:   str
  action_id:        str   -- which protected-action slot this call is
                              for; supports more than one PT SPAC
                              instance behind a single client module
  correlation_id:   str, optional  -- caller-supplied, opaque, echoed
                              back unchanged; for the caller's own
                              logging/tracing only, never inspected or
                              used in the arming decision itself
}
```

Deliberately thin. No credentials, no factors, nothing fork-tree
related travels in this direction. Everything Fork 1's grant chain,
LocalUnlockFactor check, quorum collection, and PT/CT swap-integrity
check need is already resolved *inside* the client module before it
ever computes an `ArmResponse` — the ICD doesn't forward authorization
material from the consuming system because the consuming system isn't
a party to that authorization at all. This is the concrete payoff of
the embedment-manual field sketch: everything in that table
(`extraction_grant`, `local_unlock_assertion`, `pool_shards[]`,
`masked_secret`) is internal to the client module's own boundary,
never crosses the ICD.

### `ArmResponse` (client module → consuming system)

```
ArmResponse {
  schema_version:          str
  correlation_id:          str, optional  -- echoed from the request
  outcome:                 enum { GRANTED, DENIED, ERROR }
  unlock_value:            bytes, present only if outcome == GRANTED
                              -- the DEK / unlock signal itself,
                              opaque to this contract
  reason_code:             enum, present if outcome != GRANTED
                              (see below)
  commitment_check_result: bool, present if outcome == GRANTED
                              -- surfaces spac-concept.md's PT/CT
                              swap-integrity fast-MAC result even on
                              success, since it's audit-relevant either
                              way
}
```

**Three outcomes, not two.** `DENIED` (a real check failed — quorum
not met, commitment mismatch, grant expired, local factor failed) and
`ERROR` (transport, config, or hardware fault unrelated to any
authorization decision) are different failure modes that an integrator
needs to log and react to differently — collapsing them into one
generic failure would throw away information the consuming system
needs to decide "retry" versus "escalate" versus "page someone."

**Illustrative `reason_code` values, first pass only** — finalizing
this list is deferred until the cancel/abandon question below is
settled, since a real cancel path will need its own value (e.g.
`CANCELLED`) and revisiting the taxonomy twice is wasted motion:
`QUORUM_NOT_MET`, `GRANT_EXPIRED`, `LOCAL_FACTOR_FAILED`,
`COMMITMENT_MISMATCH`, `HARDWARE_FAULT`, `TIMEOUT`,
`UNSUPPORTED_VERSION`. Deliberately coarse — enough to drive an
operational response, not fine enough to leak which specific trustee
or step failed, the same "don't leak more than the check requires"
posture the rest of this project already takes with shard-matching.

## `unlock_value` is single-use — a MUST, not a suggestion

`spac-concept.md`'s "ephemeral-at-point-of-use has to extend past the
combiner" invariant applies directly here: the consuming system MUST
treat `unlock_value` as existing only long enough to hand off to (or
itself trigger) the protected action, then zeroize it. This contract
states that as a requirement of implementing the ICD correctly, not as
best-practice advice — an integration that logs, caches, or persists
`unlock_value` anywhere breaks the invariant this entire design set
exists to uphold, regardless of how correct everything upstream was.

## No caching, no re-arm without a fresh call

A second `ArmRequest` for the same `action_id` MUST re-run the full
path behind the boundary — fresh grant check, fresh quorum submission
or ceremony re-verification, whatever Fork 1-3's choices actually
require — never served from a cached `unlock_value` or a reused
session. Caching an unlock value across calls is the same invariant
violation as failing to zeroize it, just committed on the client
module's side of the boundary instead of the consuming system's.

## Versioning

`schema_version` is checked before anything else. A client module that
doesn't recognize the requested version returns
`{outcome: ERROR, reason_code: UNSUPPORTED_VERSION}` rather than
guessing at a best-effort interpretation — matching this project's
existing "fail loudly, don't silently proceed" posture
(`envelope-delivery.md`'s re-redemption stance, AES-GCM auth-tag
failures generally).

## Audit tie-in

Every `ArmRequest`/`ArmResponse` pair — everything except
`unlock_value` itself — is a natural fit for whatever audit sink a
deployment already has: extend the existing `_broadcast()`/`print()`
SSE pattern, or export to syslog/SIEM per the compliance-driven option
already named in `embedment-manual.md`'s per-axis table (item 8). Reuse
that existing menu rather than inventing a parallel logging story here.

## Bundle A / Bundle B: same wire shape, different internals

The punchline this design is actually going for: **the ICD's shape
does not change across the fork tree.** Bundle A (networked quorum) and
Bundle B (air-gapped, hardware-bound) produce `ArmResponse` through
very different internal paths — a live human ceremony over the network
versus a Fielded Prime Element unsealing a mask and checking a grant
chain — but the consuming system's integration code is identical either
way. A deployment can move from Bundle A to Bundle B (or anywhere
between) as a backend/CONOPS decision without touching the
consuming-system side of the ICD at all. That stability is the reason
to design this contract now, ahead of any specific deployment, rather
than let each integration invent its own shape.

| | Bundle A (Networked Quorum) | Bundle B (Air-Gapped / Hardware-Bound) |
|---|---|---|
| What happens behind `ArmRequest` | Human prime trustee + pool quorum over shardic-envelope, no Fielded Prime Element | Fielded Prime Element unseals `mask` (gated by `LocalUnlockFactor`), grant-chain check if configured, pool quorum via whichever Fork 2 transport |
| Typical latency before `ArmResponse` | Seconds to ~10 min | Minutes to hours |
| What the consuming system's code does differently | Nothing | Nothing |

## Multi-function SPAC: one trustee/ceremony apparatus, many discretely-shared SPACs

Raised in review: `action_id` isn't just an internal routing label — it
names a real design axis independent of the fork tree above. The scope
of what one PT SPAC unlock actually enables — a single function, or a
defined family of functions — is a design decision made and validated
by the Approver at embedment time
(`spac-concept.md#pt-ct-swap-integrity`'s Approver role), not something
this contract imposes.

That raises a legitimate model this draft hadn't accounted for: the
same trustee set, ceremony, and shardic-envelope/combiner
infrastructure can wrap and embed **more than one SPAC**, each with its
own discretely-defined DEK/Shamir split — its own shards/unsealed
shards, never shared across SPACs even though the trustee roster and ceremony
apparatus are — issued to the same registered trustees. At arm time,
the specific function/SPAC being requested is named explicitly, and the
trustee quorum approves *that* request, not a blanket "this ceremony's
roster may unlock anything." This is a real efficiency lever: a range
of protected functions in one consuming system can share trustee
registration and ceremony infrastructure instead of each function
standing up its own independent trustee roster.

This axis is distinct from, but analogous to, `embedment-manual.md`'s
cohort-granularity axis (item 14): cohort granularity groups *hardware
units* under one Shamir split; this groups *protected functions* under
one trustee/ceremony apparatus, while keeping the split itself discrete
per function. The two are orthogonal — a deployment could combine both
(a cohort of units, each serving a multi-function SPAC set) without
either constraining the other.

**What this means for `action_id`:** it identifies a specific,
Approver-validated SPAC instance, and under this model, the ceremony
layer (`ceremony-formation.md` / the combiner) needs to know which SPAC
a given recovery request is for, so the trustee quorum is shown and
approves the actual function being unlocked rather than an
undifferentiated "recovery." **That's a ripple into the combiner/
ceremony layer this draft doesn't design.** Today's
`ceremony-formation.md`/combiner model is built around one vault, one
recovery. Whether it needs a `spac_id` (or reuses `vault_id`) surfaced
per function, and how that shows up in the trustee-facing
invitation/approval UI, is a real open item for that layer — flagged
here, not assumed away.

## Serialization: deliberately left open

This draft fixes fields and semantics, not bytes. Concrete encoding
depends on what the consuming system is written in and how it's
embedded:

- Same-process, same-language (e.g. client module is a Python library
  the consuming system imports directly): a plain in-process call with
  dataclasses is enough — no serialization exists at all, and
  inventing one would be pure overhead.
- Cross-process or cross-language embedment: plain JSON over a local
  channel (Unix domain socket, named pipe, or equivalent), matching
  this project's existing convention everywhere else it has a wire
  format, unless a specific deployment has a hard real-time or
  footprint constraint that says otherwise.

This mirrors how `shardware-token-embed-extract.md` already left
`intermediate_cert`/`extraction_grant`'s own concrete encoding open
(bespoke binary vs. CWT/JWT) as a per-deployment menu item rather than
a single fixed choice — the same treatment applies here, one level up.

## Settled (this review round)

- **Trusted local channel, assumed.** This draft assumes the consuming
  system and client module share a trust boundary without further
  checking — no additional local authentication (Unix socket
  permissions, uid checks, etc.) is designed here. **If a real
  deployment can't guarantee that assumption holds, designing the
  trusted local channel itself is explicitly external to shardic** — a
  prerequisite the integrator solves before this contract applies, not
  a gap in this design.
- **Concurrency across multiple `action_id`s is legitimate, and more
  than an implementation detail** — see "Multi-function SPAC" above.
  Each `action_id` is independent, with its own discretely-shared SPAC;
  no shared state between them at the ICD layer.

## Open questions / TBD

- **Cancel/abandon path**: does the consuming system get any way to
  abandon a slow in-flight `ArmRequest` (relevant mainly for Bundle B's
  minutes-to-hours RTO)? **Deferred** — needs its own
  flowcharting/discussion pass before this draft designs it; not
  decided here.
- **`reason_code` taxonomy**: deferred until the cancel/abandon
  question above is resolved — a real cancel path almost certainly
  needs its own outcome/reason value (e.g. `CANCELLED`), and finalizing
  the taxonomy first would just mean revisiting it once cancel lands.
- **Ceremony/combiner-layer support for multi-function SPAC** (see
  above): whether `ceremony-formation.md`'s model needs a per-function
  identifier surfaced to trustees at approval time. Not designed here.
- **Does this still match `embedment-manual.md`'s worked field
  sketch?** First review round covered concurrency, cancel, and local-
  channel trust; the audit-sink and commitment-check surfacing haven't
  had a dedicated pass yet.

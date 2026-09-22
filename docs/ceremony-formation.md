# Ceremony formation: operator-initiated invitations, decline handling, and automatic backfill (implemented, v1.0)

**Status: implemented and verified end-to-end** against the real demo
stack (`demo/combiner/app.py`'s `initiate_ceremony()`,
`get_pending_invitation()`, `respond_to_invitation()`,
`_ceremony_scan_loop()`, plus matching trustee-side polling in
`demo/trustee/app.py`). This document covers the gap between two
things that already had designs: directory **registration** (once,
ahead of any ceremony — see
[keycloak-credential-lookup.md](keycloak-credential-lookup.md)) and
ceremony **execution** (registration → vault-create → wrap →
recovery, already implemented in `demo/`). It answers: given a
directory of registered candidates, how does one specific ceremony
actually get formed — who's invited, what happens when someone
declines or never answers, and how does the operator role that
initiates all of this get authenticated and constrained? Several
concrete choices below (TTL default, no separate ceremony-level
timeout, backup-list-exhaustion behavior) were left open in the
original design and settled during implementation — each is marked
**(v1.0 decision)** where it's resolved.

> **Note on terminology:** this doc deliberately says "candidate
> directory," never "pool," for the org-wide set of registered
> trustees. `nomenclature.md` already reserves "pool trustee" / "pool
> shard" for a distinct, unrelated shardic-prime concept (the
> non-prime `D − 1` group within one vault's threshold) — reusing
> "pool" here for a different thing would create exactly the kind of
> collision that glossary exists to prevent.

> **Note on downstream sync:** [embedment-manual.md](embedment-manual.md)
> synthesizes its RTO/backup-roster framework from this doc. It's a
> snapshot, not generated — changes here won't auto-propagate. If you
> revise the backup-roster or RTO behavior described below, check
> whether embedment-manual.md needs a matching update.

## Where this sits

```
Candidate directory (registered, per keycloak-credential-lookup.md)
        │
        ▼
Operator authenticates as shardic-operator (see "The operator role" below)
        │
        ▼
Operator initiates a ceremony: defines vault contents, T/D
(including Prime-T for shardic-prime), selects T primaries + an
ordered backup list from the directory
        │
        ▼
Ephemeral per-trustee invitations issued (see below) ──▶ accept/decline/timeout
        │                                                        │
        ▼                                                        ▼
   slot filled                                          automatic backfill from
        │                                                 next-ranked backup
        ▼
Ceremony proceeds as today: registration confirmed → vault create →
codeword wrap+destroy → recovery → finalize → verify
```

This doc doesn't change anything about the crypto path or the
already-implemented registration/vault-create/recovery mechanics —
only what happens administratively before "ceremony proceeds as
today" is reached.

## The operator role

Ceremony initiation requires an authenticated `shardic-operator` — see
[keycloak-credential-lookup.md's "The operator role"
section](keycloak-credential-lookup.md#the-operator-role) for the full
identity/authorization design (`_require_operator()` in
`demo/combiner/app.py`). **Separation of duties is implemented and
verified**: an operator can never self-select as one of the T selected
trustees (primaries *or* backups) for a ceremony they themselves
initiate — `initiate_ceremony()` checks the operator's `sub` against
every primary *and* every name on the ordered backup list at
initiation time, not just the initial T. See [automatic
backfill](#automatic-backfill) below for why a backup-list gap would
be just as exploitable as a primary-list one.

## Ceremony initiation

An operator authenticated as above initiates a ceremony via
`POST /admin/ceremony/initiate`, specifying:

- **Threshold D** (`threshold_d`).
- **Prime + pool primaries** (`prime`, `pool`) — together, T primaries.
  Vault contents are fixed per-demo (`SAMPLE_SECRET_PATH`), not
  operator-specified; a real deployment would add that as a parameter
  here.
- **An ordered backup list** (`backups`), selected from the registered
  candidate directory.

`initiate_ceremony()` (`demo/combiner/app.py`) validates: `2 <=
threshold_d <= trustees_t`, every named username is distinct and
already a registered candidate, and separation of duties (below) —
before creating any invitation. This replaced a previous demo behavior
where trustee containers simply started and registered with no
formation step in between; `/admin/vault/create` now refuses to run
without a **formed** ceremony.

## Ephemeral per-trustee invitations

Each selected candidate (primary or, later, backfilled backup) gets an
ephemeral, per-trustee invitation — a slot record
(`{role, sub, status, invited_at}`) the trustee discovers by polling
`GET /trustees/pending-invitation` and responds to via
`POST /trustees/invitation-response`, both Bearer-authenticated. An
invitation carries:

- Which combiner/vault-holder instance to talk to for **this specific
  ceremony** — in the demo, trivially the one combiner instance every
  trustee already talks to; a multi-combiner deployment would need the
  invitation to actually name one.
- A TTL (`CEREMONY_INVITE_TTL_S`, below).
- A fresh liveness/proof-of-possession check — satisfied by the same
  mechanism already used for registration and unsealed shard replies: every
  call requires a currently-valid OIDC Bearer token, freshly fetched
  each poll rather than a cached/refresh-token flow. No separate PoP
  mechanism was needed.

This resolves the discovery half of the open question
`keycloak-credential-lookup.md` previously left unanswered: directory
*registration* already answers "which combiner does a candidate
register their long-lived pubkey with" (self-service, once, against
the org's known enrollment endpoint — a **pull** model). Ceremony
*participation* is a separate, later question — "where do I send my
unsealed shard for this particular ceremony" — and that's what the invitation
answers, issued by the operator/combiner at ceremony-initiation time (a
**push** model). Conflating these two was the source of the original
open question; keeping them as two distinct events, each with its own
answer, resolves it. See
[keycloak-credential-lookup.md's "Combiner discovery"
section](keycloak-credential-lookup.md#combiner-discovery-resolved)
for the registration-side half of this.

## Decline / no-response handling

Decline and silent timeout are treated **identically** — both are just
"non-acceptance" of a slot, and both funnel through the same
`_lapse_slot_locked()` helper. Decline (`POST
/trustees/invitation-response` with `accept: false`) short-circuits
immediately; silent non-response is caught by `_ceremony_scan_loop()`,
a background thread (mirroring `_heartbeat_loop`'s existing shape)
that sweeps every `CEREMONY_SCAN_INTERVAL_S` (2s) for slots past their
TTL. **v1.0 decision:** `CEREMONY_INVITE_TTL_S` defaults to 20 seconds,
configurable via env var — long enough to comfortably exceed a
trustee's poll interval (3s default), short enough to demo without a
long wait.

### Automatic backfill

The moment a slot lapses (decline or TTL expiry), the next-ranked
backup is invited immediately — no operator round-trip required. This
is deliberately different from the already-solved live-participation
problem (the dashboard's heartbeat/pause detection during an *active*
recovery session) — formation-time non-acceptance and mid-recovery
pausing are unrelated mechanisms that happen to both look like "a
trustee isn't responding." **v1.0 decision:** if the backup queue is
exhausted before a lapsed slot can be refilled, the ceremony's status
becomes `failed` outright (no partial-formation alert-and-wait state)
— matches this project's general bias toward failing loudly over
introducing a new intermediate state. A failed ceremony doesn't block
initiating a fresh one.

### Implementation requirements this creates

- **Slot-closing is race-safe**, verified live: `respond_to_invitation()`
  only accepts a response if the slot's current occupant (`sub`) still
  matches the caller *and* the slot is still `"invited"` — a late
  accept from an already-backfilled primary finds no matching slot and
  gets a 409, not a double-fill or a silent swap-back.
- **The separation-of-duties check applies to the full backup list**,
  not just the initial T primaries — `initiate_ceremony()` checks the
  operator's `sub` against every primary *and* every name on the
  ordered backup list, all at initiation time, not re-checked lazily
  only when a name is actually invited.

## Explicitly out of scope for this document

- **Live-participation tracking during an open recovery session**
  (heartbeat, pause/live status) — already implemented in
  `demo/combiner/app.py` and the dashboard; unrelated to
  formation-time decline/backfill.
- **Invitation delivery channel mechanics** — resolved in
  [notification-channels.md](notification-channels.md), still
  unimplemented itself. The v1.0 implementation here uses plain
  polling (`GET /trustees/pending-invitation`), the same mechanism
  already used for pending envelopes — adequate for a demo where every
  trustee is a container that can poll, but not the pluggable,
  admin-configurable channel that doc designs for a real deployment
  where a human needs to be proactively notified.
- **Dashboard visualization of ceremony formation** — the SSE event
  types below are broadcast and logged in the dashboard's text panel,
  and the "Create Vault" button correctly gates on ceremony status, but
  no new visual diagram/UI was built for formation itself (the
  hub-and-spoke diagram still starts at vault creation). A reasonable
  future addition, not required to call ceremony formation "done."
- **Browser XSS residual risk and trustee private-key portability
  across devices** — resolved in
  [portable-trustee-client.md](portable-trustee-client.md).
  **`.krypt` archiving/durability** — resolved in
  [vault-storage-backend.md](vault-storage-backend.md). None of the
  three are specific to ceremony formation, so they're designed
  separately rather than folded in here.

## Design decisions settled during implementation (v1.0)

The original design left five questions open; each got a concrete,
documented answer rather than staying open indefinitely:

- **Entire backup list exhausted before every slot fills** → the
  ceremony's status becomes `failed` outright. No partial-formation
  alert-and-wait state, no automatic operator notification (though the
  failure is broadcast over SSE and logged) — matches this project's
  bias toward failing loudly over adding a new intermediate state. A
  failed ceremony doesn't block initiating a fresh one.
- **Ceremony-formation-level timeout distinct from per-invitation TTL**
  → not built. Formation runs until either every slot is `accepted`
  (→ `formed`) or a lapse can't be backfilled (→ `failed`, above) — no
  separate "abandon after N hours" timer layered on top.
- **Concrete invitation TTL default** → `CEREMONY_INVITE_TTL_S`,
  defaulting to 20 seconds, configurable via env var. Chosen to
  comfortably exceed a trustee's poll interval (3s default) without
  making a live demo wait long for a lapse to occur.
- **Backup-list reordering mid-formation** → not supported. The backup
  queue is fixed at initiation time; there's no route to edit it once
  a ceremony is forming.
- **Audit/logging shape** → the same `print()`-plus-SSE-`_broadcast()`
  pattern already used everywhere else in the combiner, not a new
  mechanism. Every state transition (`ceremony_initiated`,
  `invitation_responded`, `invitation_expired`, `backfill_invited`,
  `ceremony_formed`, `ceremony_failed`) is both logged and broadcast.

---
name: shardic-nomenclature
description: Canonical glossary and lifecycle-state vocabulary for shardic's domain objects (vault, .krypt, DEK, codeword, shard, unsealed shard, mask, envelope, trustee, prime/pool, combiner, ceremony). Load this before writing or reviewing anything that names these things — code identifiers, docs, UI copy, commit messages, white paper prose, slide decks — to stay consistent with the rest of the project and avoid conflating the two easily-confused lifecycle stages (shard vs. unsealed shard) this project already has baked into its code. Also load when asked to name a new feature, field, or concept in this project, so the new name fits the existing system instead of drifting from it.
metadata:
  type: reference
---

# shardic nomenclature

This is a naming reference, not a workflow — read the table you need, apply
the term, move on. It was compiled by reading the actual code (not
invented fresh), so where a term already has a fixed meaning in
`gf256_sss*.py` / `vault_core*.py` / `shardic_envelope_crypto.py` /
`demo/combiner/app.py`, that meaning is authoritative here too. A few
entries are recommendations rather than settled fact — those say so
explicitly.

## Quick reference

| Term | One-line definition |
|---|---|
| **Vault** | The conceptual protected unit — a plaintext under threshold custody. Never a literal on-disk object. |
| **`.krypt` container** | The vault's concrete on-disk form: magic header + metadata + ciphertext. Say "the `.krypt` container," not "the vault file," when precision matters. |
| **DEK** | The random AES-256-GCM key that actually encrypts the plaintext — the thing that gets split. |
| **Codeword** | The human-facing secret string a trustee holds or types. What a person has. |
| **Shard** | A sealed Shamir shard record living in `.krypt` metadata, *pre-match*, not yet attached to a known trustee identity. What's at rest in the vault. |
| **Unsealed shard** | (shardic-envelope only) The *derived, post-match* value — mask or `(x, y)` point — a trustee sends back to the combiner. What's in motion during recovery. Never a codeword. |
| **Mask** | The prime trustee's special shard value in shardic-prime (one-time-pad-style, not a Shamir point). |
| **Envelope** | A pubkey-wrapped payload (`wrap()`/`unwrap()`). Always qualify direction: *codeword envelope* (combiner→trustee) vs. *unsealed shard envelope* (trustee→combiner). |
| **Fingerprint** | A short hash of a public key, for human verification — never used for cryptographic matching. |
| **Trustee** | A party holding one codeword. In shardic-prime: **prime trustee** (1, mandatory) or **pool trustee** (the rest). |
| **Threshold (D)** / **Trustees (T)** | Standard SSS parameters — D required to recover, T issued total. |
| **Pool threshold** | `D − 1`, shardic-prime only: required count among pool trustees, since the prime is separately mandatory. |
| **Combiner** | The service holding ciphertext + wrapped envelopes; orchestrates registration/recovery; never sees a codeword. |
| **Recovery session** | One combiner-tracked recovery attempt, identified by `session_id`. Ephemeral — doesn't survive a combiner restart. |
| **`VaultStore`** | Pluggable backing store for the combiner's `.krypt` bytes, keyed by `vault_id`. `FilesystemVaultStore` (`demo/combiner/vault_store.py`) is the only backend shipped. |
| **`shardic-operator`** | Keycloak realm role required for every `/admin/*` combiner route. Replaces the old shared `COMBINER_ADMIN_TOKEN`. Separation-of-duties enforcement is implemented too. |
| **Ceremony** | Settled term (see below) for the whole registration→verified-recovery arc, now a real route prefix (`/admin/ceremony/initiate`). |
| **Candidate directory** | The org-wide set of registered trustees (`STATE["trustee_pubkeys"]`), before any ceremony selects from them. Not "pool" — collides with shardic-prime's pool trustee. |
| **Ceremony formation** | Operator-initiated selection of T primaries + an ordered backup list, invitations, and automatic backfill on decline/timeout. Implemented, per `docs/ceremony-formation.md`. |
| **Invitation** / **Backfill** | A per-trustee ceremony-formation slot record, and the race-safe promotion of the next backup into a lapsed slot. Both implemented. |
| **`NotificationChannel`** | Pluggable, admin-configurable, fan-out delivery of a non-secret prompt. `demo/combiner/notifications.py`; wired into ceremony invitations only so far. |

**The one pair to never confuse:** *shard = at rest, in the vault,
pre-match. Unsealed shard = in motion, post-match, en route to the
combiner.* Same underlying value, two different lifecycle stages — not
a reason to merge the two names. Keeping them distinct is what lets a
sentence like "the combiner never sees a shard, only unsealed shards"
mean something precise.

## Full definitions

**Vault** — the protected file or folder plus its custody scheme, as a
concept. Never appears as a literal dict key or field name anywhere in
`vault_core.py`/`vault_core_prime.py` — it's prose-level, referring to
the `.krypt` container plus the trustees who can jointly open it.

**`.krypt` container** — the single-file format: magic header,
length-prefixed JSON metadata, raw (uncompressed) ciphertext. This is
what `vault_create.py` produces and `vault_recover.py` consumes. Legacy
split-file vaults (separate `.crypt` + `metadata.json`) are the same
concept in an older on-disk shape — still "a vault," still not "a
`.krypt` container" in the strict sense.

**DEK (Data Encryption Key)** — the random 256-bit key AES-256-GCM
actually encrypts the archive under. This is the value Shamir's Secret
Sharing splits — never the plaintext itself, never a codeword directly.

**Codeword** — the human-facing secret (memorable, dictionary, or
synthetic mode) a trustee holds and, in the base/prime schemes, types
in by hand at recovery. Referred to as `word` in some function names
(`try_match_word`) — same thing, shorter.

**Shard** / **shard record** — a sealed entry in `.krypt` metadata
(`metadata["shards"]`; older vaults on disk use the legacy key
`metadata["shares"]`, still read via a compatibility fallback), protected
by a KDF derived from its matching codeword. *Pre-match*: nothing in the
file records which trustee (or even which codeword) unlocks a given
shard record — that's the project's deliberate zero-leakage indexing
property. Recovery finds the match by trial, using AES-GCM's auth tag
as the correctness check.

**Unsealed shard** — shardic-envelope-specific. The value a trustee
*derives locally* after unwrapping its own codeword envelope and
running the unmodified `try_match_word[_prime]` against it: the
prime's mask, or a pool trustee's `(x, y)` point. The unsealed shard,
not the codeword, is what gets wrapped and sent to the combiner
(`UNSEALED_SHARD_KIND_PRIME` / `UNSEALED_SHARD_KIND_POOL` in
`shardic_envelope_crypto.py`). An unsealed shard only exists after a
codeword has already been matched — it's a *result*, not a delivery
mechanism.

**Mask** — the prime trustee's shard value in shardic-prime
(`SHARD_TYPE_PRIME`). Structurally different from a pool shard: a
one-time-pad-style mask layered over the ordinary Shamir split, not a
point on the polynomial. "Prime unsealed shard" and "mask" refer to the
same value once it's in motion during recovery — "mask" describes what
it *is*, "unsealed shard" describes its *role* in that moment.

**Pool shard** / **`(x, y)` point** — an ordinary Shamir point held by
a non-prime trustee (`SHARD_TYPE_POOL`). Becomes a "pool unsealed
shard" once derived and sent during recovery — same value, same "at
rest vs. in motion" distinction as shard/unsealed shard generally.

**Envelope** — the dict `shardic_envelope_crypto.wrap()` produces /
`unwrap()` consumes: a pubkey-wrapped payload. The *same word* covers
two different payloads traveling in opposite directions, which is a
real ambiguity risk — always qualify:
- **codeword envelope** — combiner wraps a trustee's own codeword to
  that trustee's registered public key, delivered at vault creation.
- **unsealed shard envelope** — a trustee wraps its derived unsealed
  shard back to the combiner's public key during recovery, using the
  "self-addressed envelope" pattern (the combiner's own pubkey rides
  along bundled inside the codeword envelope it sent, so no separate
  lookup is needed for the reply). The wire field carrying this
  payload is still literally named `shard_envelope` in the demo's HTTP
  API (e.g. `POST /trustees/shard-reply`) — that field name wasn't
  part of this rename, so keep citing it verbatim when referring to
  the actual API.

**Fingerprint** — a short hash-based identifier of a public key
(trustee's or combiner's), meant for a human to eyeball and compare —
never used as part of the actual cryptographic matching or wrapping
logic.

**Trustee** — a party holding exactly one codeword (base/pool scheme)
or one keypair plus one wrapped codeword envelope (shardic-envelope).
- **Prime trustee** — shardic-prime only: the single mandatory
  trustee, required for every recovery regardless of threshold. The
  human case by default — see **`Fielded Prime Element`** below (in
  "Proposed-but-not-implemented vocabulary") for the hardware-embodied
  instance of this same role.
- **Pool trustee** — shardic-prime only: any non-prime trustee; `D − 1`
  of them (the pool threshold) are required alongside the prime.
- The base scheme has no prime/pool split — all T trustees are peers,
  any D of them suffice.

**Threshold (D)** — number of codewords/shards required to recover.
**Trustees (T)** — total number issued. **Pool threshold** — `D − 1`,
shardic-prime only.

**Combiner** — shardic-envelope/demo-specific: the service that holds
the `.krypt` ciphertext and every wrapped envelope, handles trustee
registration, opens and tracks recovery sessions, and combines
received unsealed shards into the DEK via the unmodified
`reconstruct_and_decrypt_prime`. By construction, a combiner never
receives a plaintext codeword — only unsealed shards.

**Recovery session** — one combiner-tracked attempt at recovery,
identified by a `session_id`, tracked in `STATE["recovery_session"]`.
Deliberately ephemeral — doesn't survive a combiner restart, since
re-arming a session (`/admin/recovery/start`) is cheap and
non-destructive, unlike vault creation.

**`VaultStore`** (`Protocol`, implemented in
`demo/combiner/vault_store.py`) — pluggable backing store for the
combiner's `.krypt` bytes, keyed by `vault_id`. `FilesystemVaultStore`
is the only backend shipped (v1.0, matches what the combiner already
did before this existed); SQL/NoSQL stay a future, config-selected
alternate implementation, per `docs/vault-storage-backend.md`.

**`shardic-operator`** (Keycloak realm role, implemented in
`demo/keycloak/realm-export.json` + `demo/combiner/app.py`'s
`_require_operator()`) — the authenticated role required for every
`/admin/*` combiner route, replacing the old shared
`COMBINER_ADMIN_TOKEN`. Separation-of-duties enforcement (an operator
can't self-select as a ceremony trustee) is also implemented —
`initiate_ceremony()` checks the operator's `sub` against every
primary and every name on the ordered backup list.

**Ceremony** — the umbrella term for the whole arc from trustee
registration through a verified recovery, including formation.
**Settled**, no longer a bare recommendation: it emerged organically in
the live-dashboard/static-explainer work before any code used the
word, then landed for real in `/admin/ceremony/initiate`,
`STATE["ceremony"]`, and several SSE event types
(`ceremony_initiated`/`ceremony_formed`/`ceremony_failed`) — shipping
in actual route paths is what settles a name.

**Candidate directory** (implemented: `STATE["trustee_pubkeys"]`) — the
org-wide set of registered trustees, before any specific ceremony
selects from them. Deliberately *not* called "pool" — that word is
already taken by the unrelated shardic-prime **pool trustee** concept
(a per-vault `D − 1` group); reusing it here would collide.

**Ceremony formation** (implemented in `demo/combiner/app.py`:
`initiate_ceremony()`, `get_pending_invitation()`,
`respond_to_invitation()`, `_ceremony_scan_loop()`) — the
operator-initiated process of selecting T primaries + an ordered
backup list, issuing invitations, and handling decline/timeout via
automatic backfill, per `docs/ceremony-formation.md`. A ceremony is
`formed` once every slot is `accepted`, or `failed` if the backup list
runs out before that happens.

**Invitation** (implemented) — a per-trustee ceremony-formation slot
record (`{role, sub, status, invited_at}`), discovered by polling
`GET /trustees/pending-invitation` and responded to via
`POST /trustees/invitation-response`. Never triggers a fresh keypair —
distinct from *registration* (directory-side, self-service, once).

**Backfill** (implemented) — automatic promotion of the next-ranked
candidate on a ceremony's ordered backup list into a lapsed slot,
inheriting that slot's role (prime or pool). Race-safe:
`respond_to_invitation()` only accepts a response from the slot's
*current* occupant, so a late accept from an already-backfilled
primary gets a 409, not a double-fill.

**`NotificationChannel`** (`Protocol`, implemented in
`demo/combiner/notifications.py`: `LogLineChannel`, `WebhookChannel`,
`EmailChannel`, `NotificationDispatcher`) — pluggable,
admin-configurable delivery of a non-secret prompt, fanned out to
every enabled channel for a given event type (not a fallback chain).
Wired into ceremony invitations (initial and backfilled) only —
`envelope_ready`/`drop_expired` await `envelope-delivery.md`'s
still-unbuilt `EnvelopeDropPoint`.

### Proposed-but-not-implemented vocabulary

These exist only in `docs/*.md` design proposals — no code implements
them yet. Keep referring to them as *proposed* so a future session
doesn't assume they're live:

- **`CredentialLookup`** (`Protocol`, `docs/pubkey-envelope-plugin.md`)
  — resolves a trustee's registered public key.
- **`PublicKeyRecord`** (`docs/pubkey-envelope-plugin.md`) — the data
  shape backing `CredentialLookup`.
- **`EnvelopeDropPoint`** (`Protocol`, `docs/envelope-delivery.md`) —
  pull-based, single-read delivery point for a wrapped envelope.
- **`Fielded Prime Element`** (`docs/spac-concept.md`) —
  hardware-embodied instance of the prime-trustee role: a fielded
  system's own PUF/secure-element-sealed `mask`, standing in for a
  human prime trustee in `reconstruct_secret_with_prime()`. Device/
  value split parallels `shardware-token`/`unsealed shard` — the
  Element is the device, `mask` is the value it holds. Write lowercase
  in prose (`fielded prime element`), matching `prime trustee`/`pool
  trustee`.

## Lifecycle-state adjectives

The project already encodes some of these as literal string values in
running code; others are gaps this glossary names for the first time.
Where a real code value exists, it's called out — use that exact
string, don't invent a synonym for it.

**Trustee**: `unregistered` → `registered` → **`live`** → **`paused`**
→ `replied`
- `live` / `paused` are real values (`STATE["trustee_status"]` in
  `demo/combiner/app.py`), driven by heartbeat timing against
  `/trustees/pending-envelope` polling.
- `registered` / `unregistered` and `replied` aren't currently named in
  code (registration is just presence/absence in `trustee_pubkeys`;
  "replied" is membership in `session["replied"]`) — proposed names for
  states that already functionally exist.

**Vault**: `unformed` → `sealed` (colloquially `dormant`) →
`recovering` → `recovered` → `verified`
- `sealed` describes *what happened* (codewords destroyed, envelopes
  wrapped); `dormant` describes *how long it's been that way* — both
  legitimate, not interchangeable. "The vault was sealed at creation;
  it sat dormant for six months before recovery" uses both correctly
  in one sentence.
- `recovered` and `verified` are deliberately two different states
  because they're two different combiner calls
  (`/admin/recovery/finalize` vs. `/admin/recovery/verify`) — a vault
  can be recovered without (yet) being verified.

**Shard**: `unmatched` → `matched`
- Tracked via `used_indices` in `try_match_word[_prime]`. A shard
  record starts unmatched; becomes matched the moment some codeword's
  trial succeeds against it.

**Unsealed shard** (shardic-envelope only): `derived` → `submitted` →
`received`
- `derived`: computed locally by the trustee, hasn't left the device.
- `submitted`: wrapped and sent to the combiner.
- `received`: combiner has unwrapped and accepted it (real state:
  membership in `session["replied"]`).

**Envelope**: `sealed` → `pending` → `opened`
- `pending` matches the real route name (`/trustees/pending-envelope`)
  for "wrapped and available for a trustee to fetch."
- `opened`: the receiving party has unwrapped it locally.

**Ceremony**: `forming` → `formed` | `failed`
- Real values in `STATE["ceremony"]["status"]`. `formed`: every slot
  `accepted`, vault creation unlocked. `failed`: backup list exhausted
  before every slot could be filled.

**Invitation slot**: `invited` → `accepted` | `open`
- Real values in each slot's `status`. `open` is the lapsed-with-
  no-backup-left terminal state (implies the ceremony is `failed`); a
  lapsed slot with a backup available goes straight back to `invited`
  (backfilled) rather than passing through `open`.

## Applying this

- Writing UI copy, log lines, or docs: prefer the exact terms above
  over paraphrases — "shard" and "unsealed shard" especially, since
  they're easy to use interchangeably by accident and mean genuinely
  different lifecycle stages here.
- Naming a new field, route, or concept: check whether it's actually a
  new *state* of an existing entity (extend the lifecycle-adjective
  list above) before reaching for a new noun.
- If a real need arises for a term not covered here, add it to this
  file in the same style (grounded in actual code, or explicitly
  flagged as a recommendation) rather than letting it drift in
  unrecorded like "ceremony" did.

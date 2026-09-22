# shardic-envelope Keycloak demo

A portable, containerized walkthrough of **shardic-prime** (the
mandatory-prime-trustee vault scheme, see the main
[README.md](../README.md#shardic-prime-a-mandatory-prime-trustee-variant))
combined with a first real implementation of **shardic-envelope** — until
now just two design docs
([`docs/pubkey-envelope-plugin.md`](../docs/pubkey-envelope-plugin.md),
[`docs/keycloak-credential-lookup.md`](../docs/keycloak-credential-lookup.md)).

Keycloak holds a directory of candidate trustees. An authenticated
**operator** initiates a **ceremony** — per
[`docs/ceremony-formation.md`](../docs/ceremony-formation.md) — naming a
prime trustee, a pool of trustees, a threshold, and an ordered backup list;
the combiner invites each primary, and automatically backfills from the
backup list if anyone doesn't accept in time (decline and silent timeout
are treated identically). Once every slot is accepted, the ceremony is
**formed** and the vault can be created. Each trustee runs as its own
container, generates its own keypair, and registers its public key with a
**combiner** service ahead of any ceremony. At vault creation, each
trustee's codeword is pubkey-wrapped to their registered key instead of
being printed to a file — the plaintext codeword is destroyed the moment
every envelope is written. At recovery, each trustee's container decrypts
its own envelope locally, derives its **unsealed shard** (the post-match
Shamir value — the prime's mask, or a pool `(x, y)` point) using the
project's existing, completely unmodified
`vault_core_prime.try_match_word_prime`, and sends back only that
unsealed shard, wrapped to the combiner's key. **The combiner never sees
a codeword from any trustee, only unsealed shards** — and
pausing enough running trustee containers before recovery still succeeds,
proving the threshold property live.

No changes were made to `vault_core_prime.py`, `gf256_sss_prime.py`, or any
other core crypto module — shardic-envelope is a pure bolt-on
(`shardic_envelope_crypto.py`, `demo/combiner/`, `demo/trustee/`).

## Deliberate demo-only simplifications

These are conscious shortcuts for a local walkthrough, not patterns to
reuse in a real deployment:

- **Keycloak runs in `start-dev` mode** (embedded database, no Postgres
  container) — not how you'd run Keycloak for real.
- **Trustee containers authenticate via Direct Access Grant** (Resource
  Owner Password Credentials) with plaintext demo passwords baked into
  `keycloak/realm-export.json` and `.env`. A headless container can't do
  an interactive browser OIDC flow; a real deployment would use the
  interactive/device-code flow `docs/keycloak-credential-lookup.md`
  already designs.
- **The combiner's `/admin/*` routes require a real Keycloak-authenticated
  `shardic-operator` role**, per
  [`docs/keycloak-credential-lookup.md`](../docs/keycloak-credential-lookup.md#the-operator-role)
  — the operator authenticates the same way trustees do (Direct Access
  Grant, plaintext demo password), which is the shortcut here, not the
  identity model itself. Separation-of-duties *is* enforced: an operator
  cannot name themselves as a primary or backup trustee for a ceremony
  they initiate (checked against the full backup list, not just
  primaries).
- **Trustees accept ceremony invitations automatically, with no
  interactive human decision.** This demo trustee is a headless
  container, the same as it already is for registration and unsealed
  shard replies — there's no one to ask "accept this invitation?" A trustee
  that shouldn't participate in a given ceremony is simulated by pausing
  its container (`docker-compose pause`) *before* the ceremony is
  initiated, so it never polls to see the invitation — the same
  mechanism the walkthrough already uses to prove the threshold
  property during recovery, now also demonstrating decline/backfill
  during formation.
- **`/trustees/register` accepts any authenticated realm user, not just
  `shardic-trustees` group members.** Found live while verifying
  separation-of-duties (below): the `operator` account can authenticate
  against `shardic-trustee-client` and self-register as a candidate
  trustee, the same as any of the 7 named candidates. Group membership
  gates who `/admin/keycloak/group-members` *lists* as a candidate, not
  who *can register* — a real deployment would need registration itself
  scoped to the directory group.
- **The combiner's Keycloak service account has the realm-wide
  `view-users` role**, not fine-grained group-scoped admin permissions
  (which are correct but fiddly to hand-author in a realm export). Its
  *queries* still only ever target the `shardic-trustees` group, but the
  underlying grant is broader than
  [`docs/keycloak-credential-lookup.md`](../docs/keycloak-credential-lookup.md)'s
  least-privilege ideal.
- **Flask's built-in dev server**, not a production WSGI server — fine
  for a single-operator local demo.
- **No fingerprint cross-check** of the combiner's public key (bundled
  inside each envelope, the "self-addressed envelope" pattern) against
  Keycloak. Would close the last gap in that pattern's trust story for a
  real deployment; not built here.
- **The optional email notification channel routes every recipient
  through one real mailbox** using Gmail's `+suffix` addressing
  (`mailbox+alice@gmail.com`, `mailbox+bob@gmail.com`, ...) to simulate
  distinct recipients without provisioning separate mailboxes. A real
  deployment would resolve an actual per-trustee contact address from
  wherever its identity model tracks one — which this project's
  identity model deliberately doesn't (`docs/notification-channel-concept.md`).

## Notification channels

Ceremony invitations (initial and backfilled) fire through the
pluggable `NotificationChannel` interface from
[`docs/notification-channels.md`](../docs/notification-channels.md) —
`demo/combiner/notifications.py`. Three channels ship:

| Channel | Enables when | Notes |
|---|---|---|
| `log_line` | Always | Zero-config default; prints `[notify:ceremony_invite] ...` to the combiner's log. |
| `webhook` | `NOTIFY_WEBHOOK_URL` is set | POSTs the event as JSON to your own URL — the generic operator-supplied escape hatch. |
| `email` | All five `NOTIFY_EMAIL_*` vars are set | See the simplification above; needs a real Gmail app password in your local `.env`, never committed. |

Which *registered* channels actually fire for ceremony invitations is
controlled by `NOTIFY_CEREMONY_INVITE_CHANNELS` (comma-separated,
default `log_line`) — e.g. `log_line,email` once email is configured.
Multiple enabled channels all fire (fan-out), not a fallback chain.

To try the email channel: fill in `NOTIFY_EMAIL_USERNAME`,
`NOTIFY_EMAIL_APP_PASSWORD` (a Gmail app password, not your account
password), and `NOTIFY_EMAIL_BASE_ADDRESS` in your local `.env`, set
`NOTIFY_CEREMONY_INVITE_CHANNELS=log_line,email`, then re-run step 4
below — each invited trustee's notification lands at
`your-mailbox+<username>@gmail.com`.

## Live dashboard

Once `keycloak`, `combiner`, and the selected trustees are up, open
`http://localhost:5000/dashboard` in a browser for a presenter-facing view
of the ceremony instead of reading curl output: trustee registration and
live/paused status arrive over Server-Sent Events as they happen, and the
same `/admin/*` actions from the walkthrough below are available as buttons
(paste an operator Bearer token — see step 4 below for how to fetch one —
into the token field first). The dashboard is a pure bolt-on — a dashboard
tab open or closed has no effect on the curl-driven walkthrough, and vice
versa; both drive the same combiner state.

**If you're watching the dashboard, it won't show the final "verified"
banner after step 11 below** — step 11 checks recovery with a raw `docker
exec ... diff -r`, which never touches the combiner API, so the dashboard
never gets the SSE event that flips its verify banner from "pending" to
"match". Click the dashboard's **Verify** button (or call
`POST /admin/recovery/verify` yourself) to see that banner complete; the
diagram's "done" state from step 10's finalize still updates normally
either way.

## Prerequisites

- Docker or Podman with a `docker-compose`-compatible CLI.
- Internet access on first run (pulls `quay.io/keycloak/keycloak:26.7` and
  installs Python packages while building the combiner/trustee images).

## Walkthrough

```sh
cd demo
cp .env.example .env   # demo credentials, already fixed to match realm-export.json
```

**1. Bring up Keycloak, wait for it to be healthy:**

```sh
docker-compose --env-file .env up -d keycloak
docker-compose ps   # wait for keycloak to show "healthy"
```

**2. Bring up 5 primary candidates plus 1 backup.** `trustee-frank` is
tagged with the `candidates` profile (like `trustee-grace`, who stays
undefined-started this run — swap her in instead of frank for a different
demo shape):

```sh
docker-compose --profile candidates --env-file .env up -d combiner trustee-alice trustee-bob trustee-carol trustee-dave trustee-erin trustee-frank
```

**3. Registration is automatic.** Each trustee authenticates to Keycloak,
generates a local keypair, and registers its public key with the combiner
within a few seconds of starting. `/admin/*` routes need an authenticated
**operator** — someone holding the `shardic-operator` Keycloak role, not a
shared secret — so define a helper that fetches a fresh Bearer token
(Direct Access Grant, the same demo-only shortcut the trustees use):

```sh
docker-compose logs trustee-alice   # look for "registered with combiner"

operator_token() {
  curl -s -X POST http://localhost:8080/realms/shardic-demo/protocol/openid-connect/token \
    -d grant_type=password -d client_id=shardic-operator-client \
    -d username=operator -d "password=$(grep OPERATOR_PASSWORD .env | cut -d= -f2)" \
    -d scope=openid | python3 -c "import sys, json; print(json.load(sys.stdin)['access_token'])"
}

curl -s -H "Authorization: Bearer $(operator_token)" \
  http://localhost:5000/admin/keycloak/group-members
# shows all 7 candidates in the directory, for narrative context
```

`operator_token` fetches a fresh token on every call (Keycloak's default
access-token lifespan is short), so it's safe to keep calling it across a
slow, narrated walkthrough rather than reusing one variable that might
expire mid-demo.

**4. Pause `erin` to simulate a non-response, then initiate the
ceremony.** Pausing *before* initiation means erin never polls to see her
invitation — the combiner treats this identically to an explicit decline,
governed by the invitation's TTL (`CEREMONY_INVITE_TTL_S`, 20s by
default):

```sh
docker-compose pause trustee-erin

curl -s -X POST -H "Authorization: Bearer $(operator_token)" -H "Content-Type: application/json" \
  -d '{"threshold_d": 3, "prime": "alice", "pool": ["bob", "carol", "dave", "erin"], "backups": ["frank"]}' \
  http://localhost:5000/admin/ceremony/initiate
```

Expect 200 with `erin` listed among `invited` (role `pool`) and `frank`
listed in `backup_queue`. Each invited slot also fires a notification —
by default just the zero-config `log_line` channel
(`docs/notification-channels.md`), so expect a `[notify:ceremony_invite]`
line per primary in the combiner's log right after this call. See
["Notification channels"](#notification-channels) below to enable
webhook/email too.

**5. Watch erin's invitation lapse and frank get backfilled in her
place.** Wait past the TTL, then check the combiner's log:

```sh
sleep 22
docker-compose logs combiner | grep -i "ceremony\|backfill\|notify"
```

Expect, in order: `... pool invitation to erin expired`, `... backfilled
pool slot with frank`, a fresh `[notify:ceremony_invite]` line for frank's
backfilled invitation, then — once frank's (unpaused) container polls and
auto-accepts — `... ceremony ... formed -- ready for vault creation`.
Unpause erin now; she's not part of this ceremony, but there's no reason
to leave her paused. Use `docker unpause` with the container name here,
not `docker-compose unpause <service>` — under Podman, docker-compose's
service-name lookup lists only `all=false` (running) containers to
resolve against, and Podman's Docker-API compatibility layer excludes
paused containers from that listing, so it reports `No containers to
unpause` even though the container is right there:

```sh
docker unpause demo_trustee-erin_1
```

**6. Create the vault**, now that the ceremony is formed:

```sh
curl -s -X POST -H "Authorization: Bearer $(operator_token)" http://localhost:5000/admin/vault/create
```

Expect 200 with `prime_trustee: "alice"` and `pool_trustees: ["bob",
"carol", "dave", "frank"]` — frank occupies the slot erin was originally
invited to, in the same position.

**7. Verify the codewords were wrapped, then destroyed** (never left as
plaintext):

```sh
docker exec $(docker-compose ps -q combiner) sh -c 'ls /data/vault/*_trustee_words 2>&1 || echo "gone, as expected"'
```

**8. Prove the threshold-3 property live.** The vault's actual pool is
`bob`, `carol`, `dave`, `frank` (erin was backfilled out during formation)
— pausing `dave` and `frank` leaves `alice` (prime) + `bob` + `carol`
running, exactly enough:

```sh
docker-compose pause trustee-dave trustee-frank
```

**9. Trigger recovery:**

```sh
curl -s -X POST -H "Authorization: Bearer $(operator_token)" http://localhost:5000/admin/recovery/start
```

Wait a few seconds (poll interval) for the 3 live trustees to notice, decrypt
locally, and reply:

```sh
docker-compose logs -f trustee-alice trustee-bob trustee-carol
# look for "unsealed shard submitted for session ..." from each
```

**10. Finalize:**

```sh
curl -s -X POST -H "Authorization: Bearer $(operator_token)" http://localhost:5000/admin/recovery/finalize
```

Expect 200 with `"trustees_used": ["alice", "bob", "carol"]` — proving
`dave`/`frank` weren't needed.

**11. Verify byte-for-byte recovery:**

```sh
docker exec $(docker-compose ps -q combiner) sh -c \
  'diff -r /data/sample-secret /data/recovered/sample-secret && echo "MATCH"'
```

**12. Tear down** (removes volumes too — a fresh `.env`/re-run starts
clean). Unpause `dave`/`frank` first if you paused them in step 8 — `down`
can't stop a paused container cleanly. As in step 5, use `docker unpause`
with container names, not `docker-compose unpause`:

```sh
docker unpause demo_trustee-dave_1 demo_trustee-frank_1
docker-compose --profile candidates down -v
```

## Combiner API reference

| Method | Path | Auth | Purpose |
|---|---|---|---|
| POST | `/trustees/register` | Bearer (Keycloak) | Register a trustee's public key. |
| GET | `/vault/metadata` | none | Current `.krypt` metadata (not secret). |
| GET | `/trustees/pending-envelope` | Bearer | Poll for a pending recovery envelope. |
| POST | `/trustees/shard-reply` | Bearer | Submit a wrapped unsealed shard. |
| GET | `/trustees/pending-invitation` | Bearer | Poll for a pending ceremony invitation. |
| POST | `/trustees/invitation-response` | Bearer | Accept or decline a ceremony invitation. |
| POST | `/admin/ceremony/initiate` | Bearer (Keycloak, `shardic-operator` role) | Initiate a ceremony: threshold, prime, pool, ordered backup list. |
| POST | `/admin/vault/create` | Bearer (Keycloak, `shardic-operator` role) | Create the demo vault from a formed ceremony. |
| GET | `/admin/vault/download` | Bearer (Keycloak, `shardic-operator` role) | Download the created `.krypt` container's raw bytes. |
| GET | `/admin/keycloak/group-members` | Bearer (Keycloak, `shardic-operator` role) | List the 7 candidates. |
| POST | `/admin/recovery/start` | Bearer (Keycloak, `shardic-operator` role) | Arm a recovery session. |
| POST | `/admin/recovery/finalize` | Bearer (Keycloak, `shardic-operator` role) | Combine collected unsealed shards, decrypt. |
| POST | `/admin/recovery/verify` | Bearer (Keycloak, `shardic-operator` role) | Byte-for-byte compare recovered output against the original. |
| GET | `/events` | none | Server-Sent Events stream backing the live dashboard. |
| GET | `/dashboard` | none | The live dashboard itself. |
| GET | `/healthz` | none | Compose healthcheck target. |

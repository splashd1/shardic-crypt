"""
app.py -- shardic-envelope demo combiner.

Flask service that: registers trustee public keys (Keycloak-authenticated),
creates a shardic-prime demo vault and wraps each trustee's codeword to
their registered key (destroying the plaintext once every envelope is
written), serves each trustee's wrapped envelope during a recovery
session, and combines the unsealed shards trustees send back into the
reconstructed DEK via vault_core_prime.reconstruct_and_decrypt_prime --
completely unmodified from the rest of the project. The combiner never
sees a plaintext codeword or a raw trustee_N.txt file survive past
vault creation, and never needs one at recovery time either.

See demo/README.md for the full walkthrough and the list of deliberate
demo-only simplifications (Direct Access Grant auth, realm-wide Admin
API scope, etc.).
"""

import base64
import filecmp
import json
import os
import queue
import threading
import time
import uuid

from flask import Flask, Response, jsonify, request, send_from_directory

import keycloak_client
import krypt_container
import notifications
import shardic_envelope_crypto
import vault_core_prime
import vault_store

DATA_DIR = os.environ.get("COMBINER_DATA_DIR", "/data")
KEY_DIR = os.path.join(DATA_DIR, "keys")
STATE_PATH = os.path.join(DATA_DIR, "state.json")
DASHBOARD_DIR = os.path.join(os.path.dirname(os.path.abspath(__file__)), "dashboard")

KEYCLOAK_URL = os.environ["KEYCLOAK_URL"]
KEYCLOAK_REALM = os.environ["KEYCLOAK_REALM"]
ADMIN_CLIENT_ID = os.environ["ADMIN_CLIENT_ID"]
ADMIN_CLIENT_SECRET = os.environ["ADMIN_CLIENT_SECRET"]
# Separately-named from KEYCLOAK_URL/KEYCLOAK_REALM on purpose, even
# though the demo points both at the same Keycloak instance -- see
# docs/keycloak-credential-lookup.md#the-operator-role. A future split
# to a dedicated operator realm/IdP is then a config change here, not
# a rewrite of _require_operator() below.
OPERATOR_OIDC_ISSUER = os.environ["OPERATOR_OIDC_ISSUER"]
OPERATOR_REALM = os.environ["OPERATOR_REALM"]
OPERATOR_ROLE = "shardic-operator"
SAMPLE_SECRET_PATH = os.environ.get("SAMPLE_SECRET_PATH", "/data/sample-secret")
VAULT_OUTDIR = os.environ.get("VAULT_OUTDIR", "/data/vault")
RECOVERED_OUTDIR = os.environ.get("RECOVERED_OUTDIR", "/data/recovered")
HEARTBEAT_TIMEOUT_S = float(os.environ.get("HEARTBEAT_TIMEOUT_S", "10"))
HEARTBEAT_SCAN_INTERVAL_S = 2
# T/D are no longer fixed demo constants -- docs/ceremony-formation.md's
# whole point is that an operator specifies them per ceremony. See
# CEREMONY_INVITE_TTL_S: an invitation lapses (decline and timeout are
# treated identically) after this many seconds, at which point the
# ceremony scan loop backfills it from the ordered backup list.
CEREMONY_INVITE_TTL_S = float(os.environ.get("CEREMONY_INVITE_TTL_S", "20"))
CEREMONY_SCAN_INTERVAL_S = 2


def _build_notification_dispatcher() -> notifications.NotificationDispatcher:
    """Registers whichever NotificationChannel implementations have
    the env vars to construct them, then wires event types to the
    admin-configured subset of channel names -- see
    docs/notification-channels.md. LogLineChannel needs no
    configuration and is always registered; webhook/email only
    register if their env vars are actually set, so an unconfigured
    demo still starts with zero notification setup required."""
    channels: dict[str, notifications.NotificationChannel] = {"log_line": notifications.LogLineChannel()}

    webhook_url = os.environ.get("NOTIFY_WEBHOOK_URL")
    if webhook_url:
        channels["webhook"] = notifications.WebhookChannel(webhook_url)

    smtp_host = os.environ.get("NOTIFY_EMAIL_SMTP_HOST")
    smtp_port = os.environ.get("NOTIFY_EMAIL_SMTP_PORT")
    email_username = os.environ.get("NOTIFY_EMAIL_USERNAME")
    email_app_password = os.environ.get("NOTIFY_EMAIL_APP_PASSWORD")
    email_base_address = os.environ.get("NOTIFY_EMAIL_BASE_ADDRESS")
    if smtp_host and smtp_port and email_username and email_app_password and email_base_address:
        channels["email"] = notifications.EmailChannel(
            smtp_host, int(smtp_port), email_username, email_app_password, email_base_address
        )

    event_channels = {
        "ceremony_invite": [
            name.strip()
            for name in os.environ.get("NOTIFY_CEREMONY_INVITE_CHANNELS", "log_line").split(",")
            if name.strip()
        ],
    }
    return notifications.NotificationDispatcher(channels, event_channels)


NOTIFIER = _build_notification_dispatcher()

app = Flask(__name__)
_lock = threading.Lock()

# The v1.0 reference VaultStore implementation -- see
# docs/vault-storage-backend.md. Swapping this for a SQL/NoSQL-backed
# implementation later is a config change here, not a rewrite of
# do_create_vault or the admin/download route below.
VAULT_STORE: vault_store.VaultStore = vault_store.FilesystemVaultStore(VAULT_OUTDIR)

# SSE fan-out. Deliberately a separate lock from `_lock`: broadcasting to
# (potentially stalled) dashboard listeners must never be able to block a
# real ceremony operation.
_sse_listeners: list[queue.Queue] = []
_sse_lock = threading.Lock()


def _broadcast(event_type: str, data: dict) -> None:
    message = json.dumps({"type": event_type, "data": data})
    with _sse_lock:
        listeners = list(_sse_listeners)
    for q in listeners:
        q.put(message)


class CombinerError(Exception):
    def __init__(self, message, status_code=400):
        super().__init__(message)
        self.message = message
        self.status_code = status_code


def _new_state():
    private_key, public_key = shardic_envelope_crypto.load_or_create_keypair(KEY_DIR)
    return {
        "combiner_private_key": private_key,
        "combiner_public_key": public_key,
        "trustee_pubkeys": {},     # sub -> {"username", "public_key" (bytes), "fingerprint"}
        "vault": None,             # {"vault_id", "metadata", "ciphertext" (bytes)}
        "vault_assignment": None,  # {"prime_sub", "pool_subs": [sub, ...]} -- fixed at creation time
        "codeword_envelopes": {},  # sub -> {"envelope": wrapped-dict, "mode": "kdf"|"drbg"}
        "recovery_session": None,  # {"session_id", "replied": set, "mask", "pool_shards"} -- in-memory only
        "trustee_last_seen": {},   # sub -> time.time() of last authenticated request -- in-memory only
        "trustee_status": {},      # sub -> "live" | "paused" -- in-memory only, derived by _heartbeat_loop
        "last_verify": None,       # {"match": bool} -- in-memory only, set by /admin/recovery/verify
        "ceremony": None,          # in-memory only, same "cheap to re-arm" reasoning as
                                    # recovery_session -- see initiate_ceremony() for the shape
    }


def _load_state():
    state = _new_state()
    if os.path.exists(STATE_PATH):
        with open(STATE_PATH) as f:
            saved = json.load(f)
        for sub, rec in saved.get("trustee_pubkeys", {}).items():
            state["trustee_pubkeys"][sub] = {
                "username": rec["username"],
                "public_key": base64.b64decode(rec["public_key"]),
                "fingerprint": rec["fingerprint"],
            }
        if saved.get("vault"):
            state["vault"] = {
                "vault_id": saved["vault"]["vault_id"],
                "metadata": saved["vault"]["metadata"],
                "ciphertext": base64.b64decode(saved["vault"]["ciphertext"]),
            }
            state["vault_assignment"] = saved.get("vault_assignment")
        state["codeword_envelopes"] = dict(saved.get("codeword_envelopes", {}))
    return state


def _save_state_locked():
    """Caller must hold _lock. Persists everything except the ephemeral
    recovery_session -- a mid-recovery combiner restart just means
    re-running /admin/recovery/start, which is cheap and non-destructive.
    Vault creation, by contrast, destroys the plaintext trustee_N.txt
    files, so that state must survive a restart."""
    payload = {
        "trustee_pubkeys": {
            sub: {
                "username": rec["username"],
                "public_key": base64.b64encode(rec["public_key"]).decode("ascii"),
                "fingerprint": rec["fingerprint"],
            }
            for sub, rec in STATE["trustee_pubkeys"].items()
        },
        "vault": None,
        "vault_assignment": None,
        "codeword_envelopes": STATE["codeword_envelopes"],
    }
    if STATE["vault"] is not None:
        payload["vault"] = {
            "vault_id": STATE["vault"]["vault_id"],
            "metadata": STATE["vault"]["metadata"],
            "ciphertext": base64.b64encode(STATE["vault"]["ciphertext"]).decode("ascii"),
        }
        payload["vault_assignment"] = STATE["vault_assignment"]
    tmp_path = STATE_PATH + ".tmp"
    with open(tmp_path, "w") as f:
        json.dump(payload, f)
    os.replace(tmp_path, STATE_PATH)


STATE = _load_state()


# ---------------------------------------------------------------------------
# Business logic (kept separate from route bodies for testability)
# ---------------------------------------------------------------------------

def do_register_trustee(bearer_token: str, public_key_b64: str, algorithm: str) -> dict:
    if algorithm != shardic_envelope_crypto.ALGORITHM_TAG:
        raise CombinerError(f"unsupported algorithm: {algorithm!r}")
    sub, username = keycloak_client.get_verified_identity(KEYCLOAK_URL, KEYCLOAK_REALM, bearer_token)
    public_key = base64.b64decode(public_key_b64)
    fp = shardic_envelope_crypto.fingerprint(public_key)
    with _lock:
        STATE["trustee_pubkeys"][sub] = {"username": username, "public_key": public_key, "fingerprint": fp}
        STATE["trustee_last_seen"][sub] = time.time()
        STATE["trustee_status"][sub] = "live"
        _save_state_locked()
    _broadcast("trustee_registered", {"username": username, "fingerprint": fp})
    return {"trustee_id": sub, "username": username, "fingerprint": fp}


def _slot_role(index: int) -> str:
    """Slot 0 is always the mandatory prime; every other slot is pool.
    Role is a property of the *slot*, not the person occupying it --
    whoever backfills a lapsed slot inherits that slot's role."""
    return "prime" if index == 0 else "pool"


def initiate_ceremony(
    operator_sub: str,
    threshold_d: int,
    prime_username: str,
    pool_usernames: list[str],
    backup_usernames: list[str],
) -> dict:
    with _lock:
        if STATE["vault"] is not None:
            raise CombinerError("a vault already exists for this demo run", status_code=409)
        if STATE["ceremony"] is not None and STATE["ceremony"]["status"] == "forming":
            raise CombinerError("a ceremony is already forming", status_code=409)

        trustees_t = 1 + len(pool_usernames)
        if threshold_d < 2:
            raise CombinerError("threshold_d must be >= 2: 1 mandatory prime + >= 1 pool", status_code=400)
        if trustees_t < 2:
            raise CombinerError("need at least 1 pool trustee alongside the prime", status_code=400)
        if threshold_d > trustees_t:
            raise CombinerError("threshold_d cannot exceed trustees_t", status_code=400)

        primary_usernames = [prime_username] + list(pool_usernames)
        all_named = primary_usernames + list(backup_usernames)
        if len(set(all_named)) != len(all_named):
            raise CombinerError("primaries and backups must all be distinct", status_code=400)

        username_to_sub = {rec["username"]: sub for sub, rec in STATE["trustee_pubkeys"].items()}
        missing = [u for u in all_named if u not in username_to_sub]
        if missing:
            raise CombinerError(f"not registered candidates: {missing}", status_code=400)

        # Separation of duties: checked against the *entire* backup
        # list, not just the primaries -- an operator excluding
        # themselves from the visible primary list while remaining
        # reachable via backfill would defeat this. See
        # docs/ceremony-formation.md#implementation-requirements-this-creates.
        if operator_sub in (username_to_sub[u] for u in all_named):
            raise CombinerError(
                "operator cannot appear as a primary or backup trustee for a ceremony they initiate",
                status_code=403,
            )

        now = time.time()
        slots = [
            {"role": _slot_role(i), "sub": username_to_sub[u], "status": "invited", "invited_at": now}
            for i, u in enumerate(primary_usernames)
        ]
        backup_queue = [username_to_sub[u] for u in backup_usernames]

        ceremony_id = str(uuid.uuid4())
        STATE["ceremony"] = {
            "ceremony_id": ceremony_id,
            "operator_sub": operator_sub,
            "threshold_d": threshold_d,
            "trustees_t": trustees_t,
            "slots": slots,
            "backup_queue": backup_queue,
            "status": "forming",
        }
        invited = [{"role": s["role"], "username": STATE["trustee_pubkeys"][s["sub"]]["username"]} for s in slots]
        response = {
            "ceremony_id": ceremony_id,
            "invited": invited,
            "backup_queue": [STATE["trustee_pubkeys"][sub]["username"] for sub in backup_queue],
        }
        notify_events = [
            notifications.NotificationEvent(
                "ceremony_invite", s["sub"], STATE["trustee_pubkeys"][s["sub"]]["username"],
                {"ceremony_id": ceremony_id, "role": s["role"], "ttl_expires_at": s["invited_at"] + CEREMONY_INVITE_TTL_S},
            )
            for s in slots
        ]
    _broadcast("ceremony_initiated", response)
    # Outside the lock, same discipline as _broadcast -- a slow or
    # unreachable channel (webhook/email) must never block ceremony
    # operations. This is a proactive nudge, not the delivery
    # mechanism itself; the trustee still discovers and accepts the
    # invitation by polling regardless of whether any of this reaches them.
    for event in notify_events:
        NOTIFIER.notify(event)
    return response


def get_pending_invitation(sub: str) -> dict | None:
    with _lock:
        STATE["trustee_last_seen"][sub] = time.time()
        ceremony = STATE["ceremony"]
        if ceremony is None or ceremony["status"] != "forming":
            return None
        for slot in ceremony["slots"]:
            if slot["sub"] == sub and slot["status"] == "invited":
                return {
                    "ceremony_id": ceremony["ceremony_id"],
                    "role": slot["role"],
                    "ttl_expires_at": slot["invited_at"] + CEREMONY_INVITE_TTL_S,
                }
        return None


def _lapse_slot_locked(slot: dict) -> tuple[tuple[str, dict], notifications.NotificationEvent | None]:
    """Caller must hold _lock. Marks slot open and immediately tries to
    backfill it from the shared, ordered backup queue -- decline
    short-circuits the wait; the ceremony scan loop reaches the same
    call once the TTL elapses. Both funnel through here, matching
    "decline and timeout are just non-acceptance" from
    docs/ceremony-formation.md#decline--no-response-handling. Returns
    the (event_type, event_data) to broadcast, plus a NotificationEvent
    for the newly-invited backfill (or None on failure) -- both to be
    fired once _lock is released."""
    ceremony = STATE["ceremony"]
    if not ceremony["backup_queue"]:
        slot["status"] = "open"
        ceremony["status"] = "failed"
        print(f"ceremony {ceremony['ceremony_id']} failed: backup list exhausted, "
              f"no candidate left to fill the {slot['role']} slot")
        return ("ceremony_failed", {"ceremony_id": ceremony["ceremony_id"]}), None
    next_sub = ceremony["backup_queue"].pop(0)
    slot["sub"] = next_sub
    slot["status"] = "invited"
    slot["invited_at"] = time.time()
    username = STATE["trustee_pubkeys"][next_sub]["username"]
    print(f"ceremony {ceremony['ceremony_id']}: backfilled {slot['role']} slot with {username}")
    notify_event = notifications.NotificationEvent(
        "ceremony_invite", next_sub, username,
        {"ceremony_id": ceremony["ceremony_id"], "role": slot["role"], "ttl_expires_at": slot["invited_at"] + CEREMONY_INVITE_TTL_S},
    )
    return ("backfill_invited", {"ceremony_id": ceremony["ceremony_id"], "role": slot["role"], "username": username}), notify_event


def _maybe_finalize_formation_locked() -> tuple[str, dict] | None:
    """Caller must hold _lock."""
    ceremony = STATE["ceremony"]
    if all(s["status"] == "accepted" for s in ceremony["slots"]):
        ceremony["status"] = "formed"
        print(f"ceremony {ceremony['ceremony_id']} formed -- ready for vault creation")
        return ("ceremony_formed", {"ceremony_id": ceremony["ceremony_id"]})
    return None


def respond_to_invitation(sub: str, ceremony_id: str, accept: bool) -> dict:
    events = []
    notify_events = []
    with _lock:
        STATE["trustee_last_seen"][sub] = time.time()
        ceremony = STATE["ceremony"]
        if ceremony is None or ceremony["ceremony_id"] != ceremony_id or ceremony["status"] != "forming":
            raise CombinerError("no forming ceremony with that ceremony_id", status_code=409)
        slot = next((s for s in ceremony["slots"] if s["sub"] == sub and s["status"] == "invited"), None)
        if slot is None:
            # Race-safety: first valid acceptance wins. A late accept
            # from a slot that's already lapsed (declined, expired, or
            # already backfilled to someone else) lands here -- a dead
            # link, not a silent no-op or a slot double-fill. See
            # docs/ceremony-formation.md#implementation-requirements-this-creates.
            raise CombinerError("no pending invitation for this trustee -- it may have already lapsed", status_code=409)

        username = STATE["trustee_pubkeys"][sub]["username"]
        if accept:
            slot["status"] = "accepted"
            print(f"{username} accepted their {slot['role']} invitation for ceremony {ceremony_id}")
            evt = _maybe_finalize_formation_locked()
            if evt is not None:
                events.append(evt)
        else:
            print(f"{username} declined their {slot['role']} invitation for ceremony {ceremony_id}")
            broadcast_evt, notify_evt = _lapse_slot_locked(slot)
            events.append(broadcast_evt)
            if notify_evt is not None:
                notify_events.append(notify_evt)
        events.append(("invitation_responded", {"ceremony_id": ceremony_id, "role": slot["role"], "accept": accept}))
        result = {"status": slot["status"]}

    for evt_type, evt_data in events:
        _broadcast(evt_type, evt_data)
    for notify_evt in notify_events:
        NOTIFIER.notify(notify_evt)
    return result


def _ceremony_scan_loop() -> None:
    """Background daemon thread, mirroring _heartbeat_loop's shape:
    periodically sweep for invitations past their TTL and lapse them.
    Decline reaches _lapse_slot_locked() immediately via
    respond_to_invitation(); this loop is what catches silent
    non-response."""
    while True:
        time.sleep(CEREMONY_SCAN_INTERVAL_S)
        events = []
        notify_events = []
        with _lock:
            ceremony = STATE["ceremony"]
            if ceremony is not None and ceremony["status"] == "forming":
                now = time.time()
                for slot in ceremony["slots"]:
                    if slot["status"] == "invited" and (now - slot["invited_at"]) > CEREMONY_INVITE_TTL_S:
                        username = STATE["trustee_pubkeys"][slot["sub"]]["username"]
                        role = slot["role"]
                        print(f"ceremony {ceremony['ceremony_id']}: {role} invitation to {username} expired")
                        events.append(("invitation_expired", {"ceremony_id": ceremony["ceremony_id"], "role": role, "username": username}))
                        broadcast_evt, notify_evt = _lapse_slot_locked(slot)
                        events.append(broadcast_evt)
                        if notify_evt is not None:
                            notify_events.append(notify_evt)
        for evt_type, evt_data in events:
            _broadcast(evt_type, evt_data)
        for notify_evt in notify_events:
            NOTIFIER.notify(notify_evt)


def do_create_vault(input_path: str, outdir: str, use_codewords: bool = False) -> dict:
    with _lock:
        if STATE["vault"] is not None:
            raise CombinerError("a vault already exists for this demo run", status_code=409)
        ceremony = STATE["ceremony"]
        if ceremony is None or ceremony["status"] != "formed":
            raise CombinerError(
                "no formed ceremony -- initiate one via /admin/ceremony/initiate "
                "and wait for every slot to be accepted",
                status_code=409,
            )

        prime_slot = next(s for s in ceremony["slots"] if s["role"] == "prime")
        pool_slots = [s for s in ceremony["slots"] if s["role"] == "pool"]
        prime_sub = prime_slot["sub"]
        pool_subs = [s["sub"] for s in pool_slots]
        trustees_t = ceremony["trustees_t"]
        threshold_d = ceremony["threshold_d"]

        # Per whitepaper §4.8, a SPAC ceremony's default shard-protection
        # source is a DRBG-sourced key -- no wordlist, no KDF stretching --
        # necessarily delivered via shardic-envelope since it can't be
        # memorized. Traditional codeword+KDF (identical to the base/prime
        # CLI's own default) remains available as a named opt-out for this
        # whole ceremony via use_codewords=True.
        protection_mode = vault_core_prime.PROTECTION_KDF if use_codewords else vault_core_prime.PROTECTION_DRBG
        protection_modes = [protection_mode] * trustees_t

        result = vault_core_prime.create_vault_prime(
            input_path=input_path,
            trustees=trustees_t,
            threshold=threshold_d,
            word_length=None,
            word_count=1,
            kdf_method="pbkdf2",
            outdir=outdir,
            protection_modes=protection_modes,
            log=print,
        )

        credentials = result["credentials"]
        assert len(credentials) == trustees_t
        assignment = [(prime_sub, credentials[0])]
        assignment.extend(zip(pool_subs, credentials[1:]))
        assert len(assignment) == trustees_t

        envelopes = {}
        for sub, cred in assignment:
            payload = cred["codeword"].encode("utf-8") if cred["mode"] == vault_core_prime.PROTECTION_KDF else cred["key"]
            recipient_pub = STATE["trustee_pubkeys"][sub]["public_key"]
            envelopes[sub] = {
                "envelope": shardic_envelope_crypto.wrap(payload, recipient_pub),
                "mode": cred["mode"],
            }

        # Only after every envelope has been successfully written do we
        # destroy the plaintext -- mirrors pubkey-envelope-plugin.md's
        # "secure destruction of plaintext intermediates" concern. A
        # partial failure above (e.g. one wrap() call raising) leaves the
        # plaintext files intact rather than half-destroying the set.
        # A PROTECTION_DRBG credential has no file at all -- its raw key
        # was never written to disk in the first place, so there is
        # nothing to destroy for it.
        for _sub, cred in assignment:
            if cred["mode"] == vault_core_prime.PROTECTION_KDF:
                _secure_delete(cred["file"])
        words_dir = result["words_dir"]
        if os.path.isdir(words_dir) and not os.listdir(words_dir):
            os.rmdir(words_dir)

        metadata, ciphertext = krypt_container.read_krypt(result["krypt_path"])

        # create_vault_prime (shared with the CLI) always writes its
        # output to a real file under `outdir` -- that's inherent to its
        # signature, unchanged here. VAULT_STORE becomes the canonical
        # home for those bytes going forward: register them under a
        # fresh vault_id, then remove the scratch file so VAULT_OUTDIR
        # doesn't accumulate a second, un-tracked copy alongside it.
        vault_id = str(uuid.uuid4())
        with open(result["krypt_path"], "rb") as f:
            krypt_bytes = f.read()
        VAULT_STORE.store(vault_id, krypt_bytes)
        os.remove(result["krypt_path"])

        STATE["codeword_envelopes"] = envelopes
        STATE["vault"] = {"vault_id": vault_id, "metadata": metadata, "ciphertext": ciphertext}
        # Recorded once, here, rather than re-derived later from
        # trustee_pubkeys -- the ceremony's finalized slot assignment
        # (including any backfills) is the source of truth for who's
        # prime/pool, not a re-sort of whoever happens to be registered
        # by the time something queries it.
        STATE["vault_assignment"] = {
            "prime_sub": prime_sub,
            "pool_subs": pool_subs,
        }
        # Consumed -- this demo supports one vault at a time, so a new
        # ceremony can be initiated once this one's finished its job.
        STATE["ceremony"] = None
        _save_state_locked()

        response = {
            "vault_id": vault_id,
            "prime_trustee": STATE["trustee_pubkeys"][prime_sub]["username"],
            "pool_trustees": [STATE["trustee_pubkeys"][sub]["username"] for sub in pool_subs],
            "threshold": threshold_d,
            "pool_threshold": metadata["pool_threshold"],
            "shard_protection_mode": protection_mode,
        }

    _broadcast("vault_created", response)
    return response


def get_vault_krypt_bytes() -> bytes:
    with _lock:
        if STATE["vault"] is None:
            raise CombinerError("no vault has been created yet", status_code=404)
        vault_id = STATE["vault"]["vault_id"]
    # Retrieved outside the lock -- VAULT_STORE has its own I/O, no
    # reason to hold the combiner's state lock for it.
    return VAULT_STORE.retrieve(vault_id)


def _secure_delete(path: str) -> None:
    size = os.path.getsize(path)
    with open(path, "r+b") as f:
        f.write(b"\x00" * size)
        f.flush()
        os.fsync(f.fileno())
    os.unlink(path)


def start_recovery_session() -> str:
    with _lock:
        if STATE["vault"] is None:
            raise CombinerError("no vault has been created yet", status_code=409)
        session_id = str(uuid.uuid4())
        STATE["recovery_session"] = {
            "session_id": session_id,
            "replied": set(),
            "mask": None,
            "pool_shards": [],
        }
    _broadcast("recovery_started", {"session_id": session_id})
    return session_id


def get_pending_envelope(sub: str) -> dict | None:
    with _lock:
        STATE["trustee_last_seen"][sub] = time.time()
        session = STATE["recovery_session"]
        if session is None or sub in session["replied"]:
            return None
        entry = STATE["codeword_envelopes"].get(sub)
        if entry is None:
            return None
        return {
            "session_id": session["session_id"],
            "combiner_pub": base64.b64encode(STATE["combiner_public_key"]).decode("ascii"),
            "credential_envelope": entry["envelope"],
            "protection_mode": entry["mode"],
        }


def submit_unsealed_shard_reply(sub: str, session_id: str, shard_envelope: dict) -> None:
    with _lock:
        STATE["trustee_last_seen"][sub] = time.time()
        session = STATE["recovery_session"]
        if session is None or session["session_id"] != session_id:
            raise CombinerError("no active recovery session with that session_id", status_code=409)
        if sub in session["replied"]:
            return  # idempotent no-op on a duplicate reply (poll-loop retry)
        try:
            unsealed_shard_bytes = shardic_envelope_crypto.unwrap(shard_envelope, STATE["combiner_private_key"])
            kind, value = shardic_envelope_crypto.deserialize_unsealed_shard(unsealed_shard_bytes)
        except (shardic_envelope_crypto.EnvelopeError, ValueError) as e:
            raise CombinerError(f"could not process unsealed shard reply: {e}", status_code=400)
        if kind == shardic_envelope_crypto.UNSEALED_SHARD_KIND_PRIME:
            session["mask"] = value
        else:
            session["pool_shards"].append(value)
        session["replied"].add(sub)
        pool_threshold = STATE["vault"]["metadata"]["pool_threshold"]
        username = STATE["trustee_pubkeys"][sub]["username"]
        replied_count = len(session["replied"])
        print(f"unsealed shard received from trustee (session {session_id}); {replied_count} received so far")
    _broadcast("unsealed_shard_received", {
        "username": username,
        "kind": kind,
        "replied_count": replied_count,
        "pool_threshold": pool_threshold,
    })


def finalize_recovery(outdir: str) -> dict:
    with _lock:
        session = STATE["recovery_session"]
        if session is None:
            raise CombinerError("no active recovery session", status_code=409)
        metadata = STATE["vault"]["metadata"]
        pool_threshold = metadata["pool_threshold"]
        if session["mask"] is None:
            raise CombinerError(
                "the prime trustee has not replied yet -- recovery cannot proceed without it",
                status_code=409,
            )
        if len(session["pool_shards"]) < pool_threshold:
            raise CombinerError(
                f"only {len(session['pool_shards'])} of the required {pool_threshold} pool shards received so far",
                status_code=409,
            )
        result = vault_core_prime.reconstruct_and_decrypt_prime(
            metadata=metadata,
            ciphertext=STATE["vault"]["ciphertext"],
            mask=session["mask"],
            pool_shards=session["pool_shards"],
            outdir=outdir,
            log=print,
        )
        trustees_used = sorted(STATE["trustee_pubkeys"][sub]["username"] for sub in session["replied"])
        response = {"outdir": result["outdir"], "trustees_used": trustees_used}

    _broadcast("recovery_finalized", response)
    return response


def verify_recovery() -> dict:
    """Pure-Python recursive tree comparison -- python:3.12-slim doesn't
    reliably ship `diffutils`, and this mirrors exactly the paths the
    README's manual `diff -r` check already uses."""
    recovered_path = os.path.join(RECOVERED_OUTDIR, os.path.basename(SAMPLE_SECRET_PATH.rstrip("/")))
    match = _trees_match(SAMPLE_SECRET_PATH, recovered_path)
    with _lock:
        STATE["last_verify"] = {"match": match}
    _broadcast("recovery_verified", {"match": match})
    return {"match": match}


def _trees_match(left: str, right: str) -> bool:
    if not os.path.exists(right):
        return False
    if os.path.isdir(left) != os.path.isdir(right):
        return False
    if os.path.isdir(left):
        comparison = filecmp.dircmp(left, right)
        if comparison.left_only or comparison.right_only or comparison.funny_files:
            return False
        _match, mismatch, errors = filecmp.cmpfiles(
            left, right, comparison.common_files, shallow=False
        )
        if mismatch or errors:
            return False
        return all(
            _trees_match(os.path.join(left, sub), os.path.join(right, sub))
            for sub in comparison.common_dirs
        )
    return filecmp.cmp(left, right, shallow=False)


def _heartbeat_loop() -> None:
    """Background daemon thread: trustees hit /trustees/pending-envelope
    every poll_interval_s unconditionally (whether or not a recovery
    session is open), so a gap longer than HEARTBEAT_TIMEOUT_S means the
    container is paused (or gone) -- this is the only signal used, no
    Docker API access from the browser or this process."""
    while True:
        time.sleep(HEARTBEAT_SCAN_INTERVAL_S)
        now = time.time()
        transitions = []
        with _lock:
            for sub, last_seen in STATE["trustee_last_seen"].items():
                # A verified caller polling before it's ever completed
                # /trustees/register (or, as found in testing, a Keycloak
                # realm re-import minting a new sub for an
                # already-running trustee mid-session) has no
                # trustee_pubkeys record yet -- skip rather than crash
                # the thread, which would silently kill liveness
                # tracking for the rest of the process's life.
                if sub not in STATE["trustee_pubkeys"]:
                    continue
                status = "paused" if (now - last_seen) > HEARTBEAT_TIMEOUT_S else "live"
                if STATE["trustee_status"].get(sub) != status:
                    STATE["trustee_status"][sub] = status
                    transitions.append((STATE["trustee_pubkeys"][sub]["username"], status))
        for username, status in transitions:
            _broadcast("trustee_status", {"username": username, "status": status})


def _build_snapshot() -> dict:
    with _lock:
        trustees = [
            {
                "username": rec["username"],
                "fingerprint": rec["fingerprint"],
                "status": STATE["trustee_status"].get(sub, "live"),
            }
            for sub, rec in sorted(STATE["trustee_pubkeys"].items(), key=lambda kv: kv[1]["username"])
        ]
        vault = None
        if STATE["vault"] is not None:
            assignment = STATE["vault_assignment"]
            pool_threshold = STATE["vault"]["metadata"]["pool_threshold"]
            vault = {
                "prime_trustee": STATE["trustee_pubkeys"][assignment["prime_sub"]]["username"],
                "pool_trustees": [STATE["trustee_pubkeys"][sub]["username"] for sub in assignment["pool_subs"]],
                "threshold": pool_threshold + 1,  # D = 1 mandatory prime + pool_threshold
                "pool_threshold": pool_threshold,
            }
        ceremony = None
        c = STATE["ceremony"]
        if c is not None:
            ceremony = {
                "ceremony_id": c["ceremony_id"],
                "status": c["status"],
                "threshold_d": c["threshold_d"],
                "trustees_t": c["trustees_t"],
                "slots": [
                    {"role": s["role"], "username": STATE["trustee_pubkeys"][s["sub"]]["username"], "status": s["status"]}
                    for s in c["slots"]
                ],
                "backup_queue": [STATE["trustee_pubkeys"][sub]["username"] for sub in c["backup_queue"]],
            }
        session = STATE["recovery_session"]
        recovery = None
        if session is not None:
            pool_threshold = STATE["vault"]["metadata"]["pool_threshold"] if STATE["vault"] else None
            recovery = {
                "session_id": session["session_id"],
                "replied_usernames": sorted(
                    STATE["trustee_pubkeys"][sub]["username"] for sub in session["replied"]
                ),
                "pool_threshold": pool_threshold,
            }
        return {
            "trustees": trustees,
            "ceremony": ceremony,
            "vault": vault,
            "recovery": recovery,
            "last_verify": STATE["last_verify"],
        }


# ---------------------------------------------------------------------------
# Routes
# ---------------------------------------------------------------------------

def _bearer_token() -> str:
    auth = request.headers.get("Authorization", "")
    if not auth.startswith("Bearer "):
        raise CombinerError("missing Bearer token", status_code=401)
    return auth[len("Bearer "):]


def _require_operator() -> tuple[str, str]:
    """Verifies the caller holds a live Keycloak session AND has been
    granted the shardic-operator realm role -- replaces the old static
    X-Admin-Token shared secret with a real authenticated, auditable
    identity behind every /admin/* action (see
    docs/keycloak-credential-lookup.md#the-operator-role). Role
    membership is checked via the Admin API using the combiner's own
    service-account credential (the same trust model already used by
    get_group_members()), not by trusting claims out of the caller's
    own token -- see keycloak_client.py's module docstring. Returns
    (sub, username) -- sub is needed by ceremony initiation's
    separation-of-duties check (docs/ceremony-formation.md), username
    is for logging."""
    sub, username = keycloak_client.get_verified_identity(OPERATOR_OIDC_ISSUER, OPERATOR_REALM, _bearer_token())
    admin_token = keycloak_client.service_account_token(OPERATOR_OIDC_ISSUER, OPERATOR_REALM, ADMIN_CLIENT_ID, ADMIN_CLIENT_SECRET)
    if not keycloak_client.user_has_realm_role(OPERATOR_OIDC_ISSUER, OPERATOR_REALM, admin_token, sub, OPERATOR_ROLE):
        raise CombinerError(f"caller does not hold the {OPERATOR_ROLE} role", status_code=403)
    return sub, username


def _sub_from_bearer() -> str:
    """Resolves the caller's sub via a live userinfo check -- same
    verification path as registration, so a trustee can't claim another
    trustee's identity just by knowing some other valid-looking token."""
    sub, _username = keycloak_client.get_verified_identity(KEYCLOAK_URL, KEYCLOAK_REALM, _bearer_token())
    return sub


@app.errorhandler(CombinerError)
def _handle_combiner_error(e: CombinerError):
    return jsonify({"error": e.message}), e.status_code


@app.errorhandler(keycloak_client.AuthError)
def _handle_auth_error(e: keycloak_client.AuthError):
    return jsonify({"error": str(e)}), 401


@app.errorhandler(vault_store.VaultStoreError)
def _handle_vault_store_error(e: vault_store.VaultStoreError):
    status_code = 404 if isinstance(e, vault_store.VaultNotFoundError) else 500
    return jsonify({"error": str(e)}), status_code


@app.route("/healthz", methods=["GET"])
def healthz():
    return jsonify({"status": "ok"})


@app.route("/trustees/register", methods=["POST"])
def trustees_register():
    body = request.get_json(force=True)
    result = do_register_trustee(_bearer_token(), body["public_key"], body.get("algorithm", ""))
    print(f"registered trustee {result['username']} ({result['fingerprint']})")
    return jsonify(result)


@app.route("/vault/metadata", methods=["GET"])
def vault_metadata():
    with _lock:
        if STATE["vault"] is None:
            return jsonify({"error": "no vault created yet"}), 404
        return jsonify(STATE["vault"]["metadata"])


@app.route("/trustees/pending-invitation", methods=["GET"])
def trustees_pending_invitation():
    sub = _sub_from_bearer()
    invitation = get_pending_invitation(sub)
    if invitation is None:
        return "", 204
    return jsonify(invitation)


@app.route("/trustees/invitation-response", methods=["POST"])
def trustees_invitation_response():
    sub = _sub_from_bearer()
    body = request.get_json(force=True)
    result = respond_to_invitation(sub, body["ceremony_id"], body["accept"])
    return jsonify(result)


@app.route("/trustees/pending-envelope", methods=["GET"])
def trustees_pending_envelope():
    sub = _sub_from_bearer()
    envelope = get_pending_envelope(sub)
    if envelope is None:
        return "", 204
    return jsonify(envelope)


@app.route("/trustees/shard-reply", methods=["POST"])
def trustees_shard_reply():
    sub = _sub_from_bearer()
    body = request.get_json(force=True)
    submit_unsealed_shard_reply(sub, body["session_id"], body["shard_envelope"])
    return jsonify({"status": "accepted"})


@app.route("/admin/ceremony/initiate", methods=["POST"])
def admin_ceremony_initiate():
    operator_sub, operator_username = _require_operator()
    body = request.get_json(force=True)
    result = initiate_ceremony(
        operator_sub,
        threshold_d=body["threshold_d"],
        prime_username=body["prime"],
        pool_usernames=body["pool"],
        backup_usernames=body.get("backups", []),
    )
    print(f"ceremony {result['ceremony_id']} initiated by operator {operator_username}")
    return jsonify(result)


@app.route("/admin/vault/create", methods=["POST"])
def admin_vault_create():
    _operator_sub, operator_username = _require_operator()
    body = request.get_json(silent=True) or {}
    use_codewords = bool(body.get("use_codewords", False))
    result = do_create_vault(SAMPLE_SECRET_PATH, VAULT_OUTDIR, use_codewords=use_codewords)
    print(f"vault created by operator {operator_username} (shard_protection_mode={result['shard_protection_mode']})")
    return jsonify(result)


@app.route("/admin/vault/download", methods=["GET"])
def admin_vault_download():
    _operator_sub, operator_username = _require_operator()
    krypt_bytes = get_vault_krypt_bytes()
    vault_id = STATE["vault"]["vault_id"]
    print(f"vault {vault_id} downloaded by operator {operator_username}")
    return Response(
        krypt_bytes,
        mimetype="application/octet-stream",
        headers={"Content-Disposition": f'attachment; filename="{vault_id}.krypt"'},
    )


@app.route("/admin/keycloak/group-members", methods=["GET"])
def admin_group_members():
    _require_operator()
    token = keycloak_client.service_account_token(KEYCLOAK_URL, KEYCLOAK_REALM, ADMIN_CLIENT_ID, ADMIN_CLIENT_SECRET)
    members = keycloak_client.get_group_members(KEYCLOAK_URL, KEYCLOAK_REALM, token, "shardic-trustees")
    return jsonify([{"username": m["username"], "id": m["id"]} for m in members])


@app.route("/admin/recovery/start", methods=["POST"])
def admin_recovery_start():
    _operator_sub, operator_username = _require_operator()
    session_id = start_recovery_session()
    print(f"recovery session {session_id} started by operator {operator_username}")
    return jsonify({"session_id": session_id})


@app.route("/admin/recovery/finalize", methods=["POST"])
def admin_recovery_finalize():
    _operator_sub, operator_username = _require_operator()
    result = finalize_recovery(RECOVERED_OUTDIR)
    print(f"recovery finalized by operator {operator_username}")
    return jsonify(result)


@app.route("/admin/recovery/verify", methods=["POST"])
def admin_recovery_verify():
    _operator_sub, operator_username = _require_operator()
    result = verify_recovery()
    print(f"recovery verify requested by operator {operator_username}: match={result['match']}")
    return jsonify(result)


@app.route("/events", methods=["GET"])
def events():
    """SSE stream for the live ceremony dashboard. Sends one `snapshot`
    event immediately (so a dashboard opened mid-ceremony repaints
    correctly), then relays every subsequent _broadcast() call."""
    q: queue.Queue = queue.Queue()
    with _sse_lock:
        _sse_listeners.append(q)

    def stream():
        try:
            snapshot_message = json.dumps({"type": "snapshot", "data": _build_snapshot()})
            yield f"data: {snapshot_message}\n\n"
            while True:
                message = q.get()
                yield f"data: {message}\n\n"
        finally:
            with _sse_lock:
                if q in _sse_listeners:
                    _sse_listeners.remove(q)

    return Response(stream(), mimetype="text/event-stream")


@app.route("/dashboard", methods=["GET"])
def dashboard_index():
    return send_from_directory(DASHBOARD_DIR, "index.html")


@app.route("/dashboard/<path:filename>", methods=["GET"])
def dashboard_static(filename):
    return send_from_directory(DASHBOARD_DIR, filename)


if __name__ == "__main__":
    os.makedirs(DATA_DIR, exist_ok=True)
    threading.Thread(target=_heartbeat_loop, daemon=True).start()
    threading.Thread(target=_ceremony_scan_loop, daemon=True).start()
    app.run(host="0.0.0.0", port=5000, threaded=True)

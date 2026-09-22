"""
app.py -- shardic-envelope demo trustee.

Represents one trustee's own device. No inbound HTTP server -- this is
a pure client: authenticate to Keycloak as the trustee, generate/persist
a local X25519 keypair, register the public key with the combiner, then
poll for a pending recovery envelope.

When an envelope arrives, everything happens locally and nothing but
the final unsealed shard ever leaves this process:
  1. unwrap the envelope with this trustee's own private key -> the
     plaintext codeword (held in memory only, never logged or printed)
  2. immediately run the existing, UNMODIFIED
     vault_core_prime.try_match_word_prime against the vault's public
     .krypt metadata to derive this trustee's unsealed shard (the mask, if this
     is the prime trustee, or an (x, y) pool point)
  3. wrap that unsealed shard -- not the codeword -- to the combiner's public
     key (bundled in the same envelope, the "self-addressed envelope"
     pattern) and send it back

The combiner never receives a codeword from any trustee, only unsealed shards.
"""

import base64
import os
import sys
import time

import requests

import shardic_envelope_crypto
import vault_core_prime

_TIMEOUT_S = 5
_REGISTER_RETRY_S = 3


def log(msg: str) -> None:
    print(msg, flush=True)


def authenticate(base_url: str, realm: str, client_id: str, username: str, password: str) -> str:
    """Direct Access Grant (Resource Owner Password Credentials) flow.
    Re-run before every combiner-authenticated call rather than tracking
    a refresh token -- deliberate demo simplification, cheap since this
    flow has no interactive step to repeat."""
    url = f"{base_url}/realms/{realm}/protocol/openid-connect/token"
    resp = requests.post(
        url,
        data={
            "grant_type": "password",
            "client_id": client_id,
            "username": username,
            "password": password,
            "scope": "openid",
        },
        timeout=_TIMEOUT_S,
    )
    resp.raise_for_status()
    return resp.json()["access_token"]


def register(combiner_base_url: str, token: str, public_key_raw: bytes) -> None:
    """POSTs this trustee's public key to the combiner, retrying with a
    fixed backoff -- belt-and-suspenders alongside compose's
    depends_on/healthcheck ordering, in case the combiner's Flask app
    hasn't finished initializing yet."""
    url = f"{combiner_base_url}/trustees/register"
    body = {
        "public_key": base64.b64encode(public_key_raw).decode("ascii"),
        "algorithm": shardic_envelope_crypto.ALGORITHM_TAG,
    }
    while True:
        try:
            resp = requests.post(
                url,
                json=body,
                headers={"Authorization": f"Bearer {token}"},
                timeout=_TIMEOUT_S,
            )
            if resp.status_code == 200:
                log(f"registered with combiner: {resp.json()}")
                return
            log(f"registration attempt failed: HTTP {resp.status_code} {resp.text} -- retrying")
        except requests.RequestException as e:
            log(f"registration attempt failed: {e} -- retrying")
        time.sleep(_REGISTER_RETRY_S)


def _check_and_accept_invitation(combiner_base_url: str, token: str) -> None:
    """Checks for a pending ceremony invitation and immediately accepts
    it. This demo trustee has no interactive human to ask, so accepting
    on sight is the same auto-everything behavior already used for
    registration and unsealed shard replies. A trustee that shouldn't
    participate in a given ceremony is simulated by pausing its
    container (docker-compose pause) so it never polls to see the
    invitation in the first place -- decline and silent timeout are
    treated identically by the combiner either way, per
    docs/ceremony-formation.md#decline--no-response-handling."""
    resp = requests.get(
        f"{combiner_base_url}/trustees/pending-invitation",
        headers={"Authorization": f"Bearer {token}"},
        timeout=_TIMEOUT_S,
    )
    if resp.status_code != 200:
        return
    invitation = resp.json()
    accept_resp = requests.post(
        f"{combiner_base_url}/trustees/invitation-response",
        json={"ceremony_id": invitation["ceremony_id"], "accept": True},
        headers={"Authorization": f"Bearer {token}"},
        timeout=_TIMEOUT_S,
    )
    if accept_resp.status_code == 200:
        log(f"accepted {invitation['role']} invitation for ceremony {invitation['ceremony_id']}")
    else:
        log(f"invitation accept failed: HTTP {accept_resp.status_code} {accept_resp.text}")


def poll_and_respond_loop(
    combiner_base_url: str,
    keycloak_url: str,
    keycloak_realm: str,
    client_id: str,
    username: str,
    password: str,
    private_key: bytes,
    poll_interval_s: int = 3,
) -> None:
    cached_metadata = None

    while True:
        try:
            token = authenticate(keycloak_url, keycloak_realm, client_id, username, password)
            _check_and_accept_invitation(combiner_base_url, token)
            resp = requests.get(
                f"{combiner_base_url}/trustees/pending-envelope",
                headers={"Authorization": f"Bearer {token}"},
                timeout=_TIMEOUT_S,
            )
        except requests.RequestException as e:
            log(f"poll failed: {e}")
            time.sleep(poll_interval_s)
            continue

        if resp.status_code == 204:
            time.sleep(poll_interval_s)
            continue
        if resp.status_code != 200:
            log(f"unexpected poll response: HTTP {resp.status_code} {resp.text}")
            time.sleep(poll_interval_s)
            continue

        body = resp.json()
        session_id = body["session_id"]
        combiner_pub = base64.b64decode(body["combiner_pub"])
        protection_mode = body["protection_mode"]

        try:
            credential = shardic_envelope_crypto.unwrap(body["credential_envelope"], private_key)
        except shardic_envelope_crypto.EnvelopeError as e:
            log(f"could not unwrap credential envelope: {e}")
            time.sleep(poll_interval_s)
            continue

        if cached_metadata is None:
            meta_resp = requests.get(f"{combiner_base_url}/vault/metadata", timeout=_TIMEOUT_S)
            meta_resp.raise_for_status()
            cached_metadata = meta_resp.json()

        if protection_mode == vault_core_prime.PROTECTION_DRBG:
            # A DRBG-direct credential is already the raw AES-256-GCM
            # shard-protection key -- no KDF, no salt, tried directly.
            match = vault_core_prime.try_match_key_prime(
                credential, cached_metadata.get("shards", cached_metadata.get("shares")), used_indices=set()
            )
        else:
            codeword = credential.decode("utf-8")
            kdf_method, kdf_params = vault_core_prime.resolve_kdf(cached_metadata)
            match = vault_core_prime.try_match_word_prime(
                codeword, cached_metadata.get("shards", cached_metadata.get("shares")), kdf_method, kdf_params, used_indices=set()
            )
            del codeword
        del credential  # never needed again; don't let it linger in a local var
        if match is None:
            log(f"{protection_mode} credential did not match any shard record in this vault's metadata -- cannot derive an unsealed shard")
            time.sleep(poll_interval_s)
            continue

        _idx, kind, value = match
        unsealed_shard_bytes = shardic_envelope_crypto.serialize_unsealed_shard(kind, value)
        reply_envelope = shardic_envelope_crypto.wrap(unsealed_shard_bytes, combiner_pub)

        reply_resp = requests.post(
            f"{combiner_base_url}/trustees/shard-reply",
            json={"session_id": session_id, "shard_envelope": reply_envelope},
            headers={"Authorization": f"Bearer {token}"},
            timeout=_TIMEOUT_S,
        )
        if reply_resp.status_code == 200:
            log(f"unsealed shard submitted for session {session_id}")
        else:
            log(f"unsealed shard submission failed: HTTP {reply_resp.status_code} {reply_resp.text}")

        time.sleep(poll_interval_s)


def main() -> None:
    keycloak_url = os.environ["KEYCLOAK_URL"]
    keycloak_realm = os.environ["KEYCLOAK_REALM"]
    client_id = os.environ["TRUSTEE_CLIENT_ID"]
    username = os.environ["TRUSTEE_USERNAME"]
    password = os.environ["TRUSTEE_PASSWORD"]
    combiner_url = os.environ["COMBINER_URL"]
    key_dir = os.environ.get("TRUSTEE_KEY_DIR", "/data")
    poll_interval_s = int(os.environ.get("POLL_INTERVAL_S", "3"))

    private_key, public_key = shardic_envelope_crypto.load_or_create_keypair(key_dir)
    log(f"trustee {username}: public key fingerprint {shardic_envelope_crypto.fingerprint(public_key)}")

    token = authenticate(keycloak_url, keycloak_realm, client_id, username, password)
    register(combiner_url, token, public_key)

    poll_and_respond_loop(
        combiner_url,
        keycloak_url,
        keycloak_realm,
        client_id,
        username,
        password,
        private_key,
        poll_interval_s=poll_interval_s,
    )


if __name__ == "__main__":
    try:
        main()
    except KeyboardInterrupt:
        sys.exit(0)

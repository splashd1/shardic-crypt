"""
keycloak_client.py

Small HTTP helpers for the combiner's three Keycloak touchpoints:
verifying a bearer token (trustee at registration, operator on every
/admin/* route), querying the Admin API (as the shardic-combiner-admin
service account) for the shardic-trustees group's membership -- the
"show the 7 candidates" demo step -- and, via that same service
account, checking whether an authenticated caller holds the
shardic-operator realm role. Split out of app.py because multiple
routes share this, not because it's a general-purpose Keycloak SDK.

Demo-only note: token verification here is a live call to Keycloak's
userinfo endpoint (confirms the token is currently valid and gets the
verified `sub`), not local JWKS/JWT signature verification. That's a
deliberate demo simplification -- it means registration requires
Keycloak to be reachable, which is fine for this one-time action, and
is explicitly NOT the pattern recovery/reconstruction depends on
(those never touch Keycloak at all, per docs/keycloak-credential-lookup.md's
general "recovery must not require the IdP" principle).
"""

import requests

_TIMEOUT_S = 5


class AuthError(Exception):
    """Raised when a bearer token fails verification or a Keycloak call fails."""


def get_verified_identity(base_url: str, realm: str, bearer_token: str) -> tuple[str, str]:
    """Calls the OIDC userinfo endpoint with the given bearer token.
    Returns (sub, preferred_username) on success -- sub is the durable
    identity key used everywhere internally; preferred_username is only
    used for the demo's human-readable alphabetical prime/pool
    assignment and log output."""
    url = f"{base_url}/realms/{realm}/protocol/openid-connect/userinfo"
    resp = requests.get(url, headers={"Authorization": f"Bearer {bearer_token}"}, timeout=_TIMEOUT_S)
    if resp.status_code != 200:
        raise AuthError(f"token verification failed: HTTP {resp.status_code}")
    body = resp.json()
    sub = body.get("sub")
    username = body.get("preferred_username")
    if not sub or not username:
        raise AuthError("userinfo response missing 'sub' or 'preferred_username'")
    return sub, username


def service_account_token(base_url: str, realm: str, client_id: str, client_secret: str) -> str:
    """Client-credentials grant for the combiner's own service account."""
    url = f"{base_url}/realms/{realm}/protocol/openid-connect/token"
    resp = requests.post(
        url,
        data={
            "grant_type": "client_credentials",
            "client_id": client_id,
            "client_secret": client_secret,
        },
        timeout=_TIMEOUT_S,
    )
    if resp.status_code != 200:
        raise AuthError(f"service-account token request failed: HTTP {resp.status_code} {resp.text}")
    return resp.json()["access_token"]


def user_has_realm_role(base_url: str, realm: str, admin_token: str, user_id: str, role_name: str) -> bool:
    """Checks whether user_id -- the Keycloak internal user id, which is
    the same value as the `sub` claim in that user's own tokens -- has
    role_name mapped directly at the realm level. Uses the same Admin
    API + service-account trust model as get_group_members() below,
    rather than trusting role claims out of a client-supplied token
    (which this module deliberately never decodes/verifies locally --
    see the module docstring)."""
    url = f"{base_url}/admin/realms/{realm}/users/{user_id}/role-mappings/realm"
    resp = requests.get(url, headers={"Authorization": f"Bearer {admin_token}"}, timeout=_TIMEOUT_S)
    if resp.status_code != 200:
        raise AuthError(f"role-mapping lookup failed: HTTP {resp.status_code} {resp.text}")
    return any(role.get("name") == role_name for role in resp.json())


def get_group_members(base_url: str, realm: str, admin_token: str, group_name: str) -> list[dict]:
    """Resolves the group's id by name, then lists its members. Returns
    the raw Keycloak user objects (username, id, email, ...)."""
    headers = {"Authorization": f"Bearer {admin_token}"}

    search_url = f"{base_url}/admin/realms/{realm}/groups"
    resp = requests.get(search_url, headers=headers, params={"search": group_name}, timeout=_TIMEOUT_S)
    if resp.status_code != 200:
        raise AuthError(f"group search failed: HTTP {resp.status_code} {resp.text}")
    matches = [g for g in resp.json() if g.get("name") == group_name]
    if not matches:
        raise AuthError(f"group {group_name!r} not found in realm {realm!r}")
    group_id = matches[0]["id"]

    members_url = f"{base_url}/admin/realms/{realm}/groups/{group_id}/members"
    resp = requests.get(members_url, headers=headers, timeout=_TIMEOUT_S)
    if resp.status_code != 200:
        raise AuthError(f"group member listing failed: HTTP {resp.status_code} {resp.text}")
    return resp.json()

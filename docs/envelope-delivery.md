# shardic-envelope delivery: a pull-based drop point for wrapped codewords (proposed, unimplemented)

**Status: design proposal.** Nothing described here exists in the
codebase yet. This document closes a gap left open by
[pubkey-envelope-plugin.md](pubkey-envelope-plugin.md): its
["Recovery-time flow"](pubkey-envelope-plugin.md#recovery-time-flow)
section starts from "a trustee holding a `.envelope` file," without
saying how it got from the operator's machine (where wrapping happens)
onto that trustee's device. This doc designs that step, building on
the OIDC-authenticated identity already established in
[keycloak-credential-lookup.md](keycloak-credential-lookup.md).

## The problem this solves

Wrapping produces `trustee_N.txt.envelope` files on whatever machine
ran the wrap step. Getting each one to the right trustee needs a
mechanism that:

- doesn't require shardic (or the operator) to know or manage a
  delivery address — email, phone number, push token — per trustee,
  since none of that is part of the identity model
  `keycloak-credential-lookup.md` already built (it only knows a
  trustee's Keycloak `sub` and registered public key);
- doesn't introduce an online dependency at *recovery* time — that
  constraint is already load-bearing in
  [keeping the OAuth dependency scoped to registration only](keycloak-credential-lookup.md#keeping-the-oauth-dependency-scoped-to-registration-only),
  and delivery has to respect it too;
- doesn't hand the operator an unencrypted file to relay by hand over
  whatever channel happens to be convenient (email, Slack, USB), which
  is the de facto fallback if nothing else is defined.

## Design principle: pull, not push

The wrap step deposits each envelope at an authenticated, single-read
**drop point**, addressed by `trustee_id` (the same Keycloak `sub`
used throughout `keycloak-credential-lookup.md`) rather than a contact
channel. The trustee fetches it themselves, once, using the same kind
of OIDC-authenticated session already used at registration. A
separate, low-stakes notification ("a wrap event happened, go check")
can use whatever channel the org already has — it carries no secret,
only a prompt, so it doesn't need to be a trusted or secure channel
itself.

## Where it sits in the architecture

```
shardic-envelope wrap event (per pubkey-envelope-plugin.md)
        │
        ▼
trustee_N.txt.envelope
   (already PK-wrapped; plaintext codeword already destroyed
    per pubkey-envelope-plugin.md's destruction sequencing)
        │
        ▼
   ┌─────────────────────────────────┐
   │   Drop point (this doc)         │
   │   single-read, token-gated,     │
   │   keyed by trustee_id           │
   └─────────────────────────────────┘
        │
        ▼  trustee pulls, authenticated via OIDC session
           (same session pattern as registration)
Trustee's own device
        │
        ▼
Recovery-time flow, unchanged (per pubkey-envelope-plugin.md):
decrypt locally with private key, type the resulting codeword
into vault_recover.py / the GUI exactly as any other trustee would.
```

## Response-wrapping as the reference model

HashiCorp Vault's Cubbyhole / response-wrapping feature is the closest
existing analog worth designing against: store a secret keyed to a
single-use token with a TTL, redeemable exactly once. Wanted semantics
here:

- Each drop-point record: `{trustee_id, envelope_bytes, created_at,
  expires_at, redeemed: bool}`.
- Deposit happens once per trustee, from the wrap step.
- Redemption requires an authenticated request — the caller's verified
  `sub` must match the record's `trustee_id` — and succeeds **exactly
  once**. The first successful redeem atomically flips
  `redeemed = True`; every subsequent attempt fails **loudly**, not by
  silently re-serving the same bytes or silently returning nothing.
  A legitimate trustee who gets an "already redeemed" error on their
  first real attempt has just learned something is wrong — that's a
  detection signal worth surfacing clearly, not swallowing.
- Un-redeemed drops expire after a bounded TTL (days, not months). An
  expired, unredeemed drop should generate an operator-visible
  log/notification, since it means that trustee's shard is effectively
  stranded until someone re-wraps and re-deposits for them.

## Interface sketch

```python
class EnvelopeDropPoint(Protocol):
    def deposit(self, trustee_id: str, envelope_bytes: bytes, ttl: timedelta) -> None:
        """Called once per trustee by the wrap step. Raises if a live
        (non-expired, non-redeemed) drop already exists for trustee_id --
        deposits must not silently overwrite a pending delivery."""

    def redeem(self, trustee_id: str, auth_token: str) -> bytes:
        """Raises PermissionError if auth_token's verified subject != trustee_id.
        Raises AlreadyRedeemedError or ExpiredError as appropriate.
        On success, atomically marks the record redeemed and returns
        the envelope bytes -- exactly once."""
```

Authentication for `redeem()` reuses the OIDC bearer token/session
pattern from `keycloak-credential-lookup.md`'s registration flow —
no second identity system gets introduced for this. Backing store can
start at the same tier as the key registry (flat JSON/SQLite for small
trustee counts), but see below on why it deserves at least as much
operational care, arguably more.

## What this does and doesn't protect against

- **Confidentiality is unaffected by drop-point compromise.** The
  envelope is already ECIES/RSA-OAEP-wrapped per
  [the envelope construction](pubkey-envelope-plugin.md#the-envelope-construction)
  before it ever reaches the drop point, so read access to stored
  blobs doesn't expose codeword plaintext — that guarantee still rests
  entirely on the trustee's private key, unchanged. The drop point is
  a transport/availability concern layered on top of that, not a new
  confidentiality boundary.
- **What a compromised or malicious drop point *can* do:** deny
  delivery (withhold or corrupt a record), or leak metadata — who has
  a pending drop, when it was redeemed and from where. That's an
  availability/metadata risk, worth taking seriously operationally,
  but not a break of the underlying encryption.
- **What "exactly once" actually protects against — and what it
  doesn't.** It turns silent interception into a detected event: if an
  attacker redeems before the legitimate trustee does, the trustee's
  own attempt fails loudly instead of quietly handing over a second
  copy. This is a *detection* mechanism, not a *prevention* one — a
  genuinely hijacked OIDC session still wins the race, since redeem()
  can't distinguish a legitimate holder of a valid session from an
  attacker who's fully compromised it. That's the same residual risk
  already called out for
  [a hijacked OIDC session at registration time](keycloak-credential-lookup.md#new-threat-model-considerations)
  in the credential-lookup doc — this doc doesn't solve it, just
  inherits it and gives it one more place to surface (a failed
  redemption is itself a useful alarm).

## Open questions / TBD

- TTL default, and the concrete mechanism for operator notification on
  expiry (log line vs. active alert).
- Whether strict "exactly once" is too rigid for a legitimate
  re-fetch case — trustee successfully redeems but then loses the file
  before decrypting it. Leaning toward requiring an explicit
  *operator-triggered* re-deposit rather than trustee self-service
  re-fetch, so the "someone already redeemed this" signal stays
  meaningful rather than becoming routine.
- Backing store choice, and whether it should be co-located with the
  key registry from `keycloak-credential-lookup.md` or kept separate —
  this store holds live secrets-in-flight plus access metadata, which
  arguably warrants tighter handling than the registry's long-lived
  public keys.
- The "a wrap event happened, go pull your envelope" notification
  channel is deliberately out of scope here (this doc only covers the
  pull/authorization mechanism) — needs a decision, but whatever it is
  should carry no secret itself, only a prompt.

# shardware-token: PUF-sealed embed/extract with vault-signed authorization (proposed, unimplemented)

**Status: design proposal.** Nothing described here exists in the
codebase yet — no PUF hardware, no cert chain, no admin routes. This
is a hardened evolution of
[shardware-token.md](shardware-token.md#physical-medium-options)'s
physical-carriage idea: instead of dumb USB storage carrying an
already-wrapped, still-anonymous unsealed shard, the token itself is a
PUF/secure-element-backed device with its own identity, sealed
storage, and a live authorization step at extraction. It directly
answers the parent doc's ["identity without a live
session"](shardware-token.md#the-real-open-problem-identity-without-a-live-session)
problem with a third option neither of that doc's two candidates
covered: cryptographic authorization anchored to the token's own
hardware identity, gated by a live (but minimal) operator decision.

## Prior art this design leans on

- **Fuzzy extractors / secure sketches over a PUF response** — the
  standard construction for "encrypted storage that's inextractable
  without a matching physical chip": enrollment produces public helper
  data plus a stable derived key; reconstruction needs the helper data
  *and* a fresh PUF measurement. Shipping as **Intrinsic ID
  (QuiddiKey)** SRAM-PUF IP (licensed into some NXP/Microchip parts)
  and **PUFsecurity (PUFrt)** ring-oscillator/arbiter PUF IP (in some
  Nuvoton/GigaDevice secure MCUs). For prototyping the *protocol*
  below, a TPM 2.0 module or a YubiHSM-class device gives the same
  non-extractability property off the shelf, ahead of sourcing a
  bespoke PUF chip.
- **GlobalPlatform SCP03/SCP11** — the standard shape for "device
  generates a keypair, hands the pubkey to a server, receives
  provisioned material back over a mutually authenticated channel."
  The embed sequence below follows this shape rather than inventing a
  new handshake.
- **FIDO2/WebAuthn attestation** — a manufacturer-signed statement that
  a given keypair was generated inside genuine attested hardware, not
  software pretending to be a token. The embed step should require
  this: the combiner shouldn't trust a token's pubkey without proof it
  came from real PUF-backed silicon, or a compromised host could
  hand over a software-emulated fake.
- **TPM 2.0 sealing** (`TPM2_Seal`/`TPM2_Unseal`) — the reference model
  for "this blob only unseals on this exact chip," which is what the
  token's own storage needs to do with its unsealed shard.

## Embed sequence (at vault creation)

T tokens are on hand at the combiner. Per token, sequentially:

```
1. Token generates a shardic-envelope keypair locally
   (X25519, same primitive as shardic_envelope_crypto.py) --
   private key never leaves the token.
2. Token hands its pubkey + attestation statement to the combiner
   over a local, mutually authenticated channel (GlobalPlatform-style).
3. Combiner verifies attestation, then responds with:
     - the unsealed shard, wrapped to the token's pubkey
       (shardic_envelope_crypto.wrap() -- unmodified)
     - the vault's own root pubkey (see extraction, below)
4. Token seals {wrapped_unsealed_shard, vault_root_pubkey} into its own
   PUF-backed storage. The storage-unwrap key is derived from the
   PUF response combined (KDF) with a local unlock factor -- see
   "Token-side possession factor" below -- so neither the silicon
   alone nor a guessed factor alone reconstructs it.
5. Combiner destroys its own plaintext copy of the unsealed shard
   immediately -- extends the existing _secure_delete pattern already
   used for codeword envelopes (app.py:496), just applied one step
   earlier (the unsealed shard itself never has an at-rest copy
   anywhere but the token, versus today's model where it's briefly a
   server-side plaintext before wrap()).
```

## Extraction sequence (at recovery)

```
1. Token inserted. Generates a fresh random nonce locally.
2. {session_id, token_pubkey_hash, nonce} surfaced to the operator
   -- reusing the existing _broadcast() SSE pattern (recovery_started,
   unsealed_shard_received) as a new extraction_requested event: "token
   belonging to trustee X requests extraction, awaiting authorization."
3. Operator approves (single operator -- see below). Combiner's
   *intermediate* signing key signs an extraction grant naming this
   exact token_pubkey_hash + nonce, short validity window (minutes).
4. Token verifies, in order:
     a. intermediate_cert signature checks against its own stored
        vault_root_pubkey (from step 3 of embed), not expired
     b. extraction_grant signature checks against intermediate_cert's
        intermediate_pubkey
     c. token_pubkey_hash in the grant == its own pubkey
     d. nonce in the grant == the one it just generated
     e. now is within [not_before, not_after]
5. Only then: unseal, release the wrapped unsealed shard for delivery
   to the combiner (over whatever medium -- network or another
   physical hop).
```

## The two-tier certificate chain

Protecting the vault's own signing authority the same way TLS protects
a root CA -- minimize how often the high-value key is touched:

```
vault_root_key        (HSM/TPM-sealed, touched rarely -- only to
                        (re-)issue an intermediate)
      |  signs, per rotation period (e.g. weekly/monthly)
      v
intermediate_cert {intermediate_pubkey, not_after}
      |
      |  vault_intermediate_key signs, per extraction request
      v
extraction_grant {session_id, token_pubkey_hash, nonce,
                   not_before, not_after}
```

- **Token-bound**: a grant names the specific `token_pubkey_hash` it's
  for. A leaked grant is useless against any other token.
- **Freshness-bound**: the nonce is generated fresh by the token at
  each insertion, not chosen by the server -- a captured grant from a
  previous insertion won't match the next one, closing replay within
  the validity window without a stateful revocation list.
- **Revocation is free**: with `not_after` measured in minutes, there's
  no CRL/OCSP story needed -- a compromised intermediate ages out on
  its own schedule, the same philosophy SPIFFE/SPIRE uses for
  short-lived workload certs.

## Why single-operator authorization is sufficient

The operator can't originate an `extraction_requested` event -- only
approve or deny one a genuine physical token already initiated (the
nonce comes from hardware the operator doesn't control). So the actual
multi-party control here is **"D distinct physical tokens had to be
convened and inserted,"** which the trustee threshold already
provides; a second operator would add friction to a check that's
structurally redundant with the one doing the real work. Any
legitimate D-of-T quorum choosing to recover is, by definition, the
boundary this scheme is supposed to accept -- a second sign-off doesn't
defend against a threat the token-presence requirement doesn't already
foreclose.

**Residual risk, stated plainly rather than glossed over** (matching
how this project treats residual risk elsewhere -- the hijacked-OIDC-
session and browser-XSS callouts in `keycloak-credential-lookup.md`
and `portable-trustee-client.md`): a single operator who rubber-stamps
every request without real scrutiny reduces the checkpoint's value as
a *deliberate judgment point* to near zero, even though it can't be
bypassed cryptographically. That's a procedural risk, not a
cryptographic one -- worth an audit trail on every authorization
decision regardless of operator count, since two careless operators
rubber-stamp exactly as easily as one.

The existing separation-of-duties check (`initiate_ceremony()` blocks
an operator from self-selecting as a ceremony trustee) applies
unchanged here: an operator must not be able to authorize a grant
naming their own token.

Note this is a *sufficiency* argument, not an *availability* one -- a
single operator being cryptographically enough doesn't mean a single
person is always reachable when needed. See
[spac-concept.md](spac-concept.md#endgame-unlock-operator-grant--local-custodian-factor)'s
RTO discussion for extending an on-call backup roster to this role
without weakening the one-authorizer property above.

## Token-side possession factor

Per the "mere possession" discussion in the parent doc's threat model:
the storage-unwrap key should combine the PUF response with a second,
externally supplied factor, so a stolen token alone yields nothing.
This is the same requirement
[spac-concept.md](spac-concept.md#fielded-system-local-unlock-factor)'s
fielded-system `mask` needs for the same reason, just applied to a
trustee's token instead of a fielded unit -- both are instances of one
shared interface rather than two similar-but-different ones:

```python
class LocalUnlockFactor(Protocol):
    """Discrete, role-transferable local-authorization input required
    -- alongside a valid PUF/hardware unseal -- before sealed storage
    (a trustee token's unsealed shard, or a fielded system's mask) is released.
    Bound to a category (possessed/known/inherent), never assumed to
    be exhaustive of examples within a category, so the underlying
    custodian or trustee can be reassigned/re-provisioned without
    redesigning this interface. Exactly one discrete input, checked
    once -- no partial credit."""
    def check(self) -> bool: ...
```

Concrete examples, illustrative rather than a closed enum:

| Category | Examples | Note |
|---|---|---|
| **Possessed (physical)** | Mechanical key / key-switch; hardware token, smartcard, or dongle | A key-switch has no stored secret at all -- can't be guessed, only lost, copied, or coerced. A digital token/smartcard can carry its own internal PIN-gate and is easier to revoke/reprovision than re-keying a physical lock. |
| **Known (virtual)** | PIN, passphrase | Cheapest to deploy, weakest to leak or be observed -- a shared secret with no built-in accountability unless paired with logging. |
| **Inherent (identity-bound)** | Biometric input (fingerprint, iris, etc.) | Strongest single-factor identity binding, but doesn't transfer across a rotating custodian/trustee without re-enrollment -- appropriate when there's genuinely one fixed named holder rather than a rotating role. A legitimate choice, not excluded -- just a tradeoff to pick knowingly. |
| **Or other** | e.g. a challenge relayed to a separate out-of-band device the holder already carries | `check()` is the only contract; nothing assumes these three categories are exhaustive. |

For a trustee token specifically, one instance suffices per the same
reasoning as [the operator-authorization
question](#why-single-operator-authorization-is-sufficient) --
a single factor here is a configuration choice, not an architectural
ceiling; nothing prevents a deployment from requiring more than one
discrete `LocalUnlockFactor` if it wants that. Add a retry-counter
lockout (3-10 attempts) the way smartcards/YubiKeys already do, so
whichever factor is chosen can't be brute-forced offline even if the
PUF/KDF math holds.

## Physical medium, reconsidered

Unlike part 1's dumb-storage table, this variant needs an actual
secure element or PUF chip -- not a bare USB stick. Realistic starting
points: NXP EdgeLock SE050-class secure elements, a PUF IP block
(Intrinsic ID / PUFsecurity) integrated into a small MCU, or -- for
prototyping the protocol before committing to silicon -- a TPM 2.0
module or YubiHSM 2, both of which already give sealed, non-extractable
storage with an attestation story.

## Open questions / TBD

- PIN vs. biometric as the token's own local unlock factor -- not
  decided here.
- Concrete encoding for `intermediate_cert` / `extraction_grant`: a
  bespoke binary format (matches this project's other wire formats) vs.
  reusing something like a CWT/JWT shape given the cert-chain
  resemblance to standard PKI.
- Whether grant-authorization itself needs its own audit-logging
  design beyond the existing `_broadcast()` event stream, given the
  residual "rubber-stamp" risk named above.
- How the wrapped unsealed shard gets from the token to the combiner after
  extraction -- network, or a second physical hop -- not decided here;
  see [shardware-token.md](shardware-token.md#physical-medium-options)
  for the transport options this doc doesn't re-litigate.

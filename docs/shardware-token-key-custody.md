# shardware-token, part 2: hardware-backed key custody (proposed, unimplemented)

**Status: design proposal.** Nothing described here exists in the
codebase yet. This is the variant
[shardware-token.md](shardware-token.md#shardware-token-part-1-physical-carriage-of-an-unsealed-shard-proposed-unimplemented)
originally reserved as "future doc," and the opt-in hardening option
[portable-trustee-client.md](portable-trustee-client.md#browser-xss-residual-risk-resolved-web-is-the-default-documented-risk-with-an-opt-in-alternative)
already flagged without designing. Of the three shardware-token
variants, this is the narrowest: it changes nothing about the network,
the combiner, or the ceremony -- only where a trustee's own private key
lives and where the ECDH half of `wrap()`/`unwrap()` executes.

> **Note on downstream sync:** [embedment-manual.md](embedment-manual.md)
> synthesizes Fork 2 (key custody) from this doc's on-device-ECDH vs.
> local-secret-gated-software-key distinction. It's a snapshot, not
> generated -- changes here won't auto-propagate. If you revise the
> custody categories or their guarantees, check whether
> embedment-manual.md needs a matching update.

## Scope: what changes, what doesn't

Contrast against the other two variants already designed:

| Variant | What the hardware does |
|---|---|
| Physical carriage (part 1) | Is the *transport* for an already-wrapped unsealed shard; the token can be dumb storage |
| PUF-sealed embed/extract (part 3) | *Seals and vault-signed-releases* an unsealed shard already matched, gated by an extraction grant |
| Hardware-backed key custody (this doc, part 2) | Holds the trustee's own long-lived envelope keypair and performs the *ECDH step* of `wrap()`/`unwrap()`; delivery stays fully networked, exactly as `docs/pubkey-envelope-plugin.md` and `docs/envelope-delivery.md` already specify |

Registration still populates the same local key registry
(`keycloak-credential-lookup.md`); wrap still calls
`shardic_envelope_crypto.wrap()` unmodified on the combiner side;
delivery still uses the drop-point pattern
(`envelope-delivery.md`); recovery still ends with the trustee
supplying a plaintext codeword exactly as in the base walkthrough.
**Only the trustee-side unwrap step changes.**

## What the hardware can actually do -- an honest breakdown

Not every "hardware-backed" option gives the same guarantee. Two
categories exist, and conflating them oversells the weaker one:

| Category | Examples | What actually happens |
|---|---|---|
| **On-device ECDH** (private key and the point-multiplication both stay in hardware) | YubiKey OpenPGP applet (Curve25519 ECDH, firmware 5.2.3+); PIV/GIDS smartcards over PKCS#11 (NIST P-256/P-384 -- see caveat below); TPM 2.0 (`TPM2_ECDH_ZGen` against a non-extractable key) | The device computes the X25519 (or P-256) scalar multiplication itself. Only the resulting shared secret -- not sensitive on its own, without the envelope's HKDF+AES-GCM step -- ever leaves the device. |
| **Local-secret-gated software key** | FIDO2 `hmac-secret` extension | The authenticator derives a per-credential secret (`HMAC(credential_secret, salt)`) without ever exposing `credential_secret`, but this secret is used as a *key-encryption key* to decrypt a private key stored, encrypted, in browser storage. The X25519 private key briefly exists in plaintext in host/JS memory during the unwrap operation -- a real hardening over an unencrypted key, but not equivalent to "the private key never leaves silicon." |

Any UI or documentation built on top of this should say which category
a given deployment is getting, rather than presenting both as
interchangeable "hardware-backed" custody -- the security properties
are genuinely different.

**Curve compatibility is a real constraint, not a detail.**
`shardic_envelope_crypto.py`'s `ALGORITHM_TAG = "x25519-hkdf-sha256-aes256gcm"`
is hardcoded to Curve25519. The broader PIV/GIDS smartcard ecosystem
overwhelmingly supports NIST P-256/P-384/P-521 and RSA, not X25519 --
support for Curve25519 ECDH specifically is uncommon outside a few
products (YubiKey's OpenPGP applet being the concrete, available-today
exception). A deployment targeting generic PIV hardware would need a
second envelope algorithm variant (P-256 ECDH) rather than assuming
arbitrary smartcards interoperate with the existing X25519 format
unmodified -- worth deciding explicitly rather than discovering at
integration time.

## Minimal code change: decomposing `unwrap()`

`unwrap()` today computes the ECDH shared secret and immediately
derives/decrypts in the same function body, which forces every caller
to hand it a raw private key. The fix is a small, additive
decomposition -- not a rewrite -- so a hardware-backed caller can
supply an externally-computed shared secret instead, without
duplicating the HKDF/AES-GCM logic in a second implementation:

```python
# proposed, in shardic_envelope_crypto.py -- additive, existing unwrap()
# keeps working unchanged for every current caller

def parse_envelope(envelope: dict) -> tuple[bytes, bytes, bytes]:
    """Validates alg tag; returns (ephemeral_public_raw, nonce, ciphertext)."""
    if envelope.get("alg") != ALGORITHM_TAG:
        raise EnvelopeError(f"unsupported envelope algorithm: {envelope.get('alg')!r}")
    try:
        return (
            base64.b64decode(envelope["ephemeral_pub"]),
            base64.b64decode(envelope["nonce"]),
            base64.b64decode(envelope["ciphertext"]),
        )
    except (KeyError, ValueError) as e:
        raise EnvelopeError(f"malformed envelope: {e}") from e


def decrypt_with_shared_secret(shared_secret: bytes, nonce: bytes, ciphertext: bytes) -> bytes:
    """The tail of unwrap() that doesn't care where shared_secret came from."""
    aes_key = _derive_key(shared_secret)
    try:
        return AESGCM(aes_key).decrypt(nonce, ciphertext, associated_data=None)
    except InvalidTag as e:
        raise EnvelopeError("decryption failed -- wrong shared secret or tampered envelope") from e


def unwrap(envelope: dict, recipient_private_key_raw: bytes) -> bytes:
    """Unchanged signature and behavior -- now expressed in terms of the two helpers above."""
    ephemeral_public_raw, nonce, ciphertext = parse_envelope(envelope)
    recipient_private_key = X25519PrivateKey.from_private_bytes(recipient_private_key_raw)
    ephemeral_public_key = X25519PublicKey.from_public_bytes(ephemeral_public_raw)
    shared_secret = recipient_private_key.exchange(ephemeral_public_key)
    return decrypt_with_shared_secret(shared_secret, nonce, ciphertext)
```

A hardware-backed trustee client then does:

```python
ephemeral_public_raw, nonce, ciphertext = shardic_envelope_crypto.parse_envelope(envelope)
shared_secret = hardware_backend.ecdh(ephemeral_public_raw)   # on-card ECDH -- PKCS#11
                                                                # C_DeriveKey, or gpg-agent's
                                                                # PKDECRYPT for an OpenPGP card
plaintext = shardic_envelope_crypto.decrypt_with_shared_secret(shared_secret, nonce, ciphertext)
```

X25519 is a standardized primitive (RFC 7748) -- any correct
implementation, whether OpenSSL/`cryptography`, a card's on-chip
Curve25519 support, or a TPM, produces the identical shared secret for
the same keypair and ephemeral point. This interoperates by
construction, not by coincidence.

## Registration: on-device keygen, never import

The keypair **must** be generated on the hardware device itself, never
generated in software and then imported -- importing means the private
key existed in host memory at least once, which defeats the entire
point of this variant. This is a stricter requirement than
`keycloak-credential-lookup.md`'s existing "client-side only" keygen
language, which this variant simply makes literal: client-side now
means the client's own hardware, not merely the client's own process.

**Attestation matters here for the same reason it matters in
[shardware-token-embed-extract.md](shardware-token-embed-extract.md#embed-sequence-at-vault-creation):**
without it, a compromised host can report an arbitrary public key and
claim it came from genuine hardware, and the registry has no way to
tell the difference. FIDO2's standard attestation object, or a PIV
card's attestation certificate feature, both provide exactly this --
recommended as part of registration for this variant, not treated as
optional.

## Recovery: only the ECDH step changes

Everything downstream of the shared secret is byte-for-byte identical
to the existing walkthrough: the trustee still ends up with a plaintext
codeword (or, in the shardic-envelope/shardic-prime path, still derives
and submits an unsealed shard exactly as `submit_unsealed_shard_reply()`
already expects). The hardware only ever touches the ECDH half of one
`unwrap()` call -- it never sees a codeword, an unsealed shard, or the
combiner's session state.

## CLI vs. browser: a real asymmetry, not an oversight

- **CLI/container trustees** get the strong option outright: a PKCS#11-
  accessible smartcard or a TPM can perform genuine on-device ECDH, with
  no browser API limitations in the way.
- **Browser/portable trustees** (`portable-trustee-client.md`) are more
  constrained: WebCrypto's standard surface has no "call my smartcard's
  ECDH" primitive, and routing PKCS#11 through a browser would require
  a native-messaging host -- reintroducing exactly the native-app
  dependency the portable client's web-first design chose to avoid.
  The realistic browser-native option today is FIDO2's `hmac-secret`
  extension gating a software-held, encrypted key (the weaker category
  above), not true on-card ECDH. This asymmetry should be stated
  plainly wherever this option is offered, not smoothed over.

## Open questions / TBD

- Which concrete hardware target to build first -- PIV smartcard via
  PKCS#11, an OpenPGP card via `gpg-agent`, a TPM, or FIDO2
  `hmac-secret` -- is deliberately left unpicked, matching this whole
  design thread's pattern of not choosing one universal answer
  (`LocalUnlockFactor`, the physical-medium table) until a real
  deployment forces the question.
- Attestation verification policy: who curates the set of acceptable
  attestation roots (device vendors, card issuers) is a governance
  question, not a cryptographic one -- mirrors the same open question
  already flagged for the Approver role in `spac-concept.md`.
- Whether custody should be verified only once, at registration, or
  periodically re-attested (e.g. to detect a card swap after
  registration) -- not decided here.
- The second envelope-algorithm variant needed for NIST-curve-only
  smartcards (noted above) has no concrete design yet -- flagged, not
  attempted, in this document.

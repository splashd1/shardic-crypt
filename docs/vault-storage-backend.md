# Combiner vault storage: a pluggable VaultStore interface (v1.0 filesystem backend implemented)

**Status: the filesystem reference implementation described below is
implemented and verified** — `demo/combiner/vault_store.py`
(`VaultStore` Protocol + `FilesystemVaultStore`), wired into
`demo/combiner/app.py`'s `do_create_vault` and a new
`GET /admin/vault/download` route, verified end-to-end against the
real running demo stack (registration → vault create → combiner
restart mid-recovery → threshold-3 recovery → byte-for-byte verify, all
against the `VaultStore`-backed file). SQL/NoSQL backends remain
unimplemented — still a future, config-selected alternate
implementation, not built here.

## Where things stood before this

The combiner already held `.krypt` ciphertext server-side — that
wasn't new scope, just an undesigned corner of what already existed.
`demo/combiner/app.py` used to write it straight to a filesystem path
(`VAULT_OUTDIR`, defaulting to `/data/vault`, a Docker volume) with no
storage abstraction at all: filesystem wasn't a *choice*, it was the
only thing that existed. The design below is what closed that gap.

## Design principle: pluggable interface, filesystem default, no bundled infra

This follows the same shape already used twice elsewhere in this
design set — `CredentialLookup`
([pubkey-envelope-plugin.md](pubkey-envelope-plugin.md#the-credential-lookup-a-pluggable-interface-not-a-database-design))
and `EnvelopeDropPoint`
([envelope-delivery.md](envelope-delivery.md#interface-sketch)) are
both `Protocol`s: shardic defines the interface and ships one
reference implementation, and treats "what actually backs it" as an
integration decision for whoever deploys the plugin.

- **v1.0 ships a filesystem-backed implementation only.** It's what
  already runs today, it's zero new dependency, and it matches this
  project's consistent bias toward a zero-dependency default
  (PBKDF2-default/Argon2-optional in `kdf.py`, no bundled runtime
  infra anywhere else in the repo).
- **SQL/NoSQL backends are a config-selected alternate implementation
  of the same interface**, added as a fast-follow, not something
  shardic bundles or operates itself. Worth designing the interface
  now even though only the filesystem implementation ships in v1.0 —
  the same "config knob from day one so a future change is cheap, not
  a re-architecture" reasoning already used for the operator's OIDC
  issuer config in
  [keycloak-credential-lookup.md](keycloak-credential-lookup.md#the-operator-role).

### Explicitly rejected

- **Bundling a lightweight embedded DB (e.g. SQLite) as the default.**
  Filesystem already *is* the simplest possible backing store for this
  data shape — an opaque ciphertext blob keyed by a vault id. A
  bundled DB adds a dependency without adding capability over what
  plain files already do here.
- **Spinning up a docker-compose DB service by default.** That's
  operational infrastructure shardic shouldn't own or run. Consistent
  with the "no new dependency" constraint already stated in
  [notification-channel-concept.md](notification-channel-concept.md#constraints-already-fixed-by-prior-docs)
  and the offline-first posture already load-bearing in
  [keycloak-credential-lookup.md](keycloak-credential-lookup.md#keeping-the-oauth-dependency-scoped-to-registration-only) —
  the deploying org owns its own infrastructure choices, shardic
  doesn't make that choice for them.

## Interface (implemented)

```python
class VaultStore(Protocol):
    def store(self, vault_id: str, krypt_bytes: bytes) -> None:
        """Persist a .krypt container's raw bytes, keyed by vault_id.
        Raises VaultAlreadyExistsError if a live record already exists
        for vault_id -- storage must not silently overwrite an
        existing vault, mirroring EnvelopeDropPoint.deposit()'s same
        non-overwrite guarantee."""

    def retrieve(self, vault_id: str) -> bytes:
        """Return the stored .krypt bytes for vault_id. Raises
        VaultNotFoundError if none exist."""
```

This is the real interface in `demo/combiner/vault_store.py`, along
with `FilesystemVaultStore` (write-to-temp-then-`os.replace` for
crash-safety) and a `__main__` self-test mirroring the pattern already
used by `gf256_sss.py`/`shardic_envelope_crypto.py`
(`python3 demo/combiner/vault_store.py`).

`delete`/`list` are still deliberately left out — nothing in the
current design calls for either yet (vaults aren't deleted, and
there's currently no multi-vault listing UI), so they're not specified
until an actual caller needs them, per this project's general bias
against speculative interface surface.

## Durability follows from the backend choice, not a separate policy

This interface answers "where does the byte blob live," not "is it
replicated or backed up" — that's deliberate. An org that needs real
durability guarantees picks (or brings) a `VaultStore` implementation
that already provides them (e.g. a replicated Postgres cluster), the
same way choosing a durable filesystem/volume already determines the
default implementation's durability today. This design doesn't need
its own separate replication/backup policy layered on top; durability
is a property of whichever implementation gets selected, not something
this interface has to solve generically.

## Scope note: this doesn't cover the envelope drop point

Pending wrapped envelopes
([envelope-delivery.md](envelope-delivery.md#interface-sketch)) are a
related but distinct data shape — short-lived secrets-in-flight with
"exactly once" redemption semantics, versus a `.krypt` container's
long-lived, read-many ciphertext. `envelope-delivery.md` already flags
its own backing-store choice as a separate open question. This doc
doesn't presume they share an implementation, even though the
structural similarity (pluggable storage, filesystem-simple default)
is worth noticing if that question gets revisited.

## Open questions / TBD

- ~~Exact method signatures~~ — resolved by the implementation above
  (synchronous, `VaultAlreadyExistsError`/`VaultNotFoundError` as
  distinct exception types). Whether `store`/`retrieve` should become
  async for a real DB backend is still open, deferred until a non-
  filesystem implementation is actually built.
- Migration path for moving an existing vault's data from one backend
  implementation to another.
- Whether this interface should also cover other combiner state
  (`STATE["trustee_pubkeys"]`, `state.json`) or stay scoped to just
  `.krypt` bytes — today those live in the same `DATA_DIR` but via
  different mechanisms; unifying them under one interface is a bigger
  scope decision than this doc makes.

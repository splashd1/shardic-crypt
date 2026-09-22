# DLT (blockchain/hashgraph) integration — brainstorm, tabled

> Status: **tabled**. Business-case digression from a web-chat session,
> not designed, not scoped, not committed to. Captured here so it isn't
> lost, per the doc-status convention used elsewhere (`spac-concept.md`,
> `shardware-token*.md`) — this is a fork point for a possible future
> design thread, not a spec.

## Core tension (constrains everything below)

Shardic's core value prop depends on **minimal, local, non-leaking**
metadata — no shard-to-trustee mapping stored anywhere, trial-decryption
instead of an index (`vault_core.py` / the zero-leakage indexing
principle). A DLT is the opposite instinct: persistent, replicated,
often-public record-keeping. The question is not "put shardic on a
ledger" — it's **which specific event layer** benefits from an
immutable multi-party record, without pulling cryptographic material
(shards, codewords, `unlock_value`) into that record. Any future design
in this space should be evaluated against that split first.

## Candidate fits (roughly least → most radical)

1. **Ceremony formation as an auditable event log.** Ceremony formation
   (operator-initiated invite, TTL/decline, backfill) is currently
   centrally orchestrated. A DLT could record *who was invited, who
   declined, when backfill triggered* as tamper-evident audit metadata
   — process metadata, not cryptographic material. Least controversial
   fit; doesn't touch the zero-leakage boundary.

2. **SPAC arm/disarm as a non-repudiable event stream.** The ICD's
   `ArmRequest`/`ArmResponse` (`GRANTED`/`DENIED`/`ERROR`) is a discrete,
   high-stakes event well suited to a permissioned ledger — especially
   relevant for **multi-function SPAC**, where per-function
   accountability ("this trustee set approved arming function X at time
   T") is a legitimate on-chain claim. `unlock_value` itself never
   belongs on-chain (single-use by contract, must zeroize — see ICD
   draft).

3. **Threshold recovery as a smart-contract alternative to the Flask
   combiner.** More radical: a smart contract enforces "D of T
   signatures required" as consensus logic, while actual GF(256) shard
   combination stays off-chain/client-side. Trades "trust the combiner
   operator" for "trust the contract + chain consensus" — a genuine
   architectural alternative worth naming as a comparison point even if
   never built.

4. **Hashgraph vs. blockchain — different business cases, not
   interchangeable vendors.**
   - Hashgraph (aBFT, fast finality, no block latency) fits
     **real-time trustee consensus** — e.g. emergency recovery
     ceremonies where wait-on-confirmation latency matters.
   - Blockchain fits wanting a **public, permissionless audit trail**
     — proving a ceremony happened to a third party who trusts neither
     the operator nor the trustees.

## Business-case angle

Current niche (per patent-landscape assessment) sits between
enterprise HSM/Vault and bare SSS CLI tools. A DLT-anchored audit layer
is a plausible **enterprise differentiator** specifically because
HSM/Vault solutions are typically centrally-trusted-operator models.
"Our ceremony history is independently verifiable by a permissioned
consortium ledger, not just our own logs" is a sellable compliance
story (finance, defense-adjacent, supply-chain custody handoffs) that
neither a bare SSS tool nor a traditional HSM cleanly offers.

## Explicit scope-creep guardrail

Do **not** let this pull GF(256) SSS itself onto a chain — the math
doesn't need consensus, only the ceremony/authorization events around
it do. If a future design pass starts implying on-chain shard storage
or on-chain codeword/`unlock_value` handling, that's a violation of the
zero-leakage principle, not a feature — treat it as a red flag, not a
design choice to weigh.

## Open threads if this gets picked back up

- Which event layer first: ceremony-formation audit log (safest, least
  design work) vs. SPAC arm/disarm event stream (more directly tied to
  the ICD work already in progress)?
- Permissioned vs. permissionless ledger choice depends on who the
  third-party verifier is assumed to be (internal compliance vs.
  external auditor vs. general public) — not yet decided, not yet
  asked.
- Smart-contract-combiner alternative (item 3) is a bigger swing —
  probably belongs in the design whitepaper as a "considered
  alternative" section before any prototyping, if pursued at all.
- No vendor/protocol selection has been discussed (this note is
  capability-level, not implementation-level).

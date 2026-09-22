# shardic-envelope notification channel: concept paper (proposed, unimplemented)

**Status: concept paper, not a settled design.** This is one step
earlier than [pubkey-envelope-plugin.md](pubkey-envelope-plugin.md),
[keycloak-credential-lookup.md](keycloak-credential-lookup.md), and
[envelope-delivery.md](envelope-delivery.md) — those three each commit
to one concrete design. This doc doesn't. It lays out the need, the
realistic options, and what should drive picking among them, so the
actual choice can be made deliberately later rather than defaulting to
"whatever's convenient" when someone finally implements
`envelope-delivery.md`. Nothing here is a recommendation to build any
of this yet.

## The need

`envelope-delivery.md` deliberately scoped itself to the pull
mechanism — an authenticated, single-read drop point — and explicitly
punted on how a trustee learns there's something to pull:

> The "a wrap event happened, go pull your envelope" notification
> channel is deliberately out of scope here... needs a decision, but
> whatever it is should carry no secret itself, only a prompt.

That doc also names a second, distinct notification need in passing,
for a different audience: when an unredeemed drop hits its TTL, "an
operator-visible log/notification" should fire, since it means a
trustee's shard is effectively stranded until someone re-wraps and
re-deposits. These are not the same problem wearing two hats — they
have different recipients, different urgency, and arguably different
channels:

| | Trustee-facing "go check" | Operator-facing "this expired unclaimed" |
|---|---|---|
| Recipient | The trustee | Whoever operates the vault/drop point |
| Fires on | Successful `deposit()` | TTL expiry with `redeemed = False` |
| Urgency | Low-to-medium — trustee should act within the TTL window | Can be a log line, or an active alert if the operator wants SLA-backed follow-up |
| Consequence of missing it | Trustee never pulls, drop expires, shard is stranded | Nobody notices the stranded shard until recovery is actually attempted |

Both need designing. This paper covers both, but they don't have to
share one implementation.

## Constraints already fixed by prior docs

These aren't up for reconsideration here — any option below has to fit
inside them:

- **No secret in the payload.** The notification is a prompt, not a
  delivery mechanism. Confidentiality still rests entirely on the
  drop point + the trustee's private key
  ([envelope-delivery.md](envelope-delivery.md#what-this-does-and-doesnt-protect-against)).
  A notification channel can be low-trust precisely because it never
  carries anything worth stealing.
- **No new dependency at recovery time.** Notification is a
  wrap-time/deposit-time event, not a recovery-time one — it doesn't
  touch the offline-first posture
  [already load-bearing](keycloak-credential-lookup.md#keeping-the-oauth-dependency-scoped-to-registration-only)
  for `vault_recover*.py`.
- **The identity model tracks no contact address.** Per
  [keycloak-credential-lookup.md](keycloak-credential-lookup.md#the-problem-this-solves),
  a trustee is known only by Keycloak `sub` + registered public key.
  Any channel that needs an address (email, SMS, push token) is
  reaching for data that doesn't currently exist anywhere in this
  design — that's not a blocker, but it's a real piece of new scope,
  not a free lookup.

## Options for the trustee-facing channel

None of these are mutually exclusive with the operator-facing channel
below; they're being evaluated independently.

- **Email via a Keycloak profile attribute.** Keycloak already has an
  `email` field on most user records. Cheapest to wire up if the org's
  Keycloak deployment already trusts that field, but it's reaching
  outside the registry/directory split
  [keycloak-credential-lookup.md](keycloak-credential-lookup.md#key-custody-a-separate-registry-not-keycloak-user-attributes)
  drew for exactly this reason — email wasn't in scope as trustee data
  before now. Also the least secure-feeling channel by reputation
  (phishing-adjacent), even though the payload itself carries no
  secret.
- **Push notification to a registered device.** Highest-friction to
  build (needs a mobile app or at least a registered browser push
  subscription, plus a token per trustee), but the best fit if
  hardware-backed key generation
  ([keycloak-credential-lookup.md](keycloak-credential-lookup.md#registration-flow-oidc-authenticated-client-side-key-generation-only))
  already put trustees on a device shardic could plausibly reach.
- **Chat-ops webhook (Slack/Teams/Discord DM or channel post).** Cheap
  if the org already lives in one of these tools and can map a
  trustee's Keycloak `sub` to a chat identity. Weakest privacy
  posture of the options if posted to a shared channel rather than a
  DM — "trustee X has a pending shardic envelope" is metadata that
  probably shouldn't be broadcast org-wide.
- **SMS.** Works with zero assumptions about trustee technical
  sophistication, but needs a phone number (another piece of contact
  data not currently tracked) and a paid delivery provider — real
  operational cost and a third-party dependency for something that's
  otherwise entirely self-hostable.
- **Passive / no push at all — check on next authenticated touch.**
  Instead of proactively notifying, surface "you have a pending
  envelope" the next time the trustee authenticates to *anything*
  already OIDC-backed (e.g. a Keycloak login landing page, or the
  registration tool itself). Zero new infrastructure, zero new contact
  data — but weakest guarantee, since it depends on the trustee logging
  into something else on their own initiative within the TTL window.
- **Generic outbound webhook, operator-supplied.** Rather than shardic
  picking a channel, expose one interface and let the deploying org
  point it at whatever they already run (PagerDuty, an internal
  notification service, etc.). Pushes the channel decision entirely
  out of shardic's scope — consistent with how
  [pubkey-envelope-plugin.md](pubkey-envelope-plugin.md#the-credential-lookup-a-pluggable-interface-not-a-database-design)
  already treats `CredentialLookup` as "an integration decision for
  whoever deploys the plugin."

## Options for the operator-facing channel

Lower-stakes than the trustee-facing side — this is standard
operational alerting, not a new problem shardic invents:

- **Log line only.** Matches the project's overall bias toward
  simplicity, but only useful if someone's actually watching logs.
- **Active alert** (webhook into existing on-call/paging tooling).
  Appropriate if a stranded shard is treated as an operational
  incident rather than a background fact.

## Design-choice drivers

What should actually determine the pick, for a given deployment:

- **Does the org already trust a contact channel for this population?**
  If Keycloak's `email` is already the org's source of truth for
  reaching these specific users, reusing it is cheap. If not, adding
  contact-data tracking is new scope that should be weighed against
  the passive or webhook options, which need none.
- **How much urgency does the TTL actually demand?** A short TTL
  (days) with real consequences for missing it argues for push/SMS
  over passive. A long TTL with low-stakes recovery scenarios may
  make the passive "next login" option good enough.
- **Trustee technical sophistication**, the same axis
  [keycloak-credential-lookup.md](keycloak-credential-lookup.md#registration-flow-oidc-authenticated-client-side-key-generation-only)
  already had to reason about for key generation: a chat-ops webhook
  assumes trustees who live in Slack/Teams; SMS or email assumes
  neither technical fluency nor an existing app; hardware-backed
  trustees may already be reachable via push.
- **Willingness to take a new external dependency.** Email and SMS
  usually mean a third-party delivery provider (deliverability,
  cost, another thing that can be down). The generic-webhook and
  passive options keep shardic's own footprint unchanged and let the
  operator own that tradeoff instead.
- **Metadata sensitivity.** The notification's payload is safe by
  design, but "trustee X has a pending shardic envelope" is itself a
  fact some threat models may not want exposed on a shared channel
  (a public Slack channel, an easily-intercepted SMS). Channels that
  are inherently private to the trustee (DM, push, email) fit a more
  cautious posture than anything broadcast-shaped.

## What this paper deliberately doesn't do

- **Doesn't pick a channel.** That's meant to be a per-deployment
  decision informed by the drivers above, not a default this doc
  hands down.
- **Doesn't sketch a `Protocol`.** Unlike `CredentialLookup` or
  `EnvelopeDropPoint`, the interface shape depends heavily on which
  option gets picked (a webhook sender looks nothing like a passive
  check-on-login hook) — premature to fix an interface before the
  channel decision above is made.
- **Doesn't address the operator-facing alert's backing
  infrastructure** beyond naming the two options — that's ordinary
  ops tooling, not something specific to shardic-envelope.

## Open questions / TBD

- Whether the trustee-facing and operator-facing channels should share
  any implementation (e.g. both routed through one generic webhook
  interface with different event types) or stay fully independent.
- If a contact-data-requiring option is chosen, where that data lives —
  a new field on the key registry from
  [keycloak-credential-lookup.md](keycloak-credential-lookup.md#key-custody-a-separate-registry-not-keycloak-user-attributes),
  or a genuinely separate store, given that doc's stated bias toward
  keeping the registry narrowly scoped.
- Whether notification delivery failure (bounced email, undeliverable
  push) should itself be operator-visible, mirroring the TTL-expiry
  alert — currently unaddressed.
- Retry/escalation policy if the trustee-facing notification doesn't
  produce a redemption before some fraction of the TTL has elapsed
  (e.g. a reminder at 75% of TTL) — not evaluated here at all.

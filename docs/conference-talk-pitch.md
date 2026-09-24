# Conference talk pitch: shardic

**Status: living pitch document.** This is the current CFP-ready
abstract, outline, and pitch material for presenting shardic at
security/cryptography-adjacent conferences. Keep it in sync with
`shardic_white_paper.v4.1.md` if the underlying claims (what's
implemented vs. proposed, the three-level structure) change — this
document borrows its claims from there rather than re-deriving them,
so a drift check when the white paper revs is the main maintenance
cost.

Purpose: this repo's third stated goal (see README's "Why this
project exists") is evangelizing shardic's usefulness, scientific
basis, and technical workflow at cyber-related conferences. This file
is the reusable artifact for that — draft once, adapt per CFP's word
limit and audience.

---

## Elevator pitch (one sentence)

Shardic makes "no single party can decrypt this alone" a mathematical
fact instead of a policy promise — and the same D-of-T mechanism that
recovers a file today is the mechanism that can enforce genuine
human-in-the-loop control over AI-initiated actions tomorrow.

## Working titles

Pick per audience — technical vs. governance-flavored:

- *"Shardic: Threshold Recoverability by Construction, Not by Policy"*
- *"Splitting Trust, Not Just Keys: A Working Threshold Vault, and
  Where It's Headed"*
- *"Who Approved This? Enforcing Multi-Party (and Human-AI) Consent
  With Shamir's Secret Sharing"*

## Abstract (≈220 words, trim to fit a specific CFP)

Conventional encryption is monolithic: whoever holds the key — a
person, a process, a server — has unilateral, permanent control over
the plaintext. Policy can say "no one should decrypt this alone," but
nothing in the cryptography enforces it. Shardic removes that
single point of control from the math itself. A file is encrypted
under a random AES-256-GCM key, which is then split — via Shamir's
Secret Sharing over GF(256) — into T shards distributed to T
independent trustees, with a threshold D set below T. Below that
threshold, the remaining shards carry zero information about the key,
not merely a cost to break. This talk walks through a live
demonstration of the working CLI/GUI implementation — create a vault,
distribute codewords, recover with any D of T — then builds the
underlying Shamir's Secret Sharing construction from geometric first
principles (points determining a polynomial) so the audience leaves
understanding *why* it works, not just that it does. It closes with
where the same primitive generalizes next: shardic protected action
codes (SPAC) for gating any consequential action, not just file
decryption, and — one of its most consequential extensions — a
concrete cryptographic construction for human-AI mutual oversight,
where neither a rogue human nor an unchecked AI system can execute a
high-stakes action alone. Attendees leave with a mental model they can
apply immediately: threshold recoverability as a design primitive, not
a niche cryptographic curiosity.

## Target audience & format fit

- **Audience:** security architects, applied cryptography practitioners,
  DevSecOps/platform engineers evaluating key-custody designs, and
  (for the closing section) anyone tracking AI governance/oversight
  mechanisms.
- **Level:** intermediate — assumes familiarity with symmetric
  encryption and basic key management, not with Shamir's Secret
  Sharing specifically (the talk builds it from scratch).
- **Format:** works at 25 min (demo + core mechanism only, drop the
  SPAC/human-AI section to a mention), 45 min (full outline below), or
  60 min (add live audience Q&A on threshold-signature alternatives —
  FROST, HSM multisig — and where shardic fits/doesn't).
- **Also fits:** a workshop/tutorial slot (hands-on: attendees run
  `vault_create.py`/`vault_recover.py` themselves) if the venue
  supports it — the CLI has no server dependency, so a laptop and
  Python 3 is the whole setup.

## Key takeaways (for a CFP's "attendees will learn" field)

1. How Shamir's Secret Sharing turns "split a secret" from an
   all-or-nothing chunking problem into a genuine D-of-T threshold —
   and why the naive chunk/XOR approaches don't get you there.
2. A concrete, running reference implementation of threshold-recoverable
   file encryption — not just the theory — including the deliberate
   design choice to leak zero shard-to-trustee mapping information.
3. Where the same primitive generalizes: gating arbitrary
   consequential actions (SPAC), and enforcing mutual human-AI
   oversight as AI systems take on more initiation authority over
   high-stakes operations.

## Speaker outline (45-minute baseline)

| Time | Segment |
|---|---|
| 0:00–0:04 | **Hook.** The single-point-of-control problem, framed via a real incident class (insider risk / one-compromised-credential breach), not abstractly. |
| 0:04–0:10 | **Live demo.** Create a vault with `T=5`, `D=3`; show the `.krypt` file; recover with 3 of 5 codewords; show recovery *fails* with 2. Real terminal, not slides. |
| 0:10–0:22 | **The mechanism, built from first principles.** Geometric intuition (points determine a polynomial) → the precise construction (`f(x) = S + a₁x + ... `) → why fewer than D points leave the secret fully undetermined, not just hard to guess → GF(256) in one slide (why bytes, why this field, briefly). Mirrors `docs/sss_explained_for_shardic.md`. |
| 0:22–0:28 | **What's actually implemented vs. proposed**, stated plainly (this project is explicit about that line): Level 1 (base scheme, shardic-prime) and Level 2 (shardic-envelope, ceremony formation) are running code; Level 3 — SPAC, hardware-bound Fielded Prime Elements, and the human-AI oversight construction — is a design proposal built on the same unmodified math. |
| 0:28–0:38 | **Where this generalizes: SPAC and human-AI mutual oversight.** The reframe from "protected file" to "protected action." Walk one vignette end-to-end (a treasury disbursement or safety-interlock release) then the flagship case: an AI-initiated action requiring independent human sign-off, and — symmetrically — a human-initiated action requiring independent AI validation, as the *same* D-of-T rule pointed in either direction by trustee-class assignment. |
| 0:38–0:43 | **Where it doesn't fit** (credibility matters more than hype): not for frequent/live authorization, not a substitute for threshold-signature schemes like FROST or HSM-backed multisig when you need key rotation and online quorum. |
| 0:43–0:45 | **Close + call to action.** Repo link, README's use-case catalog, how to reach the project for integration conversations. |

## Suggested venues (adjust per current CFP calendar)

Security-generalist and applied-crypto tracks are the best fit; AI-governance-adjacent venues are the right fit specifically for the human-AI oversight closing section:

- Regional/community: BSides chapters (broad security audience, receptive to live demos).
- DEF CON villages (e.g. Crypto & Privacy Village) — technical depth audience for the SSS build-up.
- Applied cryptography / vendor-neutral tracks at larger conferences (e.g. RSA Conference, Black Hat Arsenal for the tool demo specifically).
- AI safety/governance tracks, for the human-AI mutual-oversight section as a standalone lightning talk or panel contribution.

## Supporting materials to bring/link

- This repo + README (working code, install-and-run).
- `docs/shardic_white_paper.v4.1.md` / `.html` / `.docx` — full paper for attendees who want the complete argument across all three levels of implementation.
- `docs/shardic_deck_v4_1_conference_talk.pptx` — the talk deck for this outline (18 slides, timed speaker notes keyed to the 45-minute segments above); fill in the speaker/venue placeholder on the title slide. For a 25-minute slot, drop the SPAC/human-AI slides to a single mention.
- `docs/shardic_deck_v4_1_overview.pptx` and `docs/shardic_deck_v4_1_foundations.pptx` — shorter demo and deeper cryptography decks, useful as backup slides or leave-behinds.
- `docs/sss_explained_for_shardic.md` — the standalone SSS build-up this talk's middle section mirrors.
- `docs/public-education-explainer.md` — the non-technical version, useful as a leave-behind/blog cross-post for attendees who want to send it to a non-cryptographer colleague.

## Speaker bio (template — fill in before submitting)

> [Name] works on shardic, an open threshold-recoverable encryption
> project applying Shamir's Secret Sharing to eliminate single points
> of control in key custody, with an active research thread on
> extending the same mechanism to enforce mutual human-AI oversight
> over consequential automated actions.

## Open items

- No talk has been submitted or delivered yet — this is pitch/prep
  material, not a record of a past talk. Update this section once a
  CFP is submitted (venue, date, acceptance status) so this doesn't
  silently drift into looking like a track record that doesn't exist.
- Demo environment for a live talk (laptop + fallback recorded demo in
  case of venue Wi-Fi/AV issues) isn't built yet — worth a
  `demo/conference-demo-script.md` if a submission gets accepted.

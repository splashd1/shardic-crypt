# Review Feedback: `shardic_white_paper.v3.2.md`

Review of the user's own edit pass on `docs/shardic_white_paper.v3.2.md` (diffed
against `v3.1.md`). Covers accuracy, formatting, and readability throughout;
the abstract was also directly edited per the author's request (see the end
of this doc for what changed there).

## Top finding: Section 11 has vanished

The abstract (as of v3.1) said: *"Section 11 names, without resolving, the
licensing and IP-ownership decision that governs all of it, and flags one
time-sensitive consequence of this whitepaper's own distribution."*

But v3.2.md has no Section 11 — it jumps straight from `# 10. Path to Proof
of Concept` to `# Appendix A`. Section 11 ("Intellectual Property and
Licensing Posture") exists in `v3.md`, `v3.1.md`, and `v3.1jd.md` — it was
present through the last file and dropped specifically in the v3.1→v3.2
pass. It wasn't a stub either — it had real content: no license chosen, no
patent filed, and a specific warning that every public distribution of this
whitepaper before a patent filing could affect priority/novelty later. That
reads like an accidental loss during editing rather than a deliberate cut,
since nothing else in the doc absorbed it and the abstract still promised it.

**Resolution:** author confirmed the removal was intentional. The abstract's
closing paragraph has been edited to stop referencing Section 11 (see
"Abstract edits applied" below). The body still has no Section 11 — restore
it from `v3.1.md` if that turns out to be wanted after all.

## Section-by-section issues

**Reader Hints (¶29):** "Next there design proposal descriptions" is missing
words/verb ("Next, there are design proposal descriptions..."); stray space
before the final period.

**§1.2:** Good — this is the earlier reworded passage and it reads
accurately. Minor: the bullet list is interrupted by two non-bulleted aside
paragraphs ("Operational assumption:..." and "A recovery can produce...")
that break the visual rhythm — consider bolding them as labeled callouts or
folding them under the bullet they qualify.

**§1.4 (104):** "Cutting the 32-byte DEK into four 8-byte chunks and handing
one chunk to each of four trustees — or ... XOR-splitting ... *also create*
multi-entity protection" — subject/verb mismatch, should be "creates" (or
recast as "Both approaches also create..."). Also (112): "A threshold secret
shard doesn't work that way" — reads oddly; likely a leftover from the
share→shard mechanical rename and should probably be "a threshold scheme" or
"a threshold-sharing construction," not "a shard."

**§1.5 (118):** "While earlier discussion talks of the protected value as a
file... disk; That framing can be abstracted..." — the sentence never
resolves its "While" clause, and the semicolon+capital "That" is a
punctuation slip. Needs a rewrite for grammar, not just punctuation.

**§2.1 (195):** "For the initial protype utility a set of code-words were
generated..." — typo ("protype"→"prototype") and subject/verb ("a set...
were"→"was," or "code-words were generated"). This paragraph's register is
noticeably rougher than the surrounding prose — reads like a first-draft
insertion that needs a polish pass.

**§3.2 (247):** The added quantum-computing aside is a genuinely good point
(SSS's info-theoretic guarantee is unaffected by quantum computers, unlike
AES/RSA), but it's glued on with `--` instead of matching the doc's em-dash
style, and the clause structure is choppy. Worth smoothing rather than
cutting.

**§3.4 (273):** "(Note: If need be, the mechanism could be modded to support
65K trustees with little system impact)" — this understates the lift.
Scaling past 255 trustees requires a field change (GF(2¹⁶) or a prime
field), new EXP/LOG tables, and processing the secret in 16-bit words — the
*math* generalizes cleanly, but "little system impact" oversells it,
especially since §7.3 elsewhere flags `.krypt` metadata size scaling
linearly with T as its own open concern at large T. Suggest softening to
something like "the underlying construction generalizes to a larger field
without new cryptographic risk, though it isn't a drop-in change."

**§3.7 (316):** "§3.6 raises two questions that a follow-on design prototype
to define the shardic 'ceremony' --essentially a lifecycle process, answered
with running code..." — this sentence doesn't parse; looks like a rewrite
that lost a clause. **§4.1 (348):** "...into the operational run-time
environment--whether code programmable logic" — same issue, likely meant
"whether code or programmable logic."

**§4 intro (340):** "there are no practical barriers to its implementation"
— this directly undercuts the paper's own §7.3 (open items: LocalUnlockFactor
category, hardware target, extraction-grant wire format all undecided) and
§9's TRL-2 rating for the SPAC core. A careful reader (or a funder doing
diligence) will catch the contradiction. Suggest narrowing to "no barriers
intrinsic to the cryptography itself" — the practical barriers are
hardware/integration work, which the rest of the paper is honest about
elsewhere.

**§4.6 (420, 435):** Two real breaks: "If the SPAC in context of system
design is non-bypassable, this is a reliable enforcement." is circular (says
nothing beyond restating itself) — consider cutting or replacing with
something substantive. And "the upshot is that SPAC needs to be integrated
into secure design practice to protect enforcing the execution pipeline's
only workable path is the SPAC" doesn't parse at all — needs a rewrite,
likely something like "...so that the ceremony is the execution pipeline's
only workable path."

**§5 intro (450):** "§5.1 is moot by default, as the main source for SEK's is
known good entropy source" has a grammar problem (apostrophe-plural "SEK's,"
missing article) but also a *content* problem: calling §5.1 "moot" undersells
it given Appendix B spends ~1,000 words justifying the codeword opt-out's
security. Suggest: "§5.1's key-length concern is moot for SPAC's default
DRBG-sourced key; the codeword opt-out remains available and is examined on
its own terms in Appendix B."

**§5.3/§6.4/elsewhere:** Recurring apostrophe-on-plural typos: "SEK's,"
"COA's" should be "SEKs," "COAs" (plural, not possessive). Worth a global
find-check rather than fixing one at a time.

**§6 heading (521) vs abstract/reader-hints:** Still says "Notional Missions
and Ceremony Lifecycle," while the abstract and reader-hints frame this
section as "representative scenarios/vignettes." This is the mismatch the
last editing pass flagged and left open — still open.

**§6.1/6.2 (533, 568):** `#### As-is baseline, to be improved by SPAC: ####`
uses closed-ATX heading syntax found nowhere else in the document, and isn't
used in Vignettes C/D (which use a bold "Notional design." lead-in instead)
— inconsistent both in style and between vignettes. Recommend matching one
convention across all four.

**§6.3 (525, 601):** Two semicolon-then-capital punctuation errors ("core;
Numeric trustee counts," "shardic; It's a concept") — same slip as §1.5,
likely a repeated find/replace artifact. Also line 525's "basically, 'Here's
what you can do under the SPAC umbrella'" is noticeably more colloquial than
the paper's register elsewhere — sticks out.

**§5.5 (488):** "extended here encompass SPAC functionality" — missing "to."

## A real content gap (also the graphics answer)

Sections **6.3 and 6.5** both have figure *captions* ("Figure 6.3.
Trustee-attested network-path pattern..." / "Figure 6.5. Hybrid human-and-AI
policy gates...") but **no actual image** — every other section with a
caption (§1.4, §1.6, §3.1–3.5, §3.7) has a real `![]()` embed in
`docs/media/`; these two don't.

Worse: the **Footnotes section** references specifics that appear nowhere in
the running text or in any embedded figure — "Tier 2 sub-threshold gates,"
"Tier 3 of Figure 6.5," "any 2 of 4 human trustees," "the combined receipt
set." These read like annotations written for a diagram that never got
built — right now they're orphaned, sourcing detail (D_H=2-of-4, a 3-tier
gate structure) that doesn't exist anywhere else in §6.5's prose.

**Suggestion:** these two are the best candidates for new diagrams, and
building them would also resolve the orphaned-footnote problem by giving
those details somewhere to actually live:

- A **Figure 6.3** receipt-chain diagram: trustee nodes in sequence, each
  validating a signed predecessor receipt before adding its own, receiver
  verifying the full chain.
- A **Figure 6.5** dual-gate diagram: the AI-evaluator gate and the
  human-trustee-threshold gate as separate boxes feeding an AND gate, with
  the tiers the footnotes already reference (Tier 1 human/AI sub-gates →
  Tier 2 sub-threshold checks → Tier 3 combined reconstruction) actually
  labeled.

## Readability, lighter touch

- The doc mixes curly quotes (§1.1) and straight quotes (most everywhere
  else) — cosmetic, but worth a pass before this goes external.
- Several paragraphs (e.g., the §1.6 item list) carry hard line-wraps
  mid-sentence from what looks like a word-processor paste — invisible in
  rendered markdown, just flagging in case of raw-text diffing.

## Abstract edits applied

Per the author's request, the abstract received direct editing (the only
section edited directly as part of this review):

1. **Removed the Section 11 reference** from the closing paragraph. It now
   ends the section walkthrough at Section 10 ("closes with what that means
   for funding...") and moves straight to the Appendices, matching the body
   as it currently stands.
2. **Fixed a dangling modifier** in the NEAT/vignette paragraph: "§6.4 then
   states this paper's governing claim directly; Vignette D (§6.5) —
   hybrid human-and-AI policy gates — immediately follows, walking it
   through a full lifecycle" now correctly attributes the "walks it
   through" action to Vignette D rather than to §6.4 itself.

Everything else above is left for the author's own pass.

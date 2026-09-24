# What Is Shardic? A Plain-Language Introduction

**Status: public education material.** Written for readers with no
cryptography background — a colleague, a policy stakeholder, a
conference attendee deciding whether to sit in on a deeper talk. No
code, no formulas beyond one you already know from school algebra.
For the math in full, see `docs/sss_explained_for_shardic.md`; for the
line-by-line implementation, see `docs/shardic-cryptographic-path.md`;
for the complete treatment across all three levels of
implementation, see `docs/shardic_white_paper.v4.1.md`. This document doesn't replace any
of those — it's the on-ramp to them.

---

## The problem: one key, one point of failure

Almost all encryption in use today works the same way underneath:
there's a key, and whoever has it can unlock the data. Sometimes
that's a person; sometimes it's a piece of software running on a
server; sometimes it's a hardware device. It doesn't matter how the
key is stored — in someone's head, in a file, in a specialized secure
chip — the shape of the trust is identical: **one party, complete and
permanent control.**

Most of the time that's fine. It's not fine for the things
organizations worry about most: a root certificate authority's private
key, the master key behind a cryptocurrency treasury, a database
credential that unlocks every customer's records, an override code for
a piece of critical infrastructure. For those, "whoever holds the key
has total control" isn't just a technical fact — it's a risk. A single
compromised laptop, a single coerced employee, a single rogue insider,
and the whole thing is exposed. Policies try to compensate — "two
people must approve," "no one person should have unsupervised access"
— but a policy is a promise about behavior, not a property of the
system. If the technology doesn't actually require two people, a
sufficiently motivated or careless person can route around the rule.

**Shardic's premise:** build the requirement into the cryptography
itself, so it isn't a promise anyone could break — it's a mathematical
fact about what the ciphertext requires.

## The idea: split the secret, not just the access

Here's the intuitive version, no math yet. Imagine instead of one key,
you generate several "shards" and give one to each of several trusted
people — call them trustees. The system is built so that:

- Any **enough** of them, working together, can unlock the data.
- **Fewer than enough**, even if they compare notes and pool
  everything they have, learn *nothing at all* about the secret — not
  a partial answer, not a shortcut, not even a hint about which
  answers are more likely.

That second property is the hard part, and it's where most people's
first instinct goes wrong. If you just cut a password into pieces —
the first half to Alice, the second half to Bob — that's not a
threshold scheme, it's an all-or-nothing scheme: you need *every*
piece, and if one person disappears, the secret is gone forever
permanently. What shardic actually uses is a much older and cleverer
piece of mathematics that has neither of those flaws.

## Why it actually works: a fact from algebra you already know

You learned in school that **two points determine a line.** Give
someone one point on a graph, and they have no idea where the line
crosses the vertical axis — infinitely many different lines pass
through that single point, heading off in every direction, crossing
the axis anywhere at all. But give two people one point each, and
together they can draw the *one* line that passes through both — and
read off exactly where it crosses the axis.

That's the entire trick, generalized. Hide the secret as the point
where a curve crosses the axis. Hand out points *on* that curve, one
per trustee. One point (or any number below the threshold) leaves
every possible secret equally plausible — the curve simply isn't
pinned down yet. Enough points, and there's exactly one curve that
fits them all, so the crossing point — the secret — falls out exactly.
Need a higher threshold? Use a curve that takes more points to pin
down (a parabola needs three, not two), and the same logic scales to
"any 5 of 9," "any 10 of 15," or whatever a given situation calls for.

This was published by cryptographer Adi Shamir in 1979 — it's called
**Shamir's Secret Sharing**, and it's not a novel or speculative idea;
it's decades-old, thoroughly studied mathematics. Shardic's
contribution isn't inventing new cryptography — it's building a real,
usable system around this primitive: encrypting a file with a modern
cipher (AES-256-GCM), generating a random key for that cipher,
splitting *that key* using Shamir's method, and handing trustees
human-usable "codewords" instead of raw mathematical points. A
deliberate extra design choice — the system never records which
codeword unlocks which shard — means even someone who captured several
trustees' codewords at once learns nothing about who holds the rest.

## What exists today, and what's next

This isn't a thought experiment. The core system — encrypt a file,
split the key, distribute codewords, recover with any qualifying
subset of trustees — is a working command-line tool and desktop
application anyone can run today (see the project README). That's
goal one of this project: make the utility real and demonstrable, not
just described.

Goal two is this document and its companions: sharing the underlying
foundation openly enough that other engineers and organizations can
evaluate it, critique it, and build on it — as a piece of a larger
**multi-entity security capability**, where "multi-entity" might mean
multiple people, multiple organizations, or, increasingly, a mix of
people and AI systems. That last case is where the project's research
is currently headed: as AI systems take on more responsibility for
initiating consequential actions — moving money, changing
infrastructure, executing decisions — the same "any D of T must
independently agree" mechanism can require a human check on an
AI-initiated action, and, just as importantly, an AI check on a
rogue or coerced human-initiated one. Neither direction is a policy
layered on top of software; both are the identical threshold guarantee
already described above, aimed at whichever party shouldn't be able to
act alone. That extension is a documented design proposal, not yet
shipped — the project is careful to keep that distinction visible
rather than blur "built" and "planned" together.

Goal three is talking about all of this in public — at conferences,
in writing, wherever people making real decisions about key custody
and AI oversight are paying attention — because "threshold
recoverability by construction" is more useful the more people
recognize it as an available option rather than treating single-key
custody as the only way encryption works.

## Where to go deeper

- **Want the math, precisely?** `docs/sss_explained_for_shardic.md`
  builds the full Shamir's Secret Sharing construction, including the
  finite-field arithmetic shardic actually uses.
- **Want to run it yourself?** The project README has install and
  usage instructions for the CLI and GUI.
- **Want the full case across all three levels of implementation,
  including the human-AI oversight design in detail?**
  `docs/shardic_white_paper.v4.1.md`.
- **Want the conference-length version of this pitch?**
  `docs/conference-talk-pitch.md`.
- **Want it as slides?** `docs/shardic_deck_v4_1_foundations.pptx`
  walks the same cryptographic foundation step by step, and
  `docs/shardic_deck_v4_1_overview.pptx` is the short version with a
  live demo.

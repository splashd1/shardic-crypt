"""Deck 3 of the v4.1 set — goal 3: evangelism. Conference talk deck following the
45-minute speaker outline in docs/conference-talk-pitch.md, with timed speaker notes."""
import sys
sys.path.insert(0, sys.path[0])
from deckkit import *

d = Deck("Conference Talk  ·  v4.1")

# 1 — title
s = d.slide(dark=True, notes="[0:00] Title. Introduce yourself in one sentence. Promise: a live demo, the math from first principles, and where it goes next — including human-AI oversight.")
text(s, 0.9, 1.1, 10, 0.4, "CONFERENCE TALK  ·  45 MINUTES", 12, GOLD, bold=True, spacing=120)
text(s, 0.9, 1.75, 11.5, 2.0, "Splitting Trust, Not Just Keys", 54, WHITE, bold=True)
text(s, 0.9, 2.85, 11.5, 1.0, "Threshold recoverability by construction, not by policy", 26, ICE)
for i, n in enumerate(["users", "tree", "shield"]):
    icon(s, 0.9 + i * 0.85, 4.4, n, 0.62, NAVY)
text(s, 0.9, 5.7, 10, 0.4, "[Speaker name]  ·  [Venue, date]", 16, SOFT)
text(s, 0.9, 6.2, 10, 0.4, "github.com/splashd1/shardic", 13, SOFT)

# 2 — hook
s = d.slide(eyebrow="The hook", title="It only took one",
            notes="[0:00–0:04] Frame via a real incident class — insider risk, one compromised credential — not abstractly. Pick a recent public example suited to the audience. Point: every one of these had policy saying 'no one should do this alone.' Nothing in the crypto enforced it.")
stat(s, 0.6, 1.8, 5.2, "1", "compromised credential, coerced admin, or rogue insider — that's all a conventional key-custody design needs to fail.", DEEP, MUTED, 120)
for i, (ic, h, b) in enumerate([("usershield", "Insider", "Trusted, authorized, acting alone."),
                                ("key", "Credential theft", "One account, full access."),
                                ("warn", "Coercion", "One person under pressure.")]):
    card(s, 6.6, 1.7 + i * 1.62, 6.1, 1.42, None, None)
    icon(s, 6.9, 1.7 + i * 1.62 + 0.4, ic, 0.62)
    text(s, 7.8, 1.7 + i * 1.62 + 0.3, 4.6, 0.4, h, 17, WHITE, bold=True)
    text(s, 7.8, 1.7 + i * 1.62 + 0.75, 4.6, 0.5, b, 14, ICE)
text(s, 0.6, 5.7, 5.6, 0.8, "Policy said \"no one does this alone.\" Nothing in the cryptography agreed.", 16, MUTED, italic=True)

# 3 — thesis
s = d.slide(dark=True, notes="The thesis in one slide. Pause here.")
text(s, 0.9, 1.3, 11.5, 0.4, "THE THESIS", 12, GOLD, bold=True, spacing=120)
text(s, 0.9, 2.0, 11.5, 2.2, "Make \"no single party can decrypt this alone\" a mathematical fact — not a policy promise.", 40, WHITE, bold=True, line=1.05)
text(s, 0.9, 4.6, 11.0, 1.2, "Encrypt once. Split the key into T shards. Any D recover it. Fewer than D hold zero information about it.", 20, ICE)

# 4 — live demo
s = d.slide(eyebrow="Live demo", title="Create 3-of-5. Recover with 3. Fail with 2.",
            notes="[0:04–0:10] Switch to a real terminal — not slides. Create T=5, D=3 on demo/sample-secret; show the single .krypt file; recover with three codewords in shuffled order; show a mistyped codeword being rejected; show that two codewords never produce output. Finish with diff -r. Fallback: recorded run if venue AV fails.")
code(s, 0.6, 1.7, 7.4, 4.8, [
    "$ python3 vault_create.py --input demo/sample-secret \\",
    "      --trustees 5 --threshold 3 --outdir ./v",
    "[*] Split DEK into 5 shards, threshold 3",
    "[*] Wrote vault container: pzzsrzg30y9z0pwv.krypt",
    "",
    "$ python3 vault_recover.py v/*.krypt --outdir ./r \\",
    "      --word <t1> --word <t3> --word <t5>",
    "  [+] Codeword accepted (1/3).",
    "  [+] Codeword accepted (2/3).",
    "  [+] Codeword accepted (3/3).",
    "[*] Success.",
    "",
    "$ diff -r demo/sample-secret r/sample-secret"], 13)
for i, (ic, h, b) in enumerate([("db", "One file", "Show the .krypt — no trustee map inside."),
                                ("check", "Any three, any order", "Shuffle the codewords on purpose."),
                                ("lock", "Wrong or too few", "Rejected by the auth tag; nothing written.")]):
    icon(s, 8.4, 1.8 + i * 1.6, ic, 0.56)
    text(s, 9.2, 1.77 + i * 1.6, 3.5, 0.4, h, 16, DEEP, bold=True)
    text(s, 9.2, 2.17 + i * 1.6, 3.5, 0.8, b, 13.5, MUTED)

# 5 — naive split
s = d.slide(eyebrow="First principles · 1", title="The obvious answer is wrong",
            notes="[0:10] Ask the room: how would you split a key among five people? Most will say chunks or XOR. Both are all-or-nothing — you can't ask for 'any 3 of 5'.")
card(s, 0.6, 1.7, 5.95, 3.1, "Chunks or XOR shares", ["Hide the key from anyone short of **all** pieces", "Reconstruction needs **every** piece", "Lose one trustee → key gone forever"], ic="cubes", fill=BROWN, body_size=15)
card(s, 6.75, 1.7, 5.95, 3.1, "What we want", ["**Any D of T** reconstruct", "**Fewer than D** learn nothing", "Lose up to **T − D** and still recover"], ic="check", body_size=15)
callout(s, 0.6, 5.1, 12.1, 1.2, "That's a threshold scheme — and Adi Shamir solved it in 1979 with one fact from high-school algebra.", 17)

# 6 — geometry
s = d.slide(eyebrow="First principles · 2", title="Two points fix a line",
            notes="[0:12] The secret is where the line crosses the axis. One point: infinitely many lines, every secret possible. Two points: one line, one crossing. For D = 3, a parabola. For D, a degree D-1 curve.")
picture(s, "sss-geometric-intuition.png", 0.8, 1.9, w=7.2)
text(s, 8.5, 1.8, 4.2, 4.2, [
    "Secret = where the line **crosses the axis**.",
    "**One point:** infinitely many lines. Every secret equally possible.",
    "**Two points:** exactly one line, one crossing.",
    "**D points** fix a curve of degree D − 1."], 17, MUTED, gap=14)

# 7 — the construction
s = d.slide(eyebrow="First principles · 3", title="Now make it precise",
            notes="[0:15] Constant term is the secret; shards are points; Lagrange interpolation at x = 0 recovers it. Mirrors docs/sss_explained_for_shardic.md.")
code(s, 0.6, 1.8, 7.3, 2.4, [
    "f(x) = S + a₁x + … + a₍D−1₎x^(D−1)",
    "",
    "f(0)    = S            # the secret",
    "shard_i = (i, f(i))    # one per trustee"], 17)
callout(s, 0.6, 4.5, 7.3, 1.6, "Any D shards → **Lagrange interpolation** → evaluate at x = 0 → S.", 17)
for i, (h, b) in enumerate([("Random coefficients", "a₁ … a₍D−1₎ drawn uniformly at random"),
                            ("T distinct x-values", "1 through T — never 0, that's the secret"),
                            ("Per byte of the DEK", "32 independent polynomials over GF(256)")]):
    badge(s, 8.4, 1.85 + i * 1.45, str(i + 1), 0.5, GOLD, DEEP, 16)
    text(s, 9.1, 1.83 + i * 1.45, 3.6, 0.4, h, 16, DEEP, bold=True)
    text(s, 9.1, 2.21 + i * 1.45, 3.6, 0.8, b, 14, MUTED)

# 8 — zero information
s = d.slide(dark=True, notes="[0:18] The key slide. Not 'hard to break' — nothing to break. Relevant to the post-quantum conversation: no computational assumption to erode.")
text(s, 0.9, 1.0, 11.5, 0.4, "FIRST PRINCIPLES · 4", 12, GOLD, bold=True, spacing=120)
text(s, 0.9, 1.6, 11.5, 1.8, "0 bits", 110, GOLD, bold=True)
text(s, 0.9, 3.55, 11.2, 1.0, "is what D − 1 shards reveal about the secret. Every possible value fits them equally well.", 24, WHITE)
text(s, 0.9, 4.75, 11.2, 1.3, "No partial credit. No \"getting warmer.\" No computational assumption for a quantum computer to erode — the information simply isn't there.", 18, ICE)

# 9 — GF(256)
s = d.slide(eyebrow="First principles · 5", title="Why GF(256), in one slide",
            notes="[0:20] Reals bring fractions and rounding that corrupt the secret. GF(256): exact, one element per byte, AES's own field. The side effect: at most 255 shards — an operational ceiling that real deployments never approach.")
picture(s, "gf256-byte-as-polynomial.png", 0.8, 1.9, w=6.5)
for i, (big, small) in enumerate([("1 byte", "= one field element. Exact arithmetic, no rounding."),
                                  ("0x11B", "AES's own reduction polynomial, generator 3."),
                                  ("255", "shards max — 0 is reserved for the secret.")]):
    text(s, 8.0, 1.75 + i * 1.55, 4.7, 0.7, big, 30, DEEP, bold=True)
    text(s, 8.0, 2.38 + i * 1.55, 4.7, 0.6, small, 14, MUTED)

# 10 — implemented vs proposed
s = d.slide(eyebrow="Implemented vs. proposed", title="Where the line is — stated plainly",
            notes="[0:22–0:28] Credibility: be explicit. Levels 1 and 2 are running code. Level 3 is a design proposal built on the same unmodified math.")
for i, (tag, fill, h, b) in enumerate([
        ("Running code", GREEN, "Level 1 · Personal utility", ["CLI + GUI, no server", "Codewords + one .krypt file", "shardic-prime mandatory trustee"]),
        ("Running code", GREEN, "Level 2 · Shardic ceremony", ["Public-key-wrapped delivery", "Keycloak-backed trustee selection", "Automatic backfill, single-read drop"]),
        ("Design proposal", GOLD, "Level 3 · SPAC", ["Gate any consequential action", "Bound to one Fielded Prime Element", "Human-AI mutual oversight"])]):
    x = 0.6 + i * 4.1
    card(s, x, 1.7, 3.85, 3.6, None, None)
    pill(s, x + 0.3, 1.98, tag, fill)
    text(s, x + 0.3, 2.42, 3.3, 0.45, h, 17, WHITE, bold=True)
    text(s, x + 0.3, 2.95, 3.3, 2.2, b, 14, ICE, bullets=True, gap=6)
callout(s, 0.6, 5.6, 12.1, 0.9, "Each level reuses the one below **unchanged**. Level 3 adds no new cryptography.", 16)

# 11 — data to capability
s = d.slide(eyebrow="Where it generalizes", title="From protected file to protected action",
            notes="[0:28] The plaintext never had to be a file. A SPAC is any enabling value: a signing key, a release-enable code. The Fielded Prime Element reuses shardic-prime's mask so a copied CT SPAC plus a legitimate quorum still fails on the wrong hardware. Precedent: Permissive Action Links, Two-Person Integrity.")
card(s, 0.6, 1.7, 3.85, 3.5, "PT SPAC → CT SPAC", "Any enabling value — a signing credential, a release-enable code — encrypted and split exactly like a file's key.", ic="lock", body_size=14)
card(s, 4.7, 1.7, 3.85, 3.5, "Fielded Prime Element", "A hardware-sealed secret takes the prime trustee's slot. Copy the ciphertext elsewhere and a full quorum still fails.", ic="shield", body_size=14)
card(s, 8.8, 1.7, 3.9, 3.5, "Old idea, new math", "Permissive Action Links and Two-Person Integrity, enforced by the math instead of procedure.", ic="bank", body_size=14)
code(s, 0.6, 5.45, 12.1, 1.15, [
    "DEK     = reconstruct_secret_with_prime(mask, pool_shards)   # unmodified",
    "CT_SPAC = AES-256-GCM(PT_SPAC, DEK)                          # unmodified"], 14)

# 12 — vignette
s = d.slide(eyebrow="One vignette, end to end", title="A high-value treasury wire, start to finish",
            notes="Walk the five stages. Contrast with the as-is: two web-app approvals that one compromised admin or two coerced officers can fake. Here, three of five officers plus the appliance's own hardware plus an on-site key-switch — and the controller's commitment is checked at arming.")
for i, (h, b) in enumerate([("Approve", "Controller validates the signing key and signs a commitment."),
                            ("Emplace", "Wrap as CT SPAC; split across 5 officers + the HSM appliance."),
                            ("Operate", "Appliance holds only ciphertext — indefinitely."),
                            ("Convene", "3 of 5 respond; compliance authorizes; custodian turns the key."),
                            ("Arm", "DEK rebuilds, integrity check passes, wire signs, secrets zeroized.")]):
    x = 0.6 + i * 2.47
    badge(s, x + 0.85, 1.75, str(i + 1), 0.62, GOLD, DEEP, 20)
    rect(s, x, 2.6, 2.27, 2.1, NAVY)
    text(s, x + 0.22, 2.82, 1.85, 0.4, h, 17, WHITE, bold=True)
    text(s, x + 0.22, 3.3, 1.85, 1.7, b, 13, ICE)
rect(s, 0.6, 5.0, 5.95, 1.2, "F6ECD2", radius=0.06)
text(s, 0.9, 5.0, 5.4, 1.2, "**As-is:** two clicks in a web app. One hijacked admin can fake both.", 14.5, BROWN, anchor="m")
rect(s, 6.75, 5.0, 5.95, 1.2, "DFF3E6", radius=0.06)
text(s, 7.05, 5.0, 5.4, 1.2, "**shardic-SPAC:** three genuine shards, this appliance, this key-switch — or nothing.", 14.5, "1D5B35", anchor="m")

# 13 — human-AI
s = d.slide(eyebrow="The flagship case", title="Human-AI mutual oversight — one rule, both directions",
            notes="[0:32] The same D-of-T rule, pointed either way by trustee-class assignment. AI-initiated action needs independent human sign-off — no prompt or internal state rebuilds a key that doesn't exist. Human-initiated action needs an independent AI evaluator's attestation against allow-listed criteria — no seniority or urgency talks it out of failing closed.")
card(s, 0.6, 1.7, 5.95, 3.4, "Humans gate the AI", "An AI proposes a consequential action. It can't execute on its own confidence or speed: below the human threshold, the key **doesn't exist** — no prompt or internal state rebuilds it.", ic="users", body_size=14.5)
card(s, 6.75, 1.7, 5.95, 3.4, "AI checks the humans", "A coerced or rogue human pushes an action. An independent AI evaluator attests only to allow-listed criteria on authenticated evidence — or **fails closed**.", ic="scales", body_size=14.5)
callout(s, 0.6, 5.4, 12.1, 1.1, "No model in the cryptographic path. Just trustee slots, assigned by class, composed with an explicit **AND**.", 16)

# 14 — hybrid gates figure
s = d.slide(eyebrow="How it composes", title="Separate gates, explicit AND",
            notes="A single Shamir split can't express 'all three AI checks AND any two humans.' Use separate gates or a vetted access-structure scheme, combined by an explicit AND, verified server-side. The AI is a bounded evaluator — never an autonomous authority, never able to waive the human threshold.")
picture(s, "hybrid-ai-human-policy-gates.png", 0.8, 1.75, h=4.95)
text(s, 7.1, 1.75, 5.6, 3.8, [
    "One D-of-T split treats all shards as **equal peers** — it can't say \"all AI checks **and** any two humans.\"",
    "So: **separate gates**, combined with an explicit AND, verified server-side.",
    "The AI gate is a **bounded evaluator**: signed, time-limited, auditable — and it can never waive the human threshold."], 15, MUTED, gap=12)

# 15 — NEAT
s = d.slide(eyebrow="Beyond the math", title="NEAT: what a critical deployment still needs",
            notes="[0:36] The math only protects you if nothing routes around the ceremony. NEAT extends the classic reference-monitor requirements. Only hardware-anchored patterns — secure-element-internal sequencing or a physical interlock — reach proof grade.")
for i, (L, h, b) in enumerate([("N", "Non-bypassable", "The ceremony is the only path to the end state."),
                               ("E", "Evaluable", "Small and standard enough to verify independently."),
                               ("A", "Always-invoked", "No admin override, debug flag, or maintenance path."),
                               ("T", "Tamper-proof", "Subverting it means breaking the hardware boundary.")]):
    x = 0.6 + i * 3.1
    rect(s, x, 1.7, 2.85, 3.5, NAVY)
    badge(s, x + 0.3, 1.98, L, 0.75, GOLD, DEEP, 28)
    text(s, x + 0.3, 2.95, 2.3, 0.4, h, 17, WHITE, bold=True)
    text(s, x + 0.3, 3.45, 2.3, 1.6, b, 14, ICE)
callout(s, 0.6, 5.5, 12.1, 1.0, "Software-only enforcement reduces risk. **Secure-element sequencing or a physical interlock** is what reaches proof grade.", 15)

# 16 — where it doesn't fit
s = d.slide(eyebrow="Credibility over hype", title="Where shardic doesn't fit",
            notes="[0:38–0:43] Say this out loud. Frequent or live authorization, per-trustee revocation, online quorum and key rotation: use FROST or HSM-backed multisig. shardic is for rare, high-stakes, deliberate recovery.")
for i, (ic, h, b) in enumerate([("userclock", "Frequent or live authorization", "Built for rare break-glass events, not every request."),
                                ("users", "Revoking one trustee", "It's split-once: changing trustees means a full re-split."),
                                ("key", "Online quorum & key rotation", "Use threshold signatures (FROST) or HSM-backed multisig."),
                                ("db", "Hundreds of trustees", "GF(256) caps at 255 — real ceremonies run in the tens.")]):
    x, y = 0.6 + (i % 2) * 6.15, 1.65 + (i // 2) * 2.3
    card(s, x, y, 5.95, 2.05, None, None, fill=BROWN)
    icon(s, x + 0.35, y + 0.35, ic, 0.62, "5A4A22")
    text(s, x + 1.25, y + 0.4, 4.4, 0.45, h, 18, WHITE, bold=True)
    text(s, x + 1.25, y + 0.92, 4.4, 1.0, b, 14, "E8DCC0")
text(s, 0.6, 6.35, 12.1, 0.4, "Rare, high-stakes, offline, small trustee set, shareable vault file — that's the sweet spot.", 14, MUTED, italic=True)

# 17 — takeaways
s = d.slide(eyebrow="Take these home", title="Three things to remember",
            notes="Mirror the CFP 'attendees will learn' list.")
for i, (h, b) in enumerate([
        ("Threshold, not chunks", "Shamir turns \"split a secret\" into a real D-of-T threshold — and below D, zero information."),
        ("It runs today", "A working reference implementation, down to a vault file that leaks no shard-to-trustee mapping."),
        ("It generalizes", "Gate any consequential action — and enforce human-AI oversight in both directions.")]):
    y = 1.7 + i * 1.6
    badge(s, 0.6, y + 0.1, str(i + 1), 0.8, GOLD, DEEP, 28)
    text(s, 1.7, y + 0.02, 11, 0.5, h, 22, DEEP, bold=True)
    text(s, 1.7, y + 0.6, 11, 0.8, b, 16, MUTED)

# 18 — close
s = d.slide(dark=True, notes="[0:43–0:45] Repo link, README use-case catalog, and how to reach the project for integration conversations. Then Q&A.")
text(s, 0.9, 1.1, 11.5, 0.4, "THANK YOU", 12, GOLD, bold=True, spacing=120)
text(s, 0.9, 1.7, 11.5, 1.6, "Math beats policies and permissions.", 46, WHITE, bold=True)
for i, (ic, h, b) in enumerate([("puzzle", "Run it", "github.com/splashd1/shardic"),
                                ("case", "Read it", "White paper v4.1 · public-education explainer"),
                                ("mail", "Build with us", "Integration conversations welcome")]):
    x = 0.9 + i * 3.95
    rect(s, x, 3.6, 3.7, 1.8, NAVY)
    icon(s, x + 0.3, 3.9, ic, 0.56, BLUE)
    text(s, x + 1.1, 3.92, 2.4, 0.45, h, 17, WHITE, bold=True)
    text(s, x + 1.1, 4.4, 2.4, 0.9, b, 13, ICE)
text(s, 0.9, 6.0, 11.5, 0.5, "Questions?", 22, SOFT, italic=True)

d.save(sys.argv[1])

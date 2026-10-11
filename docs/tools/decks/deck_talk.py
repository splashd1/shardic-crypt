"""Deck 3 of the v4.1 set — goal 3: evangelism. Conference talk deck following the
45-minute speaker outline in docs/conference-talk-pitch.md, with timed speaker notes.

v4.1.1 adds slides from the white paper — the vault pipeline and zero-leakage indexing,
shardic-prime, the two kinds of strength, the Level 2 ceremony, the bypass-resistance
ladder, and where the guarantee stops — plus four backup slides for Q&A."""
import sys
sys.path.insert(0, sys.path[0])
from deckkit import *

d = Deck("Conference Talk  ·  v4.1.1")

# 1 — title
s = d.slide(dark=True, notes="[0:00] Title. Introduce yourself in one sentence. Promise: a live demo, the math from first principles, and where it goes next — including human-AI oversight.")
text(s, 0.9, 1.1, 10, 0.4, "CONFERENCE TALK  ·  45 MINUTES", 12, GOLD, bold=True, spacing=120)
text(s, 0.9, 1.75, 11.5, 2.0, "Splitting Trust, Not Just Keys", 54, WHITE, bold=True)
text(s, 0.9, 2.85, 11.5, 1.0, "Threshold recoverability by construction, not by policy", 26, ICE)
for i, n in enumerate(["users", "tree", "shield"]):
    icon(s, 0.9 + i * 0.85, 4.4, n, 0.62, NAVY)
text(s, 0.9, 5.7, 10, 0.4, "John Davis  ·  Venue and date TBD", 16, SOFT)
text(s, 0.9, 6.2, 10, 0.4, "github.com/splashd1/shardic-crypt", 13, SOFT)

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
            notes="[0:11] The secret is where the line crosses the axis. One point: infinitely many lines, every secret possible. Two points: one line, one crossing. For D = 3, a parabola. For D, a degree D-1 curve.")
picture(s, "sss-geometric-intuition.png", 0.8, 1.9, w=7.2)
text(s, 8.5, 1.8, 4.2, 4.2, [
    "Secret = where the line **crosses the axis**.",
    "**One point:** infinitely many lines. Every secret equally possible.",
    "**Two points:** exactly one line, one crossing.",
    "**D points** fix a curve of degree D − 1."], 17, MUTED, gap=14)

# 7 — the construction
s = d.slide(eyebrow="First principles · 3", title="Now make it precise",
            notes="[0:13] Constant term is the secret; shards are points; Lagrange interpolation at x = 0 recovers it. Mirrors docs/sss_explained_for_shardic.md.")
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
s = d.slide(dark=True, notes="[0:15] The key slide. Not 'hard to break' — nothing to break. Relevant to the post-quantum conversation: no computational assumption to erode.")
text(s, 0.9, 1.0, 11.5, 0.4, "FIRST PRINCIPLES · 4", 12, GOLD, bold=True, spacing=120)
text(s, 0.9, 1.6, 11.5, 1.8, "0 bits", 110, GOLD, bold=True)
text(s, 0.9, 3.55, 11.2, 1.0, "is what D − 1 shards reveal about the secret. Every possible value fits them equally well.", 24, WHITE)
text(s, 0.9, 4.75, 11.2, 1.3, "No partial credit. No \"getting warmer.\" No computational assumption for a quantum computer to erode — the information simply isn't there.", 18, ICE)

# 9 — GF(256)
s = d.slide(eyebrow="First principles · 5", title="Why GF(256), in one slide",
            notes="[0:17] Reals bring fractions and rounding that corrupt the secret. GF(256): exact, one element per byte, AES's own field. The side effect: at most 255 shards — an operational ceiling that real deployments never approach.")
picture(s, "gf256-byte-as-polynomial.png", 0.8, 1.9, w=6.5)
for i, (big, small) in enumerate([("1 byte", "= one field element. Exact arithmetic, no rounding."),
                                  ("0x11B", "AES's own reduction polynomial, generator 3."),
                                  ("255", "shards max — 0 is reserved for the secret.")]):
    text(s, 8.0, 1.75 + i * 1.55, 4.7, 0.7, big, 30, DEEP, bold=True)
    text(s, 8.0, 2.38 + i * 1.55, 4.7, 0.6, small, 14, MUTED)

# 10 — from math to a vault
s = d.slide(eyebrow="From math to a working vault", title="Split the key, seal every shard, ship one file",
            notes="[0:18] SSS never touches the bulk data — AES-256-GCM encrypts the archive once; Shamir splits only the 32-byte DEK. Then the step people skip: a raw Shamir point is just data, so D of them stored in the clear would rebuild the key with nobody's cooperation. Each shard is sealed under its own shardic encryption key — a codeword through Argon2id today, or a full-strength key by envelope. Finally, the .krypt file carries no trustee map: records are opaque and shuffled, and recovery tries every codeword against every record — the GCM auth tag confirms the match. With T in the tens that's instant, and the file reveals nothing about who holds what. This is what takeaway 2 means.")
for i, (h, b) in enumerate([("Archive", "Pack the input into one uncompressed tar."),
                            ("Encrypt once", "AES-256-GCM under a random 256-bit DEK."),
                            ("Split the key", "Shamir splits only the 32-byte DEK into T shards."),
                            ("Seal each shard", "Under its own shardic encryption key, e.g. codeword → Argon2id."),
                            ("One .krypt", "Header, metadata, ciphertext. Safe to share.")]):
    x = 0.6 + i * 2.47
    badge(s, x + 0.85, 1.6, str(i + 1), 0.62, GOLD, DEEP, 20)
    rect(s, x, 2.4, 2.27, 1.95, NAVY)
    text(s, x + 0.22, 2.6, 1.85, 0.4, h, 17, WHITE, bold=True)
    text(s, x + 0.22, 3.08, 1.85, 1.2, b, 13, ICE)
rect(s, 0.6, 4.65, 5.95, 1.95, "F6ECD2", radius=0.06)
text(s, 0.9, 4.65, 5.4, 1.95, ["**A raw shard is just data.**", "D raw Shamir points stored in the clear would rebuild the key with nobody's cooperation — so every shard is sealed before it's stored."], 14.5, BROWN, anchor="m", gap=6)
rect(s, 6.75, 4.65, 5.95, 1.95, "DFF3E6", radius=0.06)
text(s, 7.05, 4.65, 5.4, 1.95, ["**No map inside the file.**", "Records are opaque and shuffled. Recovery tries each codeword against every record; GCM's auth tag confirms the match."], 14.5, "1D5B35", anchor="m", gap=6)

# 11 — shardic-prime
s = d.slide(eyebrow="Extending the textbook", title="shardic-prime: one trustee the math can't do without",
            notes="[0:20] Some roles must always sign off — an executor, a security lead. shardic-prime layers a one-time-pad mask over the ordinary split: the prime trustee holds the mask, the pool holds Shamir shards of the masked key. Every pool shard together still yields only random noise; the mask alone yields nothing. So the prime is mathematically essential, not just required by policy. Plant the payoff: the mask is just a value — nothing says a person has to hold it. Hold that thought for Level 3.")
code(s, 0.6, 1.7, 6.4, 2.6, [
    "mask          = random bytes, len(DEK)",
    "masked_secret = DEK XOR mask",
    "pool_shards   = split(masked_secret,",
    "                      pool_threshold, pool_size)",
    "",
    "DEK = reconstruct(pool_shards) XOR mask"], 14)
card(s, 0.6, 4.55, 6.4, 1.9, "Nothing new to trust", "Each half keeps the information-theoretic guarantee. All pool shards without the mask rebuild only noise.", body_size=13.5)
picture(s, "image5.png", 7.55, 1.85, w=5.0)
callout(s, 7.4, 5.35, 5.3, 1.1, "The mask is just a value — so **hardware** can hold it. Remember that for Level 3.", 14)

# 12 — two kinds of strength
s = d.slide(eyebrow="The question you should be asking", title="So is the real security just the codewords?",
            notes="[0:22] Answer the challenge before someone asks it. The DEK and the Shamir split are effectively unconditional. Each codeword is only computationally strong — guess space times KDF cost — and a higher D doesn't compensate, because an attacker cracks codewords one at a time, never the set at once. Two knobs; neither substitutes for the other. And for high-assurance ceremonies you skip the codeword entirely. Numbers are on the backup slide if asked.")
card(s, 0.6, 1.7, 5.95, 3.1, "Key length & Shamir split", ["256-bit DEK, no known AES-256 shortcut", "Below D: zero information", "Raising T or D changes **how many must collude**"], ic="shield", tag="Unconditional", body_size=14)
card(s, 6.75, 1.7, 5.95, 3.1, "Each codeword", ["Only as strong as its guess space × KDF cost", "Attacker cracks codewords **one at a time**", "More trustees **don't** fix a weak codeword"], ic="key", fill=BROWN, tag="Computational", tagfill=GOLD, body_size=14)
callout(s, 0.6, 5.1, 12.1, 1.3, "Yes — the codeword is the floor. Default: 8 EFF words ≈ 103 bits, Argon2id at 256 MiB per guess. For high-assurance ceremonies, replace it with a full-strength random key delivered by **shardic envelope** — parity with the 256-bit DEK.", 14)

# 13 — implemented vs proposed
s = d.slide(eyebrow="Implemented vs. proposed", title="Where the line is — stated plainly",
            notes="[0:24–0:25] Credibility: be explicit. Levels 1 and 2 are running code. Level 3 is a design proposal built on the same unmodified math.")
for i, (tag, fill, h, b) in enumerate([
        ("Running code", GREEN, "Level 1 · Personal utility", ["CLI + GUI, no server", "Codewords + one .krypt file", "shardic-prime mandatory trustee"]),
        ("Running code", GREEN, "Level 2 · Shardic ceremony", ["Public-key-wrapped delivery", "Keycloak-backed trustee selection", "Automatic backfill on decline"]),
        ("Design proposal", GOLD, "Level 3 · SPAC", ["Gate any consequential action", "Bound to one Fielded Prime Element", "Human-AI mutual oversight"])]):
    x = 0.6 + i * 4.1
    card(s, x, 1.7, 3.85, 3.6, None, None)
    pill(s, x + 0.3, 1.98, tag, fill)
    text(s, x + 0.3, 2.42, 3.3, 0.45, h, 17, WHITE, bold=True)
    text(s, x + 0.3, 2.95, 3.3, 2.2, b, 14, ICE, bullets=True, gap=6)
callout(s, 0.6, 5.6, 12.1, 0.9, "Each level reuses the one below **unchanged**. Level 3 adds no new cryptography.", 16)

# 14 — Level 2 ceremony
s = d.slide(eyebrow="Level 2  ·  running code", title="The ceremony: identity, custody, and math kept apart",
            notes="[0:25–0:27] What makes Level 2 more than a CLI. Registration: trustees come from a dedicated Keycloak group and generate their own keypairs on their own devices — the private key never touches a server shardic controls. Formation: an operator with the shardic-operator role picks T trustees plus an ordered backup list; declines and timeouts backfill automatically, race-safe; and the operator can't pick themselves. Delivery: each trustee fetches their own wrapped envelope, addressed by authenticated identity (a single-read drop point is designed but not built yet — the paper says so too). Recovery: the combiner only ever receives unsealed shards, never a codeword. The organizing principle: a compromised identity provider or a stalled ceremony can block provisioning, but neither can weaken D-of-T.")
picture(s, "ceremony-envelope-flow-v4.1.png", 0.8, 1.8, h=4.6)
for i, (h, b) in enumerate([("Register", "Trustees generate keypairs on their own devices. Keycloak handles identity — never keys."),
                            ("Form", "An operator picks T trustees plus ordered backups. Declines backfill automatically; the operator can't pick themselves."),
                            ("Deliver", "Each trustee fetches their own wrapped envelope, addressed by authenticated identity."),
                            ("Recover", "The combiner only ever sees unsealed shards — never a codeword.")]):
    y = 1.7 + i * 1.02
    badge(s, 6.6, y + 0.02, str(i + 1), 0.48, GOLD, DEEP, 15)
    text(s, 7.25, y, 5.45, 0.35, h, 15, DEEP, bold=True)
    text(s, 7.25, y + 0.33, 5.45, 0.65, b, 12.5, MUTED)
callout(s, 6.6, 5.85, 6.1, 0.85, "A compromised identity provider can stall provisioning — it can't weaken D-of-T.", 13.5)

# 15 — data to capability
s = d.slide(eyebrow="Where it generalizes", title="From protected file to protected action",
            notes="[0:27] The plaintext never had to be a file. A SPAC is any enabling value: a signing key, a release-enable code. The Fielded Prime Element reuses shardic-prime's mask so a copied CT SPAC plus a legitimate quorum still fails on the wrong hardware. Precedent: Permissive Action Links, Two-Person Integrity.")
card(s, 0.6, 1.7, 3.85, 3.5, "PT SPAC → CT SPAC", "Any enabling value — a signing credential, a release-enable code — encrypted and split exactly like a file's key.", ic="lock", body_size=14)
card(s, 4.7, 1.7, 3.85, 3.5, "Fielded Prime Element", "A hardware-sealed secret takes the prime trustee's slot. Copy the ciphertext elsewhere and a full quorum still fails.", ic="shield", body_size=14)
card(s, 8.8, 1.7, 3.9, 3.5, "Old idea, new math", "Permissive Action Links and Two-Person Integrity, enforced by the math instead of procedure.", ic="bank", body_size=14)
code(s, 0.6, 5.45, 12.1, 1.15, [
    "DEK     = reconstruct_secret_with_prime(mask, pool_shards)   # unmodified",
    "CT_SPAC = AES-256-GCM(PT_SPAC, DEK)                          # unmodified"], 14)

# 16 — vignette
s = d.slide(eyebrow="One vignette, end to end", title="A high-value treasury wire, start to finish",
            notes="[0:29] Walk the five stages. Contrast with the as-is: two web-app approvals that one compromised admin or two coerced officers can fake. Here, three of five officers plus the appliance's own hardware plus an on-site key-switch — and the controller's commitment is checked at arming. Point out why the approver exists: AES-GCM guarantees the CT SPAC decrypts to exactly what went in, but says nothing about whether what went in was the right value. A stale or substituted value would sail through — so an approver independent of whoever wraps it signs a commitment, checked thoroughly at emplacement and quickly at every arming.")
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
text(s, 0.6, 6.4, 12.1, 0.4, "Why an independent approver? AES-GCM proves the value decrypts to exactly what went in — not that what went in was right.", 13, MUTED, italic=True)

# 17 — human-AI
s = d.slide(eyebrow="The flagship case", title="Human-AI mutual oversight — one rule, both directions",
            notes="[0:31] The same D-of-T rule, pointed either way by trustee-class assignment. AI-initiated action needs independent human sign-off — no prompt or internal state rebuilds a key that doesn't exist. Human-initiated action needs an independent AI evaluator's attestation against allow-listed criteria — no seniority or urgency talks it out of failing closed.")
card(s, 0.6, 1.7, 5.95, 3.4, "Humans gate the AI", "An AI proposes a consequential action. It can't execute on its own confidence or speed: below the human threshold, the key **doesn't exist** — no prompt or internal state rebuilds it.", ic="users", body_size=14.5)
card(s, 6.75, 1.7, 5.95, 3.4, "AI checks the humans", "A coerced or rogue human pushes an action. An independent AI evaluator attests only to allow-listed criteria on authenticated evidence — or **fails closed**.", ic="scales", body_size=14.5)
callout(s, 0.6, 5.4, 12.1, 1.1, "No model in the cryptographic path. Just trustee slots, assigned by class, composed with an explicit **AND**.", 16)

# 18 — hybrid gates figure
s = d.slide(eyebrow="How it composes", title="Separate gates, explicit AND",
            notes="[0:33] A single Shamir split can't express 'all three AI checks AND any two humans.' Use separate gates or a vetted access-structure scheme, combined by an explicit AND, verified server-side — and treat that composition logic as security-critical: deny by default, and test missing, stale, duplicate, invalid, and wrong-role contributions. The AI is a bounded evaluator — never an autonomous authority, never able to waive the human threshold. Walk the rules box: authenticate and audit what it reads and which policy it ran; its attestation expires; ambiguous or conflicting evidence fails closed; and for irreversible actions it shouldn't be the only thing enabling them.")
picture(s, "hybrid-ai-human-policy-gates.png", 0.8, 1.75, h=4.95)
text(s, 7.1, 1.7, 5.6, 2.2, [
    "One D-of-T split treats all shards as **equal peers** — it can't say \"all AI checks **and** any two humans.\"",
    "So: **separate gates**, combined with an explicit AND, verified server-side, deny by default."], 14.5, MUTED, gap=10)
card(s, 7.1, 3.55, 5.6, 3.15, "An AI trustee is a bounded evaluator", [
    "Inputs, policy version, identity, attestation key: authenticated and audited",
    "Its attestation expires; ambiguous evidence **fails closed**",
    "Never waives the human quorum — and never the **sole** enabler of an irreversible action"], body_size=12.5)

# 19 — bypass ladder
s = d.slide(eyebrow="Cryptographic vs. topological bypass", title="Can the ceremony simply be skipped?",
            subtitle="The math guarantees fewer than D shards never rebuild the key. It can't guarantee the system ever calls the ceremony.",
            notes="[0:35] The most important idea after the math itself. Below-threshold recovery is a cryptographic guarantee. Whether the system ever invokes the ceremony is a topological property of the surrounding design — a second code path, a config flag, or a maintenance mode can reach the end state without it. Four patterns bind the ceremony into the execution path, weakest to strongest. The software patterns reduce risk, but a privileged insider who can edit that code can route around them. Only the hardware-anchored patterns reach the same bar as the math, because bypassing them means breaking the hardware boundary or physically defeating a circuit. Real deployments layer several; the composite is only as strong as its weakest layer.")
for i, (tier, fill, h, b) in enumerate([
        ("Medium", BROWN, "Capability binding", "The ceremony yields a value the end state needs as input — a key, not a yes/no."),
        ("Medium", BROWN, "Constrained state machine", "No edge in the operating sequence reaches the end state except through the ceremony."),
        ("High", NAVY, "Secure-element sequencing", "The hardware performs the end-state action itself; software only sees the result."),
        ("Highest", NAVY, "Physical interlock", "The actuation circuit stays open until the ceremony closes it.")]):
    x, top = 0.6 + i * 3.1, 2.85 - i * 0.3
    rect(s, x, top, 2.85, 5.45 - top, fill)
    pill(s, x + 0.3, top + 0.28, tier, GOLD if fill == BROWN else GREEN)
    text(s, x + 0.3, top + 0.72, 2.3, 0.75, h, 16, WHITE, bold=True)
    text(s, x + 0.3, top + 1.5, 2.3, 5.35 - top - 1.5, b, 13, "E8DCC0" if fill == BROWN else ICE)
rect(s, 0.6, 5.7, 5.95, 0.95, "F6ECD2", radius=0.06)
text(s, 0.9, 5.7, 5.4, 0.95, "**Software-enforced:** reduces risk — but whoever can edit that code can route around it.", 13.5, BROWN, anchor="m")
rect(s, 6.75, 5.7, 5.95, 0.95, "DFF3E6", radius=0.06)
text(s, 7.05, 5.7, 5.4, 0.95, "**Hardware-anchored:** bypass means breaking the hardware boundary. Proof grade.", 13.5, "1D5B35", anchor="m")

# 20 — NEAT
s = d.slide(eyebrow="Beyond the math", title="NEAT: what a critical deployment still needs",
            notes="[0:37] NEAT names what the previous slide implies. It extends the classic reference-monitor requirements (tamperproof, always invoked, small enough to verify). It's a deployment framework, not a cryptographic one — meeting it doesn't make the math stronger, it makes the system around the math trustworthy.")
for i, (L, h, b) in enumerate([("N", "Non-bypassable", "The ceremony is the only path to the end state."),
                               ("E", "Evaluable", "Small and standard enough to verify independently."),
                               ("A", "Always-invoked", "No admin override, debug flag, or maintenance path."),
                               ("T", "Tamper-proof", "Subverting it means breaking the hardware boundary.")]):
    x = 0.6 + i * 3.1
    rect(s, x, 1.7, 2.85, 3.5, NAVY)
    badge(s, x + 0.3, 1.98, L, 0.75, GOLD, DEEP, 28)
    text(s, x + 0.3, 2.95, 2.3, 0.4, h, 17, WHITE, bold=True)
    text(s, x + 0.3, 3.45, 2.3, 1.6, b, 14, ICE)
callout(s, 0.6, 5.5, 12.1, 1.0, "A **deployment** bar, not a cryptographic one: it doesn't make the math stronger — it makes the system around the math trustworthy.", 15)

# 21 — where it doesn't fit
s = d.slide(eyebrow="Credibility over hype", title="Where shardic doesn't fit",
            notes="[0:39–0:41] Say this out loud. Frequent or live authorization, per-trustee revocation, online quorum and key rotation: use FROST or HSM-backed multisig. shardic is for rare, high-stakes, deliberate recovery.")
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

# 22 — where the guarantee stops
s = d.slide(eyebrow="Credibility over hype  ·  2", title="What the math doesn't do on its own",
            notes="[0:41–0:43] The second half of the credibility section: each of these is a boundary the deployment has to own, not a flaw in the threshold guarantee. SPAC's open parameters are integration decisions, not open cryptographic questions. AI-trustee data feeds need multi-source authentication designed per deployment. The creator's deletion is an operational assumption the cryptography can't enforce. Reconstruction records contributions; it doesn't prove who or why. And the one-file design trades availability risk for simplicity — back it up durably.")
for i, (ic, b) in enumerate([
        ("puzzle", "Practical SPAC design parameters (hardware target, grant wire format) will be driven by target operational and security constraints."),
        ("scales", "How AI trustees get trustworthy, authenticated input data is implementation specific."),
        ("warn", "The guarantee requires the creator deleted the plaintext and all copies."),
        ("usershield", "Reconstruction is a functional protection. Identity or intent, or non-repudiation, if needed, need to integrate other mechanisms."),
        ("db", "The single .krypt file is a conscious availability risk tradeoff, though not an access risk.")]):
    y = 1.6 + i * 1.02
    rect(s, 0.6, y, 12.1, 0.86, LIGHT, radius=0.08)
    icon(s, 0.85, y + 0.15, ic, 0.56)
    text(s, 1.7, y, 10.7, 0.86, b, 16, DEEP, anchor="m")

# 23 — takeaways
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

# 24 — close
s = d.slide(dark=True, notes="[0:43–0:45] Repo link, README use-case catalog, and how to reach the project for integration conversations. Then Q&A.")
text(s, 0.9, 1.1, 11.5, 0.4, "THANK YOU", 12, GOLD, bold=True, spacing=120)
text(s, 0.9, 1.7, 11.5, 1.6, "Math beats policies and permissions.", 46, WHITE, bold=True)
for i, (ic, h, b) in enumerate([("puzzle", "Run it", ["github.com/splashd1/", "shardic-crypt"]),
                                ("case", "Read it", "White paper v4.1 · public-education explainer"),
                                ("mail", "Build with us", "Integration conversations welcome")]):
    x = 0.9 + i * 3.95
    rect(s, x, 3.6, 3.7, 1.8, NAVY)
    icon(s, x + 0.3, 3.9, ic, 0.56, BLUE)
    text(s, x + 1.1, 3.92, 2.4, 0.45, h, 17, WHITE, bold=True)
    text(s, x + 1.1, 4.4, 2.4, 0.9, b, 13, ICE, gap=0)
text(s, 0.9, 6.0, 11.5, 0.5, "Questions?", 22, SOFT, italic=True)

# 25 — backup: codeword strength
s = d.slide(eyebrow="Backup  ·  if asked about codeword strength", title="Is ~2^100 enough when the DEK is 2^256?",
            notes="Backup for slide 12. The 256-bit comparison measures the wrong thing: the DEK layer faces an unbounded, global keyspace search with nothing else in the way; a codeword faces someone holding one stolen record, searching a bounded, memory-hard space, and success yields one D-of-T point — worthless below threshold. Even at a deliberately impossible 10^12 Argon2id guesses per second, exhausting 2^100 takes ~1.3×10^18 seconds — tens of billions of years — and that guess rate implies ~250 exabytes per second of memory bandwidth. More words or higher Argon2id cost is still worthwhile headroom, not a fix.")
for i, (big, small) in enumerate([("~103 bits", "8 words from the EFF long wordlist, ~12.9 bits each."),
                                  ("256 MiB", "Argon2id memory per guess (time cost 4, parallelism 4)."),
                                  ("~10^18 s", "to exhaust 2^100 at an impossible 10^12 guesses/s — tens of billions of years.")]):
    text(s, 0.6, 1.7 + i * 1.6, 5.4, 0.7, big, 30, DEEP, bold=True)
    text(s, 0.6, 2.33 + i * 1.6, 5.4, 0.8, small, 14, MUTED)
card(s, 6.4, 1.7, 6.3, 2.1, "DEK / AES-256-GCM layer", "Attacker holds only ciphertext. Full, unstructured 256-bit keyspace, nothing else in the way — so it must be unconditionally strong.", body_size=13.5)
card(s, 6.4, 4.0, 6.3, 2.1, "Codeword layer", "Attacker holds one stolen shard record. Bounded, memory-hard search — and success buys one D-of-T point, worthless below threshold.", fill=BROWN, body_size=13.5)
text(s, 6.4, 6.3, 6.3, 0.5, "10^12 guesses/s × 256 MiB ≈ 250 EB/s of memory bandwidth — not a plausible attacker.", 12.5, MUTED, italic=True)

# 26 — backup: memorability
s = d.slide(eyebrow="Backup  ·  if asked whether people can remember eight words", title="Can a trustee really hold eight words?",
            notes="Backup for slide 12. The task is long-term retention through rehearsal, not one-shot recall — Miller's 'seven plus or minus two' is about working memory and doesn't describe a standing trustee. Diceware recommends six words as standard and ten for 10+ year use; eight sits inside that range, and real words become a mental sentence. BIP39's 'write it down' advice answers a harder question: three times the words, zero error tolerance, silent catastrophic failure, and one holder who must recall it alone.")
text(s, 0.6, 1.7, 4.9, 4.6, [
    "**Rehearsed, not recited once.** Like a PIN or alarm code — not Miller's 7 ± 2, which is about working memory.",
    "**Inside Diceware's range.** Six words standard, ten for 10+ year use.",
    "**Real words carry meaning.** Eight become one short mental sentence."], 15, MUTED, gap=14)
cols = [(5.9, 2.0, ""), (7.9, 2.4, "BIP39 seed phrase"), (10.3, 2.4, "shardic codeword")]
rows = [("Length", "12–24 words", "8 words (~103 bits)"),
        ("Wrong word", "Silently derives a different wallet", "Auth tag rejects it; retry"),
        ("Cost of a mistake", "Total, often undetected loss", "A failed match, nothing lost"),
        ("Who must recall", "One holder, alone", "Any D of T trustees")]
rect(s, 5.9, 1.7, 6.8, 0.55, DEEP, radius=0.04)
for x, w, h in cols[1:]:
    text(s, x + 0.15, 1.7, w - 0.3, 0.55, h, 13.5, WHITE, bold=True, anchor="m")
for r, (a, b, c) in enumerate(rows):
    y = 2.35 + r * 0.95
    rect(s, 5.9, y, 6.8, 0.85, LIGHT, radius=0.04)
    for (x, w, _), v, col, bold in zip(cols, (a, b, c), (DEEP, BROWN, "1D5B35"), (True, False, False)):
        text(s, x + 0.15, y, w - 0.3, 0.85, v, 13, col, bold=bold, anchor="m")
text(s, 5.9, 6.25, 6.8, 0.5, "BIP39's caution is right for its problem. It doesn't carry over to this one.", 13, MUTED, italic=True)

# 27 — backup: use cases
s = d.slide(eyebrow="Backup  ·  where it applies", title="Rare, high-stakes, no lone actor",
            notes="Backup, for 'who would actually use this?' Every case shares the shape: policy or regulation already says no single party should decrypt this alone, and access is rare and deliberate rather than routine. Full catalog in the white paper's use-case section and the README.")
for i, (ic, h, b) in enumerate([
        ("warn", "Break-glass infrastructure", "Root CA key, database master key, SCADA override — T = 7, D = 4."),
        ("tree", "Estate & succession", "A password manager's master vault split among family, lawyer, partner — T = 5, D = 3."),
        ("bank", "Government", "Generalized two-person rule, continuity-of-government credentials, election tabulation keys."),
        ("case", "Escrow & disputes", "M&A documents released only by a quorum of board, counsel, and escrow agent."),
        ("key", "Treasury cold storage", "Root key material behind a multisig wallet — no single executive moves funds."),
        ("scales", "Separation of duties", "SOX, HIPAA \"minimum necessary\" — enforced by the math, not just policy.")]):
    x, y = 0.6 + (i % 3) * 4.1, 1.65 + (i // 3) * 2.45
    card(s, x, y, 3.85, 2.25, None, None)
    icon(s, x + 0.3, y + 0.3, ic, 0.56)
    text(s, x + 1.05, y + 0.38, 2.6, 0.45, h, 15.5, WHITE, bold=True)
    text(s, x + 0.3, y + 1.05, 3.25, 1.1, b, 13, ICE)

# 28 — backup: RTO
s = d.slide(eyebrow="Backup  ·  if asked how fast a ceremony can run", title="Latency is a CONOPS choice, not a fixed cost",
            notes="Backup for the SPAC section. Target recovery time is a per-deployment parameter. Pre-forming the ceremony is the biggest lever — it moves select/invite/accept out of the clock entirely. Network delivery is near-instant; physical carriage is minutes to days, so air-gap independence and a tight recovery time largely exclude each other. A single operator and custodian are fast, but an unreachable one is a single point of availability failure — on-call backups fix that without adding authorizers. None of this reduces how many parties the cryptography requires.")
for i, (ic, h, b) in enumerate([
        ("users", "Convening the quorum", "Pre-form the ceremony before it's needed: hours of select-invite-accept become seconds to minutes. The biggest lever."),
        ("mail", "Shard delivery", "Network: near-instant. Physical carriage: minutes to days. Air-gap independence and a tight recovery time rarely coexist."),
        ("userclock", "Endgame unlock", "One operator, one custodian — fast. On-call backups protect availability without adding authorizers.")]):
    card(s, 0.6 + i * 4.1, 1.7, 3.85, 3.6, h, b, ic=ic, body_size=14)
callout(s, 0.6, 5.6, 12.1, 0.95, "Speed comes from pre-positioning inputs you already need — **never** from needing fewer of them.", 15)

d.save(sys.argv[1])

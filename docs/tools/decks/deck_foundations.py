"""Deck 2 of the v4.1 set — goal 2: public education on the cryptographic foundation,
for teams evaluating shardic as a building block for multi-entity security."""
import sys
sys.path.insert(0, sys.path[0])
from deckkit import *

d = Deck("Cryptographic Foundations  ·  v4.1")

# 1 — title
s = d.slide(dark=True, notes="This deck is for people who may never run the CLI: architects and teams deciding whether shardic's primitive belongs in their own multi-party security design.")
text(s, 0.9, 1.2, 10, 0.4, "PUBLIC EDUCATION  ·  WHITE PAPER V4.1 COMPANION", 12, GOLD, bold=True, spacing=120)
text(s, 0.9, 1.9, 11.5, 1.6, "The Cryptographic Foundation of Shardic", 48, WHITE, bold=True)
text(s, 0.9, 3.55, 10.5, 1.0, "How threshold secret sharing turns \"no one acts alone\" into math — and how to build on it.", 22, ICE)
text(s, 0.9, 6.3, 10, 0.4, "Open for evaluation and integration  ·  github.com/splashd1/shardic  ·  September 2026", 12, SOFT)

# 2 — why share this
s = d.slide(eyebrow="Why we're sharing this", title="A building block, not just a tool",
            notes="Goal: let other teams evaluate or integrate the primitive for their own multi-entity security — human-only, or human plus AI. Everything here is standard, publicly analyzable cryptography.")
for i, (ic, h, b) in enumerate([
        ("puzzle", "Reuse the primitive", "Standard parts — Shamir over GF(256), AES-256-GCM, Argon2id — composed so no single party holds control."),
        ("users", "Human-only or human + AI", "Trustees are just independent key holders. The math doesn't care whether a slot is a person or a policy-bound agent."),
        ("scales", "Evaluate it openly", "Small, standards-based, and published — so you can verify the claims rather than take them on faith.")]):
    card(s, 0.6 + i * 4.1, 1.7, 3.85, 3.6, h, b, ic=ic, body_size=14)
callout(s, 0.6, 5.6, 12.1, 0.95, "The question shardic answers: **how do we make sure no single party can expose this secret — or invoke this capability — alone?**", 16)

# 3 — naive splitting
s = d.slide(eyebrow="Start with the wrong answer", title="Why \"cut the key into pieces\" fails",
            notes="Chunking and XOR splitting can hide the key from anyone short of all pieces, but they're all-or-nothing. Lose one trustee and the key is gone forever.")
card(s, 0.6, 1.7, 3.9, 3.3, "Chunk it", "Hand each of four trustees an 8-byte slice of the 32-byte key.", ic="cubes", fill=BROWN, body_size=14)
card(s, 4.7, 1.7, 3.9, 3.3, "XOR it", "Make every piece random except the last, chosen so they all XOR back to the key.", ic="lock", fill=BROWN, body_size=14)
card(s, 8.8, 1.7, 3.9, 3.3, "Same flaw", "All-or-nothing. You can't ask for \"any D of T\" — lose one trustee and the key is gone forever.", ic="warn", fill=BROWN, body_size=14)
callout(s, 0.6, 5.35, 12.1, 1.1, "What we actually want: **any D of T** recover, and **fewer than D** learn nothing. That's a threshold scheme.", 17, NAVY)

# 4 — geometric intuition
s = d.slide(eyebrow="The intuition", title="Hide the secret as a point only enough hints can locate",
            notes="The secret is where a line crosses the vertical axis. One point on the line tells you nothing — infinitely many lines pass through it. Two points fix the line, and so the crossing.")
picture(s, "sss-geometric-intuition.png", 0.8, 1.85, w=6.9)
text(s, 8.2, 1.75, 4.5, 4.2, [
    "Picture the secret as the spot where a **line crosses the vertical axis**.",
    "Give each trustee one point on that line. **One point alone** fits infinitely many lines — every secret stays equally possible.",
    "**Two points** fix exactly one line, so exactly one crossing. That's D = 2.",
    "Need D = 3? Use a parabola. In general: a curve that takes exactly **D points** to pin down."], 15, MUTED, gap=12)
text(s, 0.8, 5.4, 6.9, 0.8, "Any D of the T points will do — not a specific D, not all T — so the scheme absorbs losing up to T − D trustees.", 13, MUTED, italic=True)

# 5 — precise construction
s = d.slide(eyebrow="The precise construction", title="Shamir's Secret Sharing (1979)",
            notes="Hide the secret as the constant term of a random degree D-1 polynomial. Shards are points on it. Lagrange interpolation at x = 0 recovers the secret from any D points.")
code(s, 0.6, 1.7, 6.2, 2.0, [
    "f(x) = S + a₁x + a₂x² + … + a₍D−1₎x^(D−1)",
    "",
    "f(0) = S          # the secret",
    "shard_i = (i, f(i))   for i = 1 … T"], 15)
for i, (h, b) in enumerate([("Build", "Random coefficients a₁…a₍D−1₎; the constant term is the secret."),
                            ("Evaluate", "Each shard is one point (i, f(i)) at a distinct nonzero x."),
                            ("Distribute", "One point per trustee — T in total."),
                            ("Reconstruct", "Any D points → Lagrange interpolation → evaluate at x = 0.")]):
    badge(s, 7.3, 1.72 + i * 1.18, str(i + 1), 0.5, GOLD, DEEP, 16)
    text(s, 8.0, 1.7 + i * 1.18, 4.7, 0.4, h, 16, DEEP, bold=True)
    text(s, 8.0, 2.07 + i * 1.18, 4.7, 0.7, b, 13.5, MUTED)
callout(s, 0.6, 4.05, 6.2, 1.6, "**D points fix a degree-(D−1) polynomial.** No more, no fewer — that one algebra fact is the whole scheme.", 15)

# 6 — zero bits
s = d.slide(eyebrow="The guarantee", title="Below threshold, the answer doesn't exist yet",
            notes="With D-1 points, one polynomial fits every possible secret equally well. That's information-theoretic: no algorithm, no quantum computer, no amount of time helps, because the information isn't there.")
stat(s, 0.6, 1.75, 4.3, "0 bits", "learned about the secret from D − 1 shards — regardless of computing power, time, or future cryptanalysis.", DEEP, MUTED, 72)
card(s, 5.3, 1.7, 3.6, 3.7, "Computational security", "Most crypto: breaking it is **hard** (factoring, discrete log). A better algorithm or bigger computer could, in principle, win.", ic="lock", fill=BROWN, body_size=13.5)
card(s, 9.1, 1.7, 3.6, 3.7, "Information-theoretic", "Shamir below threshold: nothing to break. Every candidate secret fits the shards **equally well**.", ic="shield", body_size=13.5)
callout(s, 0.6, 5.7, 12.1, 0.9, "No partial credit, no \"getting warmer.\" The Dth point doesn't refine the answer — it's the moment the answer springs into existence.", 15, NAVY, italic=True)

# 7 — GF(256)
s = d.slide(eyebrow="Making it exact", title="Why GF(256) instead of real numbers",
            notes="Real-number interpolation brings fractions and floating-point rounding that silently corrupt the secret. GF(256) is exact, one element per byte, and the same field AES uses. It also sets the 255-shard ceiling.")
picture(s, "gf256-byte-as-polynomial.png", 0.8, 1.85, w=6.3)
for i, (ic, h, b) in enumerate([("warn", "Reals break it", "Fractions and floating-point rounding silently corrupt the secret."),
                                ("check", "One element = one byte", "256 elements, closed arithmetic, no rounding — the same field AES uses."),
                                ("db", "A built-in ceiling", "255 usable x-values (0 is the secret) → at most 255 shards.")]):
    icon(s, 7.7, 1.8 + i * 1.5, ic, 0.56)
    text(s, 8.5, 1.78 + i * 1.5, 4.2, 0.4, h, 16, DEEP, bold=True)
    text(s, 8.5, 2.17 + i * 1.5, 4.2, 0.8, b, 13.5, MUTED)
text(s, 0.8, 5.5, 6.3, 0.8, "shardic applies the construction independently to each of the DEK's 32 bytes.", 13, MUTED, italic=True)

# 8 — from SSS to shardic
s = d.slide(eyebrow="From textbook to system", title="Split the key, never the file",
            notes="SSS never touches bulk data. AES-256-GCM encrypts the archive under a random DEK; SSS splits only the 32-byte DEK. Two independent layers: computational for data, information-theoretic for the key.")
picture(s, "image1.png", 0.8, 1.85, w=5.6)
card(s, 7.0, 1.7, 5.7, 2.05, "Layer 1 — AES-256-GCM on the data", "Encrypt the uncompressed tar archive once under a random DEK. Computational security, plus built-in tamper detection.", body_size=13.5)
card(s, 7.0, 3.95, 5.7, 2.05, "Layer 2 — Shamir on the key", "Split only the 32-byte DEK into T shards at threshold D. Information-theoretic below D.", body_size=13.5)
text(s, 7.0, 6.2, 5.7, 0.6, "Uncompressed on purpose: ciphertext size shouldn't leak plaintext compressibility.", 12.5, MUTED, italic=True)

# 9 — SEK sources
s = d.slide(eyebrow="Sealing each shard", title="The shardic encryption key: four pluggable sources",
            notes="A raw shard is just data, so each is sealed under its own 256-bit AES-GCM key. The guarantee only needs each trustee to hold one independently. Mix sources across trustees in one vault.")
for i, (ic, tag, h, b) in enumerate([
        ("key", "Implemented", "KDF from a codeword", "Memorized words → Argon2id (or PBKDF2). The only source a human recalls."),
        ("mail", "Implemented", "shardic envelope", "Full-strength CSPRNG key, delivered wrapped under the trustee's public key."),
        ("usershield", "Pluggable", "External token", "PIV/FIDO2, an HSM, or a shardware-token releases the key."),
        ("puzzle", "Pluggable", "Anything mainstream", "Enterprise KMS, PKI credentials — any 256-bit key held with comparable rigor.")]):
    x, y = 0.6 + (i % 2) * 6.15, 1.65 + (i // 2) * 2.35
    card(s, x, y, 5.95, 2.15, None, None)
    icon(s, x + 0.35, y + 0.35, ic, 0.62)
    pill(s, x + 5.95 - 0.3 - (0.2 + 0.085 * len(tag)), y + 0.3, tag, GREEN if tag == "Implemented" else GOLD)
    text(s, x + 1.25, y + 0.42, 3.2, 0.45, h, 18, WHITE, bold=True)
    text(s, x + 1.25, y + 0.95, 4.4, 1.1, b, 14, ICE)
text(s, 0.6, 6.45, 12.1, 0.4, "Each shard record stores only {salt, nonce, ciphertext}. The container records the KDF and parameters once, so the vault describes itself.", 13, MUTED, italic=True)

# 10 — zero-leakage indexing
s = d.slide(eyebrow="A property worth copying", title="Zero-leakage indexing: no map, just trial",
            notes="The metadata never records which codeword unlocks which shard. Recovery tries each key against every unmatched record; GCM's auth tag is the oracle. With T in the tens, that's instant — and the file leaks nothing about who holds what.")
picture(s, "image4.png", 0.8, 1.85, h=4.3)
text(s, 7.1, 1.75, 5.6, 3.4, [
    "The shard list has **no trustee mapping** — just opaque, shuffled {salt, nonce, ciphertext} records.",
    "Recovery tries each supplied key against **every unmatched record**. GCM's auth tag makes the right pairing decrypt and every wrong one fail fast.",
    "With T in the tens, trial is **effectively instant** — so don't add a mapping \"for efficiency.\""], 15, MUTED, gap=12)
callout(s, 7.1, 5.3, 5.6, 1.1, "The .krypt file on its own reveals nothing about who holds what.", 15)

# 11 — shardic-prime
s = d.slide(eyebrow="Extending the textbook", title="shardic-prime: one mandatory trustee",
            notes="A one-time-pad mask over the ordinary split. The prime trustee holds the mask; the pool holds Shamir shards of the masked secret. Neither half alone reveals anything. Because the mask is just a value, a hardware element can hold it — that's the Fielded Prime Element.")
code(s, 0.6, 1.7, 6.4, 2.6, [
    "mask          = random bytes, len(DEK)",
    "masked_secret = DEK XOR mask",
    "pool_shards   = split(masked_secret,",
    "                      D − 1, pool_size)",
    "",
    "DEK = reconstruct(pool_shards) XOR mask"], 14)
card(s, 0.6, 4.55, 6.4, 1.9, "Nothing new to trust", "Both halves keep the information-theoretic guarantee. The layering makes the prime trustee mathematically essential, not just customary.", body_size=13.5)
picture(s, "image5.png", 7.55, 1.85, w=5.0)
callout(s, 7.4, 5.35, 5.3, 1.1, "The mask is just a value — so **hardware** can hold it. That's the Fielded Prime Element.", 14)

# 12 — two kinds of strength
s = d.slide(eyebrow="Size it correctly", title="Two different strengths, two different levers",
            notes="The DEK and Shamir split are effectively unconditional. Each codeword is only computationally strong, and a higher D doesn't compensate: an attacker cracks D codewords individually. Tune both knobs.")
card(s, 0.6, 1.7, 5.95, 3.1, "Key length & Shamir split", ["256-bit DEK, no known AES-256 shortcut", "Below D: zero information", "Raising T or D changes **how many must collude**"], ic="shield", tag="Unconditional", body_size=14)
card(s, 6.75, 1.7, 5.95, 3.1, "Each codeword", ["Only as strong as its guess space × KDF cost", "Attacker cracks D codewords **one at a time**", "More trustees **don't** fix a weak codeword"], ic="key", fill=BROWN, tag="Computational", tagfill=GOLD, body_size=14)
callout(s, 0.6, 5.1, 12.1, 1.3, "Default memorable codewords: 8 EFF words ≈ 103 bits, Argon2id at 256 MiB per guess. For high-assurance ceremonies, skip the codeword entirely — a CSPRNG key delivered by shardic envelope reaches parity with the DEK.", 14)

# 13 — integrating
s = d.slide(eyebrow="Building on it", title="What stays fixed when you integrate",
            notes="Each level reuses the one beneath unchanged. Integrators change delivery, trustee organization, or what the value gates — never the split, the KDF path, or the container. Keep the implemented-vs-proposed line explicit.")
for i, (tag, fill, h, b) in enumerate([
        ("Implemented", GREEN, "Level 1 · Personal utility", "Codewords + a .krypt file. The math everything else reuses."),
        ("Implemented", GREEN, "Level 2 · Shardic ceremony", "Change how keys reach trustees and how trustees are chosen — not the math."),
        ("Design proposal", GOLD, "Level 3 · SPAC", "Change what the value gates: any consequential action, bound to one device.")]):
    x = 0.6 + i * 4.1
    card(s, x, 1.7, 3.85, 2.75, None, None)
    pill(s, x + 0.3, 1.98, tag, fill)
    text(s, x + 0.3, 2.42, 3.3, 0.45, h, 16.5, WHITE, bold=True)
    text(s, x + 0.3, 2.9, 3.3, 1.4, b, 13.5, ICE)
rect(s, 0.6, 4.75, 12.1, 1.75, LIGHT, radius=0.05)
text(s, 0.95, 4.95, 11.4, 0.4, "Invariants to preserve", 16, DEEP, bold=True)
text(s, 0.95, 5.4, 5.5, 1.0, ["One crypto core — never fork encrypt/split logic per frontend", "No shard-to-trustee mapping in metadata"], 13.5, MUTED, bullets=True, gap=4)
text(s, 6.8, 5.4, 5.6, 1.0, ["KDF fixed at creation — no downgrade on recovery", "Fail closed: no partial or best-guess output"], 13.5, MUTED, bullets=True, gap=4)

# 14 — learn more
s = d.slide(dark=True, notes="Point to the four reading paths, from plain-language to code-level.")
text(s, 0.9, 0.9, 10, 0.4, "LEARN THE FOUNDATION", 12, GOLD, bold=True, spacing=120)
text(s, 0.9, 1.4, 11.5, 1.0, "Pick your depth", 40, WHITE, bold=True)
for i, (ic, h, b) in enumerate([
        ("users", "Plain language", "docs/public-education-explainer.md"),
        ("puzzle", "The math, step by step", "docs/sss_explained_for_shardic.md"),
        ("case", "The full argument", "White paper v4.1 — md / docx / html"),
        ("tree", "Code-level path", "docs/shardic-cryptographic-path.md")]):
    x = 0.9 + i * 2.95
    rect(s, x, 2.75, 2.75, 2.6, NAVY)
    icon(s, x + 0.3, 3.05, ic, 0.56, BLUE)
    text(s, x + 0.3, 3.8, 2.2, 0.45, h, 15.5, WHITE, bold=True)
    text(s, x + 0.3, 4.3, 2.2, 0.9, b, 12, ICE)
text(s, 0.9, 5.9, 11.5, 0.5, "Evaluate it, break it, build on it — github.com/splashd1/shardic", 17, SOFT, italic=True)

d.save(sys.argv[1])

"""Deck 1 of the v4.1 set — goal 1: inform and share the utility (short overview + demo)."""
import sys
sys.path.insert(0, sys.path[0])
from deckkit import *

d = Deck("Overview & Demo  ·  v4.1")

# 1 — title
s = d.slide(dark=True, notes="Opening. One line: shardic makes 'no single party can decrypt this alone' a mathematical fact, not a policy promise.")
text(s, 0.9, 1.2, 8, 0.4, "OVERVIEW & DEMO  ·  WHITE PAPER V4.1 COMPANION", 12, GOLD, bold=True, spacing=120)
text(s, 0.9, 1.9, 11, 1.3, "SHARDIC", 72, WHITE, bold=True, spacing=300)
text(s, 0.9, 3.25, 11, 0.7, "No single party can decrypt it alone. Any D of T can.", 28, ICE)
text(s, 0.9, 4.1, 9.5, 1.0, "Threshold-recoverable encryption you can run today — a working CLI and GUI, no server, no network.", 17, SOFT)
for i, n in enumerate(["lock", "users", "key"]):
    icon(s, 0.9 + i * 0.85, 5.6, n, 0.62, NAVY)
text(s, 0.9, 6.55, 8, 0.3, "github.com/splashd1/shardic  ·  September 2026", 12, SOFT)

# 2 — the problem
s = d.slide(eyebrow="The status quo", title="One key, one point of failure",
            notes="Whoever holds the key has unilateral, permanent control. Wrapping it or locking it in an HSM moves the single point of control; it doesn't remove it.")
text(s, 0.6, 1.65, 5.6, 3.2, [
    "Conventional encryption is **monolithic**: whoever holds the key — or controls the system holding it — controls the plaintext, alone and for good.",
    "Wrap the key under a public key and the private key becomes the new single secret. Lock it in an HSM and one coerced admin still gets through.",
    "Same shape every time: **one secret, one holder, one point of failure.**"], 16, MUTED, gap=12)
for i, (ic, h, b) in enumerate([
        ("usershield", "Rogue insider", "One trusted person acts alone."),
        ("warn", "Coerced admin", "One person is pressured into acting."),
        ("key", "Stolen credential", "One compromised account is enough.")]):
    card(s, 6.8, 1.65 + i * 1.62, 5.9, 1.42, None, None)
    icon(s, 7.1, 1.65 + i * 1.62 + 0.4, ic, 0.62)
    text(s, 8.0, 1.65 + i * 1.62 + 0.3, 4.4, 0.4, h, 17, WHITE, bold=True)
    text(s, 8.0, 1.65 + i * 1.62 + 0.75, 4.4, 0.5, b, 14, ICE)

# 3 — the idea
s = d.slide(eyebrow="The shardic idea", title="Split the key, not the file",
            notes="Encrypt once under a random DEK. Split the DEK with Shamir's Secret Sharing into T shards. Each trustee unlocks their shard with their own shardic encryption key. Any D rebuild the DEK; fewer carry zero information.")
steps = [("lock", "Encrypt once", "AES-256-GCM under a random 256-bit DEK"),
         ("tree", "Split the DEK", "Shamir's Secret Sharing → T shards, threshold D"),
         ("key", "Seal each shard", "Under that trustee's own shardic encryption key"),
         ("users", "Distribute", "One codeword per trustee, out of band")]
for i, (ic, h, b) in enumerate(steps):
    x = 0.6 + i * 3.1
    card(s, x, 1.75, 2.8, 2.6, h, b, ic=ic)
    if i < 3:
        text(s, x + 2.8, 2.7, 0.3, 0.5, "›", 30, GOLD_D, bold=True, align="c")
callout(s, 0.6, 4.75, 12.1, 1.05,
        "Any **D** of **T** trustees rebuild the DEK. Fewer than D hold **zero information** about it — not \"hard to break,\" but simply not there.", 17)
text(s, 0.6, 6.05, 12.1, 0.6, "The creator can't recover alone either — once they delete their local copies and distribute the codewords.", 13, MUTED, italic=True)

# 4 — stats
s = d.slide(eyebrow="The guarantee in three numbers", title="What the math actually promises",
            notes="Three facts: any D of T recover; below D you learn zero bits; everything ships as one self-describing file.")
for i, (big, small) in enumerate([("3 of 5", "Any three trustees recover. Which three doesn't matter — and two can be lost for good."),
                                  ("0 bits", "What D − 1 shards reveal about the key, regardless of computing power."),
                                  ("1 file", "One .krypt container: header, metadata, ciphertext. No trustee-to-shard map inside.")]):
    x = 0.6 + i * 4.15
    rect(s, x, 1.8, 3.8, 3.0, LIGHT, radius=0.05)
    stat(s, x + 0.35, 2.15, 3.2, big, small, DEEP, MUTED, 58)
callout(s, 0.6, 5.2, 12.1, 0.95, "**Information-theoretic** below threshold: the guarantee doesn't erode as quantum or classical computing improves.", 16)
# below threshold: the guarantee doesn't erode as quantum or classical computing improves.", 14, MUTED, italic=True)

# 5 — demo create
s = d.slide(eyebrow="Live demo · 1 of 2", title="Create a 3-of-5 vault",
            notes="Real output from vault_create.py run against demo/sample-secret. Point out: Argon2id KDF, ~103-bit memorable codewords, one .krypt file, and the instruction to distribute then delete codeword files.")
code(s, 0.6, 1.65, 7.6, 5.0, [
    "$ python3 vault_create.py --input demo/sample-secret \\",
    "      --trustees 5 --threshold 3 --outdir ./v",
    "",
    "[i] Shard protection KDF: argon2id",
    "[*] Memorable mode: 7772 real words (EFF list)",
    "[*] Estimated codeword strength: ~103 bits",
    "[*] Archiving 'demo/sample-secret' ...",
    "[*] Split DEK into 5 shards, threshold 3",
    "[*] Wrote vault container: pzzsrzg30y9z0pwv.krypt",
    "",
    "[+] Wrote 5 trustee codeword files",
    "    Distribute each to exactly one trustee,",
    "    then DELETE them from this machine."], 13)
for i, (h, b) in enumerate([("Pick T and D", "Five trustees, any three recover."),
                            ("Memorable codewords", "Eight real words each — e.g. unruly-numbing-precision-lemon-…"),
                            ("One .krypt file", "Safe to store or share: it maps no shard to any trustee."),
                            ("Hand off, then delete", "Distribution is your trust decision — the tool never automates it.")]):
    badge(s, 8.6, 1.7 + i * 1.22, str(i + 1), 0.5, GOLD, DEEP, 16)
    text(s, 9.3, 1.68 + i * 1.22, 3.45, 0.4, h, 16, DEEP, bold=True)
    text(s, 9.3, 2.05 + i * 1.22, 3.45, 0.7, b, 13, MUTED)

# 6 — demo recover
s = d.slide(eyebrow="Live demo · 2 of 2", title="Recover with any three — and nothing less",
            notes="Real output. Codewords in any order; a wrong codeword is rejected by the AES-GCM auth tag; three good ones reconstruct and decrypt. diff -r confirms a byte-identical round trip.")
code(s, 0.6, 1.65, 7.6, 5.0, [
    "$ python3 vault_recover.py v/*.krypt --outdir ./r \\",
    "      --word <trustee 1> --word <trustee 3> --word <trustee 5>",
    "",
    "[i] This vault requires 3 of 5 codewords to recover.",
    "  [+] Codeword accepted (1/3).",
    "  [+] Codeword accepted (2/3).",
    "  [+] Codeword accepted (3/3).",
    "[*] Reconstructing DEK from recovered shards ...",
    "[*] Decrypting archive ...",
    "[*] Success.",
    "",
    "$ diff -r demo/sample-secret r/sample-secret   # identical",
    "",
    "# and when a trustee mistypes:",
    "  [-] That codeword doesn't match any remaining shard."], 13)
for i, (ic, h, b) in enumerate([("check", "Any order, any three", "Recovery never asks who you are."),
                                ("lock", "Wrong word? Rejected", "GCM's auth tag fails fast — no garbage output."),
                                ("shield", "Two isn't enough", "Short of D, recovery stops. No partial output, ever.")]):
    icon(s, 8.6, 1.75 + i * 1.62, ic, 0.56)
    text(s, 9.4, 1.72 + i * 1.62, 3.35, 0.4, h, 16, DEEP, bold=True)
    text(s, 9.4, 2.12 + i * 1.62, 3.35, 0.8, b, 13, MUTED)

# 7 — use cases
s = d.slide(eyebrow="Where it fits", title="Rare, high-stakes, nobody-acts-alone access",
            notes="Break-glass keys, estate planning, public-sector two-person rules, regulated separation of duties. Common thread: rare access, high stakes, a small static trustee set.")
for i, (ic, h, b) in enumerate([
        ("key", "Break-glass infrastructure", "Root CA keys, DB master keys, SCADA overrides — say T=7, D=4."),
        ("users", "Estate & succession", "Relatives, a lawyer, a partner (T=5, D=3), with memorizable codewords."),
        ("bank", "Government & public sector", "Any-3-of-7 officials, escrowed archives, continuity-of-government keys."),
        ("case", "Business & regulated industry", "M&A escrow, treasury cold storage, SOX/HIPAA separation of duties.")]):
    x, y = 0.6 + (i % 2) * 6.15, 1.65 + (i // 2) * 2.55
    card(s, x, y, 5.95, 2.3, None, None)
    icon(s, x + 0.35, y + 0.35, ic, 0.62)
    text(s, x + 1.25, y + 0.42, 4.4, 0.45, h, 18, WHITE, bold=True)
    text(s, x + 1.25, y + 0.95, 4.4, 1.2, b, 14, ICE)

# 8 — three levels
s = d.slide(eyebrow="One primitive, three levels", title="Start small — the same math scales up",
            notes="Each level reuses the one beneath it unchanged. Levels 1 and 2 run today; Level 3 (SPAC) is a design proposal on the same unmodified math. You can stop at any level.")
picture(s, "capability-stack.png", 0.85, 1.75, h=4.85)
for i, (tag, fill, h, b) in enumerate([
        ("Implemented", GREEN, "Level 1 — Personal & small group", "CLI + GUI. Codewords, a .krypt file, no server."),
        ("Implemented", GREEN, "Level 2 — Shardic ceremony", "Public-key-wrapped delivery, identity-backed trustee selection, automatic backfill."),
        ("Design proposal", GOLD, "Level 3 — SPAC product protection", "Gate any consequential action, bound to one fielded device — including human-AI mutual oversight.")]):
    y = 1.65 + i * 1.72
    card(s, 6.3, y, 6.4, 1.52, None, None)
    pill(s, 6.6, y + 0.25, tag, fill)
    text(s, 6.6, y + 0.62, 5.8, 0.4, h, 16, WHITE, bold=True)
    text(s, 6.6, y + 0.98, 5.8, 0.5, b, 12.5, ICE)

# 9 — fits / doesn't fit
s = d.slide(eyebrow="Honest boundaries", title="Great fit, poor fit",
            notes="Credibility matters more than hype. For frequent or live authorization with key rotation, use FROST or HSM-backed multisig.")
card(s, 0.6, 1.65, 5.95, 3.9, "Reach for shardic when…", [
    "Access is **rare and high-stakes**, not routine",
    "No single party should **ever** decrypt alone",
    "The trustee set is **small and fairly static** (tens, not thousands)",
    "You must store or share the vault file **without leaking who holds what**",
    "You want it **offline** — no server in the recovery path"], ic="check", body_size=15)
card(s, 6.75, 1.65, 5.95, 3.9, "Reach for something else when…", [
    "You need **frequent or live** authorization",
    "You must **revoke one trustee** without a full re-split",
    "You need **online quorum and key rotation** — use FROST or HSM-backed multisig",
    "Your trustee count runs past **255** (the GF(256) ceiling)"], ic="warn", fill=BROWN, body_size=15)
text(s, 0.6, 5.85, 12.1, 0.6, "Being clear about the boundary is part of the guarantee: shardic solves one problem — rare recovery that needs genuine multi-party agreement — and solves it completely.", 14, MUTED, italic=True)

# 10 — get started
s = d.slide(dark=True, notes="Close: clone, run the two commands, read the white paper or the plain-language explainer.")
text(s, 0.9, 0.9, 10, 0.4, "TRY IT IN FIVE MINUTES", 12, GOLD, bold=True, spacing=120)
text(s, 0.9, 1.4, 11.5, 1.0, "Math beats policies and permissions.", 40, WHITE, bold=True)
code(s, 0.9, 2.7, 7.0, 2.2, [
    "$ git clone github.com/splashd1/shardic",
    "$ pip install cryptography argon2-cffi",
    "$ python3 vault_create.py --input <dir> \\",
    "      --trustees 5 --threshold 3 --outdir v",
    "$ python3 vault_recover.py v/*.krypt ..."], 13, fill=NAVY)
text(s, 8.4, 2.7, 4.2, 2.4, [
    "**Read next**",
    "White paper v4.1 — docs/",
    "Plain-language explainer — public-education-explainer.md",
    "Foundations deck — the cryptography, step by step"], 14, ICE, gap=8)
text(s, 0.9, 5.6, 11, 0.5, "No server. No network. Just Python 3, a .krypt file, and D people who agree.", 17, SOFT, italic=True)

d.save(sys.argv[1])

**SHARDIC**

Sharded Encryption for Threshold-Recoverable Vaults — and Protected-Action Ceremonies

*Enforcing Multi-Person Integrity for High-Stakes Data Recovery, Capability Authorization, and Human-AI Mutual Oversight*

**White Paper — Version 3.0 (draft)**

August 2026

Project repository: github.com/splashd1/shardic

---

# Abstract

Conventional file encryption is monolithic: whoever holds the key, or controls the system that holds it, controls access to the plaintext — permanently and unilaterally. 

shardic replaces that single point of control with a threshold-recoverable model, built entirely from mature, standards-based cryptography — Shamir's Secret Sharing, AES-256-GCM, standard key-derivation functions — applied with a specific, deliberate structure of control on top. A file or directory is encrypted once under a randomly generated data encryption key (DEK), and that DEK is then split — using Shamir's Secret Sharing over GF(256) — into T shares distributed to T independent trustees. No fewer than a threshold of D trustees, each unlocking their share via an independently held **shardic encryption key**, can ever reconstruct the DEK. Below that threshold, the remaining shares carry zero information about the key — a guarantee that holds regardless of computing power, not merely one that is expensive to break. A shardic encryption key can be sourced however a deployment's trustee population actually operates — a memorized or transcribed secret run through a KDF, a shardic-envelope-delivered credential, an external hardware token, or another mainstream key-generation mechanism a deployment already trusts — because the guarantee that matters is *that* D independent parties each supply one, not *how* any single trustee came to hold theirs.

The mathematical basis and essential functionality — multi-entity enforced data protection — can be seen in the base scheme of §1–§3.5, sharded protection with no dependency beyond the Shamir/AES math itself. shardic-envelope then closed the gap between that math's information-theoretic strength and what a human-memorized secret could actually deliver, giving a trustee's protection key parity with the data-encryption key it protects. Ceremony formation followed, supplying the functional lifecycle — registration, convening, delivery, backfill — needed to mature the design from a demonstration into an operable system. SPAC is the newest layer in that lineage: it takes the same mathematics and manifests it as a practical capability, generalized from decrypting a file to gating any protected action. §1.6 states that stack explicitly before the paper works through it section by section. Sections 1–3 describe the mature, largely-implemented core — the operational need and the cryptographic mechanics, including shardic-envelope and ceremony formation, which have since moved from proposed design to running code — at a conceptual level; the reference implementation's own command-line tools are documented in the project README, not reproduced here. Section 4 generalizes the protected value from "a file" to a shardic protected action code (SPAC) — any enabling value for a protected capability, not only a decryption target — introduces the Fielded Prime Element and shardware-token constructions that make SPAC safe to field in hardware-bound deployments, addresses non-bypassable invocation (§4.6), and states briefly how a SPAC ceremony protects its own trustees' shardic encryption keys by default (§4.7) — the deeper codeword-specific treatment, including the field-deployment opt-out case, is relocated to Appendix B so the main narrative stays at the level a decision-maker actually needs.

Section 5 extends the security discussion to the SPAC layer and names what a genuinely critical deployment additionally requires beyond the threshold math itself: **RAIN** — redundant, always-invoked, independently implemented, non-bypassable (§5.5) — a design framework introduced here and still being fleshed out into concrete notional employment models as this draft matures. Section 6 then walks four notional missions through the full ceremony lifecycle this generalization makes possible, and the fourth of them is this paper's actual center of gravity. A high-value treasury disbursement (§6.1) and a safety-interlock release authorization (§6.2) establish the pattern; a path-trustee network integrity model (§6.3) extends it to sequential relay nodes. §6.4 then states this paper's governing claim directly, immediately before Vignette D (§6.5) — hybrid human-and-AI policy gates — walks it through a full lifecycle: shardic is a mechanism for *enforcing*, not merely recommending, human-in-the-loop control over an AI-initiated course of action, and, in the converse direction, for enforcing independent AI validation as a check against a rogue or coerced human-initiated course of action in SPAC execution. Neither direction is a policy preference layered on top of the mathematics — each is the same D-of-T threshold guarantee already established in §1–§3, applied so that one trustee class, human or AI, cannot act without the other. As AI systems take on a growing share of both analysis and course-of-action execution in high-value operations, this is the specific, mathematically enforced form that "keeping a human in the loop" — and, just as importantly, keeping an impartial check on the human — can actually take, rather than remaining a procedural aspiration layered on top of software that a sufficiently privileged party can still bypass.

Section 7 draws these threads together in a single summary. Everything described from Section 4 onward is a design proposal, not shipped functionality — flagged as such throughout, in the same spirit as §3.6/§3.7 flagged shardic-envelope before it shipped. Section 8 situates shardic against existing multi-party secret-protection approaches and states what actually differentiates it; Section 9 gives the project's own component-by-component Technology Readiness Level self-assessment; Section 10 states plainly what that means for funding: a phased roadmap from the already-implemented core to a working SPAC demonstration, scoped against what a proof-of-concept award would and would not claim. Section 11 names, without resolving, the licensing and IP-ownership decision that governs all of it, and flags one time-sensitive consequence of this whitepaper's own distribution. Appendix A gives the complete, standalone treatment of Shamir's Secret Sharing that §1.4 and §3.2 summarize inline; Appendix B gives the complete treatment of codeword-mode selection, tuning, and the field-deployment memorization case that §4.7 states only in summary.

## Up Front Reader Hints on Terminology & Flow

This paper is an unfolding of different maturity levels from implemented functionality described as running code that proved the functionality and efficacy of the shardic security features. Next there design proposal descriptions to identify architecture or integration work not yet fielded but principally sound . There are also illustrative concepts that identify a notional mission or configuration, not a deployment recommendation.
Terminology. T is the number of shares; D is the reconstruction threshold. A PT SPAC is the plaintext enabling value for a protected action; a CT SPAC is its protected ciphertext form. A Fielded Prime Element is a deployment-specific hardware-bound contribution intended to bind release to an approved fielded system.

# 1. The Need for Threshold-Recoverable Protection

## 1.1 Conventional Data Encryption: Monolithic, Single-Point Control

The standard model of symmetric encryption is simple: a key is generated, data is encrypted under it, and the key is stored or shared so that plaintext can later be recovered from the ciphertext. That simplicity is also the model’s structural weakness. Whoever possesses the key — a person, a process, a single server — has complete and unilateral power over the data it protects. Access is a binary, anonymous fact: either you hold the key, or you don’t. There is no way, within the cryptography itself, to require that access be a joint decision, or to prove after the fact who authorized a given recovery.

This single-point-of-control property persists even when the key management around it becomes more sophisticated. Wrapping a symmetric key with a public key so it can only be unwrapped by whoever holds the matching private key changes who the single point of control is, but not that there is one — the private key becomes the new monolithic secret. Locking a key inside an HSM, a safe, or a physically secured server changes where the single point of control lives, but a single compromised operator, a single coerced administrator, or a single stolen credential is still sufficient to defeat it. None of these supplements change the underlying shape of the trust model: one secret, one holder, one point of failure.

For routine data protection this is an acceptable, even desirable, trade-off — simplicity and low friction usually outweigh the risk. It becomes a liability precisely in the cases organizations care about most: root credentials, master keys, and archives whose disclosure or misuse by a single rogue, insider threat, or compromised party would be catastrophic.

## 1.2 Sharded Encryption: Enforcing Multi-Person Integrity

Shardic: sharded threshold-recoverable encryption addresses this by removing the single point of control from the cryptography itself, rather than relying on policy or process to compensate for it. Instead of one key held by one party, the data encryption key (DEK) is embedded as a value on a randomly generated polynomial, constructed via Shamir's Secret Sharing so that a threshold of D points is required to reconstruct it. T points on that polynomial — the shards — are each entrusted to one of T independent trustees, unlocked only via that trustee's own shardic encryption key. No shard is a fragment or segment of the DEK itself; recovering the plaintext requires at least D trustees to each independently choose to unlock their shard and contribute it to the reconstruction. Critically, this is not merely operationally enforced (e.g., by requiring D signatures at an application layer) — it is information-theoretically enforced: any collection of fewer than D shards leaves the underlying polynomial, and therefore the DEK, completely undetermined — consistent with every possible DEK value equally, no matter how much computing power is applied against it.

The practical effect is that:

- No single trustee — including whoever originally created the vault — can ever recover the data alone.

Operational assumption: this guarantee applies only after the creator has securely deleted plaintext, retained shares, codeword copies, and other recovery material, and after trustee distribution has been verified. The cryptography cannot undo copies retained outside the scheme.

- A rogue insider, a coerced employee, or a single compromised account is insufficient to cause disclosure; a collusion of at least D independent parties is required.

- The trustee pool can absorb the loss or unavailability of up to T − D trustees without losing recoverability — unlike a strict N-of-N or two-person rule, which has no slack.

A recovery can produce an auditable record of authenticated contributors when the deployment uses protected signing credentials, signed contributions, trustworthy timestamps, and retained verifiable logs. Threshold reconstruction alone does not establish identity or legal non-repudiation.



This shifts data protection from "who holds the key" — a fact about custody — to "who agreed to unlock it" — a fact about consent, distributed across independent parties who cannot individually override the group.

## 1.3 Representative Use Cases

Threshold-recoverable encryption is the right tool wherever policy, regulation, or risk tolerance already implies that no single party should be able to unilaterally decrypt something, and where access is rare and high-stakes rather than continuous and routine. Representative examples include:

### Break-glass access to critical infrastructure

A root certificate-authority private key, a production database master key, or a SCADA override credential is locked in a vault with, say, T=7 trustees — a mix of senior engineers, security officers, and an executive — and a D=4 threshold. Day to day, nobody has access to the key at all. It is reconstructed only for a genuine emergency, and only if four of the seven trustees each independently agree to participate.

### Diceware-style estate and succession planning

A family or founder splits access to a password manager's master vault, or other key-person credentials, among relatives, a lawyer, and a business partner (T=5, D=3), using memorable, whole-word codewords that trustees can actually commit to memory rather than write down.

### Government and public-sector applications

- Generalized two-person-rule systems ("any 3 of 7 officials") that tolerate absence or incapacitation without weakening the no-lone-actor requirement of the classic two-key model.

- Escrowed decryption keys for classified or lawful-intercept archives, split across officials from different branches or agencies so that no single agency — or a rogue insider within one — can unilaterally decrypt.

- Continuity-of-government credentials that must survive the loss of some custodians while still requiring majority agreement to invoke.

- Election-system tabulation keys split among representatives of multiple parties or observers.



### Business and regulated-industry applications

- M&A escrow and dispute-resolution vaults — deal terms or sensitive documents released only by quorum of board members, outside counsel, and an escrow agent.

- Cryptocurrency or treasury cold storage — splitting root key material behind a multisig wallet among founders or board members so no single executive can move funds alone.

- Whistleblower or source-protection archives, releasable only if a threshold of editors or lawyers agree.

- Regulated data with explicit separation-of-duties requirements (e.g. SOX, HIPAA "minimum necessary" contexts) — a technical enforcement of an existing compliance control rather than a policy statement alone.



Where this approach fits best: rare, high-stakes, offline "break-glass" access with a small, semi-static trustee set, where the vault file itself must be safely storable and shareable without leaking metadata about who holds what. It is a poor fit for frequent or live authorization, for revoking a single trustee without a full re-split, or for online multi-party protocols — those are better served by threshold-signature schemes (e.g. FROST) or HSM-backed multisig, which support key rotation and live quorum that this static, split-once design does not attempt to provide. §8 gives the fuller comparison against these and other existing approaches, and states what specifically differentiates shardic from each.

## 1.4 How Threshold Secret Sharing Works, Conceptually

Section 3.2 gives the precise, byte-by-byte construction. Before that, it's worth building the intuition for why a threshold scheme works at all — because the obvious first guess at how to "split a key into pieces" is not what shardic does, and doesn't have the properties §1.2 just promised.

The obvious guess, and why it falls short. Imagine cutting the 32-byte DEK into four 8-byte chunks and handing one chunk to each of four trustees — or the slightly cleverer version, XOR-splitting, where each share is random and the last one is defined so that all of them XOR back to the key. Both can be made information-theoretically sound in the narrow sense that holding fewer than all the pieces reveals nothing. But both share the same structural flaw: they are all-or-nothing schemes. Reconstruction needs every single piece, with no way to ask for "any D of T." Lose one trustee, permanently, and the key is gone forever — exactly the fragility §1.2 said threshold recovery exists to avoid.

The actual idea: hide the secret as a point only enough hints can locate. Picture the DEK not as a string of bytes but as a single point on a graph — specifically, where a straight line crosses the vertical axis. Draw that line so it also happens to pass through T other points, one assigned to each trustee. Handing a trustee "their" point tells them nothing on its own: infinitely many different lines pass through any single point, each crossing the axis somewhere completely different, so every possible secret remains equally possible. But hand over any two trustees' points together, and there is exactly one straight line that passes through both of them — which means there is exactly one place it crosses the axis. Two points determine a line; that's what makes D = 2 work.

![](./media/sss-geometric-intuition.png){width="5.2in" height="2.33in"}

Raise the threshold to three, and the trick generalizes: instead of a straight line, use a curve with one more bend (a parabola), which takes three points to pin down uniquely rather than two. One or two points still leave every possible secret equally plausible — the curve simply isn't determined yet. This is the general pattern: a threshold of D is implemented as a curve that requires exactly D points to fix, with T points handed out, one per trustee, all lying on that same curve. Because the curve only needs any D of its T points — not a particular D, and not all T — the scheme absorbs losing up to T − D trustees exactly as §1.2 described.

Why partial progress isn't a thing here. A combination lock rewards partial knowledge — get two of three digits right and you are, in a real sense, close. A threshold secret share does not work that way. One trustee's point, or even D − 1 of them together, doesn't narrow the secret down to a short list of likely candidates; it leaves every possible value exactly as plausible as before. There is no partial credit, no "getting warmer," and no way to make attempts and rule out candidates one collusion at a time — the Dth point doesn't refine the answer, it is the precise moment the answer springs into existence.

shardic's actual implementation replaces "a line" or "a curve on a graph" with a polynomial of degree D − 1 evaluated over a finite field, applied independently to each byte of the DEK — the same idea above, made precise and computable. §3.2 picks up exactly there.

## 1.5 From Data to Capability: A Preview

Everything above frames the protected value as a file — an archive recovered, once, into plaintext on disk. That framing was never load-bearing for the underlying guarantee: what threshold recovery actually enforces is that a secret value comes into existence only when D independent parties each choose to contribute toward it. A file's plaintext is one instance of "a secret value" — not the only one. Section 4 makes that generalization explicit and names it: a shardic protected action code (SPAC) is any enabling value for a protected capability — financial access, a physical safety interlock, a sensitive document, an account credential, a network-path authorization — of which "decrypt this archive" is the narrowest possible case. Sections 2–3 describe the mature core exactly as it exists today; readers only interested in the file-vault tool can stop at the end of §3.





## 1.6 The Capability Stack: How the Layers Build on Each Other

It's worth naming the stack explicitly before working through it
section by section, since each layer changes what's actually possible
without invalidating anything the layer beneath it guarantees:

1. **Sharded protection** (§1–§3.5, implemented). The core guarantee: a
   secret is split so that no fewer than D of T independently held
   shares can ever reconstruct it, and below that threshold, zero
   information about the secret exists to extract. This alone is
   sufficient for the personal, estate, and business scenarios in
   §1.3 — a family splitting a password manager's master key, a
   company escrowing a root credential — using a shardic encryption
   key sourced however the trustee population actually operates
   (§3.3).
2. **shardic-envelope** (§3.6, implemented). Delivers a trustee's
   shardic encryption key wrapped in public-key encryption under a
   keypair the trustee already controls, removing the
   human-memorability ceiling that otherwise caps how strong a
   KDF-sourced key can practically be (§3.3 revisits what this changes
   about derivation-source selection in §5.2).
3. **Ceremony formation** (§3.7, implemented). Turns "who holds a
   shardic encryption key" from an ad hoc, once-per-vault trust
   decision into a tracked, repeatable process: candidate trustees are
   registered against an identity provider, a specific quorum is
   selected and invited for a given vault, declined or timed-out slots
   backfill automatically, and delivery of each wrapped key is a
   single-read, addressed event rather than an out-of-band handoff.
4. **SPAC** (§4, §6, design proposal). Generalizes the protected value
   itself from "a file's plaintext" to any enabling code for a
   protected capability, and generalizes the ceremony from one fixed
   shape into something tailorable per deployment — which trustees,
   which local-unlock factors, which RTO — to fit the CONOPS and
   embedment environment of a specific client system.

Each layer is a strict superset of the guarantees below it: nothing at
layer 2 weakens layer 1's information-theoretic threshold, and nothing
at layer 4 weakens layer 2 or 3's already-implemented mechanics. A
deployment can stop at any layer and still have a complete, sound
system — layer 4 is simply where this paper's remaining open work
lives.

![](./media/capability-stack.png){width="5.2in" height="5.16in"}

# 2. Concept of Operations

## 2.0 Scope of This Section: Mechanical Foundation, Not End Solution

This section describes shardic's mechanical foundation at the operator's level of abstraction — how a protected value gets created, distributed, and reconstructed — independent of any particular tool. The reference implementation's command-line and GUI tools carry out exactly this sequence; their flags, output, and installation are documented in the project README, not reproduced here. This mechanical foundation is an essential component of a protection system, not an end solution: a deployment must separately establish its authorization policy, trusted operating environment, identity and credential assurance, custody procedures, audit retention, incident response, and system-specific safety controls before a protected value or SPAC is used operationally.

## 2.1 Creating a Vault

An operator with a file or directory to protect decides on two numbers before doing anything else: how many trustees (T) will each hold a shardic encryption key, and how many of them (D) must agree to recover the data. Given those numbers, vault creation is a fixed sequence: the input is archived into a single blob and encrypted once under a randomly generated 256-bit data encryption key (DEK); that DEK is split into T Shamir shares at threshold D; each share is individually protected under its own shardic encryption key (§3.3); and the result is written as one self-contained `.krypt` file, plus one credential per trustee — whatever form that credential takes for the derivation source chosen (§3.3).

The operator's remaining job at this point is entirely procedural, not cryptographic: distribute each trustee's credential to exactly one trustee, out of band, over a channel that trustee individually controls, then delete any local copies. Who receives which credential, and how, is a trust decision that belongs to the operator, not the software — the tooling deliberately does not automate distribution.

## 2.2 Recovering a Vault

At recovery time, any D of the T trustees supply their shardic encryption key — the operator does not need to know or specify which D. Recovery does not ask "which trustee are you": it tries each supplied key, via its derived AES-GCM key, against every not-yet-matched share until one authenticates (§3.4). Keys can be supplied in any order, and if fewer than D of them match, or any of them are wrong, recovery reports how many were accepted and stops — it never produces partial or best-guess output.

## 2.3 shardic-prime: A Mandatory-Trustee Variant

The base scheme treats every trustee identically — any D of T shardic encryption keys recover the vault, full stop. shardic-prime is a separate variant that adds one essential trustee on top of the base scheme: the prime trustee's key must always be among those supplied, no matter how many other keys are gathered. The remaining trustees form an ordinary interchangeable pool for the rest of the threshold. This fits situations where one specific role — an estate's executor, an organization's security lead — must always sign off, while the people backing them up can be any qualifying subset. In T=4, D=3 prime-trustee terms, that means one prime trustee plus three pool trustees, and recovery needs the prime's key plus any two of the three pool keys.

All three pool keys, gathered without the prime trustee's, recover nothing — a property guaranteed by the construction itself (§3.5), not merely enforced by the tooling. As with the base scheme, recovery does not require the operator to say in advance which supplied key belongs to the prime trustee; it is identified automatically once decryption succeeds. §4 revisits the prime trustee's role directly — it turns out to generalize to a hardware-embodied instance without requiring any new mathematics at all.





# 3. Technical Mechanics

This section describes how the .krypt container actually protects data: how the data encryption key is generated, how Shamir's Secret Sharing protects its recovery, how each individual share is, in turn, protected by a shardic encryption key, and how the scheme has since extended into public-key-wrapped delivery and multi-party ceremony formation.

## 3.1 Archive and Data Encryption Key

Vault creation proceeds in a fixed sequence:

- The input file or directory is bundled with tar into a single blob, so any input shape — one file or an entire directory tree — is handled uniformly. The archive is deliberately left uncompressed (mode "w", not "w:gz") so ciphertext size does not vary with plaintext compressibility any more than strictly necessary — compression can otherwise leak information about content through size alone.

- A random 256-bit data encryption key (DEK) is generated using a cryptographically secure random source (secrets.token_bytes).

- The archive is encrypted exactly once, under that DEK, using AES-256-GCM with a randomly generated 96-bit nonce. GCM provides both confidentiality and built-in tamper detection: any modification to the ciphertext causes authentication to fail rather than silently decrypting to garbage.



At this point, the DEK is the single piece of secret material standing between the ciphertext and the plaintext — exactly as in conventional symmetric encryption. What differs from the conventional model is what happens to that key next.

![](./media/image1.png){width="5.2in" height="3.29in"}

## 3.2 Shamir's Secret Sharing over GF(256)

Rather than being stored or handed to a single custodian, the DEK is split using a byte-wise implementation of Shamir's Secret Sharing (SSS) over the finite field GF(2⁸) — the same construction used by classic tools such as ssss, and the same field arithmetic AES itself uses (generator 3, reduction polynomial 0x11B).

The construction, applied independently to each of the DEK's 32 bytes:

- Each byte of the secret becomes the constant term of a random polynomial of degree D − 1, with the remaining coefficients drawn uniformly at random.

- Each of the T shares is that polynomial evaluated at a distinct x-coordinate (1 through T), across all 32 byte positions simultaneously.

- Reconstruction takes any D shares and applies Lagrange interpolation at x = 0, independently per byte position, to recover the original secret byte.



Why this is information-theoretic, not merely computational. A polynomial of degree D − 1 is uniquely determined by any D points on it — but with only D − 1 points, every possible value of the constant term (the secret byte) remains equally consistent with those points. An attacker holding D − 1 shares therefore learns exactly zero bits about the DEK, regardless of computing power, time, or future cryptanalytic advances against AES itself. "Information-theoretic" security means a guarantee that holds regardless of computing power — not because breaking it is hard, but because the information needed to break it simply isn't there.

![](./media/image2.png){width="5.2in" height="2.42in"}

## 3.3 Shardic Encryption Key Protection of Shares

A raw Shamir share is still just data — if written to disk unprotected, whoever possesses D of them could reconstruct the DEK without any trustee's cooperation at all. Each share is therefore itself individually encrypted before being placed in the vault, under a 256-bit AES-256-GCM key held by that share's trustee: the **shardic encryption key**. What matters for the design's guarantee is only that each trustee holds one, independently — not how any given trustee's key came to exist. Four derivation sources are named here as the pluggable mechanism this protects against a single implementation choice going stale; a deployment picks whichever fits its trustee population and CONOPS, and can mix sources across trustees in the same vault:

- **KDF from a memorized or transcribed secret** — the scheme implemented and demonstrated today. A random, human-typeable secret (a **codeword**, in this project's own terminology — see Appendix B for its three generation modes) is generated for the share, a random salt is generated, and a 256-bit key is derived from the two using PBKDF2-HMAC-SHA256 (400,000 iterations by default) or Argon2id (time_cost=4, memory_cost=256 MiB, parallelism=4 — memory-hard, and preferred when the optional argon2-cffi package is available). This is the only source of the four that asks a trustee to recall or transcribe anything; §5.1 discusses why its strength, not the Shamir/AES layer, is the design's real computational bottleneck.

- **shardic envelope** — a full-strength key drawn from a CSPRNG, with no wordlist step and no KDF stretching, delivered to the trustee public-key-wrapped rather than memorized. §3.6 describes the delivery mechanism; §4.7 states the SPAC-specific default and its rationale; Appendix B gives the fuller treatment of when the codeword alternative is preferable.

- **External token** — the key is sourced from, or released only by, a hardware credential the trustee already holds (a PIV/FIDO2 device, an HSM, a shardware-token per §4.3), rather than generated by this project's own code at all. Useful wherever a trustee population already operates as cryptographic identities with standing tooling, and the deployment would rather reuse that infrastructure than stand up a parallel one.

- **Other mainstream key-generation or derivation mechanisms** — an explicit extensibility point, not a fixed list. Share protection only ever needs a 256-bit AES-GCM key from somewhere; an enterprise KMS-issued key, a PKI-issued credential, or any other standards-based mechanism a deployment already trusts is as valid a source as the three named above, provided the resulting key is generated and held with comparable rigor.

The share (its x-coordinate plus its 32 y-bytes) is encrypted with AES-256-GCM under the resulting key, using its own random nonce. The vault records, per share, only an opaque triple: {salt, nonce, ciphertext} for a KDF-sourced key, or {nonce, ciphertext} for a key that skips the KDF step entirely (§4.7). Which derivation source, KDF method, and parameters were used are recorded once in the container's metadata — self-describing, so recovery never needs to be told out-of-band which settings a given vault used.

![](./media/image3.png){width="5.2in" height="4.11in"}

## 3.4 The .krypt Container and Zero-Leakage Indexing

All of the above — metadata and ciphertext — is bundled into a single .krypt file: an 8-byte magic header, a length-prefixed JSON metadata block, and the raw AES-GCM ciphertext of the archive (stored as raw bytes, not base64-encoded, avoiding a ~33% size penalty). This is deliberate: there is exactly one file to copy, email, or upload, with nothing to accidentally separate from a companion metadata file.

The metadata's list of protected shares carries no mapping from record to trustee, and no mapping from record to shardic encryption key — each entry is simply an opaque {salt, nonce, ciphertext} triple, and the order of entries in the file is randomly shuffled at creation time. Recovery works by trial matching: each key the operator supplies is tried, via AES-GCM, against every not-yet-matched share record in the vault. GCM's authentication tag makes this a reliable oracle — the correct pairing decrypts successfully, and every incorrect pairing fails fast with an authentication error rather than producing plausible-looking garbage.

With T in the tens, this exhaustive trial is effectively instantaneous, and it has a meaningful security consequence: the .krypt file, examined on its own, reveals nothing about which share belongs to which trustee, or how many keys would need to be compromised together to threaten a specific subset of the data.

![](./media/image4.png){width="5.2in" height="4.00in"}

## 3.5 How shardic-prime Varies

shardic-prime layers a one-time-pad mask over the ordinary Shamir construction described above, rather than introducing new field arithmetic. Given the DEK as the secret:

```
mask          = random bytes, same length as the DEK
masked_secret = DEK XOR mask
pool_shares   = split_secret(masked_secret, pool_threshold, pool_size)
```

The prime trustee's shardic encryption key protects mask directly — an all-or-nothing pad, not a point on a Shamir polynomial. Recovery requires both mask and at least pool_threshold pool shares:

```
masked_secret = reconstruct_secret(pool_shares)
DEK           = masked_secret XOR mask
```

Without mask, the pool shares — even all of them — reconstruct only masked_secret, which is uniformly random and indistinguishable from noise without the mask to remove. Without at least pool_threshold pool shares, mask alone reveals nothing either. Both halves of the construction retain the same information-theoretic guarantee as the base scheme; layering them is what makes the prime trustee mathematically essential rather than merely conventionally required.

![](./media/image5.png){width="5.2in" height="3.33in"}

This one-time-pad construction turns out to be the load-bearing piece of everything in §4: because mask is just a value, nothing about reconstruct_secret_with_prime() requires that value to be held by a human. §4.2 reuses this exact code, unmodified, to bind the same mathematics to a piece of hardware instead.

## 3.6 shardic-envelope: Public-Key-Wrapped Delivery (Implemented)

§3.3 named the KDF-from-a-memorized-secret source as the one that asks a trustee to recall or transcribe something, and §5.1 establishes that this individual key's strength, not the Shamir/AES layer, is the design's real computational bottleneck for that source. shardic-envelope removes that ceiling entirely for trustees willing to hold a cryptographic keypair, by wrapping each trustee's shardic encryption key in public-key encryption under a key they already control — rather than under a memory limit. As of this writing, shardic-envelope is implemented and demonstrated end-to-end (shardic_envelope_crypto.py, demo/combiner/app.py), not merely proposed.

- Operates strictly on the output of vault creation — the plaintext credential a trustee would otherwise have received — rather than modifying vault_core.py itself, so the existing encrypt/split/KDF path is untouched and the base scheme's guarantees are unaffected.

- Wraps each trustee's key in a hybrid, ECIES-style envelope (X25519 ECDH + HKDF-SHA256 + AES-256-GCM), deliberately shaped to mirror the vault's existing {salt, nonce, ciphertext} share-record convention rather than inventing a new format.

- The combiner — the service that holds .krypt ciphertext and every wrapped envelope, and orchestrates registration and recovery — never receives a plaintext shardic encryption key at any point, only shards derived locally by each trustee and re-wrapped for the combiner's own public key on the way back.



Recovery is unchanged from a trustee's point of view in the base scheme: they still supply a plaintext key or its derived shard. What changes is provisioning — the trustee's own device decrypts an envelope locally, once, to obtain the value they would otherwise have had to memorize, transcribe, or otherwise handle themselves.

## 3.7 Ceremony Formation, Credentials, and Delivery (Implemented)

§3.6 raises two questions that a follow-on design phase answers with running code, not just a sketch: how does a trustee's public key get established and trusted in the first place, and how does an operator convene a specific quorum of trustees for a given vault rather than improvising trust decisions ad hoc each time?

- Registration. Candidate trustees are drawn from a dedicated Keycloak group, queried via a read-only service account scoped to that group. Each trustee's keypair is generated client-side only — the private key never transits, or is even briefly held by, any server shardic controls. This deliberately keeps identity/selection (Keycloak's job) cleanly separated from key custody (never Keycloak's job).

- Ceremony formation. An operator (authenticated via a dedicated shardic-operator realm role) selects T primary trustees plus an ordered backup list from the registered candidate pool, and issues invitations. Declined or timed-out invitations backfill automatically from the ordered backup list — race-safe, so a late acceptance from an already-backfilled slot is rejected rather than silently double-filling it. An explicit separation-of-duties check blocks the operator who forms a ceremony from also self-selecting as one of its trustees.

- Delivery. Wrapped envelopes are deposited at an authenticated, single-read drop point, addressed by trustee identity rather than a contact channel. The trustee fetches their own envelope themselves, once. "Exactly once" redemption functions as a detection mechanism — a second read attempt on an already-claimed envelope is a signal something is wrong.

- Recover. Unaffected. §2.2's walkthrough describes the same underlying act either way.



![](./media/ceremony-envelope-flow.png){width="5.2in" height="4.52in"}

The organizing principle across all of this: identity and selection stay cleanly separated from key custody, and both stay separated from the offline, fail-closed recovery math described in §3.1–§3.4. A compromised identity provider or a stalled ceremony can block provisioning; neither can, on its own, weaken the D-of-T guarantee itself. §4 builds directly on top of this ceremony-formation machinery — it is reused unmodified for the pool-trustee side of a SPAC ceremony.


# 4. The SPAC Ecosystem: Extending shardic Beyond File Decryption

Status: design proposal.

We've established a functional baseline for multi-entity enforced access. What follows is a technologically sound manifestation of that capability into a practical working system. Though not yet fielded, there are no practical barriers to its implementation. The generalization matters most exactly where the stakes are highest and hardest to keep genuinely in human hands: high-value operations increasingly initiated, analyzed, or partly executed by AI systems, under time pressure that erodes purely procedural safeguards. §6.4 states that case directly once the mechanics below are in place; §5.5 names what a genuinely critical instance of it needs beyond the mathematics.



## 4.1 From Data to Capability: PT SPAC and CT SPAC

§1.5 previewed the reframe; here is the full statement of it. The plaintext shardic protects has never had to be a file — it is, more generally, the enabling value for some protected action: gaining financial access, arming a safety-critical system, unlocking a sensitive document, or granting account access, wherever "the right D-of-T parties agreed" should be the actual gate on the action, not merely a procedural approval layered on top of it. A shardic protected action code (SPAC) names that enabling value; PT SPAC and CT SPAC name its plaintext and ciphertext forms, in exactly the same relationship as any other plaintext/ciphertext pair in this project. "Decrypt this file" is simply the special case where the protected action is "the codeword holder gets to read the plaintext" — the same mechanism, applied to the narrowest possible action.

This reframe has real precedent outside cryptography. Permissive Action Links (PAL) — a code required to authorize a safety-critical action, withheld until an authorized multi-party release procedure completes — is the closest existing analog for gating a capability rather than merely data. Two-Person Integrity / the Two-Man Rule is the vocabulary for what the trustee threshold, plus the separation-of-duties enforcement already described in §3.7, already implement.

## 4.2 The Shardic Client Module and the Fielded Prime Element

A consuming system — the thing that actually executes the protected action — is built with a "plugin" at the critical-path point where the PT SPAC is needed. During development and test, the real PT SPAC sits in that pipeline directly, so the system can be validated end-to-end. Before fielding, PT SPAC is swapped for a CT SPAC embedded in a shardic client module at that same plugin point.

Fielded-system binding is the property that makes this safe to field at all: a copied CT SPAC, combined with a fully legitimate D-of-T trustee quorum, must not be sufficient to arm the protected action on a different instance of the client module than the one it was emplaced into. This needs no new cryptography — it reuses §3.5's mask/pool one-time-pad construction unmodified, with one substitution: the fielded system's own hardware-sealed secret stands in for mask.

```
mask        = the fielded system's own hardware-sealed secret
              (PUF/secure-element, non-extractable, generated once at
              emplacement, never leaves this hardware, never typed by
              a human, never a codeword)
pool_shares = ordinary trustee shares, delivered by shardware-token or
              network exactly as in §3.6-3.7
DEK         = reconstruct_secret_with_prime(mask, pool_shares)  -- unmodified
CT_SPAC     = AES-256-GCM(PT_SPAC, DEK)                         -- unmodified
```

Copy CT_SPAC to different hardware and bring a full legitimate trustee quorum along; reconstruction still fails, because mask is bound to one specific piece of silicon and was never extractable from it. This design is deliberately scoped to one specific piece of hardware, full stop — no multi-unit redundancy. If the fielded hardware is replaced, mask is gone with it; there is no export path.

## 4.3 shardware-token: Hardware-Based Ceremony Variants

Two variants exist for how a physical hardware token participates in a ceremony, differing in how much trust the token itself has to carry:

### Physical carriage

A hardware token can simply be the transport for an already-wrapped shard, replacing a network hop with a courier, hand-off, or safe-deposit retrieval — useful for a ceremony that wants to run entirely air-gapped past registration. The token itself can be genuinely dumb storage: since the shard is already public-key-wrapped before it ever reaches the token, there is nothing unencrypted on it to protect.

### PUF-sealed embed/extract

A hardened variant answers the identity question cryptographically instead. The token generates its own keypair locally at "embed" time (vault creation), receives a shard wrapped to that keypair, and seals it into PUF/secure-element-backed storage that requires a matching physical measurement of the chip itself to ever reproduce the storage key. At "extract" time (recovery), the token only releases its shard against a vault-signed extraction grant: a short-lived, token-bound, nonce-fresh authorization, chained back to a rarely-touched root signing key through an intermediate that is rotated on a policy schedule rather than touched per ceremony.

## 4.4 Roles and Governance

A SPAC ceremony introduces roles beyond the trustee/operator pair already established in §3.7, each answering a distinct question and each deliberately kept separate from the others so that no single compromised role can undermine the whole ceremony:

| Role | Answers | Held by |
|---|---|---|
| Trustee (pool) | Who must jointly agree to recover? | Ordinary shardic-envelope trustees, unchanged from §3.6–3.7 |
| Fielded Prime Element | What binds recovery to one specific piece of fielded hardware? | The fielded system's own sealed secret — never a party at all |
| Local custodian | Who is physically present to authorize the fielded hardware's own local unseal? | Whoever holds the deployment's chosen possessed (key/token) or known (PIN/passphrase) factor — a role, not an identity |
| Operator | Who authorizes a given extraction request? | A single, on-call shardic-operator-equivalent role, barred from authorizing a grant naming their own token |
| Approver | Who attests that the value being protected is the correct, tested one? | An authority independent of whoever performs the wrap/emplacement step, holding a distinct signing key from the extraction-grant chain |



The Approver's role deserves particular emphasis because it closes a gap that is easy to miss: AES-256-GCM already guarantees that a CT SPAC decrypts to exactly what was originally encrypted, or fails loudly — but it says nothing about whether what was encrypted was correct in the first place. An accidental stale value, or a malicious substitution at wrap time, would otherwise sail through untouched. The Approver signs a commitment to the validated PT SPAC at approval time, independent of the wrap operator; that commitment is checked once, slowly and thoroughly, at emplacement, and again, cheaply and quickly, at every arming event via a fast wrapped-MAC derived from the same approval.

## 4.5 Availability, Latency, and CONOPS Trade-offs

Not every SPAC deployment has the same tolerance for how long a ceremony takes. Rather than impose one universal answer, this design treats the target RTO (recovery time objective) as a per-deployment parameter, driven by the actual CONOPS — the concept of operations describing who the trustees, operator, and custodians really are, how they are staffed, and what infrastructure already exists to reach them.

Three points in a ceremony drive nearly all of the achievable latency:

- Convening the quorum. Pre-forming a ceremony ahead of the moment of need converts "select, invite, wait for acceptance" into a one-time setup cost paid before the RTO clock starts — the single largest lever available. An ad hoc, cold-start convening can take hours; a pre-formed, on-call quorum can respond in seconds to minutes.

- Share delivery. A network path is near-instant; physical carriage (§4.3) is inherently minutes to days, depending on distance and custody logistics. Air-gap independence and a tight RTO are largely mutually exclusive properties — a deployment chooses the one it actually needs.

- Endgame unlock. A single operator and a single local custodian are each fast, cryptographically sufficient decisions — but a lone authorized person who cannot be reached is a single point of availability failure, distinct from being a single point of authorization. An on-call backup roster for both roles protects availability without weakening the one-authorizer, one-custodian property at all.



None of these levers ever reduce how many independent parties are cryptographically required — every latency improvement here comes from pre-positioning and parallelizing already-required inputs, never from requiring fewer of them. Stating a target RTO is therefore also, implicitly, stating how much friction a given mission is willing to trade away — a decision the CONOPS has to make on purpose, not something this design should default on its behalf.





## 4.6 Non-Bypassable Invocation: Ensuring the Ceremony Cannot Be Skipped

Status: design proposal.

§3.1–§3.5 and §7.2 establish that below-threshold reconstruction is enforced by mathematics, not administrator trust — a claim about one specific bypass surface. A second, distinct surface exists wherever a SPAC ceremony gates one step in a larger operational sequence: a system that proceeds from an initial operating state, through one or more intermediate states, to a desired end state has a cryptographic guarantee about the ceremony only if the ceremony is actually invoked somewhere on the path to that end state. Nothing about a Shamir split, however unbreakable below threshold, prevents a different code path, a configuration flag, or a maintenance procedure from reaching the end state by a route that never calls the ceremony at all. This is a topological property of the surrounding system, not a cryptographic one, and it needs its own design treatment rather than being assumed as a side effect of §3–§4's cryptographic guarantees.

Four patterns bind the ceremony into the execution path with progressively stronger guarantees. They are not mutually exclusive — a fielded deployment typically layers more than one, and the strength of the composite is the strength of its weakest layer, not its strongest.

| Pattern | Mechanism | Bypass Resistance |
|---|---|---|
| Capability binding | The ceremony's protected value is (or unlocks) a value the end state structurally requires as an input — a signing key, a decryption key for the end state's own payload — rather than a boolean checked before proceeding | Medium: no path to the end state without the value itself, but only as strong as where that value is generated and held |
| Constrained state machine | The full operating sequence is modeled as an explicit graph with no edge that reaches the end state without passing through the ceremony, enforced by the same trust boundary that holds the ceremony's ciphertext | Medium: still an enforced check; tampering with the graph means tampering with the boundary that also protects the cryptographic material |
| Secure-element-internal sequencing | The Fielded Prime Element (§4.2) performs the end-state operation internally as a side effect of completing the ceremony; the outer system receives only the completed result, never the protected value or a pass/fail decision to act on | High: collapses the topological and cryptographic bypass surfaces into the same tamper-resistant boundary |
| Physical interlock | The end state's actuation circuit is physically incomplete until the ceremony asserts an unlock signal — a relay, key-switch, or discrete circuit closure | Highest: bypass requires physical intervention on the interlock itself, not software compromise |

The two hardware-anchored patterns are smaller extensions of designs already on the page than they might first appear. Vignette A's HSM-backed appliance (§6.1) and Vignette B's dual-key-switch secure element (§6.2) are already Fielded Prime Elements; secure-element-internal sequencing asks that same hardware to perform the disbursement signature or the interlock transition internally, rather than merely releasing a key to software that is then trusted to act on it correctly. The physical interlock pattern is a direct descendant of the Permissive Action Link precedent already cited in §4.1 — PAL systems have used physical arming-circuit interlocks for exactly this reason since long before threshold cryptography existed to protect the code that unlocks them.

Which pattern, or combination, fits a given deployment is a CONOPS decision in the same sense as §4.5's RTO trade-offs: capability binding alone may be sufficient where the consuming system's own code is already tightly controlled and audited, while a safety-critical interlock plausibly warrants the strongest tier regardless of that cost. §5.4 states precisely which guarantee each tier actually delivers.

## 4.7 SPAC Share Protection: Delivery, Entropy Source, and DRBG Parity with the DEK

Status: design proposal.

§3.3 named shardic envelope as one of a shardic encryption key's four derivation sources; a SPAC ceremony is where that choice actually matters most, because a SPAC's protected action can be materially more consequential than "a codeword holder gets to read a file" — arming a safety-critical system, releasing funds, granting account access. Two independent axes govern a trustee's actual protection value: *delivery* — whether it reaches the trustee memorized or shardic-envelope-wrapped — and *entropy source* — whether it is a human-shaped codeword stretched through a KDF, or drawn directly from an approved DRBG as a full-strength key with no wordlist step and no KDF stretching at all. A DRBG-sourced key cannot be memorized, so choosing it necessarily selects shardic-envelope or a shardware-token physical-carriage path (§4.3) for delivery; choosing shardic-envelope delivery does not, in turn, require a DRBG-sourced key — an ordinary generated codeword can still be wrapped for confidentiality in transit, exactly as it does in the base scheme today.

For a SPAC ceremony, the default on both axes is the high-assurance end: a DRBG-sourced key, drawn from the same class of CSPRNG already used to generate the DEK, every mask, and every nonce in this construction, delivered via shardic-envelope and used directly as the trustee's AES-256-GCM share-protection key. This gives a trustee's protection key parity with the 256-bit DEK it ultimately guards, rather than leaving the ceremony's weakest gate roughly 150 bits below every other layer in the same construction — no wordlist generation and no KDF stretching are applied, because neither serves any purpose against a value that is already uniformly random across the full key space.

A named, lower-assurance opt-out remains available: the same memorized-codeword protection implemented and used in the base scheme today, generated and tuned per Appendix B. It is the deliberately better choice, not merely a tolerated one, for a specific and recurring pattern of case — no persistent key material to seize, no credential-lookup trust boundary to stand up, no private-key custody burden on the trustee, relayability over any channel with no device dependency, or a trustee population with no standing cryptographic tooling — most concretely a communications-denied or device-hostile field deployment, the same operational context §4.1's Permissive Action Link precedent originates from. Appendix B gives the full case for each of those conditions, the worked field-deployment example, and the argument for why the codeword opt-out's lower bit count is an acceptable trade against the narrower, bounded attacker it actually has to survive — as distinct from the DEK/AES-256-GCM layer's unbounded, global-keyspace attacker, which is why the two are not held to the same bar.


# 5. Security Discussion

§5.1 analyzes shardic encryption key strength for the KDF-sourced case — a codeword or other memorized/transcribed secret run through a KDF — where a trustee generates, recalls, or transcribes their own secret by hand. A SPAC deployment can sidestep this discussion almost entirely by adopting §4.7's DRBG-sourced share protection — delivered via shardic-envelope, since a DRBG-sourced key cannot be memorized — in which case the computational side of §5.1's two-lever analysis is no longer the operative constraint. This is a SPAC-level choice, not an automatic consequence of using shardic-envelope generally: shardic-envelope's delivery mechanism (§3.6) composes equally well with an ordinary generated codeword, exactly as it does in the base scheme today — envelope changes how a value reaches a trustee, not what generated the value in the first place. §5.1 is retained for completeness and for the base scheme's own standalone use; codeword-mode selection and tuning specifics live in Appendix B; §5.2 states the practical, envelope-era picture directly. §5.5 closes this section with RAIN, the design framework this paper names for a genuinely critical SPAC deployment — the properties a deployment needs beyond the D-of-T guarantee itself.

## 5.1 Two Different Kinds of Strength: Key Length vs. Trustee Threshold

It is worth being explicit about which parts of this design are information-theoretically secure and which are only computationally secure, because they respond to completely different levers.

- The 256-bit DEK, and the Shamir split protecting it, are effectively unconditional: below the threshold D, shares carry zero information about the key regardless of an attacker's computing power, and AES-256 itself has no known practical cryptanalytic shortcut. Raising T or D changes how many independent parties must collude, not how hard any individual share is to attack directly — each is already effectively unbreakable on its own.

- Each individual codeword, by contrast, is only as strong as its own guessing space and KDF cost — this is ordinary computational security, and it is squarely the operator's responsibility to size correctly. Because shares are trial-matched independently (§3.4), a higher threshold D does not compensate for weak codewords: an attacker only ever needs to crack D individual codewords, each on its own merits, never the full set at once.



In short: raising trustee counts strengthens the collusion requirement; it does nothing for a codeword that is individually too weak. The two knobs must both be tuned, and neither substitutes for the other.

## 5.2 Impact of shardic-envelope and Ceremony Formation

Because §3.6's construction changes what protects a codeword — a private key instead of human memory — it changes the analysis in this section rather than sitting outside it. The direct security benefit is removing the memorability ceiling entirely: a codeword that only needs to survive one local decryption, immediately before use, can be made arbitrarily long and high-entropy with no usability penalty at all, pushing each individual KDF-sourced key's computational security arbitrarily close to §5.1's information-theoretic guarantee — collapsing the mode/length/count trade-offs Appendix B works through for the unwrapped case. That gain relocates rather than eliminates the trust dependency: the trustee's private key becomes a new single point of failure per share, and credential resolution introduces a new trust boundary of its own. Ceremony formation's separation-of-duties enforcement (§3.7) directly mitigates one specific instance of this: an operator who forms a ceremony cannot also self-select as one of its trustees, closing off the most direct form of operator self-dealing. §4.7 extends this trade-off specifically to SPAC ceremonies: DRBG-sourced share protection delivered via shardic-envelope by default, with the same memorized-codeword option available as a named opt-out — Appendix B gives the fuller treatment, including the field-deployment case where the memorized-codeword floor is the deliberately preferred choice, not merely an accepted compromise, and a worked explanation of why its lower bit count is an acceptable trade against the narrower threat it actually faces.

## 5.3 Security Considerations Specific to SPAC, Path Trustees, and Human-AI Policy Gates

Ordered-participation claims must be precise. A receipt chain can provide verifiable evidence that authenticated signers participated in a specified protocol sequence. Any security proof beyond that needs to incorporate security mechanisms suited to the purpose. If the goals are to prove physical network transit, payload inspection, or trustee independence, then system components can be layered in to support them. Bind receipts to a unique transaction, policy, predecessor, identities, time window, and endpoint; verify them server-side; reject replays; and retain independently protected audit evidence.

A normal D-of-T reconstruction condition allows any D valid shares as equally weighted peers. Requirements spanning trustee classes — such as an AI sub-threshold plus a human sub-threshold — need separate gates or a vetted access-structure scheme. The security plumbing has to account for any discrete policies around trustee shard incorporation in the ceremony. Treat the composition logic as security-critical, deny by default, and test missing, stale, duplicate, invalid, and wrong-role contributions.

AI is a bounded policy evaluator — it is objective and impartial, but not a substitute for human judgment and accountability. Its inputs, policy version, identity, attestation key, and output expiry must be authenticated and auditable. Ambiguous or conflicting evidence must fail closed. AI attestation should likely never be a sole enablement mechanism, able to bypass human quorum, endpoint binding, independent approver validation, or server-side authorization.

Non-repudiation is proof of a defined act, not intent. Cryptographic reconstruction can record authenticated contributions when each contributor uses a protected signing credential and the system retains verifiable evidence. It does not by itself resolve credential compromise, coercion, delegated access, or the legal meaning of a signature. Document these limits in the deployment CONOPS.

## 5.4 Bypass Resistance: Software vs. Hardware-Anchored Enforcement

Non-bypassability claims must specify which bypass surface they cover. §7.2's claim that threshold recovery “cannot be bypassed by any administrator, insider, or software defect” is exact for the cryptographic surface: no fewer than the required number of genuine shares will ever reconstruct the protected value, regardless of who administers the system. It does not, by itself, say anything about §4.6's topological surface — whether the ceremony is actually invoked on a given deployment's operational path.

Of §4.6's four patterns, capability binding and the constrained state machine are risk-reduction, not proof: both still rest on the integrity of the code that enforces them, and a sufficiently privileged insider who can modify that code can in principle modify the path around the ceremony as easily as around any other check. Secure-element-internal sequencing and the physical interlock are the only two that reach the same bar §7.2 claims for the threshold math itself, because bypassing them requires compromising the same tamper-resistant hardware boundary — or physically defeating a circuit — rather than modifying software logic that runs outside it.

A deployment that adopts SPAC to satisfy a genuine non-bypassability requirement, as opposed to a defense-in-depth improvement over the procedural baselines in §6.1–§6.2, should treat the software-only patterns as necessary but not sufficient, and select a CONOPS that reaches secure-element-internal sequencing or a physical interlock wherever the consequence of an undetected topological bypass would be unacceptable.

## 5.5 RAIN: A Design Framework for Critical SPAC Deployments

Status: design proposal, actively maturing — this section names and defines the framework; concrete notional employment models are a following pass, not exhaustive here.

§6.4's mutual-oversight pattern is only as trustworthy as the SPAC deployment carrying it. A deployment gating a genuinely critical decision — one where either failure direction in §6.4 would be unacceptable — needs to satisfy four properties together, not any one in isolation. **RAIN** names them:

| Property | States | Where this is defined |
|---|---|---|
| **R — Redundant** | No single instance of a trustee, evaluator, data feed, or delivery path is a point of failure for legitimate operation | New in this section |
| **A — Always-invoked** | The ceremony sits on every operational path to the end state; no route reaches the end state without it | §4.6's four bypass-resistance patterns |
| **I — Independent implementations** | Redundant components do not share a common-mode failure — different code, different vendors, or different reasoning paths, not just different instances of the same one | New in this section |
| **N — Non-bypassable** | Bypassing the ceremony requires compromising the same tamper-resistant boundary that protects the cryptographic material itself, not a weaker path around it | §5.4's bypass-resistance analysis |

RAIN is deliberately a *deployment* framework, not a cryptographic one: nothing about it changes the D-of-T guarantee in §1–§3, and a deployment that satisfies all four properties is not thereby cryptographically stronger than one that doesn't — it is topologically and operationally more trustworthy, in the same sense §4.6 already distinguishes a cryptographic bypass surface from a topological one. A deployment can adopt §6.4's pattern without satisfying RAIN — Vignettes A and B (§6.1–§6.2) already do, at a risk-reduction rather than a proof-grade level — RAIN is specifically the bar for the subset of deployments where that gap is unacceptable.

### Redundant

No legitimate-path component should be a single point of failure for the ceremony to complete — as distinct from §4.6/§5.4's non-bypassability, which asks whether an *illegitimate* path exists around the ceremony. Redundancy is about the ceremony's own availability, not its integrity:

- **Trustee redundancy.** Already established for the human/pool side by §3.7's ordered backup list and backfill; §6.4 extends the same requirement to the AI side — a single AI evaluator instance is a redundancy gap even where its verdict is individually trustworthy, since its unavailability alone should not stall, or force a bypass of, a ceremony that is otherwise ready.
- **Evaluator redundancy.** For the AI-validation direction specifically, more than one evaluator instance should be capable of producing the required attestation, so that one instance's outage, drift, or compromise does not become the deployment's reason to route around the AI gate entirely.
- **Data-feed redundancy.** §7.3 already flags AI trustee data-feed integrity as an open design question; a redundant deployment requires multi-source authenticated feeds, per that section's own stated mitigation, rather than a single feed the evaluator has no way to cross-check.
- **Delivery-path redundancy.** §4.5's network vs. physical-carriage choice should not itself be a single path for a critical deployment — an available fallback path for share/credential delivery keeps a delivery outage from becoming a forced choice between missing the RTO and skipping a trustee.

### Always-invoked

This letter is not new content — it is §4.6's existing four-pattern table (capability binding, constrained state machine, secure-element-internal sequencing, physical interlock), restated under the RAIN name because it answers exactly the question this letter asks: does every path to the end state actually pass through the ceremony? A critical SPAC deployment under RAIN should target at minimum the constrained-state-machine tier, and the two hardware-anchored tiers wherever the consequence of an undetected topological bypass would be unacceptable — the same guidance §4.6 already gives, now named as one quarter of a four-part bar rather than a standalone concern.

### Independent implementations

Redundancy alone is not enough if every redundant instance can fail the same way at the same time — the classic common-mode failure that N-version programming and diverse-redundancy safety engineering exist to address, applied here to a SPAC's trustee and evaluator population:

- **Diverse AI evaluators.** Where the AI-validation direction of §6.4 relies on more than one evaluator instance for redundancy, those instances should differ in more than deployment — different model families, different vendors, or a rule-based evaluator alongside a learned one — so that a single model's blind spot, training-data gap, or adversarial vulnerability does not silently defeat every redundant instance identically. A pool of identical model replicas satisfies Redundant without satisfying Independent implementations.
- **Diverse code paths for hardware-anchored enforcement.** Where §4.6's secure-element-internal sequencing or physical-interlock patterns are implemented across multiple fielded units, independent implementations means not every unit shares one firmware supply chain or one hardware revision as its sole common trust anchor, to the extent the deployment's threat model treats supply-chain compromise as in scope.
- **Independent approval chains.** §4.4 already separates the Approver role from the wrap operator for exactly this reason at the human level; Independent implementations asks the same question of any automated component in that chain — does a single compromised build pipeline, model checkpoint, or config file affect every redundant instance identically?

Independent implementations is the property most in tension with deployment cost and complexity, and the framework does not pretend otherwise: it is the natural next axis to scope explicitly per CONOPS, in the same spirit as §4.5's RTO trade-offs — how much diversity a given deployment can actually afford is a decision the CONOPS has to make on purpose, not something RAIN defaults on its behalf.

### Non-bypassable

Also not new content — this is §5.4's existing analysis, restated as RAIN's fourth letter: capability binding and the constrained state machine are risk-reduction, resting on the integrity of the code that enforces them; secure-element-internal sequencing and the physical interlock are the only two patterns that reach proof-grade non-bypassability, because defeating them requires compromising the same tamper-resistant boundary that protects the cryptographic material itself. A RAIN-qualified critical deployment should treat the software-only patterns as necessary but not sufficient, exactly as §5.4 already concludes.

### RAIN as a maturing framework

This section states the four properties and their relationship to already-designed material precisely; it deliberately does not yet enumerate concrete notional employment models — worked examples showing what a fully RAIN-qualified deployment looks like end to end, the way §6's vignettes do for the base mutual-oversight pattern. That is the next pass. What RAIN commits to now is the shape any such example will have to satisfy: redundant without a single legitimate-path point of failure, always-invoked on every operational route to the end state, built from independent-enough implementations that a common-mode failure can't defeat every redundant instance at once, and non-bypassable in the proof-grade, hardware-anchored sense §5.4 already defines — evaluated together, since a deployment strong on three letters and weak on the fourth has a gap sized by its weakest letter, not its average.


# 6. Notional Missions and Ceremony Lifecycle

Status: illustrative, notional.

All four vignettes below are constructed examples, not descriptions of any real system or deployment, intended to walk the full SPAC lifecycle against a concrete "as-is" baseline. Vignettes C and D extend the mission space into network-path integrity and hybrid human-AI decision governance — two employment patterns that the SPAC generalization in §4 makes possible but that have no analog in the file-vault core; §6.4, immediately before Vignette D, states the governing claim that vignette illustrates. Numeric trustee counts and thresholds are illustrative choices, not recommendations for any specific real-world case.



## 6.1 Vignette A: Escrowed Authorization of a High-Value Treasury Disbursement

Mission. A financial institution's treasury system can execute wire disbursements above a defined threshold only with genuine, non-bypassable multi-party authorization, replacing a conventional dual-control approval workflow.

As-is baseline. Two named officers each approve a pending disbursement in a web application. The control is enforced entirely by application logic and an audit log: a single compromised administrator account, a shared or hijacked session, or two coerced approvers acting under common pressure can produce two valid-looking approvals with no cryptographic guarantee that either approval reflects genuine independent intent. The audit trail records that two accounts clicked "approve" — it cannot prove that two independent human decisions actually occurred.

Notional shardic-SPAC design:

- PT SPAC: the treasury system's high-privilege disbursement-signing credential.

- T=5 pool trustees (treasury officers), D=3 pool threshold, plus one Fielded Prime Element embedded in the treasury platform's own HSM-backed appliance — the disbursement can never be signed on any other machine, even by the same five officers.

- Approver: the controller function, independent of whoever operates vault creation, cryptographically attesting that the wrapped credential is the correct, currently-authorized signing key.

- Ceremony formation: a standing, pre-formed quorum of treasury officers with an ordered backup list, per §3.7 — no ad hoc convening required at disbursement time.

- Operator: a compliance officer, authorizing each extraction request; barred from also being one of the five treasury-officer trustees.

- Local custodian: a data-center technician holding a physical key-switch at the appliance itself.

- Delivery and RTO: network share delivery (§4.3), targeting an RTO of minutes.



Lifecycle walkthrough. Approval — the controller validates the signing credential in a test environment and signs a commitment to it. Emplacement — the credential is wrapped as CT SPAC, split across the five officer-trustees and the appliance's Fielded Prime Element, and destroyed everywhere else. Fielded operation — the appliance runs normally, holding only CT SPAC. Ceremony — a disbursement above threshold triggers a notification to the standing quorum; three of five officers respond, the compliance officer authorizes the extraction grant, the on-site custodian's key-switch unlocks the Fielded Prime Element locally. Arming — DEK reconstructs, the fast wrapped-MAC check confirms the credential matches the controller's original approval, the disbursement executes, and every secret value involved is zeroized immediately after.

| Dimension | As-is (dual-control app logic) | shardic-SPAC |
|---|---|---|
| Protection | Enforced by software/process; bypassable by whoever administers it | Enforced by mathematics; below-threshold shares carry zero information regardless of administrator access |
| Safety | Silent failure modes possible if application logic has a bug | Fail-loud: AES-GCM authentication rejects any incorrect or tampered value outright |
| Assurance | Audit log proves which accounts clicked approve, not which people independently chose to | Non-repudiable: reconstruction is only possible if D independent trustees each supplied a genuine share |



## 6.2 Vignette B: Notional Safety-Interlock Release Authorization

Mission. A notional platform's safety interlock must transition from a safed to an operational state only upon a release-enable value becoming available, and only through the deliberate, independent agreement of multiple authorized parties — the same organizational problem Permissive Action Links (§4.1) solve, described here purely at the level of the authorization ceremony.

As-is baseline. A physical lock or sealed code, held by a single on-duty officer, released under a procedural two-person-rule enforced by human witnessing rather than any cryptographic mechanism. A single coerced or compromised individual with physical access, acting alone, can potentially defeat a procedural control; there is no mathematically non-repudiable record of which specific individuals authorized a given release, only paper logs and witness attestations that can themselves be falsified or coerced.

Notional shardic-SPAC design:

- PT SPAC: the notional release-enable value.

- T=5 pool trustees (a qualified duty crew), D=3 pool threshold, plus a Fielded Prime Element embedded in the platform's own secure-element hardware.

- Local custodian factor: dual key-switches (the "two local factors" option from §4.4), reflecting that a safety-critical interlock plausibly warrants the strongest available local control.

- Approver: an independent technical authority, distinct from the operational chain, attesting that the embedded value is the correctly certified one.

- Ceremony formation: a standing, pre-formed, on-alert quorum, targeting an RTO of seconds to low minutes.

- Operator: a command-authority representative, authorizing the extraction grant as the cryptographic analog of an authorized release order.



Lifecycle walkthrough. Approval — the technical authority validates and signs a commitment to the release-enable value. Emplacement — the value is wrapped as CT SPAC and split across the duty crew and the platform's Fielded Prime Element; the plaintext is destroyed everywhere else. Fielded operation — the platform holds only CT SPAC, indefinitely, with no live dependency on the crew, the operator, or the network. Ceremony — an authorized release order triggers convening of the standing duty crew; three of five respond, the command-authority operator authorizes the extraction grant, both local key-switches turn simultaneously. Arming — DEK reconstructs, the fast integrity check confirms the value matches the technical authority's original certification, the interlock transitions state, and every secret value is zeroized immediately after.

| Dimension | As-is (procedural two-person rule) | shardic-SPAC |
|---|---|---|
| Protection | A single coerced/compromised individual with physical access is a structural risk | Mathematically requires genuine independent agreement from D distinct trustees, not merely two people in a room |
| Safety | A wrong or substituted code may not be detected until use | Fail-loud at multiple points: AES-GCM authentication, plus an independent approver-signed integrity check before the value is trusted |
| Assurance | Paper logs and witness statements, alterable or coercible after the fact | A ceremony's participant set is a fact about which independent parties each supplied a genuine cryptographic contribution — not a claim resting on anyone's later testimony |



## 6.3 Vignette C: Trustee-Attested Participation Along a Trusted Network Path

Status: illustrative, notional. This vignette describes a protocol pattern layered on shardic; it is not shipped functionality. It does not claim that threshold sharing alone proves physical transit, route correctness, or content inspection.

Mission. A protected transfer must be released only after a defined set of independent, authenticated network trustees have participated in an ordered protocol. The objective is evidence of trustee participation and policy-controlled release, not a substitute for TLS, IPsec, routing security, or endpoint authorization.

Notional design. Each designated trustee node validates a transaction-bound request, its predecessor receipt, and the applicable policy before issuing a signed receipt. Receipts include a unique transaction identifier, route-policy identifier, predecessor commitment, trustee identity, timestamp, expiry, and replay-resistant nonce. The receiver verifies the complete ordered receipt chain, all signatures, freshness bounds, and the endpoint binding before releasing the protected action. A missing, duplicated, expired, invalid, or out-of-policy receipt causes a fail-closed halt.

Security boundary. A signed receipt establishes that its signer participated in the protocol; it does not establish that a human examined the payload, that the packet physically traversed a particular wire, or that a compromised trustee behaved honestly. These assurances depend on the authenticated node implementation, key custody, attestation where available, independent logging, and the deployment’s threat model. Use end-to-end encryption and standard network controls in addition to this pattern.

Figure 6.3. Trustee-attested network-path pattern. An ordered, transaction-bound receipt chain records authenticated participation by designated trustees. The receiver verifies identity, predecessor commitment, freshness, route policy, and endpoint binding before release. A missing or invalid receipt halts the ceremony.

Lifecycle. An approver signs the transaction policy and content commitment. The origin creates a fresh ceremony-bound request. Each trustee verifies the prior receipt and policy, then either adds a signed receipt or withholds it. The endpoint verifies the chain and its own local binding before requesting release. All denials and successful releases are logged with redacted, correlation-safe metadata. Secret material is zeroized after use.

## 6.4 The Governing Use Case: Enforcing Human-AI Mutual Oversight

Status: design proposal, illustrative synthesis of §4.1–§4.7 and §6.5 — no new cryptography.

Two-Person Integrity, cited in §4.1 as the closest existing precedent for a trustee threshold, was designed for a world where every party to a protected action is a human. That assumption no longer holds by default. A growing share of the courses of action (COAs) a SPAC might gate are now proposed, evaluated, or partly executed by an AI system — and the threshold construction in §1–§3 turns out to need nothing new to extend across that boundary. A trustee is, cryptographically, just a party that independently holds a shardic encryption key (§3.3) and chooses whether to contribute it; nothing in the math cares whether that party is a person or a policy-bound software agent. Assigning trustee classes deliberately — some slots human, some slots AI, composed with an explicit AND rule rather than blended into one threshold (§6.5) — is what turns the same D-of-T guarantee into an enforcement mechanism for two distinct, and directionally opposite, oversight problems:

- **Human-in-the-loop enforcement over an AI-initiated COA.** An AI system proposes, or is positioned to initiate, a consequential action — arming a capability, releasing funds, executing a decision. A SPAC ceremony requiring a threshold of independent human trustees means the action cannot execute on the AI's own confidence, speed, or internal state alone, no matter how certain the system is or how time-pressured the situation appears. This is not a policy that a sufficiently capable or sufficiently confident AI could argue its way around: the DEK simply does not exist below threshold (§1.2), so there is no code path, prompt, or internal state that reconstructs it without D independent humans each choosing to contribute.

- **AI validation as a check against a rogue human-initiated COA.** The converse case: a human trustee, or a colluding group of them below the human sub-threshold, is compromised, coerced, or acting in error, and attempts to authorize an action that should not proceed. An independent AI evaluator gate (§6.5), attesting only against allow-listed objective criteria applied to authenticated evidence, supplies a check no amount of human social engineering, authority, or urgency can talk it out of — it either finds the criteria satisfied from the actual evidence or it fails closed, with no mechanism for a human trustee, however senior or persuasive, to override that finding from inside the ceremony itself.

Neither direction is achieved by making shardic "smarter" — no anomaly detection, no learned policy, no model in the cryptographic path at all. Both are the same information-theoretic guarantee from §1.2, pointed in two directions by choice of who fills which trustee slot: below threshold, a class of party — human or AI — carries zero information toward reconstruction on its own, so neither class can act unilaterally, and neither can be talked, hacked, or hurried past the other. §6.5 walks this pattern through a full notional ceremony lifecycle; §5.3 states the security considerations specific to it; §5.5 names what a *critical* instance of this pattern — one where the consequence of a successful bypass in either direction would be unacceptable — additionally requires beyond the threshold math alone.

This is, deliberately, the same claim boundary §6.5 already states and this section does not relax: an AI evaluator is a bounded, auditable policy check, not an autonomous authority, and its role in either direction is to supply one gate among several server-side checks — never a sole enablement mechanism, and never a substitute for the human threshold it either receives from or defends against.

## 6.5 Vignette D: Hybrid Human-and-AI Policy Gates for SPAC Authorization

Status: illustrative, notional. This is a governance and protocol design, not shipped functionality. An AI evaluator is not an autonomous authority to perform a high-consequence action. This vignette is the illustrative case for the governing claim stated immediately above (§6.4), walked through a full ceremony lifecycle.

Mission. A SPAC-gated capability needs both objective checks and accountable situational judgment. Automated evaluators can apply narrow, pre-approved criteria to authenticated inputs; human trustees determine whether the action is appropriate in context and independently decide whether to participate.

Notional design. The objective and subjective conditions are separate, explicit gates. An AI policy evaluator produces a signed, time-limited attestation only when its allow-listed criteria are satisfied; ambiguity, invalid inputs, stale telemetry, conflicting sources, or evaluator failure produce no attestation. A distinct human trustee ceremony requires its own threshold of authenticated human contributions. The release service verifies both gates server-side before it reconstructs or releases the SPAC value.

This separation is important: an ordinary single D-of-T Shamir split does not encode class-specific requirements such as ‘all three AI checks and any two humans.’ Implement such a policy with separate cryptographic gates or a vetted access-structure construction, then compose them with an explicit AND rule. Do not represent the policy merely by setting D equal to the sum of desired contributions.

Figure 6.5. Hybrid human-and-AI policy gates. A bounded AI evaluator attests only when allow-listed objective criteria are met from authenticated evidence; an independent human trustee ceremony supplies situational judgment. The release service enforces an explicit AND rule across both gates and all server-side checks.

AI controls. AI evaluators must operate only on authenticated, provenance-recorded data; expose the policy version, evidence identifiers, confidence-independent pass/fail result, and expiry; be independently auditable; and have no authority to waive a missing human threshold. Training data, model behavior, and evaluation infrastructure remain potential attack surfaces and require their own governance, change control, monitoring, and rollback plan.

Lifecycle. The approver signs the ceremony template, objective-policy version, and protected-value commitment. The AI gate evaluates its defined evidence and either attests or fails closed. Human trustees receive the request context and the AI gate status, then independently contribute or withhold. The server verifies both thresholds, the Fielded Prime Element where applicable, identity and freshness controls, and the approver commitment. Only then can the action proceed; all secret values are zeroized and the event is logged.


# 7. Summary

## 7.1 What Sets This Apart From Conventional Symmetric Encryption

Conventional symmetric file encryption answers the question "how do we keep this secret?" shardic answers a different question: "how do we ensure no single party can unilaterally expose this secret — or invoke this capability?" The cryptographic primitives underneath — AES-256-GCM, a KDF, random key material — are entirely standards-based and standard. What is different is the structure of control imposed on top of them: the protected value never exists in a form any one party can extract, because it is never stored whole in the first place. It exists only fleetingly, in memory, at the moment enough independent parties have each chosen to contribute their share of it — whether that value decrypts a file, arms a protected action, attests to a payload's network transit, or satisfies a hybrid objective-and-subjective authorization gate.

Math beats policies and permissions for enforcement. This is a categorically stronger guarantee than access-control policies, multi-approval workflows, or organizational procedure layered on top of ordinary encryption — those are enforced by software or process and can be bypassed by whoever administers them. Threshold recovery below D trustees is enforced by mathematics and cannot be bypassed by any administrator, insider, or software defect in the recovery tool itself.

That enforcement property is what makes §6.4's governing use case possible at all: assigning trustee slots across human and AI classes turns the same D-of-T guarantee into mutual oversight — an AI-initiated course of action cannot execute without independent human agreement, and a rogue or coerced human-initiated one cannot execute without an independent AI evaluator's attestation — with §5.5's RAIN properties naming what a deployment needs beyond the mathematics for that guarantee to hold under real operational and adversarial conditions.

## 7.2 Advantages

- No lone-actor risk: recovery is mathematically impossible below the trustee threshold, not just procedurally discouraged.

- Graceful tolerance of trustee loss: any D of T is sufficient, so the design survives unavailable, incapacitated, or non-cooperating trustees up to T − D of them.

- Zero metadata leakage: the vault file alone reveals no trustee-to-share mapping, even under direct inspection or partial compromise.

- Self-describing recovery: KDF method and parameters travel with the vault, so recovery never depends on external configuration matching what was used at creation.

- A mandatory-signer variant (shardic-prime) is available without weakening the underlying guarantees, for cases where one specific role must always participate — and, per §4, that role generalizes to a hardware-embodied Fielded Prime Element with no new mathematics required.

- Fail-closed behavior throughout: insufficient or incorrect shardic encryption keys, unavailable KDF dependencies, or corrupted containers are reported explicitly and stop the operation — the design contains no silent-degradation path that would produce partial or misleading output.

- Generalizes past file decryption entirely: the same guarantee that protects a vault's plaintext can gate an arbitrary protected action, network-path integrity attestation, or a hybrid human-AI authorization ceremony, with the fielded-system-binding and approver mechanisms needed to do so safely already designed.

- Composable trustee classes enforcing mutual oversight (§5.5, §6.4): AI agents enforcing formally defined objective criteria, hardware relay nodes attesting to path integrity, and human trustees supplying irreplaceable situational judgment can all participate in the same threshold-recovery framework, with the mathematics enforcing that no single class can act without the others — a property no policy or workflow layer can match, and the specific basis for gating an AI-initiated course of action on independent human agreement and a human-initiated one on independent AI validation.



## 7.3 Limitations and Mitigations

- Codeword strength is the real bottleneck for the base scheme, though largely moot with more advanced shardic-envelope-based ceremony systems. The Shamir/AES layer is effectively unbreakable; an individual codeword is only as strong as its generation mode, length, and count. Mitigation: use adequate word count, prefer Argon2id where available, and adopt shardic-envelope (§3.6) for trustees who can bear key custody — Appendix B gives the fuller tuning guidance.

- This is a static, split-once design at its core. Revoking or replacing a single trustee requires a full re-split and re-distribution of a new vault; there is no live key-rotation or online quorum protocol. Mitigation: this tool is intentionally scoped to rare, high-stakes, offline "break-glass" access and deliberate-ceremony SPAC arming; frequent or live multi-party authorization should instead use threshold-signature schemes (e.g. FROST) or HSM-backed multisig.

- The .krypt container, and by extension a CT SPAC bundle, is a single point of availability failure even though it is not a single point of access failure. Mitigation: back up the container durably; there is only one artifact to protect.

- It doesn't scale limitlessly — the system is implemented with a ceiling at 255 shares, but this makes practical sense for operational realities that max out at double-digit trustee counts. Mitigation: use it where it fits; the ceiling is an operational-practicality boundary, not a cryptographic one.

- The SPAC extension (§4, §6) is, as stated throughout, an unimplemented design. Several parameters remain explicitly open rather than decided: the concrete LocalUnlockFactor category for a given deployment, the specific PUF/secure-element hardware to target, and the wire format for extraction-grant certificates. Mitigation: none of these gaps weaken the cryptographic core described in §3.1–§3.5, which every SPAC construction reuses unmodified — they are integration and deployment decisions, not open cryptographic questions.

- AI trustee data-feed integrity is an open design question. The hybrid human-AI trustee model (§6.5) introduces a trust dependency on the authenticated data feeds that AI trustees evaluate against. The specific architecture for feed authentication, AI trustee agent hardening, and the wire format for AI trustee share contributions are not yet designed. Mitigation: treat AI trustee agents as shardware-token equivalents (§4.3) and require multi-source feed authentication as a design constraint from the outset.

- Path-trustee chain liveness. An all-of-N (D = T) path-trustee configuration has no tolerance for unavailable relay nodes. Mitigation: register alternate-route trustees at ceremony formation for any hop where availability is a concern; set D < T where path-integrity enforcement can tolerate a redundant route.



Taken together, these limitations describe the boundary of the problem this design is built to solve — rare, high-stakes recovery and authorization requiring genuine multi-party agreement — rather than deficiencies within that boundary. Within it, the core guarantee stands on solid ground, whether what it protects is a file's plaintext, a protected action's enabling code, a network payload's chain of custody, or a high-consequence authorization that must be both objectively verified and humanly judged before it can proceed: no fewer than D independently held contributions will ever bring that value into existence, and that guarantee does not degrade, weaken, or silently fail under any of the failure modes considered in its design.



## Footnotes



* Conservative withholding policy (§6.5): ambiguous, conflicting, or unavailable AI trustee data feed inputs cause share withholding rather than contribution.

† Any 2 of 4 human trustees are sufficient for D_H in the representative §6.5 configuration. The remaining 2 may withhold without blocking reconstruction, provided D_AI is also satisfied.

‡ The combiner verifies the combined receipt set (§6.3) independently of each individual node's local verification. A node cannot produce a valid C_n without the predecessor's actual signed output.

§ The combined reconstruction gate at Tier 3 of Figure 6.5 is a defensive invariant check. If both Tier 2 sub-threshold gates passed, this gate is algebraically guaranteed to pass for the representative configuration shown.


# 8. Related Work and Differentiation

Status: self-assessment.

§1.3 already draws one boundary in passing — this design is a poor fit for live, rotatable, online quorum, where threshold-signature schemes or HSM-backed multisig are the better tool. What follows makes that comparison complete rather than a single caveat, across every category of existing multi-party secret protection this paper is aware of, and then states plainly what survives that comparison as actually new — the part worth continued investment, as distinct from the part that is simply a well-built implementation of known techniques.

## 8.1 The Landscape

| Category | Representative Examples | Core Mechanism | Overlap With shardic | Where It Diverges |
|---|---|---|---|---|
| Raw Shamir's Secret Sharing implementations | `ssss` (Poettering); assorted per-language SSS libraries | The same GF(256) polynomial construction as §3.2 | Identical mathematical core; shares carry zero information below threshold | Primitive only — no container format, no codeword-derived share protection, no zero-leakage indexing, no ceremony lifecycle, no generalization beyond a single split |
| Secrets-management platforms with Shamir-based unseal | HashiCorp Vault's unseal-key mechanism | M-of-N key shares, distributed once at initialization, unseal a running service's own master key | Same underlying math protecting a root secret | Protects a live server's restart step, not a portable standalone artifact; unseal keys are typically raw output known to belong to a fixed N, with no equivalent to §3.4's zero-leakage indexing; built for a service coming back online, not deliberate, rare, offline break-glass recovery |
| Multi-party approval in cloud KMS | AWS/GCP/Azure key policies requiring multiple IAM principals | Application/IAM-policy-layer gating of a sensitive operation | Multi-party gating of the same kind of sensitive action | Enforced by software policy, not information-theoretic math — precisely the "who administers it can bypass it" gap §7.1 names; requires live provider connectivity; no analog to Shamir's below-threshold zero-information guarantee |
| Threshold-signature / MPC schemes | FROST, threshold-ECDSA constructions, MPC custody platforms | Live, rotatable, cryptographically strong multi-party signing protocols | Strong multi-party control, already the better tool for the live/online case per §1.3, §7.3 | shardic is deliberately static and split-once; these solve the case shardic explicitly disclaims — a neighboring tool for a different operating profile, not a competitor |
| Enterprise HSM key-custodian recovery | M-of-N smart-card custodian schemes offered by HSM vendors for master-key backup/restore | Physical distribution of shares to named custodians, reconstruction only in a rare/emergency event | The closest commercial analog to §1.3's break-glass use case | Tied to one vendor's proprietary hardware and format; no equivalent to a portable, vendor-neutral, self-describing single-file container; no generalization beyond that one HSM's own key material |
| Cryptocurrency multisig / social recovery | Guardian-based smart-contract wallets, hardware-wallet multisig, BIP39 seed phrases (already compared directly in Appendix B) | Multiple independent signatures required on a transaction | Multi-party authorization as a governing concept | On-chain multisig requires several independent signatures, not reconstruction of one shared secret; no equivalent to zero-leakage indexing or a single portable ciphertext artifact |
| Two-Person Integrity / Permissive Action Link hardware | Fielded PAL systems (§4.1's cited precedent) | Dedicated, certified physical/electronic interlock hardware and procedure | The organizational "no single actor" pattern SPAC generalizes | Purpose-built, certified hardware for one specific mission, not general-purpose portable software; not designed to gate arbitrary capabilities the way §4.2's Fielded Prime Element abstraction is |

## 8.2 What Is Actually Novel Here

- **Zero-leakage indexing as a stated design goal (§3.4).** Brute-trial share matching against the AES-GCM auth tag, with no share-to-trustee mapping ever recorded, is not merely a possible property of Shamir's math — it is a deliberate choice this paper's review of §8.1 found no equivalent to. Most surveyed systems either record who holds which share for operational reasons, or sidestep the question because shares aren't a persisted artifact at all (the threshold-signature/MPC row).

- **The Fielded Prime Element hardware-binding construction (§4.2).** Binding reconstruction to one specific piece of fielded silicon by substituting the mask input with a hardware-sealed secret, reusing the mask/pool one-time-pad math completely unmodified, is a specific, non-obvious application of existing cryptography to a binding problem — not a new primitive, but a use of one that §8.1's categories don't address.

- **The SPAC generalization itself (§4.1).** None of §8.1's categories treats threshold secret sharing as a general capability-gating framework: each solves one fixed application (unseal, KMS approval, signing, wallet custody, one certified PAL mission). §4's formal structure — named roles (§4.4), a four-tier non-bypassable-invocation taxonomy (§4.6), two independent composable axes for delivery and entropy source unified in a single section (§4.7) — is what generalizes the pattern rather than instantiating it once more.

- **Composable trustee classes enforcing mutual oversight (§6.3–§6.5, §7.2).** Human, hardware relay/path, and bounded-AI-evaluator trustees participating in the same threshold framework under an explicit AND-composition rule across classes has no counterpart in §8.1 — and is particularly timely given the direction of "human-in-the-loop" governance requirements for autonomous and AI-assisted systems. None of §8.1's surveyed systems gates an AI-initiated action on independent human agreement, or a human-initiated one on independent AI validation, as the same enforced mathematical property.

- **RAIN as a named deployment framework for critical SPAC (§5.5).** None of §8.1's categories articulates redundancy, always-invoked coverage, implementation independence, and non-bypassability as one evaluated-together bar for a multi-party authorization deployment — each solves at most one or two of those properties, typically leaving the others as unstated assumptions.

These are this paper's own findings against the categories it surveyed, not a freedom-to-operate opinion or a patentability determination — both require patent counsel and a formal prior-art search beyond a whitepaper's own literature review.

## 8.3 Why This Differentiation Is the Better Investment

- The base scheme alone (§1–§3) sits on largely unprotectable ground: Shamir's construction is public, 45-year-old mathematics, and general-purpose implementations of it already exist as prior art (§8.1's first row). Funding that stops there funds a well-executed, useful, but not independently defensible reimplementation of a known technique — not an asset that compounds in value or supports an exclusive market position.

- The differentiation identified in §8.2 lives entirely in the SPAC layer — which is exactly the layer §9's TRL rating puts at TRL 2, architecture only, nothing built. A whitepaper description is evidence of conception, not a defensible or marketable asset on its own; a built, exercised, demonstrable implementation is what a later patent filing, licensing conversation, or acquisition discussion actually needs to point to.

- This is what reframes §10's PoC phases 2–4 as more than a maturity exercise: that funded work is specifically what converts the differentiated, higher-value layer from a paper description into a reduction-to-practice record — the concrete artifact that IP counsel, an investor, or an acquirer would want to see before valuing this above "a well-executed reimplementation of Shamir's Secret Sharing," which is a commodity buildable elsewhere for materially less.

- One item this framing surfaces without resolving: no license or IP-ownership terms currently exist for this project. That is a decision worth making deliberately — and ideally before any funded work adds patent-relevant material — since it determines who would hold rights to what continued development produces. §11 gives the fuller treatment, including one consequence of this whitepaper's own distribution that is time-sensitive independent of when that broader decision gets made.

# 9. Technology Readiness

Status: self-assessment.

This project's own Implemented / Design proposal / Illustrative legend (Reader's Guide) already separates what runs from what is specified from what is sketched. Technology Readiness Level (TRL) — the 1–9 maturity scale used throughout DoD and NASA acquisition — is a more granular, more widely recognized vocabulary for the same distinction, and the one a funder is likeliest to actually score against. What follows maps this paper's components onto that scale, states the specific basis for each rating, and is explicit about what a self-assessment can and cannot claim on its own.

## 9.1 Rating by Component

| Component | This Paper's Status | Self-Rated TRL | Basis |
|---|---|---|---|
| Base scheme, shardic-envelope, ceremony formation (§1–§3.7) | Implemented | TRL 4 — component/system validated in a laboratory environment | Running CLI and GUI frontends, packaged builds (AppImage; the Windows build script is written but has never been run, per the project's own open items), validated by repeated manual create→recover→diff round trips and `gf256_sss.py`'s built-in self-tests. Not rated higher: no automated regression suite yet, no independent or third-party cryptographic review, and no exercise outside the developer's own environment — nothing here has been through a "relevant environment" in TRL 5's sense. |
| SPAC core: Fielded Prime Element, shardware-token, non-bypassable invocation, roles and governance (§4) | Design proposal | TRL 2 — concept and application formulated | §4.2 documents that this reuses the base scheme's already-validated construction through one specific, unmodified substitution — the cryptography is not the open risk here. What is unbuilt is the system around it: hardware binding, role separation, extraction-grant ceremonies exist only as architecture. No code, no lab exercise of the SPAC system as a whole. Vignettes A and B (§6.1–§6.2) apply this same machinery through named roles and inherit this rating rather than earning a separate one. |
| Path-trustee network integrity; hybrid human-AI policy gates (§6.3, §6.5) | Illustrative, notional | TRL 1 — basic principles observed and reported | The individual building blocks — signed receipt chains, independent-gate AND composition — are established patterns on their own. Their specific combination here is sketched, not specified: §7.3 already names the wire format for AI trustee share contributions and the feed-authentication architecture as undesigned. Rated below §4 because §4 has reached architecture-level resolution (named roles, mechanism tables, threat trade-offs) that these two have not yet reached. |

## 9.2 Caveats on This Self-Assessment

- **Self-assessed, not independently validated.** A TRL determination that matters to a funding decision is normally produced or confirmed by an assessor independent of the team proposing the work. Treat the table above as a starting position for that conversation, not a substitute for it.
- **TRL measures what has been built and exercised, not how carefully it has been designed.** §4's unusual level of architectural detail for a TRL 2 item — role tables, threat trade-offs, a four-tier bypass-resistance taxonomy — reflects design rigor, not built-and-tested status. The rating tracks the latter only.
- **The scale doesn't natively distinguish "new idea" from "already-validated primitive, new integration."** §4's actual risk profile is the latter, per §4.2's documented substitution — the basis column exists specifically to carry that nuance, since TRL 2 alone would flatten it to look the same as an unproven concept.

## 9.3 Target TRL by PoC Phase

§10.2 below lays out four funding phases. Restated on this scale: Phase 1 closes the specific gaps — no automated test suite, no independent review — that currently cap the implemented core at TRL 4, moving it toward TRL 5. Phase 2 takes the SPAC core from TRL 2 to TRL 4 by building and exercising it, even against commodity hardware standing in for a not-yet-chosen secure element. Phase 3 moves that same system toward TRL 5–6 once it is validated against an actual target device rather than a stand-in. Phase 4 takes the two novel mission types from TRL 1 to roughly TRL 3, once a reference implementation and a real wire format exist to analyze rather than describe.

# 10. Path to Proof of Concept

Status: funding proposal.

Sections 1–3 describe a working system: implemented, self-tested, and validated by hand through repeated create-recover-diff cycles. Section 4 onward describes a design that reuses that same cryptographic core without modification — §4.2 is explicit that the Fielded Prime Element substitution needs no new cryptography — but exists today as architecture, not code. What follows states plainly what a proof-of-concept award would fund, in what order, and what it would produce, so that "design proposal" has a concrete path to "implemented" rather than remaining a permanent label.

## 10.1 What Funding Buys

The base scheme's maturity is not in question — that risk is already retired. What remains unbuilt is everything that turns "the mathematics generalizes cleanly" (§4.1–§4.2) into a fielded, demonstrable capability: the Fielded Prime Element binding, the shardware-token variants, the non-bypassable invocation patterns of §4.6, and the two mission types — path-trustee network integrity and hybrid human-AI gates — that have no analog in the file-vault core at all. None of this requires inventing new cryptography; all of it requires engineering time, integration work, and, for the hardware-anchored tiers, physical hardware to build against. That is what a PoC phase buys: not a research bet on whether the idea works, but the construction cost of a design whose cryptographic core is already proven.

## 10.2 Phased Roadmap

The phases below are ordered by dependency and by how much they de-risk before requiring hardware sourcing or novel integration work — each phase produces a standalone, demonstrable result rather than a partial system that only becomes useful once every later phase also lands.

| Phase | Focus | Builds On | Representative Deliverable | Target TRL Exit (§9) |
|---|---|---|---|---|
| 1 — Core hardening | Automated test coverage for `gf256_sss.py` and `krypt_container.py` (property tests: any D-of-T subset reconstructs, D−1 doesn't; round-trip and corruption-handling tests); published benchmark data for share generation, reconstruction, and Argon2id cost across representative T/D and hardware profiles | §3.1–§3.5 (implemented core) | A test-backed, benchmarked release substantiating the abstract's "largely-implemented" claim with evidence rather than assertion | TRL 4 → toward TRL 5 |
| 2 — First SPAC vignette, software-only | End-to-end build of one notional mission (§6.1's treasury disbursement is the natural first pick: no exotic hardware required, a commodity HSM or TPM stands in for the not-yet-designed PUF/secure-element target) — Approver/Operator role separation (§4.4), capability-binding-tier non-bypassable invocation (§4.6) | §3.6–§3.7 (shardic-envelope, ceremony formation) | A running demonstration of capability authorization, not file decryption — the first artifact that shows SPAC as more than a reframing | TRL 2 → TRL 4 |
| 3 — Hardware-anchored variants | shardware-token physical carriage (§4.3) first, since it requires no new trust logic; PUF-sealed embed/extract second, once a secure-element target and a hardware sourcing/partnership path are identified | Phase 2's Fielded Prime Element construction | Bypass resistance raised from Phase 2's "capability binding" tier to "secure-element-internal sequencing" (§4.6) against a real device, not a commodity stand-in | TRL 4 → TRL 5–6 |
| 4 — Novel mission types | Path-trustee network integrity (§6.3) and hybrid human-AI policy gates (§6.5) — the two mission types §6's introduction already flags as having no analog in the file-vault core | Phases 1–3's hardened, fielded SPAC foundation | The pieces of this design that are hardest to find prior art for (§1.3's related-work gap notwithstanding) built and demonstrable, not just specified | TRL 1 → TRL 3 |

Duration and cost per phase are deliberately left as proposal-specific parameters here rather than invented figures — in the same spirit as §6's illustrative T/D values, a number asserted without a specific funder, team size, and hardware-sourcing timeline behind it would be decoration, not information.

## 10.3 What This Roadmap Does Not Claim

Consistent with this paper's claim-boundary discipline (Reader's Guide), the roadmap above deliberately does not promise:

- **A path to classified or NC3-adjacent deployment.** Nothing in §4–§6 is designed against, or claims readiness for, a certified national-security accreditation regime. Vignette B (§6.2) is a notional safety-interlock pattern, not a proposal to touch an actual weapons-release system.
- **Compliance certification as a PoC deliverable.** A PoC phase produces working code and, where applicable, a mapping of its guarantees to a framework like NIST SP 800-207 — it does not produce an ATO, a FIPS validation, or a claim of "compliant" that only an accredited assessment can actually confer.
- **A committed hardware vendor or PUF technology.** §4.3's PUF-sealed variant names a category of mechanism, not a chosen part number; Phase 3 above treats vendor/technology selection as roadmap work, not a settled input.
- **Production hardening beyond PoC scope.** Each phase's deliverable is a demonstration sized to retire a specific risk, not a shipped, supported product — the gap between "PoC deliverable" and "fielded system" is real and is not closed by this roadmap alone.

## 10.4 Why Now

§1.1–§1.2 and §7.1 already make the underlying case: the gap between "administrative claim" and "cryptographic fact" is a real, quantifiable insider-threat and non-repudiation surface, and it exists in every organization that currently substitutes a witnessed procedure or an access-control policy for genuine multi-party mathematical enforcement. What has changed is not that argument — it is that §3's core is no longer speculative. A funder is not being asked to bet on whether threshold recovery generalizes past file decryption; §4's design already shows that it does, without new cryptography. The ask is narrower and lower-risk than that: fund the engineering to build what the mathematics already permits.

# 11. Intellectual Property and Licensing Posture

Status: open decision — deliberately unresolved.

§8.3 named this rather than resolved it: this project has no chosen license, no stated IP-ownership structure for future work, and — as of this writing — no patent filing behind the SPAC-layer novelty §8.2 describes, though pursuing one is a stated intent rather than an open question. What follows states the actual trade-off this decision turns on, is explicit about what is and isn't decided yet, and flags one specific, time-sensitive consequence of this whitepaper's own existence that is worth acting on before the licensing question itself is settled.

## 11.1 The Trade-off This Decision Turns On

This paper's stated goals pull in different directions here: awareness of a novel technology implementation favors making it inspectable; a fundable, IP-protected asset favors keeping the differentiated layer exclusive. Neither posture below is recommended over another here — that is the open decision — but each has a distinct cost against the other goal.

| Posture | Serves Awareness | Serves an IP-Protected Asset | Cost |
|---|---|---|---|
| Open core: base scheme (§1–§3) open, SPAC layer (§4+) closed | Base scheme — most of what demonstrates the core guarantee actually working — is publicly inspectable and runnable | SPAC layer, where §8.2's novelty claims live, stays exclusively controlled | Requires drawing and maintaining a clean boundary as the SPAC layer gets built out (§10 Phases 2–4); a boundary drawn wrong risks disclosing patent-relevant material inadvertently |
| Fully open | Maximum — everything, including future SPAC work, publicly inspectable | Minimal — no exclusivity to license, sell, or hold as a funding asset; monetization would have to come from services or support rather than the technology itself | Directly undercuts §8.3's argument that the SPAC layer's value depends on being a defensible, reduction-to-practice asset rather than a public description |
| Fully closed | Minimal beyond this whitepaper — no code to inspect or verify, weakening the credibility a working demo currently provides | Maximum — full exclusivity preserved for negotiation | Undercuts "awareness of a novel technology" directly; a funder or reviewer has only prose to evaluate until access is separately granted |
| Undecided (current state) | Whatever is already public stays public by default | Nothing forfeited, but nothing secured either — a later filing's priority date only protects what's disclosed as of that date | Not actually neutral: every commit and every distributed copy of this whitepaper made before a filing or a chosen license is a fact that could later matter to a patent's novelty/priority analysis, or to what a later-chosen license would be read to cover |

## 11.2 What Is Already Decided: Intent to Pursue Patent Protection

Unlike the licensing posture above, this part isn't open: pursuing patent protection for the SPAC-layer novelty in §8.2 — most plausibly the Fielded Prime Element hardware-binding construction and the SPAC generalization itself — is a stated intent. No provisional or non-provisional application has been filed as of this writing.

That gap between intent and filing is the one item in this section worth flagging as time-sensitive rather than merely open. §8.2 and §4 already describe the Fielded Prime Element and SPAC generalization in enough technical depth to function as a public disclosure once this whitepaper is distributed outside a confidential circle — and most patent systems outside the U.S. apply absolute novelty, where a public disclosure before filing forecloses patent rights entirely, with no grace period. The U.S. system's own grace period is narrower and more conditional than it's often assumed to be. This isn't a legal conclusion — it's a reason to treat "file before wide distribution" as the default assumption to bring to counsel, rather than a decision that can wait until after this document has already done its job of soliciting interest.

## 11.3 Recommended Next Step

Consult patent counsel about a provisional filing covering the SPAC-layer material before this whitepaper, or any version of it carrying §4/§8.2's level of detail, circulates beyond a confidential audience. A provisional application is comparatively low-cost and fast, preserves a priority date without requiring full claims or prosecution immediately, and — consistent with §9's TRL 2 rating for this layer — does not require the underlying technology to be built first. Where a funder or reviewer needs to see this level of detail before a filing is in place, an NDA is the standard alternative; which of the two (or both) fits a given conversation is exactly the kind of judgment call that belongs to counsel, not to this whitepaper.

## 11.4 What This Section Does Not Claim

- Does not claim a patent has been filed, is pending, or has been granted.
- Does not claim a license has been chosen for any part of this project's code.
- Is not legal advice. The trade-offs above are this project's own structural and business observations, not a legal conclusion — the actual decisions belong with IP/patent counsel.


# Appendix A: Shamir's Secret Sharing, Explained

§1.4 and §3.2 walk through Shamir's Secret Sharing (SSS) at the depth
needed to follow the rest of this paper. This appendix is the complete,
standalone treatment those sections point to — the same source
document maintained in the project repository as
`docs/sss_explained_for_shardic.md`,
reproduced here in full so the paper is self-contained.
For a code-grounded walkthrough of the same material — actual function
names, data shapes, and line-level detail from the current
implementation, extended through shardic-envelope and SPAC — see the
companion reference document `docs/shardic-cryptographic-path.md`;
this appendix stays at the conceptual level intentionally, so the two
complement rather than duplicate each other.

## A.1 The Problem It Solves

Say you have a secret — a key, a password, a number — and you want to split it among several people so that:

- Any **D** of them together can reconstruct it exactly.
- Any group of fewer than **D** learns *nothing* about it, not even a probabilistic edge.

That's a **(D, T) threshold scheme**: T total shares, D required to recover. Shamir's Secret Sharing (SSS), published by Adi Shamir in 1979, solves this using a simple fact from algebra: **a polynomial of degree D−1 is uniquely determined by D points, and completely undetermined by any fewer.**

## A.2 The Intuition, Before the Math

It's worth seeing *why* this works before the formula, because the obvious first guess at "splitting a secret into pieces" isn't it, and doesn't have the properties above.

**The obvious guess, and why it falls short.** Imagine cutting a secret key into equal chunks and handing one chunk to each trustee — or the slightly cleverer version, XOR-splitting, where each share is random and the last one is defined so that all of them XOR back to the key. Both can be made information-theoretically sound in the narrow sense that holding fewer than all the pieces reveals nothing. But both share the same structural flaw: they are **all-or-nothing** schemes. Reconstruction needs every single piece, with no way to ask for "any D of T." Lose one trustee, permanently, and the secret is gone forever — exactly the fragility a threshold scheme exists to avoid.

**The actual idea: hide the secret as a point only enough hints can locate.** Picture the secret not as a string of bytes but as a single point on a graph — specifically, where a straight line crosses the vertical axis. Draw that line so it also happens to pass through T other points, one assigned to each trustee. Handing a trustee "their" point tells them nothing on its own: infinitely many different lines pass through any single point, each crossing the axis somewhere completely different, so *every* possible secret remains equally possible. But hand over any **two** trustees' points together, and there is exactly one straight line that passes through both of them — which means there is exactly one place it crosses the axis. Two points determine a line; that's what makes D = 2 work.

![](./media/sss-geometric-intuition.png){width="5.2in" height="2.33in"}

Raise the threshold to three, and the trick generalizes: instead of a straight line, use a curve with one more bend (a parabola), which takes three points to pin down uniquely rather than two. One or two points still leave every possible secret equally plausible — the curve simply isn't determined yet. This is the general pattern: a threshold of D is implemented as a curve that requires exactly D points to fix, with T points handed out, one per trustee, all lying on that same curve. Because the curve only needs *any* D of its T points — not a particular D, and not all T — the scheme absorbs losing up to T − D trustees, something an all-or-nothing chunk or XOR split can never offer.

That curve is a polynomial. The next section makes it precise.

## A.3 The Precise Construction

You already know the geometric version from precalculus: two points determine a line (degree 1), three points determine a parabola (degree 2). In general, **D points determine a unique polynomial of degree D−1** — no more, no fewer. Shamir's insight is to hide the secret as the *constant term* of such a polynomial, then hand out points on its curve as shares.

1. To split a secret `S` into T shares with threshold D, build a polynomial of degree D−1:

   `f(x) = S + a₁x + a₂x² + ... + a_(D-1)x^(D-1)`

   where `a₁, ..., a_(D-1)` are **random coefficients**, and the constant term is the secret: `f(0) = S`.

2. Generate T shares by evaluating this polynomial at T distinct nonzero x-values:

   `share_i = (i, f(i))` for `i = 1, 2, ..., T`

3. Distribute one `(x, f(x))` point to each of the T trustees.

**Reconstruction:** given any D of these points, you can fit the unique degree-(D−1) polynomial that passes through them, using **Lagrange interpolation**, and evaluate it at `x = 0` to recover `f(0) = S`.

## A.4 Why Fewer Than D Shares Reveal Nothing

This is the part that separates SSS from "encryption" in the usual sense — it's not computationally hard to break with fewer shares, it's **information-theoretically impossible**.

With only D−1 points, there are infinitely many degree-(D−1) polynomials passing through them — one for *every possible value* of `f(0)`. Each candidate secret is equally consistent with the data you have. You haven't narrowed the search space at all; you've learned literally zero bits about `S`. This is a much stronger guarantee than most cryptography offers, where security rests on a hard computational problem (factoring, discrete log) that could in principle be broken by a smarter algorithm or bigger computer. Here, there's no algorithm to break — the information simply isn't present in D−1 shares.

It also means there's no such thing as partial progress. A combination lock rewards partial knowledge — get two of three digits right and you are, in a real sense, close. A threshold secret share does not work that way. D−1 points together don't narrow the secret down to a short list of likely candidates; they leave *every* possible value exactly as plausible as before. There's no "getting warmer," and no way to make attempts and rule out candidates one collusion at a time — the D<sup>th</sup> point doesn't refine the answer, it's the precise moment the answer springs into existence.

## A.5 Why GF(256) Instead of Real Numbers

If you did this arithmetic over the real numbers, you'd run into two problems: fractions creep into Lagrange interpolation, and floating-point rounding would silently corrupt the secret. So SSS is done instead over a **finite field** — a closed, exact number system with no rounding.

Shardic uses **GF(256)**, the finite field with 256 elements, which conveniently maps one field element to exactly one byte (2⁸ = 256). Every arithmetic operation — polynomial evaluation, interpolation — is closed within this system, so shares and reconstructed secrets are exact bytes with no precision loss. This is also *why* GF(256) has a hard structural ceiling: with only 256 possible nonzero x-coordinates (well, 255, since 0 is reserved for the secret's evaluation point), you can't hand out more than 255 distinct shares without either colliding x-values or moving to a bigger field (GF(2¹⁶)) or a prime-field construction. It's not a tunable setting — it's the size of the number system itself.

## A.6 How This Becomes Shardic

Shardic doesn't split your *file* with SSS — it splits the **encryption key**.

1. Your file is encrypted with **AES-256-GCM** under a randomly generated **Data Encryption Key (DEK)**. This is fast, standard symmetric encryption — SSS is never applied to bulk data because polynomial math over GF(256) doesn't scale to megabytes efficiently.
2. That 256-bit DEK is the "secret" `S` fed into Shamir's construction, split into T shares under threshold D — i.e., any D trustees can reconstruct the DEK; fewer cannot, even in principle.
3. Each share is further protected by a memorable **codeword**, run through a KDF (Argon2id or PBKDF2) so that possessing the raw share bytes isn't enough — you also need the human-memorized word.
4. At recovery time, once D correct codewords unlock D shares, Lagrange interpolation reconstructs the DEK, and AES-GCM decrypts the file.

So the security model has two independent layers stacked: **AES-GCM** protects the bulk data computationally (hard to break, but not impossible in principle), while **Shamir's Secret Sharing** protects the *key itself* information-theoretically (impossible to break with insufficient shares, full stop, regardless of computing power).

## A.7 Where Shardic Extends the Textbook Scheme

A few things shardic adds on top of vanilla SSS that are worth knowing, since they're not part of Shamir's original 1979 construction:

- **Zero-leakage indexing**: normally you'd store metadata mapping "codeword A → share 3" for lookup convenience. Shardic doesn't — it brute-trials each entered codeword against all unmatched share records, using the AES-GCM authentication tag as a correctness oracle. This means the metadata file itself leaks no information about which codeword belongs to which share, closing a side-channel that a naive implementation would otherwise expose.
- **shardic-prime**: a variant that designates exactly one trustee as the *mandatory prime trustee* — reconstruction fails without their codeword specifically, no matter how many of the remaining pool trustees are gathered. This isn't native to pure threshold SSS (which treats all D-of-T combinations as equally valid) and requires an additional constraint — a one-time-pad-style mask layered over the ordinary Shamir split — on top of the polynomial construction.
- **Entropy transparency**: the system warns rather than silently degrades if your chosen KDF parameters or codeword strength fall below a safe threshold — a UX layer around the crypto, not a change to the math itself.

## A.8 The One-Sentence Summary

Shamir's Secret Sharing turns "split a secret among T people, any D of whom can recover it" into a simple geometry fact — a degree-(D−1) polynomial needs exactly D points to pin down — and shardic uses that fact to protect not your file directly, but the single key that unlocks it, so that reconstructing access requires genuine cooperation among trustees rather than trusting any single point of failure.


# Appendix B: Codeword-Mode Selection, Tuning, and the Field-Deployment Case

§3.3 names KDF-from-a-memorized-secret as one of a shardic encryption key's four derivation sources, and §4.7 states, in summary, that a SPAC ceremony defaults away from it toward a DRBG-sourced, shardic-envelope-delivered key. This appendix gives the complete treatment §4.7 only summarizes: how a codeword is actually generated and tuned (§B.1–§B.2, applicable to the base scheme generally, not only SPAC), the full case for choosing the codeword opt-out deliberately in a SPAC deployment (§B.3), and the worked argument for why its lower bit count is an acceptable trade against the narrower threat it actually faces (§B.4–§B.5).

## B.1 Codeword Modes: Security and Usability Trade-offs

Three codeword generation modes are available, trading recall difficulty against density of entropy per character:

### Memorable mode (default)

Draws whole, real, unfiltered-by-length words from a dictionary — the bundled EFF long wordlist (7,772 words, ~12.9 bits/word) by default. This is the classic diceware approach: real words engage semantic memory in a way synthetic syllables do not, so a trustee can actually recall a phrase rather than needing to store it. It is also, per word, the strongest of the three sources — a larger, unfiltered candidate pool beats a length-filtered one.

### Dictionary mode

Words of exactly a specified length are drawn from a supplied wordlist file. Useful when every codeword should have a uniform visible shape, but filtering a natural-language dictionary down to one length typically leaves only hundreds to low thousands of candidates — roughly 8–11 bits per word, meaningfully weaker than memorable mode's unfiltered pool.

### Synthetic mode

Pronounceable random words are generated from an alternating consonant/vowel pattern at a specified length, with no dictionary at all. This produces far more combinations per length than a natural-language dictionary can (roughly 3.36 bits per character from the base alphabet sizes), but the syllables carry no meaning, making them denser but harder to actually remember than real words of equivalent length.

In every mode, word count is what actually establishes a real security margin — each additional word roughly multiplies the guessing space.

## B.2 Tuning Options

Beyond codeword mode and count, two further levers match protection strength to threat model and operating constraints: KDF selection and cost (Argon2id's memory-hardness resists parallel GPU/ASIC offline guessing far better than PBKDF2 at equivalent wall-clock cost), and trustee count and threshold (raising T − D increases tolerance for unavailable or lost trustees; raising D relative to T raises the bar for collusion at the cost of requiring more participants for every legitimate recovery). Because the KDF choice is fixed at creation time and recorded in the vault's own metadata, recovery always applies exactly the settings the vault was created with — no fallback, negotiation, or downgrade attack against the KDF is possible after the fact.

## B.3 The SPAC Field-Deployment Opt-Out

§4.7 states the SPAC default — a DRBG-sourced key delivered via shardic-envelope — and names the memorized-codeword opt-out only in summary. This section gives the fuller case.

That default is defensible, not merely tolerated, because the DEK/AES-256-GCM layer and the codeword-opt-out layer are not defending against the same adversary:

| Layer | Adversary | Search space | Why the required strength differs |
|---|---|---|---|
| DEK / AES-256-GCM | Holds only CT SPAC, no other angle of attack | Full, unstructured 256-bit keyspace | Nothing else stands between this attacker and the plaintext — the only layer that must resist a global keyspace search |
| Codeword / share record | Holds one stolen or leaked share record | Bounded, structured — a wordlist and word count, Argon2id-stretched per guess | Success yields one D-of-T point, worthless below threshold (§5.1); the search is real but bounded and cost-amplified, not global |

Pure-memory codewords remain available — named explicitly, not silently deprecated, and generated as in §B.1, protected by PBKDF2/Argon2id exactly as implemented today — as a **lower-assurance opt-out** for deployments where the trade below is the correct one to make for that CONOPS. It is the better choice, not merely an acceptable one, when:

- **No persistent key material should exist to seize.** A device holding a DRBG-sourced key, even envelope-wrapped, is a forensically imageable physical artifact. A memorized codeword leaves nothing on any device, anywhere.
- **Standing up a credential-lookup trust boundary isn't justified.** Envelope delivery depends on resolving "this trustee's current public key" via some directory or lookup service — itself a new attack surface, since a spoofed or compromised lookup would silently wrap a high-entropy key to the wrong recipient. A codeword requires no such resolution step to exist at all.
- **No private-key custody burden should be imposed on the trustee.** A DRBG-sourced key's confidentiality rests entirely on that trustee's continued, exclusive possession of an unwrapping private key; losing it destroys that share with no "try to recall it" fallback. A codeword has no equivalent single point of failure to back up, rotate, or lose.
- **The value must be relayable over any channel, with no device dependency.** A codeword can be spoken over a phone call, written on paper, or passed by courier with zero technology requirement at any step. A DRBG-sourced key requires a capable device at generation, at rest, and at unwrapping.
- **The trustee population has no standing cryptographic tooling or habits.** A codeword's participation bar is "can hold a memorized phrase"; a DRBG-sourced key's is "can safely custody a private key" — a materially higher bar for a duty crew, an estate's non-technical relative, or any trustee pool not already operating as cryptographic identities in their day job.
- **Setup friction must be minimized for a short-lived or ad hoc ceremony.** A codeword skips keypair generation, candidate-directory registration, and fingerprint verification entirely — relevant wherever §4.5's RTO/CONOPS analysis already favors minimizing convening friction over maximizing entropy headroom.

A concrete case bringing several of those bullets together at once: a SPAC ceremony's pool trustee operating in a communications-denied or device-hostile field environment — the operational context §4.1's Permissive Action Link precedent originates from. A device holding a shardic-envelope-wrapped or DRBG-sourced credential is a physical artifact: it can be seized, forensically imaged, or used as evidence of a trustee's role or affiliation independent of whether the wrapped envelope inside it is ever actually decrypted. A memorized codeword leaves none of that — nothing to seize, image, or subpoena — and can be relayed over any channel a trustee has available, including a single verbal exchange. It also sidesteps an availability risk unique to device custody: hardware surviving intact, undamaged, and un-confiscated from emplacement to an unpredictable future moment of use, in exactly the kind of environment §4.5 already notes trades availability for air-gap independence. PAL-class systems have historically favored memorized or verbally-relayed codes for this reason, predating threshold cryptography entirely; a SPAC deployment with the same operational profile has the same reason to opt out of the shardic-envelope/DRBG default.

## B.4 Why ~2^100 Is Enough for This Threat, Even Though It Isn't 2^256

It's tempting to read the codeword opt-out's bit count against the DEK's 256 bits and conclude it's simply weaker protection. That comparison measures the wrong thing, because it treats two defenses against two different attackers as if they had to clear the same bar.

The DEK/AES-256-GCM layer defends an attacker with no other angle of approach: holding only ciphertext, the full 256-bit keyspace is genuinely open to them, unstructured, with no shortcut available — the only layer in this construction that has to survive an unbounded, global search, so it has to be unconditionally strong.

A codeword defends a categorically narrower attacker: one who has already obtained a single stolen or leaked share record and is trying to crack just that one. Three structural facts bound this attack in ways the DEK's threat model simply doesn't have:

1. **The search space is combinatorial, not a raw keyspace.** The `--memorable` default (8 words from the EFF long wordlist, ~12.9 bits/word) yields roughly 103 bits before any KDF cost is applied — call it 2^100 in round terms.
2. **A single cracked record is worth exactly one D-of-T point.** Per §5.1's guarantee, that's zero information about the DEK below threshold, regardless of how many such records an attacker accumulates the same way. This doesn't mean raising D compensates for a weak individual codeword — it still has to clear its own floor on its own merits — but it does mean the *consequence* of cracking one record is bounded in a way the DEK's threat model has no analog for.
3. **Argon2id's memory-hardness makes each guess expensive in a way that resists exactly the kind of scaling that would matter here.** At this project's default cost (256 MiB, time cost 4, parallelism 4), a guess isn't a cheap hash — it's a fixed, unavoidable memory allocation per attempt, which is specifically what blocks the massive GPU/ASIC parallelism that makes a moderate, unstretched keyspace tractable.

Put concrete numbers on it: even granting an attacker a wildly generous, deliberately unrealistic 10^12 fully-Argon2id-stretched guesses per second against this exact configuration, exhausting a 2^100 space (~1.27×10^30 guesses) would take on the order of 10^18 seconds — roughly 30 billion years. And 10^12 guesses/second at 256 MiB each implies a sustained memory bandwidth on the order of 250 exabytes per second, dwarfing the aggregate memory bandwidth of the world's fastest supercomputers by many orders of magnitude — this isn't a "beyond current hardware" caveat, it's a physical-plausibility ceiling baked into the assumption itself. Any realistic Argon2id-cracking throughput is many further orders of magnitude below even that impossible starting point.

That's the actual basis for the trade: the attacker this layer has to survive was never going to approach the edge of a 2^100 space in the first place, so the nominal gap to 256 bits is not the operative number — time-to-crack against the real, bounded, memory-hard-gated attack is. Sizing the floor larger (more words, higher Argon2id cost) is still worth doing wherever a deployment can absorb the added recall or wall-clock burden, per §B.1/§B.2's tuning guidance — but that's headroom on an already-adequate floor, not a correction applied to an inadequate one.

## B.5 Is Eight Real Words a Realistic Memorization Target?

The cryptographic case above only holds together if a trustee can actually retain an 8-word codeword well enough to use it — otherwise the opt-out trades a real security floor for one that quietly erodes as people forget, mistype, or improvise. This is a different, narrower claim than the one this project has already answered in the negative: reaching genuine 256-bit-class entropy from unaided human memory isn't realistic for an untrained person, which is precisely why shardic-envelope exists rather than an argument this section disputes. The `--memorable` default's actual target is roughly 2^100 — 8 real words — a categorically smaller and more ordinary ask.

The relevant memory task is long-term retention through rehearsal, not one-shot recall. A trustee isn't asked to hear eight random words once and immediately recite them back — the discipline more often invoked to dismiss this (Miller's "seven, plus or minus two," a finding about *working memory* holding unrehearsed items for immediate use) doesn't describe what a standing trustee actually does, which is closer to how people already retain a bank PIN, a home alarm code, or a memorized passage: through ordinary, periodic repetition until it consolidates into long-term memory. Real dictionary words help specifically because they're meaningful rather than arbitrary — a trustee can turn eight words into a short mental sentence or image, a natural strategy most people already use unprompted for shorter lists (nobody needs training to remember a five-item grocery list by picturing a scene), categorically different from the deliberate, competition-grade method of loci trained memory athletes use for much longer, meaningless, exact-order sequences.

This word count also isn't a novel claim — it sits inside a range with two decades of real-world practice behind it. Diceware, the direct ancestor of `--memorable` mode's approach, has long recommended picking "the longest passphrase you feel comfortable remembering," suggesting six words as the standard target and, for its own long-term (10+ year) protection case, ten words — explicitly broken into two five-word chunks *for memorization purposes*. Eight real words sits inside that established range, not beyond it.

It's worth addressing the counter-evidence directly, since one well-known precedent points the other way at first glance: BIP39 cryptocurrency wallet seed phrases, whose standard guidance is to write the phrase down — on paper or metal, never digitally — rather than rely on memory, with memorization reserved for edge cases like crossing a hostile border, and even then only paired with a written backup, never as a sole record. That guidance is answering a harder and materially different question than shardic's codeword opt-out faces, on every relevant axis:

| Dimension | BIP39 seed phrase | shardic `--memorable` codeword |
|---|---|---|
| Length | 12, 18, or 24 words (128–256 bits) — already past the range this project agrees isn't realistically memorizable | 8 words (~103 bits) — inside diceware's own long-established memorable range |
| Tolerance for error | Zero — one wrong word typically derives a *different, wrong* wallet silently, often with no error at all | AES-GCM's auth tag detects a wrong guess unambiguously; recovery reports what matched and stops, nothing derives silently |
| Consequence of a mistake | Total, often-undetected loss of funds | A failed match — the trustee can retry with a corrected phrase; nothing is destroyed or locked out on a wrong attempt |
| Who must recall it, and how many | The single holder, in full | Any `D` of `T` trustees — this specific trustee's phrase doesn't need to survive alone |
| Rehearsal expectation | Often set once and not touched for years | A standing trustee role, naturally paired with periodic recall practice as an operational habit |

BIP39's caution is correct advice for the problem it is solving. It doesn't generalize to shardic's codeword opt-out, which targets roughly a third of the word count, fails safely and interactively rather than silently and catastrophically, and only ever needs to be one of several independent contributions rather than a single irreplaceable record. Eight real words, rehearsed the ordinary way a person retains any long-held credential, is a realistic target for the trustee population this opt-out is actually meant for.

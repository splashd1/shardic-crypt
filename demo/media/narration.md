# Narration script

Companion to `walkthrough.tape`. Each entry is keyed to the same step
numbers as `demo/README.md`'s Walkthrough and the `# SPLICE:` markers in
the tape. Written for the shardic-envelope ceremony lifecycle itself —
Podman/Docker/CLI mechanics are named only where they're literally how a
ceremony concept gets demonstrated (e.g. "pausing a container" is the
demo's stand-in for "a trustee goes silent"), never as the subject.

Short lines also appear burned into the terminal recording itself (via
`mock-shell.sh`'s `banner` helper). The fuller versions here are for
voiceover or on-screen title cards over the dashboard segments, where
there's room for a full sentence or two.

**1. The trustee directory.** Keycloak holds the roster of who's even
eligible to be invited into a ceremony — a directory, independent of the
vault itself. Nothing about a vault exists yet.

**2. Candidates come online.** Six of the seven named candidates start:
alice, bob, carol, dave, and erin as primaries, plus frank held in
reserve as the one name on the backup list. Grace, the seventh, stays
offline this run entirely — she's not part of this ceremony at all.

**3. Registration and the operator.** Each trustee generates its own
keypair the moment it starts and registers the public half with the
combiner — this is what lets a codeword be wrapped to a specific
trustee later, instead of the combiner ever holding one in the clear.
Acting on the vault from here on needs an authenticated *operator*, not
a shared secret.

**4. The ceremony is initiated — and erin is about to go silent.**
Before the ceremony even starts, erin's container is paused: not a
decline, just silence — she'll never see the invitation at all. The
operator names alice as the mandatory prime, bob/carol/dave/erin as the
pool, and frank as the (only) backup.

**5. Silence is a decline, and the backup list has a job.** Erin's pool
invitation lapses on its own timeout — the ceremony treats never
responding exactly the same as an explicit decline. The instant it
expires, the combiner backfills that slot from the ordered backup list:
frank steps into erin's place. Once every slot — prime and pool — is
accepted, the ceremony is formed.

**6. The vault is created — for the ceremony that actually formed.**
The pool that ends up holding shares is bob, carol, dave, frank — not
the pool originally proposed. Erin was backfilled out before this
moment ever happened.

**7. Nothing to leak.** Each trustee's codeword was wrapped to their own
registered public key, and the plaintext was destroyed the instant
every envelope was written. There's nothing sitting on disk in the
clear — not even for the combiner to read.

**8. The threshold, proven live.** The pool's threshold is 2 of its 4
members, plus the mandatory prime. Pausing dave and frank — simulating
them being unavailable — leaves exactly enough standing: alice, bob,
carol.

**9. Recovery: shards, never codewords.** Each live trustee decrypts
its own envelope locally and sends back only its shard — the
post-match Shamir value, never the codeword itself. The combiner
collects shards from alice, bob, and carol and nothing more.

**10. Finalized — and the record shows who was actually needed.** The
combiner combines the collected shards and decrypts. The trustees
actually used are exactly alice, bob, carol — dave and frank were never
called on.

**11. Byte-for-byte.** The recovered output is compared against the
original, not just checked for a 200 response — proving the full
threshold-recovery round trip actually reproduces the original data.

**12. Reset.** Tearing down returns the stack to a clean slate.

## Dashboard-specific beats (for the interleaved cut)

`capture_dashboard.py` now captures all of this for real and writes the
actual wall-clock offset of each beat to `dashboard-timeline.json` (a
~57s continuous recording in the run this was written against). The
beats below predate that capture and describe the same moments in
ceremony terms; match them against the timeline's keys
(`erin_paused`, `ceremony_formed`, `vault_created`,
`dave_frank_paused`, `shards_all_in`, `finalized`, `verified`, ...) when
cutting.

- After step 4: the ceremony diagram lights up with the initial
  invited/backup_queue state — a visual for "who was actually asked."
- During step 5: the diagram animating invited → expired → backfilled →
  formed is worth capturing *live*, in parallel with the CLI segment,
  rather than as a static after-the-fact cut — it's the clearest visual
  of "the backup list has a job."
- After step 8: dave/frank shown paused while alice/bob/carol stay live
  — the visual complement to "the threshold, proven live."
- After step 11: per `demo/README.md`'s "Live dashboard" note, the
  verify banner stays "pending" until `/admin/recovery/verify` is
  called separately (the byte-diff in step 11 never touches the
  combiner API). Treat that as its own beat if the dashboard segment
  should end on "verified" rather than "pending."

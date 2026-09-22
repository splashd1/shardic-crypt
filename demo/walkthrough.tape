# VHS tape for the shardic-envelope demo walkthrough (demo/README.md,
# "Walkthrough" section, steps 1-12) -- REPLAY edition.
#
# Types the exact same commands as demo/README.md, but runs against
# media/mock-shell.sh instead of a live stack: docker-compose, docker,
# and curl are shadowed by functions that replay real output captured
# from one clean live run (see media/fixtures/README.md for provenance
# and how to refresh it). No Docker/Podman/Keycloak needs to be running
# to render this.
#
# Why replay instead of live: deterministic (byte-identical reruns),
# fast (~1 min instead of ~10), renders on any machine, and no live
# Bearer token or session ever appears in the published video -- the
# token fixture is a labeled placeholder, not a real credential.
#
# Narration is deliberately about the shardic ceremony -- who's invited,
# who declines, how backfill and threshold recovery work -- not about
# Podman/docker-compose mechanics. Container pause/unpause is mentioned
# only as *the mechanism* for simulating a trustee going silent or
# unavailable, in service of the ceremony story, per project convention.
# Full narration script (for voiceover / dashboard title cards): see
# media/narration.md. Short in-terminal banners here are its summary.
#
# Install VHS: https://github.com/charmbracelet/vhs
# Render (from the repo root): vhs demo/walkthrough.tape
# Output path below is relative to wherever `vhs` is invoked from (the
# repo root, per the above) -- not relative to this file.
#
# This tape covers the CLI half only. The dashboard half (real, live --
# it isn't mocked) is captured separately by media/capture_dashboard.py
# (a Playwright script that drives one real live ceremony while
# video-recording the dashboard tab) and composed with this tape's
# output by media/compose_full_video.sh into
# media/demo-walkthrough-full.mp4. See media/README.md for the full
# pipeline. `# SPLICE:` comments below and media/narration.md's
# "Dashboard-specific beats" describe a finer-grained interleave (cutting
# into this CLI recording at each beat, using the real offsets
# capture_dashboard.py writes to media/dashboard-timeline.json) that
# compose_full_video.sh does NOT currently do -- it's a straight
# two-act composition instead. Worth building if the two-act cut isn't
# enough.

Output demo/media/demo-walkthrough.mp4

Require bash

Set Shell bash
Set FontSize 16
Set Width 1280
Set Height 1000
Set Padding 20
Set Theme "Catppuccin Mocha"
Set WindowBar Colorful
Set BorderRadius 8
Set TypingSpeed 40ms

# --- Setup (not shown on screen): enter demo/, load the replay shim ---

Hide
Type "cd demo && source media/mock-shell.sh && clear"
Enter
Wait
Show

# --- Step 1: the trustee directory comes up ---

Type `banner "Keycloak holds the roster of who's even eligible to be invited into a ceremony -- nothing about a vault exists yet."`
Enter
Wait
Sleep 1s

Type "docker-compose --env-file .env up -d keycloak"
Enter
Wait
Sleep 500ms

Type "docker-compose ps"
Enter
Wait
Sleep 1s
# SPLICE: dashboard is empty/unreachable until step 2 brings up the combiner.

# --- Step 2: candidates come online ---

Type `banner "Six of the seven named candidates start: alice/bob/carol/dave/erin as primaries, frank held in reserve as the one name on the backup list. Grace stays offline this run."`
Enter
Wait
Sleep 1s

Type "docker-compose --profile candidates --env-file .env up -d combiner trustee-alice trustee-bob trustee-carol trustee-dave trustee-erin trustee-frank"
Enter
Wait
Sleep 1s
# SPLICE: open http://localhost:5000/dashboard now -- trustees populate
# live over SSE as they register in step 3.

# ACT-BOUNDARY: 1
# --- Step 3: registration + the operator ---

Type `banner "Each trustee generates its own keypair and registers its public key the moment it starts -- this is what lets a codeword be wrapped to a specific trustee later, instead of the combiner ever holding one in the clear."`
Enter
Wait
Sleep 1s

Type "docker-compose logs trustee-alice"
Enter
Wait
Sleep 1s

Type "operator_token() {"
Enter
Type "  curl -s -X POST http://localhost:8080/realms/shardic-demo/protocol/openid-connect/token \"
Enter
Type "    -d grant_type=password -d client_id=shardic-operator-client \"
Enter
Type `    -d username=operator -d "password=$(grep OPERATOR_PASSWORD .env | cut -d= -f2)" \`
Enter
Type `    -d scope=openid | python3 -c "import sys, json; print(json.load(sys.stdin)['access_token'])"`
Enter
Type "}"
Enter
Wait
Sleep 500ms

Type `curl -s -H "Authorization: Bearer $(operator_token)" http://localhost:5000/admin/keycloak/group-members | python3 -m json.tool`
Enter
Wait
Sleep 1.5s

# --- Step 4: ceremony initiated, erin about to go silent ---

Type `banner "Erin's container is about to be paused before she ever sees an invitation -- not a decline, just silence. The operator names alice as mandatory prime, bob/carol/dave/erin as the pool, frank as the one backup."`
Enter
Wait
Sleep 1s

Type "docker-compose pause trustee-erin"
Enter
Wait
Sleep 500ms
# SPLICE: dashboard should now show erin's status flip to paused.

Type `curl -s -X POST -H "Authorization: Bearer $(operator_token)" -H "Content-Type: application/json" \`
Enter
Type `  -d '{"threshold_d": 3, "prime": "alice", "pool": ["bob", "carol", "dave", "erin"], "backups": ["frank"]}' \`
Enter
Type "  http://localhost:5000/admin/ceremony/initiate | python3 -m json.tool"
Enter
Wait
Sleep 1.5s
# SPLICE: dashboard's ceremony diagram lights up with invited/backup_queue state.

# ACT-BOUNDARY: 2
# --- Step 5: silence is a decline, backup list backfills ---

Type `banner "Erin's pool invitation lapses on its own timeout -- treated identically to an explicit decline. The combiner backfills her slot from the ordered backup list: frank steps in. Once every slot is accepted, the ceremony is formed."`
Enter
Wait
Sleep 1s

Type "# (in the live walkthrough, this is where a real ~22s wait for the invitation TTL happens)"
Enter
Wait
Sleep 500ms

Type "docker-compose logs combiner | grep -iE 'ceremony|backfill|notify'"
Enter
Wait
Sleep 2s
# SPLICE: dashboard diagram should have animated invited -> expired ->
# backfilled -> formed across this same window -- capture the dashboard
# live in parallel with this segment, not as a static after-the-fact cut.

Type "docker unpause demo_trustee-erin_1   # she's not part of this ceremony, but no reason to leave her paused"
Enter
Wait
Sleep 500ms

# ACT-BOUNDARY: 3
# --- Step 6: vault created for the ceremony that actually formed ---

Type `banner "The pool that actually ends up holding shares is bob, carol, dave, frank -- erin was backfilled out before this moment ever happened."`
Enter
Wait
Sleep 1s

Type `curl -s -X POST -H "Authorization: Bearer $(operator_token)" http://localhost:5000/admin/vault/create | python3 -m json.tool`
Enter
Wait
Sleep 1.5s
# SPLICE: dashboard flips to "vault created" state, pool shows bob/carol/dave/frank.

# --- Step 7: nothing left to leak ---

Type `banner "Each codeword was wrapped to its trustee's own registered key, then the plaintext was destroyed the instant every envelope was written. Nothing sits on disk in the clear -- not even for the combiner to read."`
Enter
Wait
Sleep 1s

Type `docker exec $(docker-compose ps -q combiner) sh -c 'ls /data/vault/*_trustee_words 2>&1 || echo "gone, as expected"'`
Enter
Wait
Sleep 1.5s

# ACT-BOUNDARY: 4
# --- Step 8: the threshold, proven live ---

Type `banner "The pool's threshold is 2 of its 4 members, plus the mandatory prime. Pausing dave and frank -- simulating them going unavailable -- leaves exactly enough standing: alice, bob, carol."`
Enter
Wait
Sleep 1s

Type "docker-compose pause trustee-dave trustee-frank"
Enter
Wait
Sleep 500ms
# SPLICE: dashboard shows dave/frank paused, alice/bob/carol still live.

# ACT-BOUNDARY: 5
# --- Step 9: recovery -- shards, never codewords ---

Type `banner "Each live trustee decrypts its own envelope locally and sends back only its shard -- the post-match Shamir value, never the codeword itself."`
Enter
Wait
Sleep 1s

Type `curl -s -X POST -H "Authorization: Bearer $(operator_token)" http://localhost:5000/admin/recovery/start | python3 -m json.tool`
Enter
Wait
Sleep 1s

Type "docker-compose logs -f trustee-alice trustee-bob trustee-carol | grep -i 'shard submitted'"
Enter
Wait
Sleep 1.5s
# SPLICE: dashboard's recovery panel fills in as each of alice/bob/carol submits.

# ACT-BOUNDARY: 6
# --- Step 10: finalized -- who was actually needed ---

Type `banner "The combiner combines the collected shards and decrypts. The record shows exactly who was actually used -- and who wasn't."`
Enter
Wait
Sleep 1s

Type `curl -s -X POST -H "Authorization: Bearer $(operator_token)" http://localhost:5000/admin/recovery/finalize | python3 -m json.tool`
Enter
Wait
Sleep 1.5s
# SPLICE: dashboard's ceremony diagram flips to "done" -- trustees_used: alice/bob/carol.

# --- Step 11: byte-for-byte ---

Type `banner "Last check: compare the recovered output against the original, not just a 200 response -- proving the full threshold-recovery round trip actually reproduces the original data."`
Enter
Wait
Sleep 1s

Type "docker exec $(docker-compose ps -q combiner) sh -c 'diff -r /data/sample-secret /data/recovered/sample-secret && echo MATCH'"
Enter
Wait
Sleep 2s
# SPLICE: this diff never hits the combiner API, so the dashboard's verify
# banner stays "pending" here -- per demo/README.md's "Live dashboard"
# note, click the dashboard's Verify button (or POST
# /admin/recovery/verify) as its own beat if the dashboard segment should
# end on "verified" rather than "pending."

Sleep 2s

# ACT-BOUNDARY: 7
# --- Step 12: reset (optional -- see note) ---
# Ends the recording on cleanup rather than the "MATCH" high note above.
# Comment this block out to end the video at step 11 instead.

Type "docker unpause demo_trustee-dave_1 demo_trustee-frank_1"
Enter
Wait
Sleep 500ms

Type "docker-compose --profile candidates down -v"
Enter
Wait
Sleep 1s

# Demo video pipeline

Three steps, run in order from the repo root:

1. **`vhs demo/walkthrough.tape`** -- renders the CLI half
   (`demo-walkthrough.mp4`) by typing `demo/README.md`'s Walkthrough
   commands against `mock-shell.sh`'s replay of real captured output
   (`fixtures/`). Deterministic, no live stack needed. See the tape's
   own header comment and `fixtures/README.md`.

2. **`python3 demo/media/capture_dashboard.py`** -- renders the
   dashboard half. Unlike the CLI half, this one's real: it needs
   `keycloak` + `combiner` + the six candidate trustees already up and
   registered (see its docstring for the exact precondition), then it
   drives one real live ceremony through pause/curl/docker commands
   while a headless Chrome tab sits on `/dashboard`, video-recording the
   whole thing via Playwright. Writes
   `dashboard-recording/page@*.webm` plus `dashboard-timeline.json` (the
   wall-clock offset of each named beat -- erin_paused, ceremony_formed,
   vault_created, dave_frank_paused, verified, etc.).

3. Compose the final video, either:
   - **`demo/media/compose_full_video.sh`** -- two acts:
     `demo-walkthrough-full.mp4` is the CLI walkthrough, a title card,
     then the dashboard capture in full. Simple, needs only steps 1-2
     above.
   - **`demo/media/compose_interleaved_video.sh`** -- a real
     phase-by-phase interleave: `demo-walkthrough-interleaved.mp4` cuts
     between the CLI and the dashboard seven times, at
     `dashboard-timeline.json`'s real beat offsets (erin paused, ceremony
     initiated, formed, vault created, dave/frank paused, shards in,
     finalized, verified). Needs one extra step first: split
     `walkthrough.tape` into its 8 acts and render each --
     `python3 demo/media/split_tape_into_acts.py && for f in
     demo/media/acts/act*.tape; do vhs "$f"; done` -- since VHS can't
     emit multiple cut points from one recording; the split happens at
     `walkthrough.tape`'s own `# ACT-BOUNDARY:` markers, so the tape
     stays the single source of truth for the CLI commands. Hard cuts,
     no title cards -- terminal vs. browser chrome makes each cut
     obvious on its own.

Playwright needs its own bundled ffmpeg for video recording, separate
from system ffmpeg: `python3 -m playwright install ffmpeg` (one-time).
`capture_dashboard.py` launches via `channel="chrome"`, reusing whatever
`google-chrome` is already installed rather than downloading a separate
Chromium -- if that's not on the machine, either install it or switch
the launch call to Playwright's own bundled Chromium
(`playwright install chromium --with-deps`, needs sudo for system
deps).

Generated outputs (`*.mp4`, `*.gif`, `dashboard-recording/`,
`dashboard-timeline.json`, `acts/`) are gitignored -- rerun the pipeline
rather than expecting them to already be on disk after a fresh checkout.

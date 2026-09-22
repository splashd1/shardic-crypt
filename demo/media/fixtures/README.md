# Fixtures

Real output captured from one clean, live run of `demo/README.md`'s
Walkthrough (steps 1-11) on 2026-07-21 against Podman, `docker-compose`
1.29.2. Not fabricated -- each file is the actual response/log content
from that run, lightly cleaned:

- Docker/Podman build spew and the `docker-compose` progress-spinner
  duplicate lines were trimmed to the final state.
- ANSI color codes were stripped from `docker-compose logs` output.
- `05-backfill-log.txt`'s per-line `[+Ns]` timing annotations (added
  during capture to sanity-check pacing) were removed -- see the
  capture note below on why the real elapsed time isn't meaningful
  here.
- `token-response.json` is NOT real -- the real Keycloak token was
  never written to disk; this is a placeholder so `mock-shell.sh`'s
  `curl` stand-in has something structurally valid to hand to
  `python3 -c "...access_token..."` in `operator_token()`.

**Capture note on step 5's timing:** the real TTL is `CEREMONY_INVITE_TTL_S`
(20s default). In the capture run, enough wall-clock time had already
passed between the `ceremony/initiate` call and attaching to
`docker-compose logs -f combiner` (curl + JSON formatting + tool
round-trips) that the whole expire -> backfill -> frank-accepts ->
formed sequence had already happened by the time the log tail attached,
so it all arrived in one burst rather than trickling in over ~20s. The
*content* is real; don't read anything into the captured timing.

## Refreshing

Re-run the Walkthrough for real (`docker-compose --profile candidates
down -v` first for a clean slate) and re-save each command's output to
its matching file here, following the step numbers in the filenames.
`mock-shell.sh` case-matches on the exact command text `walkthrough.tape`
types -- if a step's typed command changes, update both.

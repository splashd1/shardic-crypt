#!/usr/bin/env bash
# Finer-grained interleave than compose_full_video.sh: cuts the
# dashboard recording into 7 clips at dashboard-timeline.json's real
# beat offsets, and alternates them with the 8 per-act CLI clips
# (media/acts/cli-act1.mp4 .. cli-act8.mp4, from
# split_tape_into_acts.py + `vhs`'ing each act*.tape) into one video:
#
#   CLI act1 -> dash(open..erin_paused)        -> CLI act2
#   -> dash(erin_paused..ceremony_initiated)   -> CLI act3
#   -> dash(ceremony_initiated..erin_unpaused) -> CLI act4   [formation->backfill->formed, the marquee segment]
#   -> dash(erin_unpaused..dave_frank_paused)  -> CLI act5   [vault created]
#   -> dash(dave_frank_paused..recovery_started) -> CLI act6
#   -> dash(recovery_started..finalized)       -> CLI act7   [shards arriving]
#   -> dash(finalized..verified)               -> CLI act8   [verify banner flips to MATCH]
#
# Act8 (teardown) has no trailing dashboard clip -- the video ends on
# the CLI's own cleanup, same as demo-walkthrough.mp4 does standalone.
#
# Prerequisites: media/acts/cli-act1.mp4..cli-act8.mp4 (render via
# `for f in demo/media/acts/act*.tape; do vhs "$f"; done` from the repo
# root, after `python3 demo/media/split_tape_into_acts.py`), plus
# dashboard-recording/page@*.webm and dashboard-timeline.json (from
# capture_dashboard.py). Hard cuts, no title cards -- the terminal vs.
# browser chrome makes each cut self-evident.

set -euo pipefail
cd "$(dirname "${BASH_SOURCE[0]}")"

ACTS=acts
DASH_WEBM=$(ls dashboard-recording/page@*.webm | head -1)
TIMELINE=dashboard-timeline.json

[ -f "$TIMELINE" ] || { echo "missing $TIMELINE -- run capture_dashboard.py first" >&2; exit 1; }
for i in 1 2 3 4 5 6 7 8; do
  [ -f "$ACTS/cli-act$i.mp4" ] || { echo "missing $ACTS/cli-act$i.mp4 -- render demo/media/acts/act$i.tape first" >&2; exit 1; }
done

mark() { python3 -c "import json; print(json.load(open('$TIMELINE'))['$1'])"; }

T_OPEN=$(mark dashboard_open_trustees_registering)
T_ERIN_PAUSED=$(mark erin_paused)
T_INITIATED=$(mark ceremony_initiated)
T_ERIN_UNPAUSED=$(mark erin_unpaused)
T_DF_PAUSED=$(mark dave_frank_paused)
T_RECOVERY_STARTED=$(mark recovery_started)
T_FINALIZED=$(mark finalized)
T_VERIFIED=$(mark verified)

TMP=$(mktemp -d)
trap 'rm -rf "$TMP"' EXIT

cut_dash() {
  local name=$1 start=$2 end=$3
  ffmpeg -y -ss "$start" -to "$end" -i "$DASH_WEBM" \
    -vf "scale=1280:1000,fps=25" -pix_fmt yuv420p -c:v libx264 -crf 18 \
    "$TMP/$name.mp4" -v error
}

cut_dash dash1 "$T_OPEN" "$T_ERIN_PAUSED"
cut_dash dash2 "$T_ERIN_PAUSED" "$T_INITIATED"
cut_dash dash3 "$T_INITIATED" "$T_ERIN_UNPAUSED"
cut_dash dash4 "$T_ERIN_UNPAUSED" "$T_DF_PAUSED"
cut_dash dash5 "$T_DF_PAUSED" "$T_RECOVERY_STARTED"
cut_dash dash6 "$T_RECOVERY_STARTED" "$T_FINALIZED"
cut_dash dash7 "$T_FINALIZED" "$T_VERIFIED"

INPUTS=()
FILTER=""
IDX=0
add_input() {
  INPUTS+=(-i "$1")
  FILTER+="[$IDX:v]scale=1280:1000,fps=25,format=yuv420p[v$IDX];"
  IDX=$((IDX + 1))
}

add_input "$ACTS/cli-act1.mp4"
add_input "$TMP/dash1.mp4"
add_input "$ACTS/cli-act2.mp4"
add_input "$TMP/dash2.mp4"
add_input "$ACTS/cli-act3.mp4"
add_input "$TMP/dash3.mp4"
add_input "$ACTS/cli-act4.mp4"
add_input "$TMP/dash4.mp4"
add_input "$ACTS/cli-act5.mp4"
add_input "$TMP/dash5.mp4"
add_input "$ACTS/cli-act6.mp4"
add_input "$TMP/dash6.mp4"
add_input "$ACTS/cli-act7.mp4"
add_input "$TMP/dash7.mp4"
add_input "$ACTS/cli-act8.mp4"

CONCAT_INPUTS=""
for i in $(seq 0 $((IDX - 1))); do CONCAT_INPUTS+="[v$i]"; done
FILTER+="${CONCAT_INPUTS}concat=n=${IDX}:v=1:a=0[outv]"

ffmpeg -y "${INPUTS[@]}" -filter_complex "$FILTER" -map "[outv]" \
  -c:v libx264 -crf 20 demo-walkthrough-interleaved.mp4 -v error

echo "wrote demo/media/demo-walkthrough-interleaved.mp4"
ffprobe -v error -show_entries format=duration -of default=noprint_wrappers=1 demo-walkthrough-interleaved.mp4

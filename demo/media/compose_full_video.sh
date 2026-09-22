#!/usr/bin/env bash
# Composes the two recorded halves into one video:
#   demo-walkthrough.mp4 (CLI, VHS replay)  -->  title card  -->  dashboard-recording/*.webm (real live capture)
#
# Run after both halves exist:
#   1. vhs demo/walkthrough.tape                  (from repo root; produces demo/media/demo-walkthrough.mp4)
#   2. python3 demo/media/capture_dashboard.py     (needs a live stack up through registration; see its docstring)
# Then: demo/media/compose_full_video.sh
#
# This is a straight two-act composition (CLI walkthrough, then the same
# ceremony replayed through the dashboard's eyes), not a frame-by-frame
# interleave -- the CLI video's replay pacing (banners + Sleep for
# readability) and the dashboard's real-time pacing don't share a common
# clock, so cutting between them mid-scene would need re-deriving exact
# timestamps inside the CLI recording, which isn't done here. The
# `# SPLICE:` comments in walkthrough.tape and narration.md's
# "Dashboard-specific beats" still describe where a finer interleave
# would cut, using demo/media/dashboard-timeline.json's real offsets, if
# that's worth building later.

set -euo pipefail
cd "$(dirname "${BASH_SOURCE[0]}")"

FONT=/usr/share/fonts/truetype/dejavu/DejaVuSansMono.ttf
CLI=demo-walkthrough.mp4
DASH_WEBM=$(ls dashboard-recording/page@*.webm | head -1)

[ -f "$CLI" ] || { echo "missing $CLI -- render the tape first" >&2; exit 1; }
[ -f "$DASH_WEBM" ] || { echo "missing dashboard-recording/*.webm -- run capture_dashboard.py first" >&2; exit 1; }

TMP=$(mktemp -d)
trap 'rm -rf "$TMP"' EXIT

ffmpeg -y -f lavfi -i color=c=0x1e1e2e:s=1280x1000:d=4:r=25 \
  -vf "drawtext=fontfile=$FONT:text='Same ceremony -- through the live presenter dashboard':fontcolor=0xcdd6f4:fontsize=34:x=(w-text_w)/2:y=(h-text_h)/2-20,drawtext=fontfile=$FONT:text='(real-time capture, not sped up)':fontcolor=0x9399b2:fontsize=20:x=(w-text_w)/2:y=(h-text_h)/2+30" \
  -pix_fmt yuv420p "$TMP/transition.mp4" -v error

ffmpeg -y -i "$DASH_WEBM" -vf "scale=1280:1000,fps=25" -pix_fmt yuv420p -c:v libx264 -crf 18 "$TMP/dashboard.mp4" -v error

ffmpeg -y -i "$CLI" -i "$TMP/transition.mp4" -i "$TMP/dashboard.mp4" \
  -filter_complex "[0:v]scale=1280:1000,fps=25,format=yuv420p[v0];[1:v]format=yuv420p[v1];[2:v]format=yuv420p[v2];[v0][v1][v2]concat=n=3:v=1:a=0[outv]" \
  -map "[outv]" -c:v libx264 -crf 20 demo-walkthrough-full.mp4 -v error

echo "wrote demo/media/demo-walkthrough-full.mp4"
ffprobe -v error -show_entries format=duration -of default=noprint_wrappers=1 demo-walkthrough-full.mp4

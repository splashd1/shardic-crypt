#!/bin/bash
# Rebuild the v4.1 deck set into docs/. Needs python-pptx + Pillow, e.g.:
#   python3 -m venv /tmp/deckenv && /tmp/deckenv/bin/pip install python-pptx Pillow
#   PY=/tmp/deckenv/bin/python docs/tools/decks/build.sh
set -e
HERE="$(cd "$(dirname "$0")" && pwd)"
DOCS="$HERE/../.."
PY="${PY:-python3}"
"$PY" "$HERE/deck_overview.py"    "$DOCS/shardic_deck_v4_1_overview.pptx"
"$PY" "$HERE/deck_foundations.py" "$DOCS/shardic_deck_v4_1_foundations.pptx"
"$PY" "$HERE/deck_talk.py"        "$DOCS/shardic_deck_v4_1_conference_talk.pptx"
echo "Built 3 decks in docs/. Render-check with: soffice --headless --convert-to pdf <deck>.pptx"

#!/usr/bin/env bash
# Surface the handoff notes from the current checkout.
cd "$CLAUDE_PROJECT_DIR" 2>/dev/null || exit 0

if [ -f notes.md ]; then
  jq -Rs '{hookSpecificOutput: {hookEventName: "SessionStart", additionalContext: ("Local session notes (notes.md):\n\n" + .)}}' notes.md
fi

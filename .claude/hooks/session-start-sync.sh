#!/usr/bin/env bash
# SessionStart hook: pull latest repo state and surface notes.md so a new
# session (possibly on a different machine) picks up where the last one
# left off, without the user having to ask.
cd "$CLAUDE_PROJECT_DIR" 2>/dev/null || exit 0

git pull --ff-only --quiet >/dev/null 2>&1 || true

if [ -f notes.md ]; then
  jq -Rs '{hookSpecificOutput: {hookEventName: "SessionStart", additionalContext: ("Session notes synced from git (notes.md):\n\n" + .)}}' notes.md
fi

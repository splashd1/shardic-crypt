---
name: shardic-sync
description: End-of-session sync for the shardic repo. Summarizes this conversation's work into notes.md and commits + pushes it, so a Claude Code session on a different machine can pick up context (a SessionStart hook auto-pulls and surfaces notes.md there). Invoke when the user is wrapping up a shardic session, or says things like "sync notes", "wrap up", "save session notes", "/shardic-sync".
---

# shardic-sync

Run this at the end of a shardic working session, right before the user
closes out, so the *next* session — possibly on a different machine —
starts with full context via the `SessionStart` hook
(`.claude/hooks/session-start-sync.sh`), which auto-pulls and surfaces
`notes.md`.

## Steps

1. **Check for anything worth recording.** Run `git -C
   "$CLAUDE_PROJECT_DIR" status --short` and think back over this
   conversation. If nothing meaningful happened (pure Q&A, no code
   changes, no decisions, no state worth remembering), say so and stop
   — don't write a content-free entry just to have one.

2. **Read the existing `notes.md`** (if present) to match its format
   and see what the last entry already covered, so this entry doesn't
   duplicate it.

3. **Write a new dated section summarizing *this* session**, prepended
   above any previous entries (newest first, so the next `SessionStart`
   pull surfaces the freshest context immediately without scrolling).
   Use today's date. Cover, in your own judgment of what's relevant:
   - What was done (decisions made, files changed, commits created,
     commands run) — not a blow-by-blow transcript, a summary someone
     picking this up cold could act on.
   - State at the end: uncommitted changes, open PRs, CI runs
     in flight, anything left mid-way.
   - Follow-ups or open questions worth flagging next time.

   Keep it tight — this is a handoff note, not a changelog. Match the
   structure/tone of existing entries in the file if there are any.

4. **Stage, commit, and push** in one flow, no confirmation needed —
   this workflow was explicitly set up by the user to auto-sync:
   ```
   git -C "$CLAUDE_PROJECT_DIR" add notes.md
   git -C "$CLAUDE_PROJECT_DIR" commit -m "<short summary>

   Fine-tuned, vetted, and, in some cases, supplemented by Claude Sonnet 5"
   git -C "$CLAUDE_PROJECT_DIR" push
   ```
   If push fails (e.g. remote has commits this machine doesn't — another
   machine synced first), run `git pull --rebase` then push again. If
   that still conflicts, stop and surface it to the user rather than
   force-pushing.

5. **Report back** in 1-2 sentences: what got recorded and confirmation
   it's pushed.

## What NOT to do

- Don't touch anything other than `notes.md` as part of this sync
  (no drive-by commits of unrelated working-tree changes) unless the
  user separately asked for those to be committed too.
- Don't force-push or rewrite history to resolve conflicts — surface
  them instead.
- Don't skip the summary and just append raw conversation excerpts —
  synthesize, the way a person handing off to their next shift would.

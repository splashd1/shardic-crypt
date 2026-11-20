---
name: shardic-sync
description: Record a shardic session handoff in notes.md. Use when asked to wrap up, save session notes, sync notes, or run /shardic-sync. An explicit sync request publishes the handoff to the current task branch.
---

# shardic-sync

Run this at the end of a shardic working session, right before the user
closes out, so the *next* session — possibly on a different machine —
can pick up the handoff after explicitly updating its checkout.
Claude Code's SessionStart hook displays the local `notes.md`.

## Steps

1. **Check for anything worth recording.** Run `git status --short --branch` from the repository worktree and think back over this
   conversation. If nothing meaningful happened (pure Q&A, no code
   changes, no decisions, no state worth remembering), say so and stop
   — don't write a content-free entry just to have one.

2. **Read the existing `notes.md`** (if present) to match its format
   and see what the last entry already covered, so this entry doesn't
   duplicate it.

3. **Write a new dated section summarizing *this* session**, prepended
   above any previous entries so the newest handoff appears first.
   Use today's date. Cover, in your own judgment of what's relevant:
   - What was done (decisions made, files changed, commits created,
     commands run) — not a blow-by-blow transcript, a summary someone
     picking this up cold could act on.
   - State at the end: uncommitted changes, open PRs, CI runs
     in flight, anything left mid-way.
   - Follow-ups or open questions worth flagging next time.

   Keep it tight — this is a handoff note, not a changelog. Match the
   structure/tone of existing entries in the file if there are any.

4. **Publish only on an explicit sync or push request.** For a request
   to save or wrap up, leave the handoff in the working tree. If publishing
   was requested, check the branch, verify that `notes.md` contains only
   the intended handoff diff, and commit just that file with
   `git commit --only -m "Update session handoff" -- notes.md`.
   Push the current branch to its configured upstream. If there is no
   upstream, the branch has diverged, or the push fails, report the state
   so the user can coordinate integration.

5. **Report back** in 1-2 sentences: what got recorded and whether it was pushed.

## What NOT to do

- Don't touch anything other than `notes.md` as part of this sync
  (no drive-by commits of unrelated working-tree changes) unless the
  user separately asked for those to be committed too.
- Don't force-push or rewrite history to resolve conflicts — surface
  them instead.
- Don't skip the summary and just append raw conversation excerpts —
  synthesize, the way a person handing off to their next shift would.

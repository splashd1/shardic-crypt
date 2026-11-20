# shardic-crypt

## Working with both coding agents

- Check `git status --short --branch` and `git worktree list` before editing. Preserve existing edits. Assign one agent to implement a task and use the other for an independent review of the diff. If both need to edit concurrently, use distinct task branches and worktrees.
- For a handoff, record the branch and commit or PR, the scope of the changes, checks run and their outcomes, and open questions. Use the repository's existing notes or PR for durable decisions and handoffs. When asking a web assistant to review, include the GitHub link and exact commit or PR to inspect.
- Coordinate pulls, pushes, and integration explicitly. Before updating a clean checkout from its upstream, use `git pull --ff-only`. If it has diverged or contains someone else's work, surface the state before integrating.

## Project context

- Consult `CLAUDE.md` and the applicable files in `.claude/rules/` for project conventions, commands, and verification.
- Use `.claude/skills/shardic-nomenclature/SKILL.md` for project terminology and `notes.md` for recent handoffs.

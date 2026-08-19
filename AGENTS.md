# Agent Guidelines

This repository is a small local study tracking app with Flask and Tkinter
entry points. Treat Python source, templates, requirements, and
`PROJECT_PROFILE.yaml` as the operating truth. README prose is secondary when it
lags implementation.

## Development Route

For non-trivial implementation, use the parent-owned route:
Plan -> Work -> independent Sol max Review. The central instructions are
`/Users/sora/dev/jinsei/CODEX_GLOBAL_AGENTS.md`, and the deterministic task,
authority, evidence, and Git boundary is `/Users/sora/dev/jinsei/bin/jinsei`.
The Codex parent owns model launch; the current TaskIntent, exact worktree
scope, and fresh verification/review evidence must bind to the current HEAD.
Do not infer launch commands from this repository.

## Development Autonomy

Development GitHub operations are L5 under Jinsei's
`GITHUB_DEVOPS_AUTONOMY_POLICY.md` after this repo's verification and fresh
independent Sol max review evidence bound to the current HEAD pass. This
includes branch work, local commits, pushes to an existing approved remote, PR
creation/update, and issue operations.

Public deployment, repository visibility changes, billing or paid services,
secret mutation, production data mutation, public claims, and publication remain
gated.

## Engineering Rules

- Keep the Flask and Tkinter paths aligned when changing shared study-record
  behavior.
- Do not introduce remote services unless explicitly approved.
- Do not commit local SQLite databases or private study records.
- Do not deploy to Render or another host unless explicitly approved.

## Safety

Do not read, print, commit, or copy `.env*`, credentials, local SQLite runtime
databases, private study records, raw logs, or generated workspaces.

## Verification

Use the relevant subset:

```bash
python3 -m py_compile app.py study_app.py
git diff --check
```

# study-app/AGENTS.md

This repository is a small local study tracking app with Flask and Tkinter
entry points. Treat Python source, templates, requirements, and
`PROJECT_PROFILE.yaml` as the operating truth. README prose is secondary when it
lags implementation.

## Development Route

For non-trivial implementation, the current central Jinsei contract and linked
policies own the route, model and effort selection, review, task evidence, and
Git side effects:

- `/Users/sora/dev/jinsei/CODEX_GLOBAL_AGENTS.md`
- `/Users/sora/dev/jinsei/docs/policies/DEVELOPMENT_MODEL_ROUTE_POLICY.md`
- `/Users/sora/dev/jinsei/docs/policies/DEVELOPMENT_PROTOCOL.md`
- `/Users/sora/dev/jinsei/docs/policies/MANAGED_REPOSITORY_INHERITANCE.md`

This repository is a specialized Jinsei-managed implementation unit. The
`project.authority` block in `PROJECT_PROFILE.yaml` only narrows central
authority; it does not grant authority or replace central task, halt, identity,
or review checks.

## Repository Scope

This repository owns the Flask and Tkinter study-tracking implementation and
their shared local study-record behavior. For cross-repository changes, inspect
only directly affected contracts and actual consumers; do not invent runtime
relationships among repositories.

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

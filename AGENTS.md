# Agent Guidelines

This repository is a small local study tracking app with Flask and Tkinter
entry points. Treat Python source, templates, requirements, and
`PROJECT_PROFILE.yaml` as the operating truth. README prose is secondary when it
lags implementation.

## Global Routing

For non-trivial implementation, route through Jinsei / Global Coding Department:

```bash
cd /Users/sora/dev/jinsei
python3 scripts/dispatch_codex_session.py --queue-request --project "Study App" --repo /Users/sora/dev/study-app --operation-id <operation_id> --goal "<bounded goal>" --authority-band A2
python3 scripts/dispatch_codex_session.py --from-queue --limit 3
python3 scripts/dispatch_codex_session.py --check-push-review --project "Study App" --operation-id <operation_id>
```

Use Planning Worker, Implementation Worker, and Review Controller separation for
multi-file changes, database behavior, UI changes, deployment readiness, or
push readiness.

## Development Autonomy

Development GitHub operations are L5 under Jinsei's
`GITHUB_DEVOPS_AUTONOMY_POLICY.md` after this repo's verification and required
Review Controller gates pass. This includes branch work, local commits, pushes
to an existing approved remote, PR creation/update, and issue operations.

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

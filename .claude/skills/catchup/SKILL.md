---
name: catchup
description: Load previous Project Tracker session context from progress notes and git status/log before planning changes. Use at new session start or after /clear.
user-invocable: true
---

# Catchup

Load minimum context, then stop with a short state report.

1. Read `_docs/PROGRESS.md` current phase and blockers.
2. Run `git status --short --branch` and inspect latest 3 commits.
3. Recall relevant memory only if user mentions prior decisions or old context.
4. Report: active branch, dirty files, current phase, next safest step, blockers.

Do not edit files. Do not run app/tests/build.

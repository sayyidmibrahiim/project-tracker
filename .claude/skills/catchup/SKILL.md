---
name: catchup
description: Load previous Project Tracker session context from progress notes, git status/log, and graphify freshness before planning changes. Use at new session start or after /clear.
user-invocable: true
---

# Catchup

Load minimum context, then stop with a short state report.

1. Read `_docs/PROGRESS.md` current phase and blockers.
2. Run `git status --short --branch` and inspect latest 3 commits.
3. Check `D:/Ibrahim/Projects/project_tracker/graphify-out/graph.json` exists and note freshness.
4. Recall relevant memory only if user mentions prior decisions or old context.
5. Report: active branch, dirty files, current phase, next safest step, blockers.

Do not edit files. Do not run app/tests/build.

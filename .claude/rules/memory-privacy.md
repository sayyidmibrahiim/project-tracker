---
globs:
  - "**/*"
---

# Memory Privacy

- Do not store secrets, credentials, tokens, API keys, passwords, private keys, or PII in claude-mem, context-mode, session notes, or Claude auto-memory.
- claude-mem is DISABLED (2026-07-09) — its hooks caused multi-second lag on every tool call plus 60s SessionStart timeouts. Do not rely on it until re-enabled and perf-fixed; use `_docs/session-notes.md` for cross-session recall instead. When re-enabled: recall at session start, update on every important change, decisions/conventions only — not transcript dumps.
- Current code and docs are authority; memory is recall aid only.
- If memory conflicts with source, verify source and update/delete wrong memory.
- Use `_docs/session-notes.md` for brief recovery ledger: branch, changed files, approved design, decisions, next step, blockers.

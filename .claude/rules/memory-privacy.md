---
globs:
  - "**/*"
---

# Memory Privacy

- Do not store secrets, credentials, tokens, API keys, passwords, private keys, or PII in claude-mem, context-mode, session notes, or Claude auto-memory.
- Store decisions and conventions, not transcript dumps.
- Current code and docs are authority; memory is recall aid only.
- If memory conflicts with source, verify source and update/delete wrong memory.
- Use `_docs/session-notes.md` for brief recovery ledger: branch, changed files, approved design, decisions, next step, blockers.

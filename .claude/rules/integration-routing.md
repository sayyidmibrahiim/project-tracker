---
globs:
  - "**/*"
---

# Integration Routing

Use only integrations needed for current task. Do not health-check all tools every prompt.

## Owners

| Integration  | Owns                                                  | Use when                                                                 | Skip when                                                    |
| ------------ | ----------------------------------------------------- | ------------------------------------------------------------------------ | ------------------------------------------------------------ |
| caveman      | Response style compression                            | Operational updates, reviews, bug triage, evidence summaries             | Stakeholder prose, UI copy, legal/safety text                |
| context-mode | Tool/CLI output compression + in-session continuity   | Large command output, compaction/resume continuity, ctx search/stats     | Do not duplicate via custom output hooks or MCP-only install |
| claude-mem   | Cross-session recall                                  | Prior decisions, user preferences, old bugs, conventions                 | Current code facts; verify source instead                    |
| Headroom     | Optional local proxy                                  | User asks to configure/start Headroom or use its proxy                   | Normal code lookup/search                                    |
| RTK          | Optional manual CLI compression                       | Explicit `rtk ...` commands on native Windows                            | Never claim auto-rewrite on native Windows                   |
| cli-delegate | Delegate prompts to any AI CLI (opencode, mimo, etc.) | User says "ask mimo", "delegate to opencode", "/delegate-to-another-cli" | Never auto-trigger; explicit user request only               |

## Windows rules

- Native PowerShell hooks only for project custom hooks.
- Headroom proxy URL: `http://localhost:8787`. Install with `pip install "headroom-ai[proxy]"` when user asks to set it up.
- RTK auto-rewrite needs Unix shell/WSL. Native Windows = manual prefix only.

## Sensitive paths

All tools must avoid `.env`, `*.env.*`, `secrets/`, credentials, `*.pem`, and `*.key` unless user explicitly approves a specific read for defensive audit.

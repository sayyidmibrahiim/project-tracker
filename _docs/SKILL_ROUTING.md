# Skill Routing — Project Tracker

> Integrations routing authority: `.claude/rules/integration-routing.md`. This file adds skill-level routes (skills ≠ integrations).

Use skills intentionally. Max 2–3 per task. Do not invoke unrelated skills.

## Default Routes

| When you want to…                | Use this (primary) | Secondary         | Notes                                                            |
| -------------------------------- | ------------------ | ----------------- | ---------------------------------------------------------------- |
| **Create/change UI**             | `ui-ux-pro-max`    | `impeccable`      | One design skill per task; load only the most relevant           |
| **Review screenshot/comparison** | `design-review`    | —                 | Compares against DESIGN.md, SPEC, live implementation; gaps only |
| **Polish UI**                    | `impeccable`       | —                 | Only at end of slice, never mid-iteration                        |
| **Svelte/TS code**               | `context7-mcp`     | —                 | Resolve Svelte docs → query API                                  |
| **Python backend**               | —                  | —                 | Use core domain knowledge; no skill wrapper needed               |
| **Bug fix**                      | `diagnosing-bugs`  | —                 | Start with reproduction, not guesswork                           |
| **Code review**                  | `review`           | `ponytail-review` | Before merge                                                     |
| **Simplify**                     | `ponytail-review`  | `ponytail-audit`  | After working implementation                                     |
| **Git ops / commit**             | `caveman`          | —                 | Response style only; `ultra` is session-level                    |
| **Memory (cross-session)**       | `claude-mem`       | —                 | Session start + stable decisions; not every turn                 |
| **Large output / resume**        | `context-mode`     | —                 | Tool output compression + in-session continuity                  |
| **Manual CLI compress**          | `RTK`              | —                 | Explicit `rtk ...` on native Windows only; no auto-rewrite       |

## Integration Routing — WHEN (not IF)

Each integration is **auto-relevant only when its trigger matches**. Do not load all preemptively.

| Integration      | Owner                                | Auto-relevant when…                                           | Windows notes                                                       |
| ---------------- | ------------------------------------ | ------------------------------------------------------------- | ------------------------------------------------------------------- |
| **caveman**      | Response style compression           | Operational summaries, reviews, bug triage                    | `ultra` is session-level; normal for stakeholder text               |
| **context-mode** | Tool output compression + continuity | Large command output, `/compact`, `/resume`, ctx search/stats | Enabled plugin path only; don't add duplicate hooks                 |
| **claude-mem**   | Cross-session recall                 | Session start, prior decisions/preferences, stable decisions  | Memory untuk DECISIONS & context lintas sesi saja, bukan dump semua |
| **Headroom**     | Optional local proxy                 | User asks to configure/start Headroom or use proxy             | Proxy URL `http://localhost:8787`; install `pip install "headroom-ai[proxy]"` |
| **RTK**          | Manual CLI compression               | Explicit `rtk ...` commands                                   | Manual-only; auto-rewrite only in WSL/Unix shell                    |

Sensitive paths stay denied for all integrations: `.env`, `*.env.*`, `secrets/`, credentials, `*.pem`, `*.key`.

## Anti-Patterns

- Do NOT invoke all skills "just to be safe" — each costs tokens
- Do NOT use planning skills for trivial 1-file fixes
- Do NOT use `impeccable` or `ui-ux-pro-max` for backend-only work
- Do NOT use `review` before implementation is working
- Do NOT use simplify on code that's not yet verified
- Do NOT install context-mode plugin and MCP-only path together
- Do NOT claim RTK auto-rewrite works in native Windows

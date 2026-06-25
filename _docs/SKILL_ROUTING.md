# Skill Routing — Project Tracker

Use skills intentionally. Max 2-3 per task. Do not invoke unrelated skills.

## Routing Matrix

| Task Type             | Primary Skill                                | Secondary                                    | When                            |
| --------------------- | -------------------------------------------- | -------------------------------------------- | ------------------------------- |
| **UI/UX Design**      | `frontend-design`                            | `ui-ux-pro-max`                              | Any visual/design work          |
| **Design Polish**     | `frontend-polish`                            | —                                            | After initial design is working |
| **Svelte/TS Code**    | `context7-mcp` (Svelte docs)                 | `fullstack-dev-skills:typescript-pro`        | Frontend implementation         |
| **Python Backend**    | `fullstack-dev-skills:python-pro`            | —                                            | Backend services, domain logic  |
| **API/Bridge**        | `fullstack-dev-skills:api-designer`          | —                                            | pywebview bridge design         |
| **Bug Fix**           | `superpowers:systematic-debugging`           | —                                            | Any debugging                   |
| **Planning**          | `superpowers:writing-plans`                  | `superpowers:brainstorming`                  | Non-trivial architecture        |
| **Code Review**       | `code-review`                                | `ponytail-review`                            | Before merge                    |
| **Simplification**    | `simplify`                                   | `ponytail-audit`                             | After working implementation    |
| **Git Ops**           | `caveman:caveman-commit`                     | `superpowers:finishing-a-development-branch` | Commits, branch management      |
| **Memory**            | `agentmemory:recall`                         | `agentmemory:remember`                       | Session start, stable decisions |
| **Codebase Query**    | `graphify`                                   | —                                            | Before reading raw files        |
| **CLAUDE.md Changes** | `claude-md-management:revise-claude-md`      | —                                            | Updating this file              |
| **Verification**      | `superpowers:verification-before-completion` | `verify`                                     | After implementation            |
| **Security**          | `fullstack-dev-skills:security-reviewer`     | `fullstack-dev-skills:secure-code-guardian`  | COM, file ops, automation       |
| **New Session**       | `agentmemory:recall`                         | `graphify`                                   | Every session start             |

## Context7 Triggers

Use `context7-mcp` (resolve library → query docs) before implementing with:

- Svelte (component syntax, stores, lifecycle)
- Vite (config, plugins)
- Tailwind (utility classes, config)
- pywebview (API, JS bridge, window config)
- APScheduler (job scheduling, triggers)
- Any unfamiliar or version-sensitive library

## Anti-Patterns

- Do NOT invoke all skills "just to be safe" — each costs tokens
- Do NOT use planning skills for trivial 1-file fixes
- Do NOT use frontend-design for backend-only work
- Do NOT use code-review before implementation is working
- Do NOT use simplify on code that's not yet verified

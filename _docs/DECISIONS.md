# Decisions — Project Tracker

> **Purpose:** Permanent cross-session record of **why** decisions were made.
>
> - `_docs/session-notes.md` → what's active now (Now/Next/Blocked + active_menu)
> - `_docs/PROGRESS.md` → status/tracking
> - **DECISIONS.md** → locked architectural and tooling decisions with rationale

## Format

| ID       | Date         | Decision           | Rationale         | Status                            |
| -------- | ------------ | ------------------ | ----------------- | --------------------------------- |
| `D-XXXX` | `YYYY-MM-DD` | Decision statement | Why we chose this | `LOCKED` / `SUPERSEDED` / `DRAFT` |

---

## Decision Log

| ID     | Date       | Decision                                                                                                                                                                                                               | Rationale                                                                                                                                   | Status |
| ------ | ---------- | ---------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------- | ------------------------------------------------------------------------------------------------------------------------------------------- | ------ |
| D-0001 | 2026-06-28 | Navigation = bottom dock (macOS-style). `Sidebar.svelte` is a legacy/contextual component — it implements the bottom dock, not a persistent left sidebar. Navigation truth is PRD §10.3.                               | Consistency with PRD §10 design + user approval. Eliminates conflict between Sidebar vs dock references across docs.                        | LOCKED |
| D-0002 | 2026-06-28 | Memory tool = `claude-mem`. `agentmemory` is disabled to avoid duplicate capture/injection.                                                                                                                            | Single memory layer reduces token waste and confusion. `claude-mem` is active; `agentmemory` disabled at project level.                     | LOCKED |
| D-0003 | 2026-06-28 | Single status source = `_docs/PROGRESS.md`. `PROJECT_STATUS.md` at root is a 3-line redirect. Full history in `_docs/_archive/PROJECT_STATUS_history.md`.                                                              | Eliminates conflicting status files. One file to read, one to update.                                                                       | LOCKED |
| D-0004 | 2026-06-29 | Config/docs cleanup: branch `chore/config-cleanup`. Cleaned stale references (notes.md, tree.txt), removed agentmemory from routing docs, tightened CLAUDE.md lifecycle rules, aligned WORKFLOW.md branch conventions. | Reduce token waste by removing dead references and clarifying session-vs-turn discipline. All changes are docs-only/config, 0 product code. | LOCKED |
| D-0005 | 2026-06-29 | TitleBar replaces Sidebar. Frameless pywebview window with CSS drag regions. Window controls via Python bridge (`win_minimize/toggle_maximize/close`).                                                                 | Teams-like frameless titlebar approved by user. Bottom dock removed — nav moves to titlebar icons.                                          | LOCKED |
| D-0006 | 2026-06-29 | All CR Number & Drone Ticket inputs use 3-icon pattern (Copy SVG + Open SVG + Edit SVG) + two-state toggle: input when empty, display label + icons when filled. Enter/blur triggers save.                             | Consistent UX across Dashboard, ProjectDetails, and SubProjectTable. User approved pattern from ProjectDetails CR Number identity card.     | LOCKED |

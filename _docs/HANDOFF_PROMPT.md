# Handoff Prompt — Project Tracker Appcode Structure

Kamu adalah AI agent yang melanjutkan pekerjaan di repo **Project Tracker DBS**.
Repo ada di `D:/Ibrahim/Projects/project_tracker`.
Baca `CLAUDE.md` dulu sebelum melakukan apapun — itu adalah workflow/tooling guardrails yang wajib diikuti.

## WAJIB BACA SEBELUM CODING (Cold Start / Truth Order)

1. `CLAUDE.md` — workflow rules, branch format, tech stack, commands
2. `_docs/WORKFLOW.md` — git branch convention, implementation discipline
3. `_docs/PROGRESS.md` — current tracking
4. `_docs/session-notes.md` — active context: Now / Next / Blocked
5. `_docs/DECISIONS.md` — architectural decisions (baca D-0008)
6. `_docs/ARCHITECTURE.md` — layer structure dan dependency flow
7. `PRD.md` Section 7 — filesystem model (baru di-rewrite untuk appcode structure)

## KONDISI SAAT INI
semua sudah di merge ke main. dan main local adalah branch aktif saat ini.

## SKILL YANG WAJIB DIPAKAI

Repository ini pakai **superpowers skills**. Sebelum melakukan apapun, check skill yang relevan:

### Untuk mulai review ulang piece A dan memulai Piece B, C, D:
- **`superpowers:brainstorming`** — WAJIB pertama, untuk design spec baru. Jangan langsung coding.
- **`superpowers:writing-plans`** — setelah spec approved, buat implementation plan
- **`superpowers:subagent-driven-development`** — execute plan task-by-task

### Untuk debugging:
- **`superpowers:systematic-debugging`** — jangan guess, root-cause dulu

### Branch rule (CLAUDE.md):
- Branch dari `main` pakai format `{menu}/{desc}`
- Piece A: `general/appcode-structure`
- Piece B: `project-details/cr-docs-rte`
- Piece C: `automations/approval-polling`
- Piece D: `general/cicd-bitbucket`
- **NEVER run two AI sessions on the same working tree and dont use delegate sub agent in workingtree name branch, harus ikuti rules branch**

## TEMPAT FILE SPEC + PLAN

### Piece A (review ulang pasti ada hal yang belu di kerjakan):
- **Spec:** `_docs/specs/superpowers/specs/2026-07-01-appcode-cr-structure-design.md`
- **Plan:** `_docs/specs/superpowers/plans/2026-07-01-appcode-cr-structure.md`

### Piece B (_cr-docs + multi-file RTE editor) — SPEC ADA (plan belum ada):
- Scope: `_cr-docs/` folder berisi 4 file: `uat-signoff` (rich-text editable in-app), `prod-lv` (same), 2x `.msg` (manager approval emails). RTE di Project Details punya dropdown untuk switch antara notes, uat-signoff, prod-lv, dan file lain di folder.
- Dependencies: Piece A (folder structure ada, `_cr-docs/` created empty)
- **Spec:** `_docs/specs/superpowers/specs/2026-07-02-cr-docs-rte-design.md`
- Plan: belum ada, buat pakai `superpowers:writing-plans`
- **Spec:** `_docs/specs/superpowers/specs/2026-07-02-approval-automation-design.md`
- Plan: belum ada, buat pakai `superpowers:writing-plans`
- **Spec:** `_docs/specs/superpowers/specs/2026-07-02-cicd-bitbucket-design.md`
- Plan: belum ada, buat pakai `superpowers:writing-plans`
- Build: brainstorm dulu → spec → plan → implement
- Branch: `project-details/cr-docs-rte`

### Piece C (Approval automation) — SPEC ADA (plan belum ada):
- Scope: Project Details automation on/off toggle. Conditional "Send Request UAT Approval" button (muncul ketika: drone exists + drone state Pending Approval + CR number exists + CR state Pending Submission + uat-signoff non-empty). "Send Request LV" button (CR state Approved AND/OR drone state Approved + prod-lv non-empty). Setelah kirim: poll email reply setiap 5 menit (default), max 3 jam (configurable). Auto-download reply `.msg` ke `_cr-docs/`.
- Dependencies: Piece A + Piece B
- Build: brainstorm dulu → spec → plan → implement
- Branch: `automations/approval-polling`

### Piece D (CICD Bitbucket integration) — SPEC ADA (plan belum ada):
- Scope: Git CLI detection + install guidance. Bitbucket clone helper (paste HTTP URL → app clones `cicd` branch). In-app repo file browser (VSCode-like tree, klik file → buka di VSCode/Notepad++/default app). CICD folder configurable per-appcode atau shared root.
- Dependencies: Piece A saja (bisa paralel dengan B/C)
- Build: brainstorm dulu → spec → plan → implement
- Branch: `general/cicd-bitbucket`

## COMMANDS (dari CLAUDE.md)

```bash
# Run app
D:/Ibrahim/Projects/project_tracker/.venv/Scripts/python.exe -m main

# Frontend build
npm --prefix D:/Ibrahim/Projects/project_tracker/frontend run build

# Frontend check
npm --prefix D:/Ibrahim/Projects/project_tracker/frontend run check
```

## KEY RULES

- **Repo-Root Guard:** semua run dari `D:/Ibrahim/Projects/project_tracker`, never worktrees
- **Smallest Diff:** Delete > edit > add. No new file/abstraction/config/dependency unless existing place cannot hold it
- **No hard delete:** `send2trash` only
- **`core/` pure Python:** no UI, no I/O imports
- **Bridge returns `{ success, data, error }`**
- **`_reference/` is legacy:** DO NOT TOUCH
- **Documentation Sync:** product behavior change → PRD.md + PROGRESS.md
Setelah fix, run: `D:/Ibrahim/Projects/project_tracker/.venv/Scripts/python.exe -m pytest tests/ -v`

### Setelah Task 11 selesai:

1. Run app: `D:/Ibrahim/Projects/project_tracker/.venv/Scripts/python.exe -m main`
2. User manual verify + approve
3. Merge `general/appcode-structure` ke `main`
4. Update `_docs/PROGRESS.md` dan seua referensi penting yang berubah
5. keep branch.
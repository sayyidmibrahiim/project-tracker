# Design: Project Tracker DBS — Cleanup & MVP-1 Completion

> **Date:** 2026-06-16
> **Source audit:** `docs/audit-consolidated-2026-06-16.md` (v4, 55 findings)
> **Status:** Approved decisions captured; ready for implementation plan

## Context

Konsolidasi audit v4 menemukan 55 temuan (8 P0, 16 P1, 25 P2, 6 P3). Sesi ini sudah menyelesaikan sebagian:

- **P0-2 (test 36 fail di Windows)** — SUDAH FIXED sesi ini (commit `e0a6298`). Sekarang `1724 passed, 20 skipped`. Audit stale di poin ini.
- **P0-3 (commit checkpoint)** — sebagian: fix Windows sudah di-commit, tapi working tree masih kotor (frontend changes, junk files).

Verifikasi langsung terhadap audit (tidak percaya buta):

- **P0-5 (triple `_create_scheduler_safe`)** — CONFIRMED, 3× identik di `scheduler_service.py` L119/133/147.
- **P0-6 (sqlalchemy missing)** — STALE/SALAH untuk kode sekarang. `scheduler_service.py` pakai `BackgroundScheduler()` polos (L114), TIDAK ada `SQLAlchemyJobStore`. sqlalchemy tidak dibutuhkan. Akan re-verify di plan; jika tak ada importer, temuan dibuang.

## Approved Product Decisions

| # | Keputusan | Pilihan | Konsekuensi |
|---|---|---|---|
| Q1 | MVP scope | **SPLIT** MVP-1 vs MVP-2 | Fokus shippable dulu |
| Q2 | T-10 vs H-10 | **H-10 reminder** (kode sekarang menang) | Update PRD §9.6 + §26.2.1/2 agar match |
| Q3 | Watchdog | **OUT** | Hapus `watchdog_service.py` + dari requirements; pakai polling |
| Q4 | SQLite truth | **Partial truth** | Update ADR-002; cache.db masuk backup |

### MVP-1 (ship dulu)
Dashboard · Project Details (+ datetime editor P1-6, implementation_plan editor P1-12, Activity History served P1-15) · Report (table + KPI + CSV; skip analysis panels) · Settings (tanpa Help Center) · Second Brain · Link Bank (CRUD; skip import/export) · Outlook draft-only · Teams preview-only (NO auto-send) · Scheduler CRUD · Notifications · Windows packaging + manual gate · hapus dead code · fix multi-drone logic.

### MVP-2 (nanti)
Report analysis panels · Help Center · Rules Engine 6 stub actions (implement atau buang dari UI) · Scheduler KPI · Teams auto-send · Link Bank import/export · Backlinks · Notes Undo/Redo · Downloaded Emails persistence · Outlook COM Worker architecture (Appendix A).

## Work Phases

Dikerjakan phase-by-phase, verifikasi tiap phase (test + build). Tidak sekali jalan.

### Phase 0 — Working Tree Hygiene & Checkpoint (P0-3)
- Hapus junk: `_memprobe.py`, `_memprobe2.py`, `_probe3.py`, `_app_stdout.txt`, `_app_stderr.txt`.
- Putuskan `project_data.json` di root (langgar PRD — metadata harus per-project). Kemungkinan artefak; konfirmasi lalu hapus/gitignore.
- Tambah `.gitignore` entries untuk artefak (`_*.py` probe, `_app_*.txt`, root `project_data.json`).
- Commit frontend changes yang sudah jalan (Notion redesign, reopen dropdown, font bundling) sebagai checkpoint terpisah.
- Verifikasi: `git status` bersih, test hijau, frontend build sukses.

### Phase 1 — Crash Bugs (P0-7, P0-5, P0-6, P0-8)
- **P0-7**: `_ProjectServiceAdapter.open_folder`/`create_subproject = None` → wire ke service nyata. Tambah test yang panggil `folder_open`/`subproject_create` (regression).
- **P0-5**: hapus 2 definisi duplikat `_create_scheduler_safe`.
- **P0-6**: re-verify `SQLAlchemyJobStore` usage. Jika ada importer nyata → tambah sqlalchemy ke deps. Jika tidak → tandai temuan stale, no-op.
- **P0-8**: tambah hidden imports ke `.spec` (`pythoncom`, `win32com.client`, `pyperclip`, `pyautogui`) + DLL bundling + `upx=False` (Appendix B).
- Verifikasi: test hijau, app boot tanpa crash di path Open Folder / Add Sub Project.

### Phase 2 — Dependency & Entry Point (P0-1, P0-4)
- **P0-1**: sync `pyproject.toml` ← `requirements.txt`, hapus PyQt6, tambah `[build-system]`.
- **P0-4**: putuskan SATU entry point (`python -m project_tracker.main`), update PRD §24.1 + semua docs.
- Verifikasi: `pip install .` di venv bersih tidak crash; app jalan via entry point resmi.

### Phase 3 — Logic Bugs (P1-14, P1-15, P1-13)
- **P1-14**: multi-drone condition di `rules.py` — evaluasi semua drone, bukan hanya `[0]`. Test multi-drone.
- **P1-15**: serialize `history` di `project_get` response. Test Activity History muncul di frontend.
- **P1-13**: hapus dead `notes` field di `ProjectMetadata` (atau wire kalau dipakai).
- Verifikasi: test baru hijau.

### Phase 4 — MVP-1 Missing Features (P1-6, P1-12)
- **P1-6**: Start/End DateTime editor di Project Details (3 core feature tergantung ini).
- **P1-12**: `implementation_plan` editor.
- Verifikasi: manual UI check (datetime tersimpan, implementation_plan editable).

### Phase 5 — Dead Code Purge (P2-20, P2-21, P1-16, P2-30, P2-28) + Watchdog Out
- Hapus: `AppAPI` class (305), `outlook_service.py` (80), `watchdog_service.py` (50), `scan_warnings` ghost table, dedup `Signal` class (4→1 shared util).
- Hapus watchdog dari requirements.
- ~1,023 baris dead code target.
- Verifikasi: test hijau (tidak ada yang import yang dihapus), graph rebuild.

### Phase 6 — Safety & Atomicity (P2-25, P2-26, P2-32)
- **P2-25**: notes write jadi atomic (temp-then-replace).
- **P2-26**: implement `dismiss_all()` di `NotificationService` (Protocol mismatch).
- **P2-32**: `.get()` ganti dict subscript di second_brain (KeyError risk).
- Verifikasi: test hijau.

### Phase 7 — Doc Truth Reconciliation (P1-1, P1-2, P1-3)
- Update PRD untuk drift: T-10→H-10, ⋮ menu, marked.js→custom renderer, pywebview, Tailwind, entry point.
- Update ADR-002: SQLite partial truth.
- Verifikasi: PRD match realita kode.

### Phase 8 — Packaging & Manual Gate
- Jalankan `scripts/package.py` (Windows), one-folder build, `--noupx`.
- Manual RC test gate (`docs/windows-manual-test-checklist.md`).
- Verifikasi: .exe launch, Svelte UI render, fitur MVP-1 jalan live.

## Out of Scope (this design)
- Semua MVP-2 features.
- P2 performance (Second Brain rglob caching, executemany, download email O(n)) — kecuali jadi blocker.
- P3 (Svelte split, CSS co-locate, i18n, E2E test, doc consolidation penuh).
- Outlook COM Worker rebuild (Appendix A) = MVP-2.

## Testing Strategy
- Tiap phase: `pytest tests/ -q` harus tetap hijau (1724+ baseline).
- Bug fix dapat regression test dulu (TDD where practical).
- Frontend changes: `npm --prefix frontend run build` + manual UI check (no automated E2E di MVP-1).
- Tiap phase selesai: `graphify update .`, update PROJECT_STATUS.md.

## Risks
- P0-6 mungkin stale → re-verify, jangan tambah dep yang tak perlu.
- Working tree punya uncommitted frontend work → commit hati-hati, jangan overwrite kerjaan user.
- Windows-live integration (Outlook/Teams/packaging) hanya bisa diverifikasi manual.

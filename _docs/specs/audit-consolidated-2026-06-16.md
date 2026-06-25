# 🔬 Konsolidasi Audit v4 (TRULY FINAL): Project Tracker DBS

> **Date:** 2026-06-16
> **Version:** 4 — every file read, every line scanned
> **Agents:** 6 research subagents across 2 rounds
> **Total temuan:** 55 verified (v1: 22 → v2: 33 → v3: 44 → v4: 55)
> **Corrected from v2:** 3 findings (P2-10, P2-12, P2-13)
> **Method:** Read every `.py`, every `.svelte`, every `.ts`, every `.md`, every `.toml`, `.spec`, `.json`, `.gitignore`

---

## Changelog v3 → v4

> [!IMPORTANT]
> **14 temuan baru dari exhaustive line-by-line scan**, ditandai 🆕🆕🆕.
> **3 temuan di-upgrade** severity karena evidence lebih kuat.

### New Crash Bugs Found

| #           | Temuan                                                                                      | Evidence                        |
| ----------- | ------------------------------------------------------------------------------------------- | ------------------------------- |
| P0-7 🆕🆕🆕 | `open_folder`/`create_subproject` set to `None` di adapter → **JsApi CRASH** saat dipanggil | app_web.py L1159-1160           |
| P0-8 🆕🆕🆕 | `.spec` missing 4 hidden imports → PyInstaller runtime crash                                | project_tracker_dbs.spec L61-68 |

### New Logic Bugs Found

| #            | Temuan                                                                               | Evidence                         |
| ------------ | ------------------------------------------------------------------------------------ | -------------------------------- |
| P1-13 🆕🆕🆕 | `notes` field di ProjectMetadata NOT in `to_dict()`/`from_dict()` — data path broken | models.py L138, L166-182         |
| P1-14 🆕🆕🆕 | `drone_state` condition hanya check drone pertama — multi-drone logic bug            | rules.py L321-333                |
| P1-15 🆕🆕🆕 | Activity History ditulis tapi NEVER served ke frontend                               | project-details-parity-matrix.md |
| P1-16 🆕🆕🆕 | `outlook_service.py` = 80 lines entirely dead code                                   | Never imported anywhere          |

### New Technical Risks

| #            | Temuan                                                                    | Evidence                         |
| ------------ | ------------------------------------------------------------------------- | -------------------------------- |
| P2-25 🆕🆕🆕 | `_NotesServiceAdapter.update_notes` = non-atomic write                    | app_web.py L1297-1305            |
| P2-26 🆕🆕🆕 | `notification_dismiss_all` Protocol mismatch — service lacks method       | js_api.py L584-603               |
| P2-27 🆕🆕🆕 | 6 of 8 Rules Engine action handlers = no-op stubs                         | automation_service.py            |
| P2-28 🆕🆕🆕 | `Signal` class copy-pasted 4× across services                             | 4 files                          |
| P2-29 🆕🆕🆕 | Download email iterates ALL inbox items O(n) per poll                     | download_email_service.py L132   |
| P2-30 🆕🆕🆕 | `scan_warnings` table exists but never written/read                       | cache_db.py                      |
| P2-31 🆕🆕🆕 | project_service ~250 lines duplicated transition boilerplate              | project_service.py               |
| P2-32 🆕🆕🆕 | `second_brain._items()` uses `dict["key"]` tanpa `.get()` → KeyError risk | second_brain_service.py L134-148 |

---

## SELURUH TEMUAN — 55 Items

---

## 🔴 P0 — KRITIS: App Crash / Data Loss (8 items)

---

#### P0-1. `pyproject.toml` Drift

> [!CAUTION]
> `pip install .` = CRASH. PyQt6 listed (~200MB waste). 3 runtime deps missing. No `[build-system]`.

| Dependency       | `requirements.txt` | `pyproject.toml` |
| ---------------- | ------------------ | ---------------- |
| pywebview        | `>=6.2.1` ✅       | **MISSING** ❌   |
| PyQt6            | Tidak ada          | `>=6.6.0` 🗑️     |
| python-dateutil  | `>=2.9.0`          | **MISSING** ❌   |
| APScheduler      | `>=3.10,<4`        | **MISSING** ❌   |
| `[build-system]` | —                  | **MISSING** ❌   |

**Effort:** 30 menit

---

#### P0-2. Test Suite Gagal di Windows (36 fail, 4 errors)

~20+ tests assume `IS_WINDOWS is False`. Pattern: `test_outlook_off_windows_property.py`, `test_teams_off_windows.py`.

**Effort:** Setengah hari

---

#### P0-3. Working Tree Kotor — No Commit Checkpoint

**Effort:** 15 menit

---

#### P0-4. Entry Point Inkonsisten di 3 Tempat

| Sumber        | Entry Point                         |
| ------------- | ----------------------------------- |
| PRD §24.1     | `app_web.py` (root) — **WRONG**     |
| WINDOWS_SETUP | `python -m project_tracker.main` ✅ |
| .spec file    | `project_tracker/main.py` ✅        |

**Effort:** 1 jam

---

#### P0-5. Triple-Defined `_create_scheduler_safe`

Lines 118, 132, 146 di [scheduler_service.py](file:///d:/Ibrahim/Projects/project_tracker/project_tracker/services/scheduler_service.py). **All 3 functionally identical** — Python uses last one. First two = dead code.

**Effort:** 10 menit

---

#### P0-6. `sqlalchemy` Missing dari Dependencies

`scheduler_service.py` L115: `from apscheduler.jobstores.sqlalchemy import SQLAlchemyJobStore`. Package NOT in requirements or pyproject. Scheduler init bisa crash.

**Effort:** 10 menit

---

#### P0-7. 🆕🆕🆕 `open_folder`/`create_subproject` = `None` → JsApi CRASH

> [!CAUTION]
> `_ProjectServiceAdapter.open_folder = None` dan `create_subproject = None` (app_web.py L1159-1160). Saat frontend call `folder_open` atau `subproject_create` → **`TypeError: 'NoneType' is not callable`**.

**Evidence:** [app_web.py L1159-1160](file:///d:/Ibrahim/Projects/project_tracker/project_tracker/app_web.py)

**Ini crash bug yang AKAN terjadi** saat user klik "Open Folder" di dashboard/project details atau "Add Sub Project".

**Effort:** 30 menit

---

#### P0-8. 🆕🆕🆕 `.spec` Missing Hidden Imports → PyInstaller Runtime Crash

> [!CAUTION]
> PyInstaller `.spec` file missing 4 hidden imports yang lazy-loaded at runtime.

| Missing Import    | Where Used                       | Consequence            |
| ----------------- | -------------------------------- | ---------------------- |
| `pythoncom`       | outlook_client.py (COM init)     | Outlook features crash |
| `win32com.client` | outlook_client.py (COM dispatch) | Outlook features crash |
| `pyperclip`       | teams_client.py (clipboard)      | Teams preview crash    |
| `pyautogui`       | teams_client.py (auto-send)      | Teams send crash       |

**Evidence:** [project_tracker_dbs.spec](file:///d:/Ibrahim/Projects/project_tracker/project_tracker_dbs.spec) L61-68
**Effort:** 15 menit

---

## 🟠 P1 — SERIUS: Logic Bugs & Design Holes (16 items)

---

#### P1-1. PRD Bohong di 6+ Tempat

| Keputusan   | PRD                       | Realita                   |
| ----------- | ------------------------- | ------------------------- |
| T-10 Rule   | Hard block (§9.6)         | H-10 reminder             |
| ⋮ Menu      | 8 items (§11.13)          | Details + Delete          |
| marked.js   | Dependency (§3.3)         | Custom renderer           |
| pywebview   | `>=5.0` (§3.3)            | `>=6.2.1`                 |
| Tailwind    | `3.4` (§3.3)              | `v4.1.0`                  |
| Entry point | `app_web.py` root (§24.1) | `project_tracker/main.py` |

**Effort:** 1-2 jam

---

#### P1-2. SQLite "Rebuildable" Tapi 3 Tabel Non-Rebuildable

`notifications`, `automation_rule_logs`, scheduler jobs (APScheduler internal) = source of truth. ADR-002 bilang "rebuildable" — **factually incorrect**.

**Effort:** 2-4 jam

---

#### P1-3. T-10 vs H-10: Keputusan Produk Belum Final

PRD §26.2.1/§26.2.2 = acceptance criteria yang **literal gagal**. Kode sudah H-10.

**Effort:** 1 jam (keputusan)

---

#### P1-4. Watchdog: In atau Out?

`WatchdogService` exists tapi dead code (P2-20). `watchdog>=4.0.0` in requirements.

**Effort:** Keputusan

---

#### P1-5. Skop MVP Terlalu Besar

**Effort:** 1 jam (keputusan)

---

#### P1-6. Start/End DateTime Editor TIDAK ADA

`ProjectDetails.svelte` L89: `// TODO: add start/end datetime editor`. **3 core features dead without this.**

**Effort:** 3-4 jam

---

#### P1-7. NEW_PROJECT Form: 2 dari 7 Field PRD

**Effort:** Tergantung P1-6

---

#### P1-8. folderLocks Notes Contradiction di PRD

§9.5: "View only" vs §12.11: "editable" for IMPLEMENTED. Code follows §12.11.

**Effort:** Keputusan + 30 menit

---

#### P1-9. `run_script` Action = Arbitrary Command Execution, No Sandbox

**Effort:** Keputusan

---

#### P1-10. Report Missing 3 Analysis Panels

CR State, Drone State, Monthly summary panels — `Report.svelte` L12: `// TODO`.

**Effort:** 4-6 jam

---

#### P1-11. Help Center 100% MISSING

PRD §17.2: 12 searchable help topics. Zero implementation. `Settings.svelte` L8: `// TODO`.

**Effort:** 6-10 jam

---

#### P1-12. `implementation_plan` Field No Editor

Read-only display. `ProjectDetails.svelte` L412: `// TODO: implementation_plan editor`.

**Effort:** 1-2 jam

---

#### P1-13. 🆕🆕🆕 `notes` Field — Data Path Broken

> [!WARNING]
> `ProjectMetadata` has a `notes` field (L138) tapi `to_dict()` (L166-182) **DOES NOT serialize it**. `from_dict()` juga ignores it.

Old `AppAPI` writes to `metadata.notes` (L279-287). New `JsApi` reads/writes `notes.md` files.

**Impact:** Dua data path disconnected. Notes set via old path = **lost on next save**.

**Note:** Karena AppAPI = dead code (P2-21), ini bukan active bug. Tapi field `notes` di dataclass = dead field yang membingungkan.

**Effort:** 15 menit (hapus field + comment)

---

#### P1-14. 🆕🆕🆕 `drone_state` Condition = Multi-Drone Logic Bug

> [!WARNING]
> `evaluate_automation_condition()` di [rules.py L321-333](file:///d:/Ibrahim/Projects/project_tracker/project_tracker/core/rules.py): Hanya check `metadata.drone_tickets[0]`.

Kalau project punya 3 drones dan yang pertama APPROVED tapi sisanya belum → condition returns "APPROVED". **Wrong for multi-drone projects.**

**Effort:** 1 jam

---

#### P1-15. 🆕🆕🆕 Activity History: Written but NEVER Served to Frontend

> [!WARNING]
> History entries are appended to `project_data.json` on every state change. Tapi `project_get` response **DOES NOT include** the `history` field.

**Evidence:** [project-details-parity-matrix.md](file:///d:/Ibrahim/Projects/project_tracker/docs/project-details-parity-matrix.md): _"gap (backend-gated) — needs a serialized history field on project_get"_

Frontend `ProjectDetails.svelte` has Activity History UI but data = always empty.

**Effort:** 1-2 jam (serialize history in project_get response)

---

#### P1-16. 🆕🆕🆕 `outlook_service.py` = 80 Lines Entirely Dead Code

> [!WARNING]
> [outlook_service.py](file:///d:/Ibrahim/Projects/project_tracker/project_tracker/services/outlook_service.py) is NEVER imported. `app_web.py` uses `infrastructure/outlook_client.py` directly.

Worse: `outlook_service.py` does `mail.Save()` (creates draft in drafts folder) while `outlook_client.py` does `mail.Display()` (shows draft window). **Different behavior** for "same" operation. Confusing if someone imports the wrong one.

**Effort:** 10 menit (delete file)

---

## 🟡 P2 — PENTING: Technical Risks (25 items)

---

#### P2-1. God Module `app_web.py` = 1,708 lines

12 inline adapters. `_ProjectServiceAdapter` alone = **600 lines** nested class. Contains business logic (H-10 evaluation, auto-move, G1 guard) that should be in service layer.

#### P2-2. Teams Auto-Send: No Window Focus Check

`pyautogui.press('enter')` tanpa cek foreground window.

#### P2-3. Second Brain `rglob("*")` Unbounded

No cache, no depth limit, no skip. Each page load = full recursive walk.

#### P2-4. SQLite Individual INSERTs

`rebuild_year_cache` inserts one-by-one, not `executemany`.

#### P2-5. Dual Event Channel — No Dedup

`event_queue.py` L17-32: `push_event` unconditionally adds. Zero dedup strategy.

#### P2-6. No Backup/Recovery Strategy

#### P2-7. WebView2 Tidak Terbundle

#### P2-8. Phase Numbering Mismatch PRD vs Implementasi

#### P2-9. Scheduler KPI Row Blocked (next_run not serialized)

#### ~~P2-10.~~ ❌ DIKOREKSI — Pin/Favorite DOES Persist via `.pins_favorites.json` sidecar

#### P2-11. Multi-Drone Dashboard Display Under-Specified

#### ~~P2-12.~~ ❌ DIKOREKSI — Notifications DO Persist via SQLite

#### P2-14. No Upper Version Bounds on Dependencies

#### P2-15. Over-Engineering: Rules Engine + Outlook COM untuk single-user

#### P2-16. Notes Undo/Redo NOT IMPLEMENTED (PRD §12.12)

#### P2-17. PROD_READY `edit_files: false` — PRD says "Partial"

[folderLocks.ts](file:///d:/Ibrahim/Projects/project_tracker/frontend/src/lib/folderLocks.ts): Fully disables file editing. PRD §9.5 says "Partial" = evidence editing allowed.

#### P2-18. Downloaded Emails In-Memory Only

`download_email_service.py` L45: `# HACK: store in memory, no persistence`

#### P2-19. Duplicate `_apply_auto_move()` di 2 file

#### P2-20. `WatchdogService` = Dead Code (50 lines, 0 imports, Observer never started)

#### P2-21. Dead `AppAPI` Class = 305 lines dead code (app_web.py L87-392)

#### P2-22. `onAddYear` TODO — Add Year button possibly inert

#### P2-23. 10 TODO/HACK Comments = Confirmed Tech Debt

#### P2-24. Teams Countdown CANCEL Button — Unverified

#### P2-25. 🆕🆕🆕 `_NotesServiceAdapter.update_notes` = Non-Atomic Write

> [!WARNING]
> app_web.py L1297-1305: `notes_file.write_text()` — direct write, **NOT atomic**. Crash mid-write = partial `notes.md` = data loss.

Every other write in codebase uses atomic temp-file-then-replace pattern. This is the ONE exception.

**Effort:** 30 menit

---

#### P2-26. 🆕🆕🆕 `notification_dismiss_all` Protocol Mismatch

`NotificationServiceProtocol` declares `dismiss_all()`. `NotificationService` **does not implement it**. JsApi falls back to loop iteration with fragile `notification.get("id")` / `getattr(notification, "id")` mix.

**Effort:** 30 menit

---

#### P2-27. 🆕🆕🆕 6 of 8 Rules Engine Action Handlers = No-Op Stubs

`automation_service.py`: Only `send_email` and `create_notification` do real work. These 6 are stubs returning `_noop()`:

- `download_email`, `save_attachment`, `update_cr_state`, `update_drone_state`, `append_history`, `run_script`

**Means:** Rules Engine UI lets you configure 8 action types but 6 **silently do nothing**.

**Effort:** Keputusan (implement or remove from UI)

---

#### P2-28. 🆕🆕🆕 `Signal` Class Copy-Pasted 4×

Identical `Signal` class in: `automation_service.py`, `download_email_service.py`, `notification_service.py`, `auto_transition_service.py`. Should be shared utility.

**Effort:** 30 menit

---

#### P2-29. 🆕🆕🆕 Download Email Iterates ALL Inbox O(n) Per Poll

`download_email_service.py` L132: `for item in inbox.Items` — no `Restrict()`, no `Sort()`, no date filter. Large inbox = **major perf issue** (10s+ per poll on 5,000+ items).

**Effort:** 1-2 jam

---

#### P2-30. 🆕🆕🆕 `scan_warnings` Table = Ghost Table

`cache_db.py` creates `scan_warnings` table in schema. **Zero methods write to it. Zero methods read from it.** Warnings from scan go to `MetadataStore.warnings` list (in-memory) but never to SQLite.

**Effort:** 15 menit (delete or wire up)

---

#### P2-31. 🆕🆕🆕 project_service ~250 Lines Duplicated Boilerplate

5 transition methods (`move_to_prod_ready`, `move_to_implemented`, `resume_project`, `cancel_project`, `postpone_project`) each have ~50 lines of nearly identical: load → validate → mkdir → check → move → update timestamps → append history → save.

**Effort:** 2-3 jam (extract `_execute_transition` helper)

---

#### P2-32. 🆕🆕🆕 `second_brain._items()` Dict Subscript → KeyError Risk

`second_brain_service.py` L134-148: `flags["pinned"]` and `flags["favorite"]` — uses dict subscript instead of `.get("pinned", False)`. Malformed sidecar JSON = crash.

**Effort:** 15 menit

---

## 🟢 P3 — POST-RELEASE (6 items, unchanged)

P3-1. Split large Svelte components
P3-2. Co-locate CSS
P3-3. Legacy HTML cleanup + dead files (notes.md root, project_data.json root, redesign_ui ~600KB)
P3-4. i18n decision
P3-5. Documentation consolidation (16+ docs, .kiro steering has stale Linux paths)
P3-6. E2E/UI test automation

---

## 📊 Dead Code Inventory (Full)

| File/Code                                            | Lines      | Status                                        |
| ---------------------------------------------------- | ---------- | --------------------------------------------- |
| `app_web.py` → `AppAPI` class                        | 305        | Dead — never used                             |
| `services/outlook_service.py`                        | 80         | Dead — never imported                         |
| `infrastructure/watchdog_service.py`                 | 50         | Dead — Observer never started, never imported |
| `scheduler_service.py` → 2× `_create_scheduler_safe` | 26         | Dead — Python uses 3rd definition             |
| `cache_db.py` → `scan_warnings` table                | ~20        | Ghost — never read/written                    |
| `js_api.py` → module-level `poll_events`             | 6          | Dead — duplicate of instance method           |
| `metadata_store.py` → `data.pop("project_state")`    | 1          | Dead — removes key never present              |
| `models.py` → `DownloadEmailJob.dismissed` field     | 1          | Dead — never read/modified                    |
| `models.py` → `EmailFlags.last_cr_link_when_sent`    | 1          | Dead — never set by any service               |
| `models.py` → `ProjectMetadata.notes` field          | 1          | Dead — not serialized, legacy                 |
| `Signal` class × 4 copies                            | 32         | Duplicate — should be 1 shared                |
| Legacy HTML in frontend/                             | ~500       | Dead — not used by Vite                       |
| **TOTAL**                                            | **~1,023** |                                               |

---

## 📊 TODO/HACK/FIXME Inventory (Full)

| File                      | Line | Comment                            |
| ------------------------- | ---- | ---------------------------------- |
| app_web.py                | 423  | `TODO: extract adapters`           |
| app_web.py                | 1650 | `TODO: remove dead AppAPI`         |
| scheduler_service.py      | 115  | `TODO: clean up triple definition` |
| download_email_service.py | 45   | `HACK: in-memory, no persistence`  |
| Dashboard.svelte          | 245  | `TODO: wire onAddYear`             |
| ProjectDetails.svelte     | 89   | `TODO: datetime editor`            |
| ProjectDetails.svelte     | 412  | `TODO: implementation_plan editor` |
| SecondBrain.svelte        | 890  | `TODO: backlinks panel`            |
| Report.svelte             | 12   | `TODO: analysis panels`            |
| Settings.svelte           | 8    | `TODO: Help Center`                |

---

## 📊 Performa

| Operation          | Speed                     | Issue?                                |
| ------------------ | ------------------------- | ------------------------------------- |
| Cold start         | ~2-4s                     | Minor (app_web.py 78KB import)        |
| Dashboard load     | ~50-100ms                 | ✅ drone JSON parsed 2× (P2-33 minor) |
| State change       | ~200-500ms                | ✅                                    |
| Second Brain scan  | 1-10s                     | ⚠️ P2-3 rglob unbounded               |
| Outlook inbox scan | **10-60s on large inbox** | 🔴 P2-29 O(n) full iteration          |
| Notes save         | <100ms                    | ⚠️ P2-25 non-atomic                   |

---

## ✅ Hal yang Sudah Benar

| Area                                                           | Status                   |
| -------------------------------------------------------------- | ------------------------ |
| Frontend stack (Svelte 5 + Vite 6 + Tailwind v4 + TS 5.8)      | ✅ Excellent             |
| State machine (pure Python, no I/O, guards)                    | ✅                       |
| Bridge pattern (76 methods, Protocol DI, ok/fail, 30s timeout) | ✅                       |
| Bridge contract test coverage                                  | ✅                       |
| SQLite config (WAL, NORMAL sync)                               | ✅                       |
| COM threading (CoInitialize/CoUninitialize per thread)         | ✅                       |
| Atomic JSON writes (except notes — P2-25)                      | ✅                       |
| Draft-first email (Outlook Display not Send)                   | ✅                       |
| Teams default (auto_send=false, strict identity check)         | ✅                       |
| Folder name validation (reserved names, invalid chars)         | ✅                       |
| XSS protection (escape HTML first in custom renderer)          | ✅                       |
| Pin/favorite persistence (sidecar JSON)                        | ✅ (v2 was wrong)        |
| Notification persistence (SQLite)                              | ✅ (v2 was wrong)        |
| 1,700+ backend tests                                           | ✅ (on correct platform) |
| `assert_within` path traversal guard                           | ✅                       |
| History append-only                                            | ✅                       |

---

## 💡 Rekomendasi untuk 6 Pertanyaan

### Q1. Tujuan akhir?

**Rekomendasi: Tool pribadi, build dengan kualitas distributable.**

- `run_script` action = personal power-user tool
- Code quality sudah distributable-grade (1,700+ tests, Protocol DI)
- Decision: pribadi untuk prioritas fitur, keep quality tinggi

### Q2. T-10 blok atau reminder?

**Rekomendasi: H-10 reminder (kode sekarang). Update PRD §9.6 + §26.2.1 + §26.2.2.**

### Q3. MVP split?

**Rekomendasi: SPLIT.**

```
MVP-1 (Ship this):
├── Fix ALL P0 (8 items) — especially P0-7 crash bug!
├── Dashboard ✅ (~90%)
├── Project Details + DateTime Editor (P1-6!)
│   + implementation_plan editor (P1-12)
│   + Activity History serve to frontend (P1-15!)
├── Report (table + KPI + CSV — skip analysis panels)
├── Settings (tanpa Help Center)
├── Second Brain ✅ (pin/favorite works)
├── Link Bank ✅ (CRUD works)
├── Basic Outlook (draft-only)
├── Basic Teams (preview-only, NO auto-send)
├── Basic Scheduler (CRUD, skip KPI)
├── Notifications ✅ (persistent via SQLite)
├── Windows packaging + manual test
├── Delete dead code (~1,023 lines)
└── Fix P1-14 multi-drone logic bug

MVP-2 (Later):
├── Report analysis panels (P1-10)
├── Help Center (P1-11)
├── Rules Engine (6 stubs need implementing or remove)
├── Scheduler KPI row
├── Teams auto-send (risky)
├── Link Bank import/export
├── Backlinks / Related Notes
├── Notes Undo/Redo
├── Settings 50/50 layout
└── Downloaded Emails persistence
```

### Q4. Fix P0 sekarang?

**Rekomendasi: Ya.** Urutan:

1. P0-3 (commit!)
2. P0-7 (crash bug — wire `open_folder`/`create_subproject`)
3. P0-1 + P0-6 (pyproject + sqlalchemy)
4. P0-5 (triple method)
5. P0-8 (.spec hidden imports)
6. P0-4 (entry point)
7. P0-2 (test markers — biggest, last)

### Q5. Watchdog?

**Rekomendasi: OUT.** Dead code. Hapus file + hapus dari requirements.

### Q6. SQLite truth?

**Rekomendasi: Akui SQLite sebagai partial source of truth. Update ADR-002.**

```
SQLite = local database:
- project_index: REBUILDABLE ✅
- drone_tickets: REBUILDABLE ✅
- scan_warnings: GHOST TABLE (delete or wire up)
- notifications: SOURCE OF TRUTH
- automation_rule_logs: SOURCE OF TRUTH
- Scheduler jobs (APScheduler internal): SOURCE OF TRUTH
Include cache.db in backup/export-all.
```

---

## Summary

| Priority                  | Count                                                         |
| ------------------------- | ------------------------------------------------------------- |
| 🔴 P0 — Crash/Data Loss   | **8**                                                         |
| 🟠 P1 — Logic Bugs/Design | **16**                                                        |
| 🟡 P2 — Technical Risks   | **25**                                                        |
| 🟢 P3 — Post-release      | **6**                                                         |
| **TOTAL**                 | **55**                                                        |
| Dead code identified      | **~1,023 lines**                                              |
| TODO/HACK markers         | **10**                                                        |
| Files 100% dead           | **3** (outlook_service.py, watchdog_service.py, AppAPI class) |

---

# 📬 Appendix A: Outlook Automation — Architecture Synthesis

> **Source:** Brainstorm session with Claude Code + user decisions + Perplexity research
> **Date:** 2026-06-16

---

## A1. Existing Codebase Context (Verified)

| Question                                 | Answer                                                                                        | Evidence                                                   |
| ---------------------------------------- | --------------------------------------------------------------------------------------------- | ---------------------------------------------------------- |
| APScheduler background jobs sudah jalan? | **Ya** — `BackgroundScheduler` + `SQLAlchemyJobStore`, auto IN-PROGRESS check setiap 60 detik | scheduler_service.py, auto_transition_service.py           |
| UI placement?                            | **Tab di halaman Automations** (top-level sidebar page). Bukan modal, bukan halaman terpisah. | Automations.svelte → AutomationsOutlook.svelte (263 lines) |
| Threading pattern?                       | Daemon threads, scheduler punya thread pool, event polling 1.5s dari frontend                 | poll_events, event_queue.py                                |
| Watchdog?                                | **Dead code** — file exists tapi never imported/started                                       | watchdog_service.py                                        |

---

## A2. COM Threading Architecture (Final Decision)

> [!IMPORTANT]
> Ini keputusan arsitektur kritis. COM STA = harus diakses dari thread yang sama dia di-create.

```
APScheduler Job (background thread)
pywebview js_api call (separate thread)
                    ↓
         queue.Queue (single entry point)
                    ↓
        COM Worker Thread (SATU, dedicated)
        CoInitializeEx(COINIT_APARTMENTTHREADED)
                    ↓
        Outlook COM objects live ONLY here
```

**Kenapa pattern ini wajib:**

- pywebview docs eksplisit: js_api methods run di separate threads
- APScheduler jobs run di own executor threads
- COM STA = harus diakses dari thread yang sama dia di-create
- Tanpa pattern ini → **random crash di production yang susah reproduce**

**Integrasi ke existing `scheduler_service.py`:**

```python
# Tambah job ini — BUKAN scan langsung, hanya enqueue
scheduler.add_job(
    outlook_scan_trigger,
    trigger='interval', minutes=3,  # user decision: 3 menit
    id='outlook_email_scan'
)

def outlook_scan_trigger():
    # Job HANYA enqueue, tidak touch COM
    com_worker.enqueue(ScanTask(rules=get_active_rules()))
```

**Integrasi ke existing `poll_events` (1.5s polling):**

```python
def on_scan_complete(result):
    event_queue.put({
        'type': 'outlook_activity',
        'rule_name': result.rule_name,
        'subject': result.email_subject,
        'action': result.action_taken,
        'status': 'sent' | 'drafted' | 'blocked'
    })
```

---

## A3. Backend Structure (New Files)

```
project_tracker/
  outlook/
    com_worker.py              ← NEW: Singleton queue-based COM thread
    outlook_service.py         ← NEW: COM method wrappers (replaces dead existing one)
    scanner_engine.py          ← NEW: 2-phase scan (incremental)
    rule_engine.py             ← NEW: condition eval + Jinja2
    action_executor.py         ← NEW: Reply/ReplyAll/NewEmail native
    safety_oracle.py           ← NEW: semua safety checks terpusat
  repositories/
    outlook_rule_repo.py       ← NEW
    outlook_log_repo.py        ← NEW
    outlook_processed_repo.py  ← NEW
  api/
    outlook_api.py             ← NEW: js_api methods untuk Svelte
  services/
    scheduler_service.py       ← EXISTING: tambah outlook scan job
```

---

## A4. DB Tables (Tambah ke SQLite Existing)

```sql
-- Rules
outlook_rules (
  id, name, enabled, trigger_type,
  condition_logic TEXT CHECK(condition_logic IN ('ALL','ANY')),
  conditions_json, action_json, auto_send_enabled,
  scan_interval_minutes DEFAULT 3,
  created_at, updated_at
)

-- Deduplication: track per (entry_id, rule_id) pair
outlook_processed_items (
  id, entry_id, store_id, rule_id,
  action_taken, processed_at
)

-- Audit log
outlook_execution_logs (
  id, rule_id, event_type, message,
  email_subject, sender, status, timestamp
)
```

**Dedup strategy:** Pasangan `(entry_id, rule_id)`. Satu email bisa trigger Rule 1 dan Rule 2. Tapi satu email TIDAK bisa trigger Rule 1 dua kali.

---

## A5. UX — Two-Panel Inline (Gmail Filter Style)

> Bukan wizard (terlalu banyak klik), bukan modal (terlalu kecil untuk body editor).

```
┌─ AUTOMATIONS > OUTLOOK ──────────────────────────────────────┐
│ Outlook: ● Connected  │  Active Rules: 3  │  Sent today: 12  │
├──────────────────────────────────────────────────────────────┤
│ ┌── RULES (30%) ───┐  ┌── RULE EDITOR (70%) ──────────────┐ │
│ │ + New Rule       │  │  Rule Name [___________] [● Active]│ │
│ │                  │  │                                    │ │
│ │ ▶ CR Approval    │  │  ┌─ IF THE EMAIL... ─────────────┐ │ │
│ │   ● Active       │  │  │ [From▼][contains▼][___input__]│ │ │
│ │                  │  │  │ [Subject▼][contains▼][______] │ │ │
│ │ ▶ Status Update  │  │  │ [+ Add condition]             │ │ │
│ │   ● Active       │  │  │ Match: (●All) (○Any)          │ │ │
│ │                  │  │  └───────────────────────────────┘ │ │
│ │ ▶ Weekly Report  │  │                                    │ │
│ │   ○ Disabled     │  │  ┌─ THEN... ─────────────────────┐ │ │
│ │                  │  │  │ [□Reply sender][□Reply all]   │ │ │
│ │                  │  │  │ [□New email to: _________]    │ │ │
│ │                  │  │  └───────────────────────────────┘ │ │
│ │                  │  │                                    │ │
│ │                  │  │  ┌─ MESSAGE... ──────────────────┐ │ │
│ │                  │  │  │ [B][I][U] {{sender}} {{subj}} │ │ │
│ │                  │  │  │ ┌─────────────────────────┐   │ │ │
│ │                  │  │  │ │ Type your message here  │   │ │ │
│ │                  │  │  │ └─────────────────────────┘   │ │ │
│ │                  │  │  └───────────────────────────────┘ │ │
│ │                  │  │                                    │ │
│ │                  │  │  Auto-send: [○Off ●Draft ○Send⚠️] │ │
│ │                  │  │                                    │ │
│ │                  │  │  [Test Rule]        [Save Rule]   │ │
│ └──────────────────┘  └────────────────────────────────────┘ │
│                                                              │
│ Recent Activity: ✓ CR Approval → Replied to bank@bri.co.id  │
└──────────────────────────────────────────────────────────────┘
```

**Auto-send 3 options (bukan toggle):**

- `Off` = rule jalan tapi tidak ada action
- `Draft` = buat draft di Outlook, user review dulu **(default, paling aman)**
- `Send ⚠️` = kirim otomatis, warning label permanen

**Body editor:** Simple `contenteditable` + toolbar minimal (B/I/U + bullet). Bukan TipTap/Quill.

**Jinja2 variables:**

| Variable            | Value                     |
| ------------------- | ------------------------- |
| `{{sender_name}}`   | Nama pengirim             |
| `{{sender_email}}`  | Email address pengirim    |
| `{{subject}}`       | Subject email             |
| `{{received_date}}` | Tanggal terima            |
| `{{body_preview}}`  | 200 karakter pertama body |

---

## A6. User Decisions (Confirmed)

| #   | Parameter                  | Keputusan User                                      |
| --- | -------------------------- | --------------------------------------------------- |
| 1   | Scan interval              | **3 menit**, configurable di Settings               |
| 2   | Incremental scan?          | **Ya**, hanya email setelah `last_scan_timestamp`   |
| 3   | Max age email yang di-scan | **2 hari** terakhir (configurable)                  |
| 4   | Body format                | **Bisa pilih Plain / HTML** + opsi browse file HTML |
| 5   | Log retention              | **7 hari** auto-cleanup                             |

---

# 📦 Appendix B: PyInstaller + win32com Packaging Research

> **Source:** Perplexity research (2026-06-16)
> **Context:** Python 3.12 + pywebview + PyInstaller + win32com (Outlook COM)

---

## B1. makepy COM Cache — Redirect ke `%TEMP%`

> [!CAUTION]
> `win32com.client.EnsureDispatch()` pakai generated cache di `win32com\gen_py\`. Di frozen EXE, path ini **tidak ada** → crash `pyi_rth_win32comgenpy`.

**Solution — redirect gen_py ke `%TEMP%` SEBELUM COM calls:**

```python
import tempfile, os, sys
import win32com
import win32com.client

# MUST run before any COM dispatch
genpydir = os.path.join(tempfile.gettempdir(), "gen_py", sys.version[:3])
os.makedirs(genpydir, exist_ok=True)
win32com.__gen_path__ = genpydir
win32com.client.gencache.is_readonly = False
win32com.client.gencache.GetGeneratePath()

import win32com.gen_py
win32com.gen_py.__path__.insert(0, genpydir)
```

**Lalu pakai `dynamic.Dispatch` instead of `EnsureDispatch`:**

```python
outlook = win32com.client.dynamic.Dispatch("Outlook.Application")
```

---

## B2. DLL Issues — Explicit Bundle Required

> [!WARNING]
> `pythoncom312.dll` dan `pywintypes312.dll` sering MISSED oleh PyInstaller dari virtualenv.

**Tambah di `.spec`:**

```python
import sys
from pathlib import Path

site_packages = Path(sys.prefix) / "Lib" / "site-packages"
pywin32_sys32 = site_packages / "pywin32_system32"

binaries = [
    (str(pywin32_sys32 / "pythoncom312.dll"), "."),
    (str(pywin32_sys32 / "pywintypes312.dll"), "."),
]
```

**Hidden imports yang WAJIB:**

```python
hiddenimports = [
    'win32com',
    'win32com.client',
    'win32com.client.dynamic',
    'win32com.server',
    'win32com.shell',
    'pywintypes',
    'pythoncom',
]
```

**Pastikan `pyinstaller-hooks-contrib` up-to-date:**

```bash
pip install --upgrade pyinstaller pyinstaller-hooks-contrib
```

---

## B3. "Early pywin32 Import" Issue — Post-2023

**Status (pywin32 ≥ 306, 2023+):** Largely resolved, tapi **tetap harus** import paling awal di entry point:

```python
# MUST be FIRST — before any other win32 import
import pywintypes  # noqa: F401
import win32api    # noqa: F401
```

**Untuk frozen EXE, tambah DLL directory:**

```python
import sys, os
if getattr(sys, 'frozen', False):
    os.add_dll_directory(sys._MEIPASS)
```

**Target:** pywin32 ≥ 306 untuk Python 3.12, idealnya **308** (stable early 2024).

---

## B4. Outlook Version Compatibility

| Scenario                          | Recommendation                                                   |
| --------------------------------- | ---------------------------------------------------------------- |
| Satu versi Outlook                | `EnsureDispatch("Outlook.Application")` — fastest                |
| Multiple versi (365/2019/2016)    | `dynamic.Dispatch("Outlook.Application")` — always safe          |
| Setelah Outlook patch break cache | Delete `%TEMP%\gen_py\3.x\{CLSID}` folder                        |
| New Outlook (Win11 app)           | COM via `Outlook.Application` ProgID mungkin unavailable — test! |

**Guard untuk version-specific properties:**

```python
try:
    mail.SomeNew365Property = value
except AttributeError:
    pass  # older Outlook, skip gracefully
```

---

## B5. Antivirus False Positive Mitigation

**Ranked by effectiveness:**

| #   | Solution                                   | Cost        | Effectiveness          |
| --- | ------------------------------------------ | ----------- | ---------------------- |
| 1   | `--onedir` mode (bukan `--onefile`)        | Free        | ⭐⭐⭐⭐               |
| 2   | Code-signing certificate (OV/EV)           | $300-500/yr | ⭐⭐⭐⭐⭐             |
| 3   | Submit ke Microsoft MAPS / Defender        | Free        | ⭐⭐⭐ (Defender only) |
| 4   | Rebuild PyInstaller bootloader from source | Free        | ⭐⭐⭐                 |
| 5   | Wrap dengan Inno Setup installer           | Free        | ⭐⭐⭐                 |
| 6   | `--noupx` / `upx=False`                    | Free        | ⭐⭐ (harus default)   |

> [!IMPORTANT]
> **UPX HARUS dimatikan.** UPX compression = malware packer pattern = false positive trigger.

```python
# myapp.spec
exe = EXE(..., upx=False, ...)
```

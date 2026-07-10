# Session Notes

> Brief recovery ledger. Do not paste transcripts or secrets.
>
> - **DECISIONS.md** → permanent ADRs (why)
> - **PROGRESS.md** → tracking (what's done, what's next)
> - **session-notes.md** → what's active NOW

---

## 2026-07-10 (Native window resize + Aero Snap — branch `general/window-responsive-fixes`)

**Now:** frameless window now gets real edge/corner resizing AND Windows Aero Snap via the native OS modal loop (`WM_NCLBUTTONDOWN` + hit-test codes). Replaces the inert cursor-only resize-edges a prior session on this branch deleted (see block below) — these are functional, not decorative.

- `web/js_api.py`: new `_win_hit_drag(hit)` helper — resolves the WinForms Form (`BrowserView.instances[win.uid]`), then on the UI thread (`form.BeginInvoke(Action(...))`) does `ReleaseCapture()` + `SendMessageW(hwnd, WM_NCLBUTTONDOWN, hit, 0)`. Windows-only, call-time guarded (try/except → `ok()` no-op elsewhere). Public bridge methods `win_start_drag()` (HTCAPTION=2, gives Aero Snap) + `win_start_resize(direction)` (8 dirs → HTLEFT..HTBOTTOMRIGHT 10–17).
- `frontend/src/lib/bridge.ts`: `winStartDrag()`, `winStartResize(direction)` wrappers.
- `TitleBar.svelte`: `.titlebar` `-webkit-app-region: drag` **removed**; drag now JS `onmousedown={handleTitlebarMouseDown}` → `winStartDrag()` (skips interactive chrome via `closest(...)`). This is what enables Aero Snap — CSS app-region drag = manual move, no snap. `ondblclick` maximize kept (native never receives DBLCLK since we only send NCLBUTTONDOWN on each mousedown).
- `App.svelte`: 8 `.resize-edge` divs (edges + corners) `onmousedown={(e)=>startResize(dir,e)}`; `styles.css` positions them `position:fixed z-index:1100` (above titlebar 1000) with per-edge cursors. Min size enforced by OS (pywebview `min_size=(960,640)`), no JS clamp needed.

**Why native loop, not JS coordinate-forwarding:** only the OS move/resize loop produces the snap-layout preview shadow + quarter/half tiling. Pointer-delta → resize API = laggy and gives no snap. Ladder rung 4 (native platform feature).

**Verify:** svelte-check 0 errors (13 warnings — 9 new = cosmetic a11y on resize divs / titlebar mousedown, same accepted class); `npm run build` clean; `web.js_api` + `app_web` import clean headless; `win_start_drag`/`win_start_resize`/`_win_hit_drag` present on JsApi. **Native window behavior NOT verifiable headless (GUI + interactive Windows session required)** — user must test live.

**Manual checklist (user, live app after build+restart):**
- [ ] Drag empty titlebar area → window moves; drag to top edge = maximize snap preview; drag to left/right screen edge = half-screen snap; corner = quarter snap (snap shadow visible).
- [ ] Drag over nav icons / search / buttons does NOT move the window.
- [ ] Double-click empty titlebar → maximize/restore still works.
- [ ] Drag each of the 4 edges → window resizes that side; cursor shows correct arrow on hover.
- [ ] Drag each of 4 corners → diagonal resize.
- [ ] Resize cannot shrink below 960×640 (OS min-size).
- [ ] Minimize / maximize / close buttons unaffected.

**Round 2 (after live test: resize+min_size PASSED; snap/guard/dblclick FAILED):**
- **#2+#3 shared root cause:** `winStartDrag()` fired on every titlebar mousedown → native NC move loop started instantly + captured input until mouseup, swallowing the dblclick sequence and every caption button click. **Fix (TitleBar.svelte):** threshold-armed drag — mousedown only records start pos; `winStartDrag()` fires from mousemove after >4px; bare click/dblclick never enters the OS loop. Added `onmousemove`/`onmouseup` on `.titlebar`; broadened guard to include `.titlebar-right`.
- **#3 also:** `winState` stale (relied on maybe-not-firing `pywin-state` events). **Fix (js_api.py `win_toggle_maximize`):** now reads real `form.WindowState` (WinForms), flips on UI thread via `BeginInvoke`, returns `{state}`; `bridge.ts` typed to `{state}`; TitleBar `toggleMaximize()` sets `winState` from the return. Backend = source of truth, no event dependency.
- **#1 snap:** NC move loop already runs (resize proves it); frameless window just isn't Aero-arrangeable. **Fix (js_api.py `_enable_native_snap`, called on `w.events.shown`):** re-add `WS_MAXIMIZEBOX|WS_THICKFRAME` on the raw HWND + `SWP_FRAMECHANGED`. **UNCERTAIN — needs live test:** if a thin sizing border appears or half/quarter snap stays partial, next round adds a `WM_NCCALCSIZE` subclass (with maximized inset) — deferred (bad WndProc crashes msg loop, can't test headless).

Verify R2: svelte-check 0 errors (13 warnings, cosmetic); build clean; `web.js_api`+`app_web` import clean; `_enable_native_snap` + `win_toggle_maximize` present. Live behavior still unverifiable headless.

**Next:** user live re-test (esp. #1 snap border/tiling) → if snap partial, WM_NCCALCSIZE round. Uncommitted.

**Round 3 (Chrome-like frameless finish — border removal + Win11 buttons):**
- **#1 border (root fix, was deferred in R2):** `WS_THICKFRAME` reserves a non-client frame Windows draws as the top border. **Fix (js_api.py):** new `_build_nc_frame_hook()` returns a WinForms `NativeWindow` subclass whose `WndProc` handles `WM_NCCALCSIZE` — leaves `rgrc[0]` (window rect) as the client rect (borderless), sets `m.Result=0`, returns without base; when `IsZoomed`, insets by `SM_CXFRAME+SM_CXPADDEDBORDER` / `SM_CYFRAME+SM_CXPADDEDBORDER` so a maximized/snapped window keeps the taskbar. `_enable_native_snap` attaches it via `AssignHandle` (BEFORE `SWP_FRAMECHANGED`), stored in module-global `_nc_frame_hook` so it's never GC'd. Chose `NativeWindow` over raw `GWL_WNDPROC` swap — WinForms calls base.WndProc + owns callback lifetime = much lower crash risk. Fallback: skip `AssignHandle` → border returns, app stable.
- **#2 buttons:** `TitleBar.svelte` window controls now Win11-style — thin SVG icons (min = `M0 5 H10`, max = 9×9 rect, restore = offset squares, close = X), `stroke-width:1 shape-rendering:crispEdges`. CSS: 46px wide, full 48px bar height, no radius, gap 0, `margin:0 -8px 0 4px` on `.win-controls` to sit flush in the corner; hover min/max `rgba(255,255,255,.06)` / active `.09`, close hover `#c42b1c`.
- **#3/#4/#5 (drag/dblclick/guard):** unchanged — R2 code already correct; verify live.

Verify R3: svelte-check 0 errors (13 cosmetic warnings); `npm run build` clean (fresh bundle in web/static — **user must restart app before testing**); `web.js_api` import clean headless, `_build_nc_frame_hook` present. WndProc/native behavior unverifiable headless.

**Next R3:** user live-test — border gone? buttons Win11? snap/dblclick/guard OK? maximized keeps taskbar? If maximized inset off a few px, tune `SM_*` sum live. Uncommitted.

**Round 4 (live test R3: border STILL present + drag DEAD):**
- **#2 drag regression root cause:** R2's threshold-armed drag fired `winStartDrag()` on *mousemove after 4px* — async bridge round-trip arrives too late, OS never grabs the move loop (resize works because resize-edge divs fire on *mousedown*, immediate). **Fix:** restored pywebview's `-webkit-app-region: drag` on `.titlebar` (compositor-level, reliable, no async race); removed JS threshold handlers (`handleTitlebarMouseDown/Move/Up`, `dragArmed`, `winStartDrag` import). Kept `ondblclick` maximize + child `no-drag`. **Trade-off:** pywebview app-region drag repositions the window itself → **NO Aero Snap** with this method. Drag reliability chosen over snap; snap = follow-up needing WebView2 non-client-region support (`IsNonClientRegionSupportEnabled`, not exposed by pywebview 6.2.1 out of the box). `win_start_drag`/`_win_hit_drag` backend kept (unused by drag now; resize still uses `_win_hit_drag`).
- **#1 border root cause:** pythonnet `NativeWindow` WM_NCCALCSIZE override silently didn't intercept (border stayed = WS_THICKFRAME frame still drawn). **Fix:** replaced with deterministic **ctypes `GWLP_WNDPROC` subclass** (`_install_frameless_wndproc`) — chains to original proc via `CallWindowProcW`, returns `0` for `WM_NCCALCSIZE` (client == whole window → no frame), insets when `IsZoomed`. WNDPROC callback + original proc held in module-globals (`_frameless_wndproc_ref/_orig`) so never GC'd. 64-bit-safe (`SetWindowLongPtrW`, `LRESULT=c_longlong`). Best-effort try/except → border stays if it fails, app stable.

Verify R4: svelte-check 0 errors (12 cosmetic warnings); build clean (fresh bundle — **restart before test**); `web.js_api` import clean, `_install_frameless_wndproc` present. WndProc + app-region drag unverifiable headless.

**Next R4:** user live-test — (1) border gone now? (2) drag works (window follows)? (3) dblclick maximize? Note: Aero Snap intentionally OFF this round. If border still present, the ctypes subclass isn't taking → need live logging. Uncommitted.

**Round 5 (live test R4: border/resize/buttons/guard passed; drag + dblclick still failed):**
- **Root cause:** WebView2 in pywebview 6.2.1 does not honor `.titlebar { -webkit-app-region: drag; }`, so web content keeps the pointer and the window never moves. R2 also proved that calling the async bridge after a mousemove threshold is too late for Windows to enter its native move loop; the working resize path calls the same `WM_NCLBUTTONDOWN` forwarding on mousedown.
- **Fix (`TitleBar.svelte` only):** restored the existing `winStartDrag` bridge import and added one empty-titlebar `onmousedown` handler. Non-left clicks and interactive descendants are ignored. A second click (`event.detail >= 2`) toggles maximize before any native move loop starts; a first click immediately calls `winStartDrag()` for native movement + Aero Snap. Removed standalone `ondblclick` and the ineffective `.titlebar` app-region drag rule; child no-drag rules remain.
- **Regression contract:** `frontend/tests/components.test.mjs` now locks the mousedown/native-drag, second-click maximize, no-`ondblclick`, and no-titlebar-app-region behavior. Test was observed RED before the fix, then GREEN: 26 passed / 0 failed.
- **Verify R5:** `npm --prefix D:/Ibrahim/Projects/project_tracker/frontend run check` = 0 errors / 13 warnings (known a11y class); build = clean, 256 modules transformed (Project Tracker process confirmed closed first). Native drag/double-click remains unverified because it needs the interactive Windows GUI. Fresh `web/static` bundle requires app restart before testing.
- **Files this round:** `frontend/src/lib/components/TitleBar.svelte`, `frontend/tests/components.test.mjs`, `_docs/session-notes.md`. Backend, `App.svelte`, and `bridge.ts` were not changed in Round 5.
- **Next R5:** user restart + live-test drag/Aero Snap, double-click maximize/restore, interaction guard, resize/min-size, border/taskbar regressions. If drag still fails, discuss enabling WebView2 `IsNonClientRegionSupportEnabled`; do not attempt it blind. Work remains uncommitted.

**Round 6 (live test R5: drag + double-click failed; controls/resize/frame passed):**
- **Observed:** empty-titlebar drag did nothing and double-click did not toggle maximize/restore. Nav/search/buttons stayed isolated, native edge/corner resize + 960×640 minimum worked, border stayed absent, and maximized taskbar behavior passed.
- **Root cause:** R5's interaction guard rejected `nav`, `.titlebar-nav`, and `.titlebar-right`. The centered `.titlebar-nav` is `flex: 1`, so it owns nearly all visually empty titlebar space. Those clicks returned from `handleTitlebarMouseDown` before reaching either `winStartDrag()` or the `event.detail >= 2` maximize branch. This means R5 never actually exercised the native drag bridge; WebView2 capture was not yet the demonstrated blocker.
- **Fix:** narrowed the guard to real controls and overlay content only: buttons, form controls, links/`role=button`, `.search-box`, `.notif-popover`, and `.help-popover`. Empty space inside the flex nav and right chrome now behaves like a normal Windows caption; actual nav/search/window controls remain non-draggable. No backend, bridge, resize-zone, or frame-hook change.
- **Windows-standard resize:** intentionally retained the passing path. Edge/corner zones only initiate `WM_NCLBUTTONDOWN` with Windows HT resize codes; Windows owns movement, cursor loop, min-size enforcement, and final geometry rather than custom JavaScript resizing.
- **Regression:** strengthened `frontend/tests/components.test.mjs` so flex containers cannot re-enter the drag guard while search/popovers remain protected. Observed RED on the old selector, then GREEN: 26 passed / 0 failed.
- **Verify R6:** `svelte-check` = 0 errors / 13 known warnings; production build = clean, 256 modules transformed after confirming the app was closed. Fresh `web/static` requires restart. Native behavior still awaits user live-test.
- **Next R6:** restart app; test empty nav whitespace + left/right chrome whitespace for drag/Aero Snap and double-click restore/maximize, then recheck controls and resize. If movement still fails after this selector fix, add one-shot bridge instrumentation before considering WebView2 non-client-region support. Work remains uncommitted.

**Round 7 (live test R6 passed; maximize/taskbar, maximized-resize state, horizontal scroll follow-up):**
- **Observed:** drag, Aero Snap, double-click, controls guard, normal resize, border removal, and minimum size all passed. New failures: maximized window covered the non-autohide taskbar; custom top resize remained active while maximized and corrupted the remembered restore/maximize geometry; Dashboard's narrow-window data grid exposed only vertical scrolling.
- **Taskbar root cause + fix (`web/js_api.py`):** `WM_NCCALCSIZE` removed the frame and manually inset only the client rectangle, but the top-level maximized window still used monitor bounds and could cover the taskbar. The frameless WndProc now handles `WM_GETMINMAXINFO`: it first chains to WinForms (preserving `min_size`), then sets `ptMaxPosition`/`ptMaxSize` from the active monitor's `rcWork` rather than `rcMonitor`. This supports taskbars on any edge and offset secondary monitors. `WM_NCCALCSIZE` now only removes the frame; no double inset.
- **Maximized-resize root cause + fix:** eight transparent resize zones were always mounted, including while maximized, and `_win_hit_drag` accepted resize HT codes in that state. `TitleBar.svelte` now reports its backend-sourced state to `App.svelte`; App removes resize zones while maximized. Backend also rejects resize HT codes when the real WinForms state is Maximized, while HTCAPTION drag remains allowed for standard drag-down restore.
- **Horizontal-scroll root cause + fix (`styles.css`):** at 960 px, `.project-table` had `clientWidth=928` and internal `scrollWidth=1166`, but `width:100%; overflow:hidden` trapped that overflow so `.table-scroll` incorrectly remained `scrollWidth=928`. The table now uses `width:max-content; min-width:100%; overflow:visible`; browser verification shows `.table-scroll clientWidth=928 / scrollWidth=1166`, so its existing horizontal scrollbar owns the wide grid. No global/body scrollbar added.
- **Regression:** backend work-area geometry + WndProc/resize guard contracts were RED, then `14 passed`; frontend resize-state + Dashboard overflow contracts were RED, then `41 passed`. `svelte-check` = 0 errors / 13 known warnings. Production build = clean, 256 modules transformed after confirming the app was closed.
- **Files this round:** `web/js_api.py`, `frontend/src/App.svelte`, `frontend/src/lib/components/TitleBar.svelte`, `frontend/src/styles.css`, `tests/test_phase_c_js_api_contract.py`, `frontend/tests/components.test.mjs`, `frontend/tests/dashboard-inline-edit.test.mjs`, `_docs/session-notes.md`.
- **Next R7:** restart and live-test maximized taskbar/work area, no resize cursor/action while maximized, drag-down restore, repeated maximize/restore geometry, and Dashboard horizontal scrollbar at minimum width. Work remains uncommitted.

**Round 8 (R7 live test passed; merge approved):**
- User confirmed every final shell check passes: taskbar remains visible when maximized; resize cursor/action is absent while maximized; drag-down restore and repeated double-click/button maximize↔restore preserve the correct normal rectangle; Dashboard exposes horizontal scrolling at minimum width. Earlier passing behavior remains intact: empty-chrome drag + Aero Snap, interactive guards, native edge/corner resize, 960×640 minimum, hidden top frame, and Win11 caption controls.
- Final architecture is locked in D-0015: Svelte emits guarded caption/resize intent, `web/js_api.py` owns WinForms/Win32 interop, and Windows owns move/resize/Snap/restore geometry. `-webkit-app-region: drag` and JavaScript coordinate resizing are explicitly not the supported path.
- Related references synced: PRD responsive + TitleBar rules, D-0005/D-0015, TECH_STACK desktop shell, ARCHITECTURE desktop-window boundary, DESIGN_RULES minimum/responsive/table behavior, PROGRESS tracking, and this ledger.
- **Final gate 2026-07-11:** targeted backend window contracts 14 passed; full frontend suite 188 passed; svelte-check 0 errors / 13 known a11y warnings; `web/js_api.py` compiles; production build clean (256 modules) after confirming the app was closed; `git diff --check` clean before staging.
- **Merge R8:** feature commit `bf2014e1`; merged to `main` as `18859d1b` on 2026-07-11. Branch kept per user rule. Post-merge sequence: record this tracking update, verify merged tree, push `main`, then restore unrelated local memory/Headroom/automation-doc changes per path.

**active_menu:** general (window infra, cross-menu)

---

## 2026-07-10 (Window management + responsive fixes — branch `general/window-responsive-fixes`)

**Status:** initial implementation snapshot; superseded by Native window Rounds 1–8 above. Final behavior passed user live verification and is approved for merge.

**Initial implementation:** 5 requested fixes implemented + 1 extra found during audit on `general/window-responsive-fixes` (branched from `main`):
- `web/js_api.py` `win_toggle_maximize`: now takes `current_state: str` param (frontend's already-accurate `winState`, synced via existing `register_win_events`/`pywin-state` event) as source of truth instead of stale `w.maximized` on pywebview 6.2.1.
- `frontend/src/lib/bridge.ts` `winToggleMaximize(currentState: string)` forwards it.
- `TitleBar.svelte`: new `handleTitlebarDoubleClick` guards `target.closest("button, input, select, textarea, nav, a, [role='button']")` before toggling, bound via `ondblclick` on `.titlebar` root (task claimed a duplicate binding at two line numbers — actual code only had one).
- Dead breakpoints bumped above `min_size=(960,640)` (app_web.py) to 1024px: `TitleBar.svelte` (was 900px), `ProjectDetails.svelte` (was 700px), plus `CICDBrowser.svelte` (was 959px — found via grep audit, not in original task).
- `styles.css` `.project-table` + `Dashboard.svelte` `.dashboard-project-table`: removed fixed `min-width` (1540px/1450px), grid columns converted to `minmax(floor, fr)` fluid tracks, containers `width:100%`.
- `App.svelte` + `styles.css`: deleted all 8 fake `.resize-edge*` divs/CSS (cursor-only, no real hit-test resize logic).

**Task claim discrepancies (verified against source, not assumed):** the "820px email dialog" dead breakpoint named in the task does not exist anywhere in `frontend/src` (grepped, zero matches) — skipped as fictional.

**Verify:** svelte-check 0 errors (4 pre-existing unrelated a11y warnings); `npm run build` succeeded clean. Runtime app launch NOT verified — Bash-tool background launch runs in a non-interactive Windows session ("Services", not "Console"), so WebView2 fails with `Invalid window handle` (0x80070578). This is an environment/session-isolation limitation, not a code defect from these changes. User must run `D:/Ibrahim/Projects/project_tracker/.venv/Scripts/python.exe -m main` from their own interactive terminal to manually verify maximize/restore, titlebar dblclick guard, breakpoint reflow near 960–1024px, table fluidity 960–1449px, and that resize-edge removal doesn't break existing drag-resize behavior.

**Outcome:** later native-window rounds restored real edge/corner resizing, drag/Aero Snap, taskbar-safe maximization, stable restore geometry, and owned horizontal table scrolling. See Rounds 1–8 above; merge approved.

**active_menu:** general (window/responsive infra, cross-menu)

---

## 2026-07-09 (Piece D — CICD Bitbucket integration — branch `general/cicd-bitbucket`)

**Now:** Piece D implemented + verified on `general/cicd-bitbucket` (branched from `main`; the Automation epic Slices 1–5 were merged to main as `5257da05` before this branch, so main already had Logs as the 8th nav). 4 tasks, 4 commits:
- **Task 1** `b4cbc84f`: `services/cicd_service.py` — stdlib-only (`subprocess`/`shutil`, no new dep). Pure helpers `check_git`, `parse_repo_name` (strips `.git`), `parse_porcelain` (XY→modified/untracked/staged, rename→new path), `build_file_tree` (recursive, `.git` skipped, dirs-first). `CicdService`: `start_clone` spawns a **daemon thread** (`git clone -b cicd --single-branch`, `creationflags=CREATE_NO_WINDOW` — first subprocess in app) writing a poll-able job dict; `clone_status`, `list_repos` (per-repo status summary), `list_files`. `tests/test_cicd_service.py` (consolidated — one file per user decision): 14 tests (parse/tree/detection/clone-lifecycle via monkeypatched subprocess + bridge envelope via FakeCicdService).
- **Task 2** `8faffd9d`: `web/js_api.py` — `CicdServiceProtocol` + `cicd_service` ctor kwarg + 5 methods `cicd_git_status`/`cicd_clone`/`cicd_clone_status`/`cicd_list_repos`/`cicd_list_files` (standard `try/None-guard→SERVICE_UNAVAILABLE/ok/except→CICD_*_FAILED` envelope). `app_web.py` — nested `_CicdServiceAdapter` reuses `_AppCodeServiceAdapter.get_appcode_config` to resolve the CICD dir (`per_appcode`→`{appcode}/CICD`, `shared_root`→`cicd_shared_path`); wired via hoisted `_appcode_adapter` + `_cicd_adapter=_CicdServiceAdapter(_appcode_adapter, CicdService())`.
- **Task 3** `5a262b4a`: `frontend/src/lib/components/CICDBrowser.svelte` (new full page, raw `callBridge` like Logs, inline types, recursive `{#snippet fileTree}` with `<details>` expand/collapse, poll `cicd_clone_status` every 1.2s, orange/green status dots, git-not-installed + no-repos empty states, per-appcode/shared-root config row via `appcode_update_config`, file click reuses `file_open`). TitleBar `navItems`+`navIcons` add 9th "CICD" (git-branch icon between Logs and Settings). App.svelte `PageId`/`validPages`/import/render branch. `components.test.mjs` +2 source-contract tests.
- **Task 4** (this): full verify gate + docs (D-0014, PRD §17A, PROGRESS Piece D block + checklist).

**Decisions (DEFAULT AMAN / smallest-diff, all in D-0014):** stdlib subprocess no dep; background daemon-thread clone + poll (no UI freeze); reuse `get_appcode_config` + `file_open`; config UI on CICD page not Settings (per-appcode config); one test file not three; strip `.git` + `--single-branch`; dir nodes no aggregate badge. Create Drone Ticket (Jenkins) stays out of scope.

**Verify:** svelte-check 0 errors/4 pre-existing warnings, 156 files; frontend 184 pass (+2 CICD); `test_cicd_service.py` 14 pass; full pytest 1878 passed + 6 known baseline (test_phase_c_js_api_project x3, test_phase_d_app_web_project_service_adapter x1, test_year_create x2), NO new fails; build ✓ (app closed 2026-07-09) + app smoke ✓ clean (0-byte stdout/stderr, no traceback).

**Design-first harden pass** (`8c2d4e43`, after user pushed on UI/UX maturity): CICDBrowser rewritten — git-check gate kills the mount install-steps flash (`checking` state); per-region loading (git/repos/tree/clone spinner, reduced-motion safe); clone-URL inline validation (Clone disabled until valid HTTP(S)); shared-root path reuses `util_choose_folder` native picker + guarded save (shared_root persists only after Apply with a non-empty path); `:focus-visible`/`:active` keyboard states on repos/files/dirs; per-file **letter badges M/U/S** instead of color-only dots (a11y — color not sole cue); auto-select the just-cloned repo; responsive stack at ≤900px and ≤560px + ellipsis truncation + `min-width:0`. svelte-check 0 err, frontend 184 pass, build ✓, smoke ✓. Honest caveat: no browser/screenshot tool for pywebview here → visual pixel-check is still the user's live step (repo design-first flow).

**Manual gate:** user runs `npm run build` (app closed) → restart → Piece D checklist in PROGRESS.md → merge to main waits approval. Branch NOT deleted.

**active_menu:** cicd

---

## 2026-07-08 (Automation System epic — Slice 5: Logs top-level menu + right-sidebar + retention — final slice)

**Now:** Slice 5 implemented + verified on `automations/approval-polling`. Automation System epic Slices 2–5 are all coded + committed pending user manual check + merge approval.
- `infrastructure/cache_db.py`: new `AutomationLogRow` + `automation_logs` table (module, rule_id, cr_id, timestamp, event_type, detail). New helpers: `append_log`, `list_logs(module/cr_id/rule_id, newest-first)`, `purge_logs_for_cr`, `clear_all_logs`, `clear_rule_logs`. `automation_rule_logs` left untouched for rules-only backward compat. Schema validation table set updated.
- `web/js_api.py` + `_RulesAdapter`: `logs_list`, `logs_clear`, `rules_clear_logs`; adapter exposes `list_logs`, `clear_logs`, `clear_rule_logs` via existing cache-aware rules service. `RulesServiceProtocol` extended.
- Retention: `_ProjectServiceAdapter._run_transition` purges `automation_logs` when CR becomes FINISHED/CANCELED after successful transition (POSTPONED kept because reversible). Swallows retention errors so moves never fail due to log purge.
- Frontend: new `Logs.svelte` global overview page (cards All/Outlook/Teams/CR Automation/Rules Engine; module+CR filters; Refresh/Clear all; table). App.svelte PageId += `logs`, validPages += logs, render chain += `<Logs initialCrId>`. TitleBar navItems += Logs + icon.
- Rules `Logs`: existing panel upgraded to fixed right-sidebar drawer with Refresh/Export(JSON)/Clear/Close. Clear uses new `rules_clear_logs` (clears `automation_rule_logs` for that rule).
- PD Automations header: `[Logs]` button → App pendingLogCrId → Logs page filtered by current CR. Decision: PD uses top-level filtered Logs page instead of sidebar because PD context is project/CR, not rule; smallest correct diff.
- **Verify:** svelte 0/4; frontend 182; targeted pytest 78; full pytest 1864 + 6 baseline (no new); build ✓; smoke ✓.
- **Manual gate:** User restart app (build ran), test combined checklist in PROGRESS.md; merge to main waits approval. Branch not deleted.
- **active_menu:** automations / project-details

---

## 2026-07-08 (Automation System epic — Slice 4: Auto Update CR State engine + Teams followup + auto-reply dedup)

**Now:** Slice 4 implemented + verified on `automations/approval-polling`. Continuing autonomous loop.
- New `services/cr_state_engine.py`: `patterns_configured()`/`match_email()`/`apply_transition()`. Pattern-gated email→CR transition. **DEFAULT AMAN: no patterns = no-op.** All configured patterns (AND) must match (regex, case-insensitive); invalid regex→no-match+warn; legal transition→state+History `AUTO_UPDATE_CR_STATE`; illegal→History `AUTO_UPDATE_CR_STATE_BLOCKED`+skip (never force).
- `core/models.py`: `ProjectMetadata.auto_update_patterns: dict` (from_dict/to_dict wired) — `{"from","subject","body","target_state"}`.
- `services/approval_polling_service.py`: `_on_found` (reply hook) runs engine when metadata available; engine errors swallowed (never break reply handling). Added `logging` + `_log`.
- `services/automation_service.py`: auto-reply dedup (Slice 3 deferred item) — `execute_rule` checks `_recently_fired(rule_id, cr_id)` within 1h window for `goal='auto_reply'` rules → skip+log via `automation_rule_logs` cache; fail-open on cache error. `_dedup_window_seconds=3600`.
- Frontend `ProjectDetails.svelte`: Teams followup wired — `[Draft]`→`teams_preview_message` (followup text from CR+project_name), `[Send]`→ConfirmModal(`pendingTeamsSend`)→`teams_send_message`, `[Setting]`→deep-link rules preset `send_teams`. `teamsFeedback` display.
- Create Drone Ticket: **STAYS stub** (Jenkins API deferred) — no change.
- **Verify:** svelte 0/4; frontend 182; targeted pytest 67 (incl 10 new `test_cr_state_engine.py`); full pytest 1860 + 6 baseline (no new); build ✓; smoke ✓.
- **Next:** Slice 5 (Logs top-level menu + right-sidebar + retention — LAST slice).
- **active_menu:** automations / project-details

---

## 2026-07-08 (Automation System epic — Slice 3: Rules Engine goal-driven + wired handlers + scope + conflict + pre-seeded)

**Now:** Slice 3 implemented + verified on `automations/approval-polling`. Continuing autonomous loop.
- `services/automation_service.py`: ctor += `metadata_store` slot; `rules_conflict_key()` module-level (pure, testable). 5 no-op handlers rewritten with real delegation: `_handle_update_cr_state`/`_handle_update_drone_state` validate via `core/state_machine.validate_cr/drone_transition` (DEFAULT AMAN: illegal→skip+log, never force; missing target_state/project_path/metadata→skip), `_handle_append_history` writes HistoryEntry, `_handle_download_email`/`_handle_save_attachment` stay no-op (Slice 4). Imports: `CRState`/`DroneState` from `core.enums`, `HistoryEntry` from `core.models`, `validate_*` from `core.state_machine`, `InvalidTransitionError` from `core.exceptions`, `Path` top-level.
- `app_web.py`: `_RulesAdapter` += `detect_conflicts()` (trigger+goal+scope WARNING, never block) + `seed_defaults()` (3 DISABLED pre-seeded rules, idempotent). `_PRESEEDED_RULES` constant. Seed called at `run()` start via new `rules_seed_defaults` bridge (NOT in `create_js_api` — keeps test factories seed-free). `_conflict_key` delegates to service-level.
- `web/js_api.py`: `RulesServiceProtocol` += `detect_conflicts` + `seed_defaults`. Bridge += `rules_detect_conflicts` + `rules_seed_defaults`.
- Frontend `RulesActions.svelte`: goal wizard (5 GOALS, goal drives default action set), scope picker (SCOPE_TYPES all/specific/filtered, specific→cr_ids comma-list), conflict badge + pre-seeded "seed" badge in rule cards. Props `presetGoal`+`onPresetGoalConsumed` + `$effect` opens create-form with preset.
- PD deep-links (ProjectDetails.svelte): `openAutomations(kind?, goal?)` → App.svelte `pendingRuleGoal` → `<Automations initialRuleGoal>` → `<RulesActions presetGoal>`. `[+ Add Email Automation]`→send_email; CR `[Setting]`→auto_update_status; `[+ Add Automation Teams]`→send_teams.
- **Incident during impl:** initial seed in `create_js_api` broke `test_rules_engine_unit.py` (asserted empty store) — moved seed to `run()` startup. Initial `from app_web import rules_conflict_key` in test polluted sys.modules with webview → broke 4 `import_does_not_require_pywebview` + 3 project_list tests — moved `rules_conflict_key` to `services/automation_service.py` (no webview dep).
- **DEFERRED to Slice 4**: auto-reply dedup/rate-limit — sender lives in Slice 4 engine; YAGNI now.
- **Verify:** svelte-check 0/4; frontend 182; targeted pytest 57 (incl 12 new `test_phase_c_automation_slice3.py`); full pytest 1850 + 6 baseline (no new); build ✓; smoke ✓.
- **Next:** Slice 4 (Auto Update CR State pattern engine + Teams followup wired + auto-reply dedup).
- **active_menu:** automations / project-details

---

## 2026-07-08 (Automation System epic — Slice 2: PlaceholderResolver + per-CR templates + editor + Test)

**Now:** Slice 2 implemented + verified on `automations/approval-polling`. Continuing autonomous loop (Slices 2→5 per approved mega-plan).
- `services/email_service.py`: new `PlaceholderResolver` class (reflective over `ProjectMetadata`/`DroneTicket`/`AppSettings` via `dataclasses.fields`); `{FIELD}`, `{NESTED.FIELD}`, `{DRONE.0.LINK}` formats; 11 required + 5 optional legacy aliases preserved; `available_tokens()` → `[(token, preview_value)]` for autocomplete; `resolve(text)->(resolved, unresolved[])`; `assert_required_resolved()` keeps Requirement 8.5 contract. Removed `_placeholder_values`/`_assert_placeholders_resolved`/`_substitute` (no external callers). Attachment: `_resolve_attachment_path()` from `category.attachment_template_file` + `settings.email.template_folder_path` (missing → None + warn).
- `services/template_service.py` (new): pure helpers `get_effective_template`/`save_project_template`/`save_default_template`/`reset_project_template`/`list_templates` (no I/O; caller persists).
- `services/approval_polling_service.py`: + `reset_template`, `list_templates`, `test_template` (real Outlook draft + `APPROVAL_TEST_DRAFT_OPENED` history), `autocomplete_tokens`. Protocol `ApprovalServiceProtocol` extended.
- `web/js_api.py`: + `approval_reset_template`/`approval_list_templates`/`approval_test_template`/`approval_autocomplete_tokens`.
- `frontend/src/lib/bridge.ts` + `types.ts`: + `resetApprovalTemplate`/`listApprovalTemplates`/`testApprovalTemplate`/`approvalAutocompleteTokens` + `ApprovalTemplateSummary` type.
- `ApprovalTemplates.svelte`: `{` autocomplete (keyboard nav Arrow/Enter/Tab/Escape, filter-as-you-type, real preview values), **Test** + **Reset to default** buttons; `AutomationsOutlook.svelte` accepts `openTemplateKind` deep-link + `$effect` opens editor.
- Deep-link: PD Outlook `[Setting]`(kind) → `onNavigateAutomations(kind)` → App.svelte `pendingTemplateKind` → `<Automations initialTemplateKind>` → `<AutomationsOutlook openTemplateKind>` → editor popup.
- **Decision (DEFAULT AMAN):** legacy token aliases preserved (no template breakage); attachment missing file → None + warn (no render fail); one project == one CR here so per-project ≈ per-CR (YAGNI — no separate CR dimension).
- **Verify:** svelte-check 0 errors/4 warnings (a11y cosmetic); frontend 182 pass; targeted pytest 45 pass (incl. 10 new `test_placeholder_resolver.py`); full pytest 1838 pass + 6 baseline fails (no new); build ✓; app smoke ✓ clean.
- **Next:** Slice 3 (Rules Engine goal-wizard + wire 5 no-op actions + scope + conflict + pre-seeded + auto-reply dedup).
- **active_menu:** automations / project-details

---

## 2026-07-08 (Automation System epic — Slice 1: PD 3-group section)

**Now:** New epic after user brainstorm (Grok chat) → Outlook + General Automation system, 5 slices, spec `_docs/specs/superpowers/specs/2026-07-08-automation-system-design.md`. Locked: PD-box-first; fold Piece C (backend kept, PD UI replaced); Logs = new top-level menu (Slice 5); `[Send]` confirmed, `[Draft]` not. Slice 1 implemented on `automations/approval-polling`:
- Backend `services/approval_polling_service.py`: `send_request(kind, mode)` — draft opens Outlook draft + `APPROVAL_DRAFT_OPENED`, NO poll job; send delivers then polls when auto-download on; extracted `_match_and_save` + `_one_shot_check`; `force_check(kind)` one-shot inbox scan → `_on_found` on match; `set_auto_update_cr_state`; `get_status` gains `cr_number` + `auto_update_cr_state`.
- `core/models.py`: `ProjectMetadata.auto_update_cr_state: bool` (flag only; email-pattern engine = Slice 4).
- `web/js_api.py`: `send_uat/lv_approval_request(mode)`, `approval_force_check`, `approval_set_auto_update_cr_state` (+ protocol). `bridge.ts` `approvalSend/approvalForceCheck/approvalSetAutoUpdateCrState`; `types.ts` `ApprovalStatus` += `cr_number`,`auto_update_cr_state`.
- `ProjectDetails.svelte`: 3-group markup (Automations Outlook / Automation CR / Automation Teams), status dots 🟢🟡🔴⚪ via `autoDot`/`autoLabel`, ConfirmModal `pendingSend` for `[Send]`, `[Draft]`/`[Force Check]`/`[Stop]`/auto-download toggle, `[Open Setting]`→`onNavigateAutomations`. CR+Teams groups = honest dev-stubs. `App.svelte` wires `onNavigateAutomations`.

**Known limits (accepted):** draft never polls; auto-download-OFF send has no persistent job so PD dot can't show "sent" post-reload (toast covers it); force-check/worker `SaveAs` race is benign (idempotent); `auto_update_cr_state` engine deferred to Slice 4.

**Next:** build (app closed) → user manual checklist Slice 1 → approve → Slice 2 (PlaceholderResolver + Template per-CR + editor popup + Test). No merge to main until user approves.

**Verification:** svelte-check 0/0; frontend 182 pass; targeted pytest 27; full pytest 1828 pass + 6 known baseline fails.

**active_menu:** automations / project-details

---

## 2026-07-06 (Piece C UI rework — Branch 3, after first manual check)

**Now:** User manual check rejected 2 things: (1) new Approval tab (Outlook tab already owns email templates), (2) approval controls squeezed into PD command bar. Rework committed in 3 slices: `ca6be1f1` backend (automation_enabled → `bool|None` inherit `settings.automation_default_enabled`; `approval_auto_download` dict per kind, OFF = send records history but no polling job; `TERMINAL_CR_STATES` FINISHED/POSTPONED/CANCELED force effective off + `automation_locked`; `set_auto_download` + `approval_set_auto_download` bridge), `226c9670` Automations page (Approval tab deleted; SEND AUTOMATION = 2 rows Email Ack (UAT)/Email LV (Prod) opening ApprovalTemplates as kind-preset dialog; SOP rows + EmailTemplateDialog.svelte deleted — `settings.email.categories` data kept, backend outlook_draft/send_email still consumes it; "New-CR automation default" toggle in panel title row), `3dd2c09c` PD (dedicated CR-only "Automations" section bottom-left pane: master toggle + lock hint, always-visible send rows, auto-download toggles, 6 dev-stubs → toast "masih tahap development"; body `inert` + dimmed when off).

**Known quirks:** legacy `automation_enabled: false` reads as explicit OFF (no inherit-reset UI — add if user asks). `ApprovalStatus.automation_enabled` is now the EFFECTIVE value. `OutlookActions.svelte` remains an orphan (pre-existing, untouched). Send not enabled-gated server-side (pre-existing, UI-gated).

**Next:** User closes app → `npm run build` → user manual checklist (delivered in session) → docs commit → merge only after approval.

**Verification:** svelte-check 154 files 0/0; frontend tests 182 pass; targeted pytest 27 pass; full pytest 1825 passed / 20 skipped / 6 known baseline failures (extra 7th failure earlier was TEMP-path-too-long from sandbox tmp dir, not code).

**active_menu:** automations

---

## 2026-07-06 (Piece C implemented — Branch 3)

**Now:** Branch 3 `automations/approval-polling` implemented through automated verification. Scope: `ProjectMetadata.automation_enabled` + `approval_templates`, default approval templates/settings fields, SQLite `approval_polling_jobs`, `ApprovalPollingService` with Outlook send/draft + reply polling + startup resume + shutdown hook, JsApi/bridge wrappers, Project Details approval toggle/UAT/LV controls, Automations Approval Templates editor.

**Next:** User closes Project Tracker app → run frontend build → user manual checklist. No merge until manual pass + explicit merge approval.

**Blocked:** Build intentionally not run yet because RTE safety rule forbids `npm run build` while app may be open. Full pytest still has 6 known baseline failures outside Piece C (`test_phase_c_js_api_project.py` x3, `test_phase_d_app_web_project_service_adapter.py` x1, `test_year_create.py` x2).

**Verification:** `npm --prefix frontend run check` 0/0; frontend node tests 123 pass; targeted pytest 53 pass; full pytest 1821 passed / 20 skipped / 6 known baseline failures; app smoke alive after 15s with empty stdout/stderr.

**active_menu:** automations

---

## 2026-07-06 (Branch 3 plan ready — Piece C)

**Now:** Branch 2 merged to main. Branch 3 `automations/approval-polling` created; detailed executable plan committed at `_docs/specs/superpowers/plans/2026-07-06-piece-c-approval-polling-plan.md` (written to be executed verbatim by ANY model — full code per task, locked design decisions, no room for improvisation). Spec = `_docs/specs/superpowers/specs/2026-07-02-approval-automation-design.md`.

**Next:** Execute the plan task-by-task with superpowers:executing-plans on this branch (Tasks 1–8: models → cache_db → service → bridge → frontend wrappers → PD controls → template editor/settings → verify+docs+gates). Rules binding: no new Python test files; follow plan anchors exactly; STOP if an anchor is missing; build gate + manual gate before commit of the final slice; no merge without user approval.

**Blocked:** None.

**active_menu:** automations

---

## 2026-07-06 (fix round v2 complete — Branch 2)

**Now:** Fix round v2 steps 0–7 all committed after per-step user manual verification. This session: step 5c image drag-resize `4ca0abd` (handle CSS reworked once after "gaudy" feedback: 8px, 1px border, subtle shadow); step 6 SVG toolbar icons `b1cf0dc` (18 buttons, lucide-style inline SVG, 13px stroke-2, currentColor; link 🔗 included); step 7 `37d8ca7` default TNR 18px editor ↔ 13.5pt exporter + fixes from manual feedback: SIZES must be strings (`bind:value` strict equality made the size select blank) and per-file last font/size memory via module-scope `Map<targetFile, {font,size}>` (session-scoped; `initialFileKey = untrack(() => targetFile)` avoids `state_referenced_locally` warning). Docs synced: PRD §12.12, PROGRESS.

**User rule 2026-07-06:** default session skills = using-superpowers + ponytail full + caveman full (recorded in CLAUDE.md/AGENTS.md §"Default Session Skills"; those files stay uncommitted — user-owned edits present).

**Next:** User decides merge Branch 2 → main. After merge: Branch 3 `automations/approval-polling` (Piece C). Optional follow-up if requested: persist per-file font/size to disk (currently session-scoped).

**Blocked:** None new. Known nonblocking pre-commit pytest fail `test_project_list_returns_converted_rows` (pre-existing on main, queued Branch 5).

**Verification:** svelte-check 154 files 0/0; frontend tests 121 pass; phase E pytest 27 pass (TEMP redirect for stale `pytest-current` lock); builds ok; user manual `pass` on steps 5c/6/7.

**active_menu:** project-details

---

## 2026-07-04 (rollback — Branch 2 fix round)

**Issue:** After the first manual check, a 5-part fix round was shipped as one bundle (toolbar `rev` → `$state` active states; idle export 20s→5s + countdown; hidden `.rte` attribute; "?" help popover; Narrow 12.7mm margins + 720px WYSIWYG page width + export clamp + AssetImage resize NodeView + `<img width>` markdown round-trip). User reported **"semua behavior jadi gak normal"** → full rollback to `9882694` code state (commits `e80996d` partial + `a30c512` reverted; user's `.codex/` + `AGENTS.md` kept). Binding lessons recorded in CLAUDE.md + AGENTS.md §"RTE Change Safety".

**Root-cause status:** NOT yet identified — exact symptoms not specified. Suspect ranking to test ONE at a time (each with user verify before the next): (1) AssetImage NodeView (touches every editor incl. notes.md — biggest blast radius); (2) reactive `rev` re-render per transaction; (3) 720px docx page width; (4) environment mismatch — `web/static` rebuilt mid-session while app open / branch switched (web/static is gitignored, does not follow checkout); (5) hidden-attr + countdown (cosmetic, unlikely).

**Update 2026-07-05:** User confirmed app normal again after rollback + rebuild + restart. Symptoms identified: RTE slow-load + titlebar nav frozen (the `app:interaction-lock` held the whole shell while RTE load hung) — consistent with the stale-`web/static`/lock-without-failsafe hypothesis. Fix round v2 is delegated to Codex desktop via the step-by-step prompt at `_docs/specs/superpowers/plans/2026-07-05-codex-fix-round-v2-prompt.md` (steps 0–7, ONE behavior per step, user verify between; step 0 = interaction-lock watchdog; new points: SVG toolbar icons, default TNR 18px↔13.5pt).

**Update 2026-07-05 (Step 1 failed):** Step 0 passed manual verification and was committed as `c94e387`. Step 1 (`rev` changed to `$state(0)` for toolbar active states) failed manual verification: menu navigation became unusable, save/loading became very slow, and file switching became very slow. Step 1 was still uncommitted, was rolled back immediately, and the baseline bundle was rebuilt. Root cause: the editor-mount `$effect` contains synchronous `rev++` calls; once `rev` became `$state`, those read+write operations subscribed the effect to its own state and repeatedly invalidated/recreated the editor. Retry must keep `rev` non-reactive and use a separately throttled toolbar-only state update outside effect tracking.

**Update 2026-07-05 (Step 1 retry ready):** Retry keeps `rev` non-reactive and adds `uiTick` as a toolbar-only state token. Tiptap `transaction` listener is registered from `queueMicrotask()` and throttled by `requestAnimationFrame`, so the editor-mount `$effect` does not subscribe to toolbar refresh state. Automated verification passed: focused Project Details frontend test, `npm --prefix D:/Ibrahim/Projects/project_tracker/frontend run check`, `npm --prefix D:/Ibrahim/Projects/project_tracker/frontend test`, and `npm --prefix D:/Ibrahim/Projects/project_tracker/frontend run build`. Awaiting user manual verification before commit.

**Update 2026-07-05 (Step 1 committed + Step 1.5 in progress):** User manually verified Step 1 retry and it was committed as `65202cf`. Follow-up diagnosis on `D:\Ibrahim\WORK\SSID\2026\CR\UAT_PREPARE\popopopopopopop\_cr-docs\uat-signoff.docx` found a stale-DOCX migration loop: `open_document()` backed up the old source sidecar but left `source.json` in place, so the frontend migration save used `base_revision: 0` while backend still loaded revision 27 and raised `StaleRevisionError`. Step 1.5 minimal fix deletes the stale sidecar after backing it up; regression test added in `tests/test_phase_e_notes_persistence.py`.

**Update 2026-07-05 (Step 1.5 retry):** Manual test still froze after DOCX migration/import: backend log showed `RTE_REVISION_STALE` spam (`Revision 0 is stale (stored 1)`) and frontend log showed hundreds of `rte_document_save` starts. Root cause: `NotesEditor` called `flush("migration")` synchronously inside editor-mount/path `$effect`; `flush()` reads/writes Svelte state (`migrationPending`, `docRevision`, `status`), subscribing the effect and recreating the editor/save loop. Minimal frontend fix now computes local `shouldMigrate` and queues migration flush via `queueMicrotask()` outside effect tracking. Source-contract test added in `frontend/tests/project-details-fase3-fase4.test.mjs`.

**Next:** Finish Step 1.5 retry verification after app closes (`npm run build` must not run while app is open), then user manually verifies `uat-signoff.docx` load/save/file-switch/menu responsiveness. If pass → commit Step 1.5 only. If fail → rollback uncommitted Step 1.5 and rebuild baseline. After all RTE steps pass, merge Branch 2 → Branch 3 `automations/approval-polling` (Piece C).

---

## 2026-07-04 (later — Branch 2)

Branch aktif: `project-details/tiptap-docx-pipeline` (Branch 1 header-redesign merged to main after user verify).

**Now:** DOCX pipeline (D-0012) implemented end-to-end: dot-folder drone guard; `infrastructure/docx_writer.py` (Tiptap JSON→python-docx, full mapping table, atomic replace, DocxTargetLockedError); `services/rte_document_service.py` (source.json store, revision/hash, stale-revision reject, IMPLEMENTED lock, mammoth migration + external-Word-edit stale rule, content-addressed image assets, ExportCoordinator single worker latest-revision-wins); 6 bridge methods `rte_document_open/save, rte_image_save, rte_asset_read, rte_export_request/status` + shutdown flush in app_web; frontend AssetImage extension, paste/drop upload, docx_pipeline editor mode (idle 20s export, 1s poll while exporting, status labels), markdown.ts `.rte/assets` round-trip; ProjectDetails routes docx via pipeline (editable unless IMPLEMENTED).

**Next:** User manual verify pipeline checklist → merge → Branch 3 `automations/approval-polling` (Piece C).

**Blocked:** 6 pre-existing test failures on main (year_create, project_list — fail identically on main; queued for Branch 5). Stray `notes.md` created at repo root by app/pytest run — Branch 5.

**Verification:** svelte-check 154 files 0/0; frontend tests 164 pass; pytest full suite 1809 pass / 6 pre-existing fails (identical on main); app smoke 14s clean; build ok.

**active_menu:** project-details

---

## 2026-07-04 (Branch 1)

Branch aktif: `general/header-redesign` (Branch 1 of master plan; Branch 0 merged to main same day).

**Now:** Header redesign implemented: red `.app-header` deleted (Header.svelte removed), Dashboard controls (Year/Add Year/Add Project/Refresh) moved into Dashboard `.page-header-actions` with portal-style Add-Year popover; live clock (`ddd, dd MMM yyyy HH:mm:ss`) added to TitleBar right cluster; nav icons got aria-labels + red active-indicator bar; avatar debug tooltip removed; red tokens unified (`#DA1E28` fallbacks, `.btn-danger` `#B5382F/#942D26`, `#DC2626` hardcodes → tokens). PRD §10.2–10.4 rewritten (also aligned stale dock text to D-0005 TitleBar). D-0011 recorded. Fixed stale WSL `core.hooksPath` in .git/config; pre-commit gains one svelte-check retry vs transient esbuild OOM; retired graphify post-commit/post-checkout hooks deleted (D-0009).

**Next:** User manual verify header redesign (checklist delivered) → merge to main → Branch 2 `project-details/tiptap-docx-pipeline`.

**Blocked:** Branch 1 merge awaits user manual verification.

**Verification:** svelte-check 152 files 0/0; frontend tests 156 pass / 0 fail; app smoke 14s clean (no stderr); `npm run build` ok (pre-existing chunk-size warning).

**Master plan (earlier today):** `_docs/specs/superpowers/plans/2026-07-04-completion-master-plan.md` approved (7 branches). Locked: per-format RTE strategy (md/txt direct; docx = source.json + python-docx export), free/offline exporter (office network blocks GitHub/PyPI/paid registries), no-mockup design rule.

**active_menu:** general (header shell)

---

## 2026-07-03

Branch aktif: `project-details/rte-interaction-bugs`.

**Now:** Piece B RTE format-aware follow-up implemented in code. Project Details no longer shows `Export to Word` for active RTE files. Backend now returns RTE capability metadata; `.md` saves Markdown, `.txt` saves UTF-8 plain text, `.docx` is read-only until safe source-sync adapter exists, `.msg` is unsupported/open externally. CR doc dropdown flushes active editor via `flushNow()` before file switch. App-level `app:interaction-lock` disables TitleBar/Header during RTE load/flush.

**Next:** User manual verify CR project flow: select `notes.md`/`uat-signoff.docx`/`prod-lv.docx`, confirm DOCX read-only, edit/save `.md`, test titlebar/header lock during load, reopen project.

**Blocked:** Full DOCX editable source-sync engine intentionally deferred.

**Changed files:** `app_web.py`, `web/js_api.py`, `frontend/src/App.svelte`, `frontend/src/lib/activityLogger.ts`, `frontend/src/lib/bridge.ts`, `frontend/src/lib/types.ts`, `frontend/src/lib/markdown.ts`, `frontend/src/lib/components/Header.svelte`, `frontend/src/lib/components/NotesEditor.svelte`, `frontend/src/lib/components/ProjectDetails.svelte`, `frontend/src/lib/components/TitleBar.svelte`, `frontend/tests/components.test.mjs`, `frontend/tests/markdown.test.ts`, `frontend/tests/project-details-fase3-fase4.test.mjs`, `tests/test_phase_e_notes_persistence.py`, `_docs/PROGRESS.md`, `_docs/DECISIONS.md`, `_docs/session-notes.md`.

**Verification:** `npm --prefix D:/Ibrahim/Projects/project_tracker/frontend run test` = 155 pass / 0 fail. `npm --prefix D:/Ibrahim/Projects/project_tracker/frontend run check` = 0 errors / 0 warnings. `D:/Ibrahim/Projects/project_tracker/.venv/Scripts/python.exe -m pytest tests/test_phase_e_notes_persistence.py -v` = 13 pass / 0 fail. `D:/Ibrahim/Projects/project_tracker/.venv/Scripts/python.exe -m pytest tests/test_bridge_contract_guard.py -v` = 3 pass / 0 fail when `TEMP/TMP` point at job tmp to avoid stale Windows pytest-current cleanup lock. `D:/Ibrahim/Projects/project_tracker/.venv/Scripts/python.exe -m main` smoke = no stdout/stderr traceback captured before 12s stop.

**active_menu:** project-details

---

## 2026-07-02

Tooling update: Code graph integration retired by user request. Active docs/settings use native search/read tools for code lookup. Headroom installed in repo venv and setup reference added with proxy URL `http://localhost:8787` and install command `pip install "headroom-ai[proxy]"`. Global `ANTHROPIC_BASE_URL` remains routed to `http://127.0.0.1:20128/v1`; Headroom proxy uses `8787`.

**Now:** Piece A UI/UX implemented on `general/appcode-structure-audit`; manual-check bugs fixed. Dashboard: 3 multi-select checklist dropdowns (CR State / Appcode / Project Type) use fixed-position menu/scrim so header overflow cannot clip list; 2-line project metadata (`Type · Appcode · time · full date`); Non-CR rows render safe (no CR/Drone edit). Add Project form: CR/Non-CR radio, appcode placeholder dropdown + inline `+` create (`appcode_list`/`appcode_add`), start/end datetime only; no CR link / implementation plan; never sends `drone_name`. Project Details: `isSubproject` → `isNonCr`; Non-CR shows state dropdown (`set_non_cr_state`), hides CR/Drone sections, keeps schedule editable. Backend `create_project` persists optional start/end and ignores `drone_name` (lazy drone). `appcode_add` creates current-year `CR/{states}` and `Non-CR`; appcode discovery includes manual folders with year subfolders (e.g. SSID). Drone copy rename (`Sub Project` → `Drone`) across Dashboard/ProjectDetails/DroneTable.

Cross-menu fix sweep (one-time branch scope override approved by user):

- Global Plan: productionized as official menu 7, native HTML5 drag/drop (status + reorder), seeded all 17 audit backlog items.
- Automations: scheduler `project_provider` now real (was `lambda: []`); added `scheduler_entry_trigger` bridge + UI target entry; metrics derived from real entries (no more hardcoded `0`); rules Execute exposed separately from preview Evaluate.
- Report: Month + Drone State filters; CR/Drone/Monthly summary cards; expanded table columns (#, CR Number, T-10, Last Updated); native save-dialog CSV with UTF-8 BOM, Blob fallback.
- Second Brain: wired search/sort/type/date filters to real filesystem notes; added Link Bank export/import/rename/restore.
- Settings: removed Theme switch (PRD = fixed theme); added T-10/numeric validation, trailing-slash guard, restart-required notice.

**Next:** Piece A merged to `main`. Plan Piece B (`project-details/cr-docs-rte`): `_cr-docs` editable files + multi-file RTE editor dropdown.

**Blocked:** None in startup. Windows manual verification needed for real filesystem/create/move flows.

**active_menu:** main; next branch `project-details/cr-docs-rte`

**Changed files:** `frontend/src/lib/components/NewProjectForm.svelte`, `frontend/src/lib/components/Dashboard.svelte`, `frontend/src/lib/components/ProjectDetails.svelte`, `frontend/src/lib/components/DroneTable.svelte`, `frontend/src/lib/components/Report.svelte`, `frontend/src/lib/types.ts`, `app_web.py`, plus updated assertions in `frontend/tests/components.test.mjs`, `frontend/tests/as-is-prototype-parity.test.mjs`, `frontend/tests/dashboard-inline-edit.test.mjs`, `frontend/tests/project-details-fase1.test.mjs`, `frontend/tests/project-details-fase3-fase4.test.mjs`, `_docs/PROGRESS.md`, `_docs/session-notes.md`.

**Verification:** `npm --prefix frontend run check` = 0 errors/0 warnings; `npm --prefix frontend test` = 149 pass/0 fail; `npm --prefix frontend run build` = ok; `D:/Ibrahim/Projects/project_tracker/.venv/Scripts/python.exe -m main` startup clean. No new Python test files by user hard rule; Python tests intentionally skipped.

---

## 2026-07-01

Branch aktif: `general/ux-features`
File diubah: App.svelte, Dashboard.svelte, ProjectDetails.svelte, Settings.svelte, EmailTemplateDialog.svelte, GlobalPlan.svelte, Report.svelte, SecondBrain.svelte, TitleBar.svelte, Toast.svelte (new), WelcomeGuide.svelte (new), toastStore.ts (new)
Keputusan teknis: toast store with undo action support; Settings autosave 1500ms debounce; undo toasts 5s timeout; onboarding once-and-never via localStorage
Verifikasi: build passes (pre-existing warnings only)

---

## 2026-06-29

Branch aktif: `design/titlebar`
File diubah: TitleBar.svelte (new), Sidebar.svelte → .bak, all 6 menu pages (page-header), Dashboard/ProjectDetails/SubProjectTable (3-icon CR/Drone), app_web.py, web/js_api.py, infrastructure/outlook_client.py, styles.css, App.svelte, Header.svelte, bridge.ts, various config/docs
Keputusan teknis: D-0005 (TitleBar replaces Sidebar), D-0006 (3-icon pattern for all CR/Drone inputs)
Verifikasi: svelte-check 0 errors, vite build clean

---

## 2026-06-27

Branch aktif: `chore/bootstrap-tooling`
File diubah: bootstrap tooling/config docs only
Design approved: none
Keputusan teknis: context-mode owns tool-output compression; claude-mem owns cross-session recall; agentmemory disabled to avoid duplicate capture/injection; retired code graph integration no longer used; RTK manual-only on native Windows.
Smoke: plugin list OK; retired code graph integration was degraded/noisy; RTK OK.
Blocked: Windows manual product verification remains separate from bootstrap.

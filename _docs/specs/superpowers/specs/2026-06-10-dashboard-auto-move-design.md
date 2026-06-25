# Dashboard Auto-Move + Gap-Closure Design

> **Date:** 2026-06-10
> **Branch:** prd-v31-migration
> **Scope:** Dashboard menu only (frontend + backend). Other menus follow later in their own specs.
> **Status:** Approved (sections 1–4 + G1/R3/R4 confirmed by user 2026-06-10)

## Context

The Dashboard (`Dashboard.svelte`, `Header.svelte`, `DashboardRowMenu.svelte`) and its
backend (`project_tracker/app_web.py` adapters, `project_tracker/services/project_service.py`,
`project_tracker/core/state_machine.py`, `project_tracker/core/rules.py`) were audited.
T1–T17 from the prior parity pass closed the data/interaction gaps, but inline CR/Drone
state changes are deliberately **metadata-only** (no folder move, no history, no
notification). This contradicts PRD §11.10/§11.11 which expect state changes to drive
folder transitions.

The auto-move engine is **half-built**: `target_project_state_for_cr_state()` already maps
CR state → folder state, and `ProjectService` already has `move_to_prod_ready`,
`move_to_implemented`, `cancel_project`, `postpone_project`, `resume_project`,
`reopen_project`, and `auto_transition_in_progress` — all with guards and history writes.
The work is **wiring + completing the evaluator**, reusing tested methods. Not greenfield.

## User Decisions (authoritative)

1. **Auto-move ON.** State change drives folder move across all conditions (not just one).
2. **T-10 reclassified.** It is NOT a hard guard. It is a soft **H-10 reminder**:
   H-10 = `start_datetime − 10 days`. Past H-10 with CR/Drone not APPROVED → management
   cutoff exists, but the CR can still proceed (change start date or request manager
   approval). Behavior = notification + activity-log note only. Never blocks.
3. **POSTPONED/CANCELED inline → route through move methods** (folder moves + history),
   replacing current metadata-only behavior. Keep the existing ConfirmModal.
4. **Safety model = silent move + notification** (no toast/undo, no pre-move confirm).
5. **G1 — new hard guard (mirrors office CR web portal):** if a project has any drone
   ticket, CR state cannot become APPROVED until **all** drone states are APPROVED.
   No drones → CR may go APPROVED directly.

## Section 1 — Auto-Move Evaluator (core)

New pure function in `core/state_machine.py`:

```
resolve_auto_move(cr_state, drone_states, current_folder) -> ProjectState | None
```

Returns the target folder state, or `None` for no-op. Pure; no I/O. Reuses
`target_project_state_for_cr_state()`.

| CR set to | Drone precondition                          | Source folder            | Target      | Notes                                  |
| --------- | ------------------------------------------- | ------------------------ | ----------- | -------------------------------------- |
| APPROVED  | all drones APPROVED (G1 guarantees) or none | UAT_PREPARE              | PROD_READY  | structural guards apply (links, dates) |
| FINISHED  | cascade drones → FINISHED first             | PROD_READY               | IMPLEMENTED | only legal drone paths cascade         |
| POSTPONED | —                                           | UAT_PREPARE / PROD_READY | POSTPONED   | exit; no deployment guard              |
| CANCELED  | —                                           | any non-terminal         | CANCELED    | exit; no deployment guard              |

No-op when: target == current folder, folder is IMPLEMENTED (terminal/locked), or the
source→target project-state transition is illegal (`PROJECT_STATE_TRANSITIONS`).

The orchestration (calling the right `ProjectService` move method) lives in the service/
adapter layer, NOT in core. Core only decides the target.

## Section 2 — H-10 Reminder (replaces T-10 guard)

- Remove T-10 from `validate_uat_to_prod_ready_transition` failed_guards. Structural guards
  (CR link, drone links, dates present + coherent, drone APPROVED) remain.
- New helper computes H-10 = `start_datetime − h10_reminder_days`.
- Reminder fires when `now >= H-10` AND (CR != APPROVED OR any drone != APPROVED).
- Effect: one notification + one history/activity note per project
  ("⚠ H-10 cutoff passed — CR/Drone not yet APPROVED. Change start date or request
  management approval."). Never blocks any transition.
- **Configurable:** `h10_reminder_days` in Settings (default 10).
- **Dedup:** `h10_notified_at` stamp in metadata; reminder fires once until the condition
  resolves (CR/drone reach APPROVED) or start date changes, then re-arms.
- Evaluated on dashboard load + a daily APScheduler check (NotificationService already wired).

## Section 3 — Wiring + History/Notifications

- After a successful inline CR/Drone state persist, run `resolve_auto_move`; if it returns
  a target, call the matching existing `ProjectService` method (which performs the
  `shutil.move`, writes history, and is Windows-runtime real / Linux temp-dir tested).
- POSTPONED/CANCELED inline (with existing ConfirmModal) now route through
  `postpone_project` / `cancel_project`.
- Every inline state change AND link paste appends a history entry (currently missing on
  `update_cr_state`, `update_drone`, `update_cr_link`) and emits a notification.
- **Guard-fail UX:** state change still persists; folder stays; non-blocking banner shows
  the structural reason. (T-10 no longer contributes failures.)

## Section 4 — Smaller Dashboard Gaps (batch last)

- **A4** Show extracted identifier (`CR202604…`, `D-SSIDBI-159`) beside each link cell
  (uses existing `extract_cr_number`/`extract_drone_ticket`).
- **C2** Semantic state color chips (APPROVED green, PENDING amber, CANCELED/POSTPONED red).
- **C4** Inline per-cell saving spinner (currently only disables input).
- **B4** Long project/sub name ellipsis + title tooltip.
- **B3** Root set but zero year folders → "Add Year" empty-state nudge.

Design polish only; no domain-logic risk.

## Hard Guard G1 — CR APPROVED requires Drones APPROVED

In `update_cr_state` (and core validation): when target == APPROVED and the project has
≥1 drone ticket, reject if any drone state != APPROVED. Inline error:
"CR cannot be APPROVED — N drone(s) not yet APPROVED." No drones → allowed.
This makes auto-move deterministic: when CR finally reaches APPROVED, all drones are
already APPROVED, so the PROD_READY move never lands in a partial state.

## R3 — EventQueue on every move

Every auto-move (and the routed POSTPONED/CANCELED) pushes an event onto the existing
`web/event_queue.py` so the 1.5s dashboard poll refreshes the row automatically and stays
consistent with watchdog-driven updates.

## R4 — Drone-FINISHED cascade surfacing

When CR→FINISHED cascades drones→FINISHED, any drone whose current state has no legal path
to FINISHED (e.g. UAT, PENDING APPROVAL — only IN-PROGRESS→FINISHED is legal) is NOT
silently skipped. The IMPLEMENTED move is blocked and the reason surfaces:
"N drone(s) cannot auto-finish (state X). Move to IMPLEMENTED blocked."

## Explicitly Out of Scope

- Drone-only state change triggering auto-move while CR is not yet at the target state
  (over-trigger; evaluator runs but only acts when CR is already at the target).
- Right-click context menu (prototype + PRD use the ⋮ button; not a gap).
- Toast/undo and pre-move confirmation (user chose silent move + notification).
- Other menus (Project Details, Report, Second Brain, Automations, Settings) — separate specs.

## Verification Plan (Linux)

- New core unit tests for `resolve_auto_move` (all rows + no-op cases) and G1 guard.
- Service tests for each routed move (temp dirs only; never real folders).
- H-10 reminder tests (fires once, dedup, re-arm, never blocks).
- Frontend SSR tests for banner reasons, G1 inline error, extracted-ID display.
- Full gates: `npm run check`, `npm run build`, `pytest -q`, `py_compile`.
- Windows-only manual: real `shutil.move`, `os.startfile`, WebView2 render — deferred to
  the existing Windows manual-test gate.

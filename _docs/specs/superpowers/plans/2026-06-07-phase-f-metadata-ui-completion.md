# Phase F — Safe Metadata/UI Completion Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Complete remaining safe metadata mutations (drone state, link bank CRUD) and frontend wiring without filesystem/Windows/external side effects.

**Architecture:** Adapter pattern in `app_web.py` delegates to state-machine guards (drone) or LinkBankStore (links). Frontend uses existing bridge wrapper. All mutations metadata-only.

**Tech Stack:** Python 3.12, Svelte 5, TypeScript, pytest, TDD

---

## File Structure

| File                                                | Responsibility                                                       |
| --------------------------------------------------- | -------------------------------------------------------------------- |
| `project_tracker/app_web.py`                        | `_ProjectServiceAdapter` drone state method, `_LinkBankAdapter` CRUD |
| `project_tracker/infrastructure/link_bank_store.py` | Add stable `id` + `archived` to link model                           |
| `tests/test_phase_f_drone_state_guarded.py`         | Drone state guard tests                                              |
| `tests/test_phase_f_linkbank_stable_ids.py`         | Link bank ID + CRUD tests                                            |
| `frontend/src/lib/components/ProjectDetails.svelte` | Drone state dropdown UI                                              |
| `frontend/src/lib/components/SecondBrain.svelte`    | Link bank add/edit/archive UI                                        |
| `frontend/src/lib/types.ts`                         | DroneTicket drone_state_options, LinkItem id/archived                |

---

## Task 1: F.1 — Guarded Drone State Update (Backend)

**Files:**

- Modify: `project_tracker/app_web.py` (add `update_drone_state` to `_ProjectServiceAdapter`)
- Create: `tests/test_phase_f_drone_state_guarded.py`

### Contract

- New adapter method: `update_drone_state(project_path, drone_index, target_state)`
- Uses `validate_drone_state_change_allowed(drone_link, current, target)` from `core/state_machine.py`
- Requires `drone_link` non-empty (guard validates)
- Persists `drone_state` + `drone_state_updated_at` via MetadataStore
- No folder moves, no project state change
- JsApi already has `drone_update(path, index, data)` — but E.2 explicitly skips `drone_state`. New dedicated path needed.

### Decision: Separate method vs extend drone_update

Option A: Add a new JsApi method `drone_update_state(path, index, state)` — requires js_api.py signature change (FORBIDDEN by default).

Option B: Extend existing `_ProjectServiceAdapter.update_drone` to accept `drone_state` through guarded path when present in data dict.

**Chosen: Option B** — no js_api.py change needed. The existing `drone_update(path, index, data)` JsApi method delegates to adapter. Adapter already ignores `drone_state` in data. Change: when `drone_state` is present in data, validate via `validate_drone_state_change_allowed()` and apply if valid. Reject with error if invalid. No new JsApi signature.

- [ ] **Step 1: Write failing tests**

```python
# tests/test_phase_f_drone_state_guarded.py
# Tests:
# 1. drone_update with valid drone_state transition succeeds + persists
# 2. drone_update with invalid drone_state transition fails with error
# 3. drone_update with drone_state but empty drone_link fails
# 4. drone_update with drone_state IN-PROGRESS (auto-only) rejected
# 5. drone_update without drone_state still works (E.2 preserved)
# 6. drone_state_updated_at set on success
```

- [ ] **Step 2: Run tests — expect FAIL (drone_state ignored)**

Run: `pytest tests/test_phase_f_drone_state_guarded.py -v`

- [ ] **Step 3: Implement guarded drone_state in adapter**

In `_ProjectServiceAdapter.update_drone()`: if `"drone_state"` in data, import and call `validate_drone_state_change_allowed(ticket.drone_link, ticket.drone_state, DroneState(data["drone_state"]))`. On success, set `ticket.drone_state` + `ticket.drone_state_updated_at = local_now()`.

- [ ] **Step 4: Run tests — expect PASS**

Run: `pytest tests/test_phase_f_drone_state_guarded.py -v`

- [ ] **Step 5: Run full suite**

Run: `pytest tests/ -q`

- [ ] **Step 6: Commit**

```bash
git add project_tracker/app_web.py tests/test_phase_f_drone_state_guarded.py
git commit -m "implement phase F.1 guarded drone state update (backend)"
```

---

## Task 2: F.1 — Guarded Drone State Update (Frontend)

**Files:**

- Modify: `frontend/src/lib/components/ProjectDetails.svelte`
- Modify: `frontend/src/lib/types.ts` (if needed)

- [ ] **Step 1: Add drone state dropdown to drone row**

In the drone row display (non-edit mode), add a `<select>` with DroneState options + Save State button. Options: `UAT`, `PENDING APPROVAL`, `APPROVED`, `IN-PROGRESS`, `FINISHED`, `CANCELED`.

Save calls existing `drone_update(path, index, {drone_state: selectedValue})`.

- [ ] **Step 2: Add drone state local edit state**

Per-drone `droneStateEdits: Record<number, string>` tracking local dropdown value. Init from `t.drone_state`. Save button disabled when unchanged.

- [ ] **Step 3: Handle success/error feedback**

On error (invalid transition), show inline error. On success, refresh detail. Clear error.

- [ ] **Step 4: Verify**

Run: `npm --prefix frontend run check && npm --prefix frontend run build`

- [ ] **Step 5: Commit full F.1**

```bash
git add project_tracker/app_web.py tests/test_phase_f_drone_state_guarded.py frontend/src/lib/components/ProjectDetails.svelte
git commit -m "implement phase F.1 guarded drone state update"
```

---

## Task 3: F.2 — Second Brain Pin/Favorite

**BLOCKED — SKIP**

Reason: Production `SecondBrainService()` uses default `items_provider=list` → returns empty items. Pin/favorite are in-memory only with no persistence layer. PRD explicitly lists "Real Second Brain filesystem index" as deferred. Wiring frontend would:

- Show empty list (no items to pin)
- Lose pin/fav state on restart

This is fake success territory. Skip until real filesystem index is implemented.

---

## Task 4: F.3 — Link Bank Stable IDs + CRUD (Backend)

**Files:**

- Modify: `project_tracker/infrastructure/link_bank_store.py`
- Modify: `project_tracker/app_web.py` (`_LinkBankAdapter`)
- Create: `tests/test_phase_f_linkbank_stable_ids.py`

### Contract

Current link shape: `{"name", "url", "notes", "category"}` — no `id`, no `archived`.

Target: add `id` (UUID4 hex, generated on first load for legacy links) + `archived` (bool, default false). Backward-compatible: missing `id`/`archived` in JSON → generate/default on read.

- [ ] **Step 1: Write failing tests**

```python
# tests/test_phase_f_linkbank_stable_ids.py
# Tests:
# 1. Legacy links without id get stable id on read
# 2. Links with id preserve existing id
# 3. archived defaults to False for legacy links
# 4. add_link generates new id
# 5. archive_link sets archived=True by id
# 6. update_linkbank updates fields by id
# 7. archived links excluded from default get_linkbank (or marked)
# 8. Round-trip: write → read preserves ids
```

- [ ] **Step 2: Run tests — expect FAIL**

- [ ] **Step 3: Update `_normalize_link` in link_bank_store.py**

```python
import uuid

def _normalize_link(link: dict[Any, Any]) -> dict[str, str]:
    return {
        "id": str(link.get("id", "")) or uuid.uuid4().hex,
        "name": str(link.get("name", "")),
        "url": str(link.get("url", "")),
        "notes": str(link.get("notes", "")),
        "category": str(link.get("category", "")),
        "archived": str(link.get("archived", "false")),
    }
```

- [ ] **Step 4: Update `_LinkBankAdapter` in app_web.py**

Wire `add_link`, `update_linkbank` (update by ID), `archive_link` (set archived=true by ID). Remove RuntimeError raises.

- [ ] **Step 5: Run tests — expect PASS**

- [ ] **Step 6: Run full suite**

- [ ] **Step 7: Commit**

```bash
git add project_tracker/infrastructure/link_bank_store.py project_tracker/app_web.py tests/test_phase_f_linkbank_stable_ids.py
git commit -m "implement phase F.3 link bank stable id actions (backend)"
```

---

## Task 5: F.3 — Link Bank CRUD (Frontend)

**Files:**

- Modify: `frontend/src/lib/components/SecondBrain.svelte`
- Modify: `frontend/src/lib/types.ts`

- [ ] **Step 1: Update LinkItem type with id + archived**

```typescript
interface LinkItem {
  id: string;
  name: string;
  url: string;
  notes: string;
  category: string;
  archived: string; // "true" | "false"
}
```

- [ ] **Step 2: Add Link form**

Name, URL, category, notes inputs + Add button. Calls `linkbank_add_link` via bridge.

- [ ] **Step 3: Edit Link inline**

Edit button per card → inline inputs → Save calls `linkbank_update` via bridge with `{id, name, url, notes, category}`.

- [ ] **Step 4: Archive Link button**

Archive button per card → calls `linkbank_archive_link` via bridge with `id`. Remove from visible list on success (or mark dimmed).

- [ ] **Step 5: Filter out archived by default**

`filteredLinks` excludes `archived === "true"` unless user toggles "show archived".

- [ ] **Step 6: Verify**

Run: `npm --prefix frontend run check && npm --prefix frontend run build`

- [ ] **Step 7: Commit full F.3**

```bash
git add frontend/src/lib/components/SecondBrain.svelte frontend/src/lib/types.ts project_tracker/infrastructure/link_bank_store.py project_tracker/app_web.py tests/test_phase_f_linkbank_stable_ids.py
git commit -m "implement phase F.3 link bank stable id actions"
```

---

## Task 6: F.4 — Automation Preview UI Polish (Optional)

**Files:**

- Modify: `frontend/src/lib/components/Automations.svelte`

- [ ] **Step 1: Assess if meaningful improvement exists**

Current state: evaluate-all button added in D.16. Rules list shows conditions as raw JSON. Potential improvement: render conditions as readable key/op/value pills instead of `JSON.stringify`.

- [ ] **Step 2: Implement condition pills if meaningful**

Replace `{JSON.stringify(cond)}` with structured `{cond.field} {cond.operator} {cond.value}` display.

- [ ] **Step 3: Verify**

Run: `npm --prefix frontend run check && npm --prefix frontend run build`

- [ ] **Step 4: Commit if changed**

```bash
git add frontend/src/lib/components/Automations.svelte
git commit -m "improve phase F.4 automation preview ui"
```

Skip if no meaningful improvement found.

---

## Task 7: F.5 — Status Update

**Files:**

- Modify: `PROJECT_STATUS.md`

- [ ] **Step 1: Update with all completed F slices + new test count**
- [ ] **Step 2: Commit**

```bash
git add PROJECT_STATUS.md
git commit -m "update project status after phase F"
```

---

## Execution Order

1. F.1 backend + frontend (drone state guard)
2. F.2 SKIP (Second Brain blocked)
3. F.3 backend + frontend (link bank stable IDs + CRUD)
4. F.4 optional polish
5. F.5 status update

## Stop Conditions

- LinkBankStore backward compat unclear → stop F.3
- Drone guard semantics unclear → stop F.1
- Frontend check/build fails → fix before commit
- Test failure not obvious within slice → stop

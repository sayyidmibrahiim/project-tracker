# Automations Parity Slice Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Audit Automations against PRD §16/prototype, then implement the smallest high-value gap: PRD tab order/default Outlook plus safe Outlook workspace scaffold.

**Architecture:** Keep `Automations.svelte` as tab dispatcher. Add Automations-page Outlook scaffold in a new focused Svelte component; keep project-scoped `OutlookActions.svelte` unchanged. Frontend calls typed bridge only if user explicitly runs draft/download actions; no Windows execution claimed on Linux.

**Tech Stack:** Svelte 5 + TypeScript + Vite + existing `callBridge`; Python bridge/service untouched unless audit finds contradiction.

---

## Files

- Create: `docs/automations-parity-matrix.md` — audit matrix required by approved spec.
- Create: `frontend/src/lib/components/AutomationsOutlook.svelte` — Automations-tab Outlook workspace scaffold.
- Modify: `frontend/src/lib/components/Automations.svelte` — PRD tab order + mount Outlook scaffold.
- Modify: `frontend/tests/components.test.mjs` — SSR checks for tab order and Outlook scaffold labels.
- Modify: `PROJECT_STATUS.md` — record slice result + Windows gates.

## Task 1: Build Automations parity matrix

**Files:**

- Create: `docs/automations-parity-matrix.md`

- [ ] **Step 1: Create matrix doc**

Write `docs/automations-parity-matrix.md`:

```markdown
# Automations Parity Matrix

Sources:

- `PRD.md` §16
- `redesign_ui/automations_redesign.py`
- `frontend/src/lib/components/Automations.svelte`
- `frontend/src/lib/components/OutlookActions.svelte`
- `frontend/src/lib/components/TeamsActions.svelte`
- `frontend/src/lib/components/SchedulerActions.svelte`
- `frontend/src/lib/components/RulesActions.svelte`

| Requirement                               | PRD §16 behavior                                                                   | PyQt prototype intent                      | Current Svelte behavior                                                                | Status  | Chosen fix                                                                                |
| ----------------------------------------- | ---------------------------------------------------------------------------------- | ------------------------------------------ | -------------------------------------------------------------------------------------- | ------- | ----------------------------------------------------------------------------------------- |
| Tab order                                 | Outlook, Teams, Scheduler, Rules Engine                                            | Same order in `QTabWidget`                 | Rules, Outlook, Teams, Scheduler; defaults to Rules                                    | gap     | Change dispatcher order/default to Outlook, Teams, Scheduler, Rules Engine                |
| Outlook two-column send/download layout   | Send automation left; Download automation right; KPI row                           | Two cards with send/download tables + logs | Placeholder only in Automations page; project-scoped `OutlookActions` exists elsewhere | gap     | Add Automations Outlook scaffold with KPI row, two columns, honest guarded action states  |
| Email Template Dialog flow                | Full dialog with category/to/cc/subject/body/attachment/mode/conditions/log        | `EmailTemplateDialog` in prototype         | Absent from Automations page                                                           | gap     | Keep as next slice; scaffold Edit Template button as deferred with reason                 |
| Downloaded Emails dialog                  | Dialog lists subject/from/CR/date/tag, newest first, search/sort, expandable cards | MessageBox placeholder                     | Absent from Automations page                                                           | gap     | Keep as next slice; add Downloaded Emails button with guarded bridge hook placeholder     |
| Teams layout                              | Two-column automation/status layout                                                | Two-column layout + dialog                 | Single message form, preview-first, auto-send guarded                                  | partial | Defer; safety already present                                                             |
| Teams dialog/preview/send                 | Dialog with rules; preview default; auto-send gated                                | `TeamsAutomationDialog`                    | Preview/send controls present; no saved automation dialog/countdown                    | partial | Defer after Outlook scaffold                                                              |
| `teams_auto_send=false` default           | Auto-send disabled by default                                                      | Preview First mode                         | `TeamsActions` disables Send unless setting true                                       | done    | No change                                                                                 |
| Scheduler KPI row                         | Due Soon, Overdue, Paused, Total Entries                                           | KPI row exists                             | Status bar + entry cards, no KPI row                                                   | gap     | Defer; next scheduler slice                                                               |
| Scheduler CRUD/status/action confirmation | Add/edit/pause/delete/run with confirmations for risky channels                    | Table + Add Reminder                       | CRUD exists; trigger confirmation for risky channels; delete lacks confirmation        | partial | Defer; add delete confirmation in later slice                                             |
| Rules Engine CRUD                         | Rule editor with trigger/conditions/actions                                        | Table + Add Rule                           | CRUD exists, action ordering exists, limited trigger/condition editor                  | partial | Defer; already high-value enough                                                          |
| Rule execution logs                       | Latest 20 execution log                                                            | Static log textarea                        | Per-rule logs view exists                                                              | partial | Defer global log                                                                          |
| Ordered rule actions                      | Actions run top-to-bottom                                                          | Action list implied                        | Ordered UI and backend execution present                                               | done    | No change                                                                                 |
| Draft-first Outlook                       | Draft default; send requires confirmation                                          | Draft Only default                         | Project-scoped `OutlookActions` supports draft-first; Automations page missing         | partial | Scaffold Automations Outlook page with draft-first copy and disabled/deferred send config |
| Preview-first Teams                       | Preview default; send gated                                                        | Preview First default                      | Implemented in `TeamsActions`                                                          | done    | No change                                                                                 |
| Windows-only guarded behavior             | COM/pyautogui guarded                                                              | Prototype visual only                      | Backend/frontend copy reports dev-skipped/off-Windows                                  | done    | Preserve                                                                                  |

## Selected implementation target

Implement the smallest high-value visible gap:

1. Fix Automations tab order/default to PRD order.
2. Add Automations Outlook workspace scaffold with KPI row, two-column send/download layout, logs, draft-first safety copy, and deferred template/download dialogs with explicit reasons.

No backend changes in this slice.
```

- [ ] **Step 2: Verify matrix has no contradictions**

Run:

```bash
rtk grep -n "TODO\|TBD\|project_state" docs/automations-parity-matrix.md
```

Expected: no `TODO`, no `TBD`, no inappropriate `project_state` mention.

## Task 2: Add Outlook workspace scaffold

**Files:**

- Create: `frontend/src/lib/components/AutomationsOutlook.svelte`

- [ ] **Step 1: Create component**

Write `frontend/src/lib/components/AutomationsOutlook.svelte`:

```svelte
<script lang="ts">
  import { callBridge, isPywebviewReady } from "../bridge";

  type Feedback =
    | { kind: "none" }
    | { kind: "notice"; text: string }
    | { kind: "error"; text: string };

  const sendCategories = [
    { code: "ACK_UAT", purpose: "UAT acknowledgment", conditions: "CR submitted" },
    { code: "ACK_SOP", purpose: "SOP acknowledgment", conditions: "CR submitted" },
    { code: "APRVL_CR", purpose: "CR approval request", conditions: "Ready for approval" },
    { code: "APRVL_SOP", purpose: "SOP approval request", conditions: "SOP ready" },
  ];

  const downloadJobs = [
    { category: "On Going ACK", details: "Monitor ACK replies" },
    { category: "On Going Tech LV", details: "Monitor technical lead approvals" },
  ];

  const kpis = [
    { label: "Send Categories", value: sendCategories.length },
    { label: "Download Jobs", value: downloadJobs.length },
    { label: "HTML Templates", value: 0 },
    { label: "On Going ACK", value: 0 },
    { label: "On Going Tech LV", value: 0 },
  ];

  let feedback: Feedback = $state({ kind: "none" });
  let busy: boolean = $state(false);

  function showTemplateDeferred(code: string) {
    feedback = {
      kind: "notice",
      text: `Email Template Dialog for ${code} is deferred to the next Outlook slice. Draft-first Outlook actions remain available from Project Details.`,
    };
  }

  async function openDownloadedEmails() {
    feedback = { kind: "none" };
    if (!isPywebviewReady()) {
      feedback = { kind: "notice", text: "Downloaded Emails requires the pywebview bridge. Browser preview is read-only." };
      return;
    }
    busy = true;
    const response = await callBridge<unknown>("outlook_download_emails");
    busy = false;
    if (!response.ok) {
      feedback = { kind: "error", text: response.error.message };
      return;
    }
    feedback = { kind: "notice", text: "Downloaded Emails bridge returned. Detailed searchable dialog is the next Outlook slice." };
  }
</script>

<div class="ao-root">
  <div class="ao-kpis" aria-label="Outlook automation KPIs">
    {#each kpis as kpi}
      <div class="ao-kpi">
        <span class="ao-kpi-value">{kpi.value}</span>
        <span class="ao-kpi-label">{kpi.label}</span>
      </div>
    {/each}
  </div>

  <div class="ao-columns">
    <section class="ao-card" aria-label="Send automation">
      <div class="ao-card-head">
        <div>
          <h3>SEND AUTOMATION</h3>
          <p>Hint: select a category to configure its draft-first template.</p>
        </div>
        <button class="ao-btn ao-btn-primary" type="button" onclick={() => showTemplateDeferred("NEW")}>+ Add Category</button>
      </div>

      <div class="ao-table" role="table" aria-label="Outlook send categories">
        <div class="ao-tr ao-th" role="row">
          <span>Category</span><span>Purpose</span><span>Conditions</span><span>Action</span>
        </div>
        {#each sendCategories as row}
          <div class="ao-tr" role="row">
            <span class="ao-code">{row.code}</span>
            <span>{row.purpose}</span>
            <span>{row.conditions}</span>
            <button class="ao-link" type="button" onclick={() => showTemplateDeferred(row.code)}>Edit Template</button>
          </div>
        {/each}
      </div>

      <div class="ao-log">
        <strong>Send Automation Log</strong>
        <p>[deferred] Template configuration is pending. Project Details keeps Draft email as the default safe action.</p>
      </div>
    </section>

    <section class="ao-card" aria-label="Download automation">
      <div class="ao-card-head">
        <div>
          <h3>DOWNLOAD AUTOMATION</h3>
          <p>Relation to Send categories. Windows Outlook COM remains guarded.</p>
        </div>
        <button class="ao-btn" type="button" onclick={openDownloadedEmails} disabled={busy}>Downloaded Emails ▶</button>
      </div>

      <div class="ao-table two" role="table" aria-label="Outlook download jobs">
        <div class="ao-tr ao-th" role="row"><span>Category</span><span>Details</span></div>
        {#each downloadJobs as row}
          <div class="ao-tr" role="row"><span class="ao-code">{row.category}</span><span>{row.details}</span></div>
        {/each}
      </div>

      <div class="ao-log">
        <strong>Download Tool Log</strong>
        <p>[deferred] Searchable Downloaded Emails dialog will list subject, sender, CR number, date, and category.</p>
      </div>
    </section>
  </div>

  <p class="ao-safety">Draft-first Outlook is the safe default. Send-immediately requires explicit confirmation and Windows Outlook COM.</p>

  {#if feedback.kind === "notice"}
    <div class="ao-feedback ao-notice" role="status">⊘ {feedback.text}</div>
  {:else if feedback.kind === "error"}
    <div class="ao-feedback ao-error" role="alert">⚠ {feedback.text}</div>
  {/if}
</div>

<style>
  .ao-root { display:flex; flex-direction:column; gap:10px; min-height:0; }
  .ao-kpis { display:grid; grid-template-columns:repeat(5,minmax(110px,1fr)); gap:8px; }
  .ao-kpi { background:#fff; border:1px solid #E5E7EB; border-left:3px solid var(--color-dbs-red); border-radius:6px; padding:8px 10px; box-shadow:var(--shadow-subtle); }
  .ao-kpi-value { display:block; color:var(--color-dbs-red); font-size:20px; line-height:1; font-weight:900; }
  .ao-kpi-label { display:block; margin-top:4px; color:var(--color-muted); font-size:9px; font-weight:850; text-transform:uppercase; letter-spacing:0.25px; }
  .ao-columns { display:grid; grid-template-columns:minmax(0,1fr) minmax(0,1fr); gap:12px; min-height:0; }
  .ao-card { background:#fff; border:1px solid #D7DCE2; border-radius:8px; padding:12px; display:flex; flex-direction:column; gap:10px; min-width:0; }
  .ao-card-head { display:flex; align-items:flex-start; justify-content:space-between; gap:10px; }
  .ao-card h3 { margin:0; color:var(--color-ink); font-size:12px; font-weight:900; letter-spacing:0.2px; }
  .ao-card p { margin:3px 0 0; color:var(--color-muted); font-size:10px; font-weight:700; line-height:1.35; }
  .ao-table { display:flex; flex-direction:column; border:1px solid #E5E7EB; border-radius:6px; overflow:hidden; }
  .ao-tr { display:grid; grid-template-columns:0.8fr 1.2fr 1.2fr 0.8fr; gap:8px; align-items:center; padding:7px 8px; border-top:1px solid #E5E7EB; font-size:10px; font-weight:750; color:var(--color-ink); }
  .ao-table.two .ao-tr { grid-template-columns:1fr 1.5fr; }
  .ao-tr:first-child { border-top:0; }
  .ao-th { background:#111; color:#fff; font-size:9px; font-weight:900; text-transform:uppercase; letter-spacing:0.3px; }
  .ao-code { font-family:monospace; font-weight:900; }
  .ao-btn, .ao-link { padding:5px 10px; border:1px solid #D7DCE2; border-radius:5px; background:#fff; color:var(--color-ink); font-size:10px; font-weight:850; cursor:pointer; white-space:nowrap; }
  .ao-btn:hover:not(:disabled), .ao-link:hover:not(:disabled) { border-color:var(--color-dbs-red); color:var(--color-dbs-red); }
  .ao-btn:disabled { opacity:0.55; cursor:not-allowed; }
  .ao-btn-primary { background:var(--color-dbs-red); border-color:var(--color-dbs-red); color:#fff; }
  .ao-log { min-height:70px; background:var(--color-workspace-panel); border:1px solid #E5E7EB; border-radius:6px; padding:8px; color:var(--color-muted); font-size:10px; font-weight:700; }
  .ao-log strong { color:var(--color-ink); display:block; margin-bottom:4px; }
  .ao-safety { margin:0; color:var(--color-muted); font-size:10px; font-weight:800; }
  .ao-feedback { padding:7px 10px; border-radius:6px; font-size:10px; font-weight:850; }
  .ao-notice { background:#f3f4f6; border:1px solid #D7DCE2; color:var(--color-muted); }
  .ao-error { background:var(--color-soft-pink-surface); border:1px solid var(--color-soft-pink-border); color:var(--color-dbs-red); }
  @media (max-width: 980px) {
    .ao-kpis { grid-template-columns:repeat(2,minmax(120px,1fr)); }
    .ao-columns { grid-template-columns:1fr; }
  }
</style>
```

- [ ] **Step 2: Run Svelte build to catch syntax errors**

Run:

```bash
rtk npm --prefix frontend run build
```

Expected: Vite build succeeds.

## Task 3: Wire PRD tab order/default

**Files:**

- Modify: `frontend/src/lib/components/Automations.svelte`

- [ ] **Step 1: Replace dispatcher script/imports and tabs**

Edit `frontend/src/lib/components/Automations.svelte` to this complete content:

```svelte
<script lang="ts">
  /**
   * Automations screen — PRD §16 tab dispatcher.
   *
   * Tab order is fixed by PRD: Outlook, Teams, Scheduler, Rules Engine.
   * Each tab owns only UI state. Python services remain owner of automation
   * persistence, rule execution, scheduler jobs, and Windows-only integrations.
   */
  import AutomationsOutlook from "./AutomationsOutlook.svelte";
  import TeamsActions from "./TeamsActions.svelte";
  import SchedulerActions from "./SchedulerActions.svelte";
  import RulesActions from "./RulesActions.svelte";

  type TabId = "outlook" | "teams" | "scheduler" | "rules";

  const tabs: { id: TabId; label: string }[] = [
    { id: "outlook", label: "Outlook" },
    { id: "teams", label: "Teams" },
    { id: "scheduler", label: "Scheduler" },
    { id: "rules", label: "Rules Engine" },
  ];

  let activeTab: TabId = $state("outlook");

  function onTabSwitch(tab: TabId) {
    activeTab = tab;
  }

  export function refresh() {}
</script>

<div class="am-screen">
  <div class="am-tab-bar" aria-label="Automations tabs">
    {#each tabs as tab}
      <button class="am-tab" class:active={activeTab === tab.id} onclick={() => onTabSwitch(tab.id)}>{tab.label}</button>
    {/each}
  </div>

  {#if activeTab === "outlook"}
    <div class="am-pane"><AutomationsOutlook /></div>
  {:else if activeTab === "teams"}
    <div class="am-pane"><TeamsActions /></div>
  {:else if activeTab === "scheduler"}
    <div class="am-pane"><SchedulerActions /></div>
  {:else}
    <div class="am-pane"><RulesActions /></div>
  {/if}
</div>

<style>
  .am-screen { flex:1; min-height:0; display:flex; flex-direction:column; padding:14px; gap:10px; overflow:hidden; }
  .am-tab-bar { display:flex; gap:4px; flex:0 0 auto; background:var(--color-workspace-panel); border:1px solid #D7DCE2; border-radius:8px; padding:6px; box-shadow:0 4px 15px rgba(0,0,0,0.30); }
  .am-tab { height:28px; border-radius:5px; padding:0 16px; background:transparent; border:1px solid transparent; color:var(--color-ink); font-weight:850; font-size:11px; cursor:pointer; transition:background 0.15s ease,color 0.15s ease; }
  .am-tab:hover { background:var(--color-soft-pink-surface); color:var(--color-dbs-red); }
  .am-tab.active { background:var(--color-dbs-red); color:#fff; font-weight:900; }
  .am-pane { flex:1; min-height:0; overflow-y:auto; padding:4px 2px; }
</style>
```

- [ ] **Step 2: Build**

Run:

```bash
rtk npm --prefix frontend run build
```

Expected: build succeeds and `web/static/` updates.

## Task 4: Add SSR regression tests

**Files:**

- Modify: `frontend/tests/components.test.mjs`

- [ ] **Step 1: Add imports/constants**

Add below existing constants:

```js
const AUTOMATIONS = "../src/lib/components/Automations.svelte";
const AUTOMATIONS_OUTLOOK = "../src/lib/components/AutomationsOutlook.svelte";
```

- [ ] **Step 2: Add tests at file end**

Append:

```js
test("Automations renders PRD tab order with Outlook first", async () => {
  const body = await renderComponent(AUTOMATIONS, {});
  const outlook = body.indexOf("Outlook");
  const teams = body.indexOf("Teams");
  const scheduler = body.indexOf("Scheduler");
  const rules = body.indexOf("Rules Engine");
  assert.ok(outlook >= 0, "Outlook tab is rendered");
  assert.ok(teams > outlook, "Teams follows Outlook");
  assert.ok(scheduler > teams, "Scheduler follows Teams");
  assert.ok(rules > scheduler, "Rules Engine follows Scheduler");
  assert.match(body, /SEND AUTOMATION/);
  assert.doesNotMatch(body, /Project-scoped/);
});

test("AutomationsOutlook renders two-column Outlook scaffold and draft-first safety copy", async () => {
  const body = await renderComponent(AUTOMATIONS_OUTLOOK, {});
  assert.match(body, /SEND AUTOMATION/);
  assert.match(body, /DOWNLOAD AUTOMATION/);
  assert.match(body, /Downloaded Emails/);
  assert.match(body, /Draft-first Outlook is the safe default/);
  assert.match(body, /ACK_UAT/);
  assert.match(body, /APRVL_CR/);
});
```

- [ ] **Step 3: Run frontend component tests**

Run:

```bash
rtk npm --prefix frontend run test -- components.test.mjs
```

Expected: component tests pass. If npm test script does not accept arg, run full frontend test:

```bash
rtk npm --prefix frontend run test
```

Expected: all frontend tests pass.

## Task 5: Update project status

**Files:**

- Modify: `PROJECT_STATUS.md`

- [ ] **Step 1: Add latest slice note near top after current phase summary**

Insert:

```markdown
Automations parity slice started from `master-prompt.md`: PRD §16/prototype audit matrix added, Automations tab order/default aligned to PRD (Outlook, Teams, Scheduler, Rules Engine), and Outlook Automations scaffold added with two-column send/download layout and explicit draft-first/deferred Windows-safe messaging. Real Outlook COM and Downloaded Emails dialog behavior remain Windows/manual or next-slice gates.
```

- [ ] **Step 2: Ensure no Windows release claim**

Run:

```bash
rtk grep -n "Windows release ready\|final Windows-release verified\|Windows manual verification is still required" PROJECT_STATUS.md
```

Expected: status still says Windows manual verification required; no new release-ready claim.

## Task 6: Final verification

**Files:**

- No edits unless fixing failures.

- [ ] **Step 1: Run frontend tests**

Run:

```bash
rtk npm --prefix frontend run test
```

Expected: all frontend tests pass.

- [ ] **Step 2: Run frontend build**

Run:

```bash
rtk npm --prefix frontend run build
```

Expected: build succeeds.

- [ ] **Step 3: Run Python bridge smoke only if backend untouched remains true**

If only frontend/docs changed, skip Python tests and report skipped. If backend changed, run:

```bash
rtk /home/sayyidmibrahim/Development/projects/project_tracker_dbs/.venv/bin/python -m pytest tests/test_phase_c_js_api_automations.py tests/test_phase_c_js_api_scheduler.py -q
rtk /home/sayyidmibrahim/Development/projects/project_tracker_dbs/.venv/bin/python -m py_compile project_tracker/app_web.py project_tracker/web/js_api.py
```

Expected: tests pass; py_compile no output.

- [ ] **Step 4: Inspect diff**

Run:

```bash
rtk git diff -- docs/automations-parity-matrix.md frontend/src/lib/components/Automations.svelte frontend/src/lib/components/AutomationsOutlook.svelte frontend/tests/components.test.mjs PROJECT_STATUS.md
```

Expected: diff limited to planned files plus generated `web/static/` if build output is tracked.

## Self-review checklist

- Spec coverage: parity matrix required and implemented; one bounded gap selected; Windows-only gates explicit.
- Placeholder scan: no `TODO`, no `TBD`, no vague future behavior hidden as done.
- Type consistency: `TabId` values match dispatcher branches; SSR test paths match component paths.
- No new dependencies.
- No backend business logic moved into Svelte.
- No Windows execution claimed on Linux.

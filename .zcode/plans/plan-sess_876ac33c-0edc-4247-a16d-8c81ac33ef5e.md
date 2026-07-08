# Automation Epic — Slices 2→5 (Mega-plan, Autonomous Loop)

## Execution Model (decided)
1 plan, 1 approval, then **autonomous loop** Slice 2 → 3 → 4 → 5. Per slice:
**implement → verify gate (all green) → commit → docs sync → manual checklist → next slice.**

### STOP conditions (only reasons I halt mid-loop)
1. Verify gate fails AND root-cause fix attempt fails.
2. Spec ambiguity / code anchor gone (can't find reuse target).
3. Destructive decision outside **DEFAULT AMAN** (§below) needs user call.

Otherwise: jalan terus.

### Cross-slice conventions
- **Backend flat layout** (no `backend/`): `core/`, `services/`, `infrastructure/`, `web/js_api.py` (single module, ~103KB).
- **Frontend** components in `frontend/src/lib/components/`.
- **Svelte 5 runes**: `$state`/`$derived`/`$props` free; `$effect` ONLY with `void <dep>;` dependency-prefix idiom — NEVER read+write same `$state` in one effect (2026-07-05 self-subscription incident). Use `untrack` for prop init.
- **Layer rules** (ARCHITECTURE.md): frontend → bridge → services → core/infra. Domain state Python-owned.
- **Smallest Diff**: edit > add; reuse before new.
- **Verify gate per slice** (ALL green before commit):
  ```
  .venv/Scripts/python.exe -m pytest tests/test_phase_c_automation_service.py tests/test_phase_c_js_api_automations.py -q
  .venv/Scripts/python.exe -m pytest tests -q        # 6 baseline fail OK, NO new fail
  npm --prefix frontend run check                    # 0 errors
  npm --prefix frontend test
  npm --prefix frontend run build                    # ONLY if app closed (user restart after)
  .venv/Scripts/python.exe -m main                   # smoke ~15s, clean stdout/stderr
  ```
- **Commit** per slice `feat(automations): ...`; NO merge to main; NO branch delete.

---

## SLICE 2 — PlaceholderResolver + Template per-CR + editor popup + Test

### 2.1 PlaceholderResolver (services/email_service.py — edit, smallest diff)
New class `PlaceholderResolver` inside `email_service.py`. Replace `_placeholder_values` (L135-166) + `REQUIRED_PLACEHOLDERS` (L54-66) usage; keep both as **alias map** so existing templates don't break.

- `PlaceholderResolver(metadata: ProjectMetadata, settings: AppSettings, extra_context: dict|None=None)`
- `resolve(template_text: str) -> tuple[str, list[str]]` → (resolved_text, unresolved_tokens[])
- **Reflective discovery** via `dataclasses.fields()` over `ProjectMetadata`, `DroneTicket`, `AppSettings`. Tokens = `{UPPER_SNAKE(field)}`.
- Formats: `{FIELD}` flat; `{NESTED.FIELD}` (e.g. `{PROJECT.NAME}`); `{DRONE.0.LINK}` indexed into `metadata.drone_tickets[0].drone_link`.
- **11 legacy aliases preserved** (REQUIRED_PLACEHOLDERS → field paths):
  `{PROJECT_NAME}`→project_name, `{CR_NUMBER}`→cr_number, `{CR_LINK}`→cr_link, `{CR_STATE}`→cr_state.value, `{DRONE_TICKET}`→drone_tickets[0].subfolder_name, `{DRONE_LINK}`→drone_tickets[0].drone_link, `{DRONE_STATE}`→drone_tickets[0].drone_state.value, `{START_DATETIME}`→start_datetime, `{END_DATETIME}`→end_datetime, `{IMPLEMENTATION_PLAN}`→implementation_plan, `{DISPLAY_NAME}`→settings display.
  Plus 5 non-required legacy aliases (`{SUBPROJECT_NAME}`="", `{START}`, `{END}`, `{USER}`, `{YEAR}`).
- Unresolved **required** token → `UnresolvedPlaceholderError` (existing exception, L25-36) — preserve contract.
- `render_email_template` (L84) body refactored to call resolver; signature + `RenderedEmail` return unchanged.

### 2.2 Attachment resolution (email_service.py:132)
Stop forcing `attachment_path=None`. Compute from `category.attachment_template_file` (models.py:282) + `settings.email.template_folder_path` (models.py:314):
- both set → `Path(template_folder) / attachment_template_file`; validate exists; missing → None + log warn (don't fail render).

### 2.3 Template model + storage
- Keep existing dict storage (`ProjectMetadata.approval_templates` L152, `AppSettings.default_approval_templates` L531) — **no dataclass migration** (smallest diff).
- Add service helpers (new `services/template_service.py`, ~60 lines — justified: reflection + per-CR override merge logic is reusable across Slice 3/4):
  - `get_template(metadata, settings, kind, cr_id=None) -> dict` (merge base + cr override)
  - `save_template(target: metadata|settings, kind, template_dict, cr_id=None)`
  - `list_templates(settings) -> [{name,type,cr_override_count,last_modified}]`
- Bridge methods (extend `web/js_api.py` ~L1648 email cluster): `template_get(kind, cr_id, project_path)`, `template_save`, `template_test` (open Outlook draft with REAL resolved data → log "Test Draft Opened" via automation_logs stub or existing notification), `template_reset(kind, cr_id, project_path)`, `template_list`.
- bridge.ts: add typed wrappers `getTemplate/saveTemplate/testTemplate/resetTemplate/listTemplates`.

### 2.4 Frontend
- **ApprovalTemplates.svelte**: extend current form with CR dropdown (`select` specific CR or "Base/Default"), `attachments` field (filenames from template_folder), Save/Test/Reset-to-Default buttons. Switch CR → load that CR override or base.
- **Autocomplete**: `{` keypress in subject/body → dropdown of tokens + REAL preview value (resolved via bridge `template_preview_tokens(project_path)`); keyboard nav Arrow/Enter/Tab to insert.
- **Template list panel** in AutomationsOutlook.svelte: columns Name, Type, CR Override Count, Last Modified, Actions (Edit/Test/Delete).
- **Wire PD `[Setting]`** (ProjectDetails.svelte:1256): extend `onNavigateAutomations(kind?)` → App.svelte passes to Automations prop `initialTab='outlook'` + `openTemplateKind=kind` → opens editor popup.

### 2.5 Verify / commit / docs / checklist
- Tests added: resolver (resolved + unresolved list, nested `{DRONE.0.LINK}`, legacy alias still resolves), attachment path (set/missing/None), template get/save/reset merge.
- Commit: `feat(automations): slice 2 reflective placeholder resolver + per-CR templates + editor popup + test`
- Docs: PROGRESS.md, session-notes.md (new entry), PRD §16+§12, spec deviations.
- Checklist: autocomplete real values + kbd nav; CR switch no mix; per-CR save/reload; Test opens Outlook draft + logs; Reset clears; pre-Slice-2 templates still render; attachment renders; PD `[Setting]` deep-links.

---

## SLICE 3 — Rules Engine goal-driven + wire no-op + scope + conflict + pre-seeded + auto-reply dedup

### 3.1 Rule model extension (backward-compatible)
Extend stored rule dict (persisted under `settings.automation.rules_engine["rules"]` via `_RulesAdapter` app_web.py:1718):
```
Rule{id, name, goal: 'send_email'|'auto_reply'|'download_email'|'auto_update_status'|'send_teams',
     enabled, scope{type:'all'|'specific'|'filtered', cr_ids?, filter?},
     trigger{type, config}, action{template_id?, target_state?, condition?},
     is_pre_seeded, conditions? (legacy)}
```
Old rules (conditions-only) still evaluate; new fields optional.

### 3.2 Goal wizard (RulesActions.svelte)
`+ New Rule` → step 1 pick GOAL → step 2 form adapts (template picker for email goals; target CRState picker for update-status; message + target for teams). Mandatory **Applies to**: All CR / Specific CR (multi-select) / Filtered CR (filter builder on cr_state/drone_state/etc). Test + Logs per rule (Logs reuses existing `rules_get_logs`).

### 3.3 Wire 5 no-op handlers (automation_service.py:420-443)
Replace `self._noop(action)` with real delegation. Add ctor injection slots (extend `__init__` L115-138): `metadata_store`, `history_service`, `drone_service`, `download_service`. Wire in `app_web.py` factory.
- `_handle_update_cr_state` (L430) → metadata_store transition (validate via `core/rules.py` + `state_machine.py` legal transitions) + History append. Illegal transition → log + skip (no raise).
- `_handle_update_drone_state` (L435) → drone state transition + History.
- `_handle_download_email` (L420) → approval_polling/Outlook download path.
- `_handle_save_attachment` (L425) → save to project attachment folder.
- `_handle_append_history` (L440) → history service.

### 3.4 Conflict detection
On save/enable: scan enabled rules; 2 sharing `trigger.type + goal + scope` → WARNING (not block). Surface in rule list + form badge.

### 3.5 Pre-seeded rules (DISABLED by default)
Seed on first-run migration (in `_RulesAdapter._read` or app_web init): 3 rules `is_pre_seeded=True, enabled=False`:
- "Send UAT Acknowledgement" (send_email, ACK_UAT template)
- "Send LV Acknowledgement" (send_email, ACK_SOP template)
- "Auto Update CR State" (auto_update_status, no pattern → no-op per Slice 4 DEFAULT AMAN)
User toggles on explicitly. Idempotent seed (skip if exists by `is_pre_seeded + name`).

### 3.6 Auto Reply dedup
Auto-reply goal: auto-send ONLY when per-rule toggle `auto_send` ON (**default OFF**). Dedup: store send signature `(rule_id, cr_id, template_hash, ts)` in SQLite; skip if within rate-limit window (1h default). Prevents double-poll double-send.

### 3.7 Wire PD stubs
- PD `[+ Add Email/Teams Automation]` (ProjectDetails.svelte:1269, 1312) + CR `[Setting]` (:1280) → extend `onNavigateAutomations({tab:'rules', presetGoal, scope:{cr_id}})`.

### 3.8 Verify / commit / docs / checklist
- Tests: goal wizard rule shape persists; conflict warning fires; pre-seeded disabled + idempotent; wired handlers mutate fake store (update_cr_state legal + illegal transition); auto-reply dedup (fire twice in window → 1 send).
- Commit: `feat(automations): slice 3 goal-driven rules + wired actions + scope + conflict + preseeded + autoreply dedup`
- Checklist: goal wizard renders per-goal form; scope All/Specific/Filtered saved; conflict warning shows; pre-seeded appear disabled; Test/Logs per rule; PD add-buttons deep-link rules with preset.

---

## SLICE 4 — Auto Update CR State engine + Drone Ticket (stub) + Teams followup

### 4.1 Auto Update CR State engine (DEFAULT AMAN: no pattern = no-op)
New `services/cr_state_engine.py`:
- Patterns per project stored in `ProjectMetadata` (new field `auto_update_patterns: dict{from?, subject?, body?}` — regex/substring).
- On email received (from polling/download callback), match patterns against from/subject/body. Match + legal transition (`core/rules.py` validate) → transition CR state + History entry.
- **DEFAULT AMAN**: no patterns configured → engine NO-OP. Only user-set patterns trigger. No hard-coded transitions anywhere.
- Illegal transition → log + skip.
- PD `Auto Update CR State` toggle (Slice 1 flag) now drives engine when patterns set.

### 4.2 Create Drone Ticket — STAYS stub
Jenkins API deferred. Keep dev-stub message; no change beyond honest label.

### 4.3 Teams followup wired (ProjectDetails.svelte:1305-1307)
Replace 3 devStub buttons:
- `[Draft]` → `teams_service.preview_message(template-resolved per CR via Slice 2 resolver)`
- `[Send]` → ConfirmModal (irreversible outward) → `teams_service.send_message`
- `[Setting]` → deep-link Teams template editor (Slice 2 system, Teams variant)

### 4.4 Verify / commit / docs / checklist
- Tests: engine no-op without patterns; pattern match + legal transition → state changes + History; pattern match + illegal transition → skip; Teams followup preview/send bridge.
- Commit: `feat(automations): slice 4 auto-update CR state engine (pattern-gated) + teams followup wired`
- Checklist: toggle ON without patterns = nothing happens; set from/subject pattern + receive matching email → CR transitions + History; illegal pattern match → skipped + logged; Teams Draft previews resolved message; Teams Send confirms then sends; PD Teams Setting deep-links.

---

## SLICE 5 — Logs top-level menu + right-sidebar + retention

### 5.1 New table `automation_logs` (decided: clean separation)
`infrastructure/cache_db.py`: `CREATE TABLE automation_logs (id INTEGER PK, module TEXT, rule_id TEXT NULL, cr_id TEXT NULL, timestamp TEXT, event_type TEXT, detail TEXT)`. Helpers `append_log(row)`, `list_logs(module?, cr_id?, limit)`. **Keep `automation_rule_logs` untouched** for rules-only backward compat.
LogEntry logical model: `{id, module, rule_id?, cr_id?, timestamp, event_type, detail}`.

### 5.2 8th nav "Logs"
- `App.svelte`: `PageId` += `"logs"` (L18); `validPages` += `"logs"` (L78); render chain (L253-269) += Logs page + import.
- `TitleBar.svelte`: `navItems` += `{id:"logs",label:"Logs"}` (L29-37); `navIcons["logs"]=<svg>` (L123-131); keyboard shortcut entry (L225-233).
- New `Logs.svelte`: overview cards per module (Outlook/Teams/CR Automation/Rules Engine/All) + dropdown filter (module, cr_id, event_type, date range) + table.

### 5.3 Right-sidebar per rule/automation
PD + Rules `Logs` button → **right sidebar** (not modal/page): chronological log for that entity + Refresh/Export(JSON/CSV)/Clear. Rules reuse `rules_get_logs`; cross-module uses new `logs_get(module, cr_id?)` bridge.

### 5.4 Retention
Purge `automation_logs` rows for a CR when it reaches `CRState.FINISHED` or `CANCELED`. Hook in state transition service (where CR terminal transitions land).

### 5.5 Verify / commit / docs / checklist
- Tests: append_log/list_logs roundtrip; filter by module/cr_id; retention purge on terminal CR.
- Commit: `feat(automations): slice 5 logs top-level menu + right-sidebar + retention`
- Checklist: nav shows 8 items + Logs icon a11y; Logs page overview + filters work; PD/Rules Logs button opens right sidebar; Refresh/Export/Clear work; CR → FINISHED purges its logs.

---

## After Slice 5 — Final report
Per slice: files changed, commit hash, verify result. Combined manual checklist all 4 slices. Reminders:
- Build run → user **restart app** before testing.
- Merge to main waits user approval. Branch NOT deleted.

## DEFAULT AMAN summary (decisions I take autonomously, flagged in docs)
- Slice 2: legacy token aliases preserved; attachment missing file → None + warn (no fail).
- Slice 3: pre-seeded rules DISABLED; auto-reply auto_send OFF; conflict = warning only.
- Slice 4: **no patterns = no CR transition ever**; illegal transition = skip+log.
- Slice 5: retention purges only on FINISHED/CANCELED; rule_logs table untouched.

If anything outside these needs a call → STOP + ask.
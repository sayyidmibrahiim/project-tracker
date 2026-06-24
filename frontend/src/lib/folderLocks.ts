/**
 * Folder-state locking model (frontend mirror of PRD §9.5).
 *
 * This maps a project's `project_state` (Folder_State) to the set of high-risk
 * actions that are disabled in that state, so the UI can render disabled,
 * non-interactive controls with an accurate Disabled_State_Message.
 *
 * IMPORTANT: This is a UI affordance only. The Python backend (ProjectService /
 * filesystem guards) remains the authoritative guard — the frontend never
 * relies on this map for correctness, only for honest disabled-state messaging.
 *
 * Source of truth: PRD §9.5 "Folder State Locking Rules".
 */

/** Folder_State values, mirroring `core.enums.ProjectState`. */
export type FolderState =
  | "UAT_PREPARE"
  | "PROD_READY"
  | "IMPLEMENTED"
  | "POSTPONED"
  | "CANCELED";

/** High-risk actions that a Folder_State may lock. */
export type LockableAction =
  | "edit_metadata"
  | "rename_project"
  | "delete_project"
  | "subproject_delete"
  | "file_create"
  | "file_rename"
  | "file_delete"
  | "notes_edit"
  | "change_cr_drone_state"
  | "move_folder";

/**
 * Disabled actions per Folder_State (PRD §9.5).
 *
 * - UAT_PREPARE: fully editable — nothing disabled.
 * - PROD_READY (partial lock): metadata edit, rename, delete, and destructive
 *   file ops disabled; notes editing, CR/Drone progression, and folder moves
 *   to IMPLEMENTED/POSTPONED remain allowed.
 * - IMPLEMENTED (fully locked / read-only): everything disabled except viewing;
 *   notes are view-only (edits disabled).
 * - POSTPONED / CANCELED: editable per §9.5 (resume/reopen handled separately).
 */
const DISABLED_ACTIONS: Record<FolderState, ReadonlySet<LockableAction>> = {
  UAT_PREPARE: new Set<LockableAction>(),
  PROD_READY: new Set<LockableAction>([
    "edit_metadata",
    "rename_project",
    "delete_project",
    "subproject_delete",
    "file_create",
    "file_rename",
    "file_delete",
  ]),
  IMPLEMENTED: new Set<LockableAction>([
    "edit_metadata",
    "rename_project",
    "delete_project",
    "subproject_delete",
    "file_create",
    "file_rename",
    "file_delete",
    "notes_edit",
    "change_cr_drone_state",
    "move_folder",
  ]),
  POSTPONED: new Set<LockableAction>(),
  CANCELED: new Set<LockableAction>(),
};

/** Human-readable label for each Folder_State, used in lock messages. */
const STATE_LABEL: Record<FolderState, string> = {
  UAT_PREPARE: "UAT_PREPARE",
  PROD_READY: "PROD_READY",
  IMPLEMENTED: "IMPLEMENTED",
  POSTPONED: "POSTPONED",
  CANCELED: "CANCELED",
};

/** Return true when `state` is a recognized Folder_State. */
export function isFolderState(state: string): state is FolderState {
  return state in DISABLED_ACTIONS;
}

/**
 * True when `action` is disabled by the Folder_State locking rule for `state`.
 * Unknown states are treated as fully locked (fail-safe): every action disabled.
 */
export function isActionDisabled(state: string, action: LockableAction): boolean {
  if (!isFolderState(state)) {
    return true;
  }
  return DISABLED_ACTIONS[state].has(action);
}

/**
 * Disabled_State_Message naming the Folder_State locking rule that makes
 * `action` unavailable, or `null` when the action is allowed in `state`.
 */
export function lockReason(state: string, action: LockableAction): string | null {
  if (!isActionDisabled(state, action)) {
    return null;
  }
  if (!isFolderState(state)) {
    return `This action is unavailable: unknown project state "${state}".`;
  }
  const label = STATE_LABEL[state];
  if (state === "IMPLEMENTED") {
    if (action === "notes_edit") {
      return "Notes are view-only while the project is IMPLEMENTED (fully locked).";
    }
    return `This action is disabled while the project is ${label} (fully locked / read-only).`;
  }
  if (state === "PROD_READY") {
    return `This action is disabled while the project is ${label} (partial lock).`;
  }
  return `This action is disabled while the project is ${label}.`;
}

/** All actions disabled for a given Folder_State (useful for bulk UI gating). */
export function disabledActions(state: string): LockableAction[] {
  if (!isFolderState(state)) {
    return [
      "edit_metadata",
      "rename_project",
      "delete_project",
      "subproject_delete",
      "file_create",
      "file_rename",
      "file_delete",
      "notes_edit",
      "change_cr_drone_state",
      "move_folder",
    ];
  }
  return [...DISABLED_ACTIONS[state]];
}

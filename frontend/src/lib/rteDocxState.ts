// Pure state helpers for the DOCX pipeline editor mode (D-0012).
// Kept DOM-free so node --test can unit-test scheduling + label logic.

import type { RteExportState } from "./types";

/** What the editor shows for the derived-DOCX side of the pipeline. */
export type DocxExportDisplay = "idle" | "exporting" | "done" | "locked" | "failed";

/** Map a backend export state onto the editor display state. */
export function mapExportState(state: RteExportState | null): DocxExportDisplay {
  if (!state) return "idle";
  if (state.state === "running") return "exporting";
  if (state.state === "pending_retry") return "locked";
  if (state.state === "error") return "failed";
  if (
    state.last_exported_revision > 0 &&
    state.last_exported_revision >= state.revision &&
    !state.export_pending
  ) {
    return "done";
  }
  return "idle";
}

/** Status-bar label for a docx pipeline document. Falls back to the base
 *  source-save label when the export side has nothing to report. */
export function docxStatusLabel(display: DocxExportDisplay, baseLabel: string): string {
  switch (display) {
    case "exporting":
      return "Exporting DOCX…";
    case "done":
      return "DOCX saved";
    case "locked":
      return "DOCX locked — will retry";
    case "failed":
      return "Export failed — source safe";
    default:
      return baseLabel;
  }
}

/** Status-bar label while the idle-export countdown is ticking. */
export function docxCountdownLabel(secondsLeft: number): string {
  return `Saved — DOCX in ${Math.max(1, Math.round(secondsLeft))}s`;
}

/**
 * Idle-export scheduler (flow-tiptap §8): fires `onIdle` once after `idleMs`
 * of no `bump()` calls. Selection-only editor events must NOT bump it —
 * callers bump on content saves only.
 */
export class IdleExportScheduler {
  private timer: ReturnType<typeof setTimeout> | undefined;
  private readonly idleMs: number;
  private readonly onIdle: () => void;

  // Explicit assignments (not TS parameter properties): node --test runs this
  // file in strip-only mode, which cannot desugar parameter properties.
  constructor(idleMs: number, onIdle: () => void) {
    this.idleMs = idleMs;
    this.onIdle = onIdle;
  }

  bump(): void {
    this.cancel();
    this.timer = setTimeout(() => {
      this.timer = undefined;
      this.onIdle();
    }, this.idleMs);
  }

  cancel(): void {
    if (this.timer !== undefined) {
      clearTimeout(this.timer);
      this.timer = undefined;
    }
  }

  get pending(): boolean {
    return this.timer !== undefined;
  }
}

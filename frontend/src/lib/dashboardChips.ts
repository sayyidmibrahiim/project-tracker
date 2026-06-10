/**
 * Pure helpers for the Dashboard CR/Drone state cells.
 *
 * Kept out of the .svelte component so the state -> semantic-class mapping
 * is unit-testable with the Node test runner (no DOM / SSR needed).
 */

export type StateChip = "chip-approved" | "chip-pending" | "chip-negative" | "chip-neutral";

/**
 * Map a CR or Drone state label to a semantic colour-chip class.
 *
 * Accepts both the display form ("PENDING APPROVAL", "IN-PROGRESS") and the
 * enum form ("PENDING_APPROVAL", "IN_PROGRESS"); matching is case-insensitive
 * and separator-insensitive.
 *
 * - APPROVED              -> green   (chip-approved)
 * - PENDING * (any)       -> amber   (chip-pending)
 * - CANCELED / POSTPONED  -> red     (chip-negative)
 * - everything else       -> neutral (chip-neutral)
 */
export function stateChipClass(state: string | null | undefined): StateChip {
  const norm = (state ?? "").trim().toUpperCase().replace(/[\s-]+/g, "_");
  if (norm === "APPROVED") return "chip-approved";
  if (norm.startsWith("PENDING")) return "chip-pending";
  if (norm === "CANCELED" || norm === "POSTPONED") return "chip-negative";
  return "chip-neutral";
}

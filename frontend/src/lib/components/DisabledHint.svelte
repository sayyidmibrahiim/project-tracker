<script lang="ts">
  /**
   * Disabled_State_Message control (Requirement 3.5, 3.6).
   *
   * Renders a disabled, non-interactive control alongside an accurate message
   * that either names the Folder_State locking rule making the action
   * unavailable (Req 3.5) or indicates the capability is deferred / not yet
   * available (Req 3.6).
   *
   * This component never issues a bridge call and the control cannot be
   * activated by the user.
   */
  let {
    label,
    message,
    variant = "lock",
  }: {
    /** The action's control label (e.g. "Delete", "Rename"). */
    label: string;
    /** The Disabled_State_Message explaining why the action is unavailable. */
    message: string;
    /** "lock" = Folder_State lock; "deferred" = not yet implemented. */
    variant?: "lock" | "deferred";
  } = $props();
</script>

<span class="disabled-hint" data-variant={variant}>
  <button
    class="disabled-hint-btn"
    type="button"
    disabled
    aria-disabled="true"
    title={message}
  >
    {label}
  </button>
  <span class="disabled-hint-message" role="note">
    <span class="disabled-hint-icon" aria-hidden="true">
      {variant === "deferred" ? "⏳" : "🔒"}
    </span>
    {message}
  </span>
</span>

<style>
  .disabled-hint {
    display: inline-flex;
    align-items: center;
    gap: 8px;
    flex-wrap: wrap;
  }

  .disabled-hint-btn {
    height: 28px;
    border-radius: 5px;
    padding: 0 12px;
    background: #fff;
    border: 1px solid var(--color-input-border, #D7DCE2);
    color: var(--color-muted, #6B7280);
    font-weight: 800;
    font-size: 11px;
    white-space: nowrap;
    cursor: not-allowed;
    opacity: 0.55;
    flex: 0 0 auto;
    pointer-events: none;
  }

  .disabled-hint-message {
    display: inline-flex;
    align-items: center;
    gap: 5px;
    font-size: 10px;
    font-weight: 750;
    color: var(--color-muted, #6B7280);
    line-height: 1.4;
  }

  .disabled-hint[data-variant="deferred"] .disabled-hint-message {
    color: var(--color-muted-light, #9CA3AF);
  }

  .disabled-hint-icon {
    font-size: 10px;
  }
</style>

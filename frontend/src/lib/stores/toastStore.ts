export type ToastAction = { label: string; fn: () => void };
export type ToastType = "success" | "error" | "info" | "warning";

export interface ToastItem {
  id: string;
  message: string;
  type: ToastType;
  duration: number;
  action?: ToastAction;
}

type Listener = (toasts: ToastItem[]) => void;

let items: ToastItem[] = [];
let listeners = new Set<Listener>();
let counter = 0;

const MAX_VISIBLE = 3;

export function subscribe(fn: Listener): () => void {
  listeners.add(fn);
  fn(items);
  return () => listeners.delete(fn);
}

export function addToast(
  message: string,
  type: ToastType = "info",
  duration = 3000,
  action?: ToastAction,
): string {
  const id = `t${++counter}`;
  const item: ToastItem = { id, message, type, duration, action };
  items = [item, ...items].slice(0, MAX_VISIBLE);
  emit();
  if (duration > 0) setTimeout(() => removeToast(id), duration);
  return id;
}

export function removeToast(id: string) {
  items = items.filter((t) => t.id !== id);
  emit();
}

function emit() {
  listeners.forEach((fn) => fn(items));
}

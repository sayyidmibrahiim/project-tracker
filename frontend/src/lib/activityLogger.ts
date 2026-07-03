import type { BridgeResponse } from "./types";

type ActivityEvent = Record<string, unknown>;

const MAX_QUEUE = 200;
const BATCH_SIZE = 20;
const FLUSH_MS = 500;
let queue: ActivityEvent[] = [];
let timer: ReturnType<typeof setTimeout> | undefined;
let getPageRef: (() => string) | undefined;

function nowIso(): string {
  return new Date().toISOString();
}

function trimText(value: string | null | undefined, max = 80): string {
  const v = (value || "").replace(/\s+/g, " ").trim();
  return v.length > max ? `${v.slice(0, max)}…` : v;
}

function elementSummary(el: Element | null): Record<string, unknown> | null {
  if (!el) return null;
  const html = el as HTMLElement;
  return {
    tag: el.tagName,
    id: html.id || "",
    className: typeof html.className === "string" ? trimText(html.className, 120) : "",
    text: trimText(html.innerText || html.textContent || ""),
    ariaLabel: html.getAttribute("aria-label") || "",
    title: html.getAttribute("title") || "",
    role: html.getAttribute("role") || "",
  };
}

function importantContainer(el: Element | null): string {
  if (!el) return "";
  const selectors = [
    ".nav-tab", ".titlebar", ".titlebar-nav", ".pd-section", ".ne-root",
    ".ne-toolbar", ".app-header", ".notif-popover", ".help-popover", ".toast",
  ];
  for (const s of selectors) if (el.closest(s)) return s;
  return "";
}

function safeEventPayload(event: Event): ActivityEvent {
  const target = event.target instanceof Element ? event.target : null;
  const payload: ActivityEvent = {
    eventType: event.type,
    page: getPageRef?.() ?? "",
    target: elementSummary(target),
    container: importantContainer(target),
  };
  if (event instanceof PointerEvent) {
    payload.pointerType = event.pointerType;
    payload.button = event.button;
    payload.clientX = event.clientX;
    payload.clientY = event.clientY;
    payload.ctrlKey = event.ctrlKey;
    payload.shiftKey = event.shiftKey;
    payload.altKey = event.altKey;
    payload.metaKey = event.metaKey;
    payload.elementFromPoint = elementSummary(document.elementFromPoint(event.clientX, event.clientY));
  } else if (event instanceof MouseEvent) {
    payload.button = event.button;
    payload.clientX = event.clientX;
    payload.clientY = event.clientY;
    payload.elementFromPoint = elementSummary(document.elementFromPoint(event.clientX, event.clientY));
  } else if (event instanceof KeyboardEvent) {
    payload.key = event.key;
    payload.code = event.code;
    payload.ctrlKey = event.ctrlKey;
    payload.shiftKey = event.shiftKey;
    payload.altKey = event.altKey;
    payload.metaKey = event.metaKey;
  }
  return payload;
}

async function sendRaw(event: ActivityEvent): Promise<void> {
  try {
    const api = window.pywebview?.api as Record<string, unknown> | undefined;
    const fn = api?.frontend_log;
    if (typeof fn !== "function") return;
    await (fn as (event: ActivityEvent) => Promise<BridgeResponse<{ logged: boolean }>>)(event);
  } catch {
    // Logging must never break app behavior.
  }
}

function scheduleFlush(): void {
  if (timer) return;
  timer = setTimeout(() => {
    timer = undefined;
    void flushActivityLogs();
  }, FLUSH_MS);
}

export function logActivity(event: ActivityEvent): void {
  try {
    queue.push({ ts: nowIso(), ...event });
    if (queue.length > MAX_QUEUE) queue = queue.slice(queue.length - MAX_QUEUE);
    if (queue.length >= BATCH_SIZE) void flushActivityLogs();
    else scheduleFlush();
  } catch {
    // no-op
  }
}

export async function flushActivityLogs(): Promise<void> {
  const batch = queue.splice(0, BATCH_SIZE);
  if (!batch.length) return;
  await sendRaw({ ts: nowIso(), source: "frontend.batch", events: batch });
  if (queue.length) scheduleFlush();
}

export function logBridgeCall(event: ActivityEvent): void {
  logActivity({ source: "bridge.callBridge", kind: "bridge", ...event });
}

export function installGlobalActivityLogging(getPage: () => string): () => void {
  getPageRef = getPage;
  const capture = (event: Event) => logActivity({ source: "App.globalCapture", kind: "ui", ...safeEventPayload(event) });
  const error = (event: ErrorEvent) => logActivity({
    source: "window.error",
    kind: "error",
    message: event.message,
    filename: event.filename,
    lineno: event.lineno,
    colno: event.colno,
    error: event.error instanceof Error ? { name: event.error.name, message: event.error.message, stack: event.error.stack } : String(event.error),
  });
  const rejection = (event: PromiseRejectionEvent) => logActivity({
    source: "window.unhandledrejection",
    kind: "error",
    reason: event.reason instanceof Error ? { name: event.reason.name, message: event.reason.message, stack: event.reason.stack } : String(event.reason),
  });
  window.addEventListener("pointerdown", capture, true);
  window.addEventListener("click", capture, true);
  window.addEventListener("keydown", capture, true);
  window.addEventListener("change", capture, true);
  window.addEventListener("error", error);
  window.addEventListener("unhandledrejection", rejection);
  logActivity({ source: "activityLogger", kind: "lifecycle", event: "installed", page: getPage() });
  return () => {
    window.removeEventListener("pointerdown", capture, true);
    window.removeEventListener("click", capture, true);
    window.removeEventListener("keydown", capture, true);
    window.removeEventListener("change", capture, true);
    window.removeEventListener("error", error);
    window.removeEventListener("unhandledrejection", rejection);
    void flushActivityLogs();
  };
}

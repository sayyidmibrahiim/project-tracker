/**
 * DEV-ONLY mock of the pywebview bridge for browser preview (Tailscale/localhost).
 *
 * Installs a fake `window.pywebview.api` so the Svelte UI renders with sample
 * data outside the desktop shell. Guarded behind `import.meta.env.DEV` at the
 * call site in main.ts, so this is tree-shaken out of the production build and
 * never ships. NOT a contract — only enough surface to preview the Dashboard.
 */

type Resp<T> = { ok: true; data: T; error: null } | { ok: false; data: null; error: { code: string; message: string } };
const ok = <T>(data: T): Resp<T> => ({ ok: true, data, error: null });

const SAMPLE_PROJECTS = [
  {
    project_path: "C:\\\\Projects\\\\2026\\\\UAT_PREPARE\\\\SOP CR",
    project_name: "SOP CR",
    project_state: "UAT_PREPARE",
    year: "2026",
    cr_number: "CR202604209900114",
    cr_link: "https://drone.local/cr/CR202604209900114",
    cr_state: "PENDING APPROVAL",
    start_datetime: "2026-05-22T00:00:00+07:00",
    end_datetime: "2026-06-10T00:00:00+07:00",
    drone_ticket_count: 4,
    drone_tickets: [
      { subfolder_name: "sub project a", drone_ticket: "D-SSIDBI-159", drone_link: "https://drone.local/ticket/DRN-001", drone_state: "APPROVED", owner: "lana" },
      { subfolder_name: "sub project b", drone_ticket: "D-SSIDBI-160", drone_link: "https://drone.local/ticket/DRN-002", drone_state: "PENDING APPROVAL", owner: "lana" },
      { subfolder_name: "sub project c", drone_ticket: "D-SSIDBI-161", drone_link: "https://drone.local/ticket/DRN-003", drone_state: "UAT", owner: "rio" },
      { subfolder_name: "sub project d", drone_ticket: "D-SSIDBI-162", drone_link: "https://drone.local/ticket/DRN-004", drone_state: "CANCELED", owner: "rio" },
    ],
  },
  {
    project_path: "C:\\\\Projects\\\\2026\\\\PROD_READY\\\\project_tracker",
    project_name: "project_tracker with a deliberately very long name to show ellipsis truncation",
    project_state: "PROD_READY",
    year: "2026",
    cr_number: "CR202605110023001",
    cr_link: "https://drone.local/cr/CR202605110023001",
    cr_state: "APPROVED",
    start_datetime: "2026-06-15T09:00:00+07:00",
    end_datetime: "2026-06-20T17:00:00+07:00",
    drone_ticket_count: 0,
    drone_tickets: [],
  },
  {
    project_path: "C:\\\\Projects\\\\2026\\\\CANCELED\\\\legacy migration",
    project_name: "legacy migration",
    project_state: "CANCELED",
    year: "2026",
    cr_number: "",
    cr_link: "",
    cr_state: "CANCELED",
    start_datetime: null,
    end_datetime: null,
    drone_ticket_count: 0,
    drone_tickets: [],
  },
  {
    project_path: "C:\\\\Projects\\\\2026\\\\POSTPONED\\\\q3 rollout",
    project_name: "q3 rollout",
    project_state: "POSTPONED",
    year: "2026",
    cr_number: "CR202604010099002",
    cr_link: "https://drone.local/cr/CR202604010099002",
    cr_state: "POSTPONED",
    start_datetime: "2026-07-01T09:00:00+07:00",
    end_datetime: "2026-07-05T17:00:00+07:00",
    drone_ticket_count: 1,
    drone_tickets: [
      { subfolder_name: "rollout-a", drone_ticket: "D-SSIDBI-201", drone_link: "https://drone.local/ticket/DRN-201", drone_state: "PENDING APPROVAL", owner: "lana" },
    ],
  },
];

const SAMPLE_SUMMARY = {
  total_projects: 4,
  by_project_state: { UAT_PREPARE: 1, PROD_READY: 1, IMPLEMENTED: 0, POSTPONED: 1, CANCELED: 1 },
  by_cr_state: { "PENDING APPROVAL": 1, APPROVED: 1, POSTPONED: 1, CANCELED: 1 },
  by_t10_status: {},
  total_drone_tickets: 5,
};

export function installMockBridge(): void {
  const api: Record<string, (...args: unknown[]) => unknown> = {
    dashboard_data: () => ok({ projects: SAMPLE_PROJECTS, summary: SAMPLE_SUMMARY }),
    year_list: () => ok(["2026", "2025", "2024"]),
    settings_get: () => ok({ root_folder: "C:\\\\Projects" }),
    notification_list: () => ok([]),
    poll_events: () => ok([]),
    // Inline edits / transitions: acknowledge so the UI clears its spinner.
    cr_update_state: () => ok({ project_path: "", project_state: "", cr_state: "" }),
    drone_update: () => ok({ project_path: "", drone_ticket_count: 0 }),
    cr_update_link: () => ok({ project_path: "" }),
    project_open_folder: () => ok({}),
    folder_open: () => ok({}),
    folder_reopen: () => ok({ project_path: "", project_state: "UAT_PREPARE" }),
    project_delete: () => ok({}),
    year_create: () => ok("2027"),
  };
  (window as unknown as { pywebview: { api: typeof api } }).pywebview = { api };
}

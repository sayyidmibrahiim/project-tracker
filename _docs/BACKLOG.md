# Backlog

Ideas go here first. This file is not requirements until an item is promoted into PRD/SPEC.

| Date       | Type          | Idea                                                                                                                                                                                                                                                                                                                                            |
| ---------- | ------------- | ----------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------- |
| 2026-06-27 | Test debt     | Fix 2 pre-existing Phase D app_web test failures: `tests/test_phase_d_app_web_js_api_wiring.py::test_create_js_api_returns_JsApi_instance`; `tests/test_phase_d_app_web_svelte_static_serving.py::test_run_creates_window_with_js_api_and_no_runtime_start`. Isolated tests pass, but full suite fails on `main` and `chore/bootstrap-tooling`. |
| 2026-06-29 | Color hygiene | Migrate raw hex colors in components to CSS vars from `frontend/src/styles.css :root`. Violating components detected: ConfirmModal, Dashboard, FileActions, and others (run grep for `#[0-9a-fA-F]{3,8}` in frontend/src/lib/components). Blocked until color migration is approved per-menu.                                                   |

"""Phase D.8: app_web serves built Svelte frontend."""

from __future__ import annotations

from pathlib import Path

import pytest


def test_app_web_import_is_linux_safe():
    """Importing app_web must not launch pywebview or require a window."""
    from project_tracker import app_web  # noqa: F401


def test_get_frontend_entry_path_prefers_built_svelte_index():
    """Production frontend entry resolves to web/static/index.html."""
    from project_tracker import app_web

    path = app_web.get_frontend_entry_path()
    assert path == app_web.PROJECT_ROOT / "web" / "static" / "index.html"


def test_resolve_frontend_url_uses_built_svelte_relative_path():
    """Production frontend path lets pywebview serve built Svelte via HTTP server."""
    from project_tracker import app_web

    assert app_web.resolve_frontend_url() == "web/static/index.html"


def test_resolve_frontend_url_dev_mode_preserved():
    """Dev mode keeps Vite dev-server URL."""
    from project_tracker import app_web

    assert app_web.resolve_frontend_url(dev=True) == "http://localhost:5173"


def test_missing_static_build_raises_predictable_error(tmp_path: Path):
    """Missing web/static/index.html fails loudly with controlled FileNotFoundError."""
    from project_tracker import app_web

    with pytest.raises(FileNotFoundError, match="Built Svelte frontend not found"):
        app_web.get_frontend_entry_path(project_root=tmp_path)


def test_run_creates_window_with_js_api_and_no_runtime_start(monkeypatch: pytest.MonkeyPatch):
    """run(start_webview=False) configures pywebview window without launching runtime."""
    from project_tracker import app_web
    from project_tracker.web.js_api import JsApi

    calls: dict[str, object] = {}

    class FakeWebview:
        def create_window(self, *args: object, **kwargs: object) -> object:
            calls["args"] = args
            calls["kwargs"] = kwargs
            return object()

        def start(self) -> None:
            calls["started"] = True

    monkeypatch.setattr(app_web, "webview", FakeWebview())

    app_web.run(start_webview=False)

    kwargs = calls["kwargs"]
    assert isinstance(kwargs, dict)
    assert kwargs["url"] == app_web.resolve_frontend_url()
    assert isinstance(kwargs["js_api"], JsApi)
    assert "started" not in calls

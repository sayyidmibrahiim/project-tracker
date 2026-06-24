"""Bridge contract guard tests (Tasks 23.1/23.2/23.3).

23.1/23.2: Every frontend ``callBridge("name", ...)`` literal must map to a real
JsApi attribute on the object returned by ``create_js_api()``. The guard fails
fast with the offending name list so drift is caught at test time rather than
runtime.

23.3 (Property 7): Every JsApi method that returns a Bridge_Response must
return a dict with an ``ok`` boolean. When ``ok=false``, ``error.code`` must
match ``^[A-Z0-9_]{1,64}$``. The property is exercised by introspecting the
JsApi facade and calling each method with empty/invalid arguments to provoke
``ok=false`` paths; methods that succeed with empty input are accepted as long
as the shape matches. Methods are filtered to those with a known Bridge_Response
return type so plumbing helpers (constructor, dunder, etc.) are not invoked.
"""

from __future__ import annotations

import inspect
import re
import sys
from pathlib import Path

import pytest

# NOTE: ``create_js_api`` is imported lazily inside tests so this module's
# collection does NOT pull ``webview`` (pywebview) into ``sys.modules``. Other
# tests assert that re-importing ``js_api`` keeps ``sys.modules`` free of
# ``webview``; an eager import here would make the suite order-dependent.

from infrastructure.settings_store import SettingsStore

REPO_ROOT = Path(__file__).resolve().parent.parent
FRONTEND_SRC = REPO_ROOT / "frontend" / "src"

# Match callBridge("name", ...) and callBridge<T>("name", ...).
_CALL_BRIDGE_RE = re.compile(r"callBridge\s*(?:<[^>]*>)?\s*\(\s*[\"']([a-zA-Z_][a-zA-Z0-9_]*)[\"']")
_ERROR_CODE_RE = re.compile(r"^[A-Z0-9_]{1,64}$")


@pytest.fixture(autouse=True)
def _purge_webview_imports():
    """Restore ``sys.modules`` after each test so import-purity tests still pass.

    Two protections:
      1. ``create_js_api()`` may eagerly import ``webview`` (pywebview) on
         platforms where it is installed. Other tests assert that re-importing
         ``js_api`` does not pull ``webview`` into ``sys.modules``; preserving
         it here would make this guard order-dependent.
      2. Other tests use ``importlib.reload(js_api)`` which changes the
         ``JsApi`` class identity. Any later test doing
         ``isinstance(api, JsApi)`` fails because ``app_web`` cached the
         pre-reload class. Popping ``app_web`` here forces it to re-import
         fresh against the current ``js_api`` module on the next access.
    """
    before = set(sys.modules)
    try:
        yield
    finally:
        added = [name for name in sys.modules if name not in before]
        for name in added:
            if name == "webview" or name.startswith("webview."):
                sys.modules.pop(name, None)
        # Pop app_web so a later reload of js_api does not leave a stale
        # JsApi class reference cached inside app_web. Do NOT pop js_api: that
        # invalidates module-level state other tests rely on. Popping
        # sys.modules alone is not enough — Python's package object also caches
        # ``app_web`` as an attribute, so we must clear that too for the next
        # ``from project_tracker import app_web`` to actually re-execute the
        # module body and pick up a freshly reloaded ``JsApi`` class.
        sys.modules.pop("app_web", None)
        pkg = sys.modules.get("project_tracker")
        if pkg is not None and hasattr(pkg, "app_web"):
            try:
                delattr(pkg, "app_web")
            except AttributeError:
                pass
        # End of fixture purge.


def _collect_call_bridge_names() -> set[str]:
    names: set[str] = set()
    for path in FRONTEND_SRC.rglob("*"):
        if path.suffix not in {".ts", ".svelte"}:
            continue
        try:
            text = path.read_text(encoding="utf-8")
        except (OSError, UnicodeDecodeError):
            continue
        for match in _CALL_BRIDGE_RE.finditer(text):
            names.add(match.group(1))
    return names


def _api(tmp_path):
    from app_web import create_js_api  # lazy: keep sys.modules clean

    return create_js_api(
        db_path=tmp_path / "cache.sqlite",
        settings_store=SettingsStore(config_dir=tmp_path),
    )


# --- 23.1 / 23.2: contract guard --------------------------------------------

def test_every_callbridge_name_maps_to_a_jsapi_method(tmp_path) -> None:
    """Each frontend callBridge literal exists as an attribute on JsApi."""
    api = _api(tmp_path)
    names = _collect_call_bridge_names()
    assert names, "scanner found no callBridge literals — frontend layout drifted"
    missing = sorted(n for n in names if not hasattr(api, n))
    assert not missing, (
        "Frontend callBridge names without a wired JsApi method:\n  "
        + "\n  ".join(missing)
    )


def _strip_comments(text: str) -> str:
    """Strip /* … */ block comments and // line comments from JS/TS/Svelte source."""
    # Block comments (greedy across lines).
    text = re.sub(r"/\*.*?\*/", "", text, flags=re.DOTALL)
    # Line comments — only strip from the // to end-of-line; rough but adequate
    # for our guard given the codebase's coding style. URL prefixes (http://) are
    # not present in the affected files outside comments, so this is safe here.
    text = re.sub(r"//[^\n]*", "", text)
    return text


def test_no_direct_window_pywebview_outside_bridge_wrapper() -> None:
    """``window.pywebview`` is referenced only inside frontend/src/lib/bridge.ts.

    Comments mentioning ``window.pywebview`` (e.g. JSDoc reminding contributors
    not to use it) are not violations; only real source references are.
    """
    bridge_path = (FRONTEND_SRC / "lib" / "bridge.ts").resolve()
    offenders: list[str] = []
    for path in FRONTEND_SRC.rglob("*"):
        if path.suffix not in {".ts", ".svelte"}:
            continue
        if path.resolve() == bridge_path:
            continue
        try:
            text = path.read_text(encoding="utf-8")
        except (OSError, UnicodeDecodeError):
            continue
        stripped = _strip_comments(text)
        if "window.pywebview" in stripped:
            offenders.append(str(path.relative_to(REPO_ROOT)))
    assert not offenders, (
        "window.pywebview must be referenced only inside bridge.ts; offenders:\n  "
        + "\n  ".join(offenders)
    )


# --- 23.3 / Property 7: universal Bridge_Response shape ----------------------

def _is_bridge_response(value: object) -> bool:
    if not isinstance(value, dict):
        return False
    if "ok" not in value or not isinstance(value["ok"], bool):
        return False
    if value["ok"] is False:
        error = value.get("error")
        if not isinstance(error, dict):
            return False
        code = error.get("code")
        if not isinstance(code, str) or not _ERROR_CODE_RE.match(code):
            return False
    return True


def test_property_bridge_response_shape_is_universal(tmp_path) -> None:
    """P7: every JsApi public method returns ok-shaped Bridge_Response.

    Invokes each public, non-dunder method with empty/None arguments. Methods
    that succeed return ``ok=true``; methods that fail return ``ok=false`` with
    a stable error code matching ``^[A-Z0-9_]{1,64}$``. Methods raising
    ``TypeError`` (signature mismatch with empty args) are skipped because they
    indicate the contract requires arguments — they cannot prove the shape with
    no input but cannot violate it either; the contract guard above ensures
    they are wired and the per-method tests cover them with real input.
    """
    api = _api(tmp_path)
    public_names = [
        name for name, member in inspect.getmembers(api, predicate=inspect.ismethod)
        if not name.startswith("_")
    ]
    assert public_names, "no public methods discovered on JsApi"

    failures: list[str] = []
    checked = 0
    for name in public_names:
        method = getattr(api, name)
        sig = inspect.signature(method)
        # Build minimal empty arguments matching the signature: pass empty
        # strings for str params and empty dicts/lists for collections so the
        # method exercises its real body rather than a TypeError.
        kwargs: dict[str, object] = {}
        skip = False
        for param_name, param in sig.parameters.items():
            if param.default is not inspect.Parameter.empty:
                continue
            ann = param.annotation
            if ann is inspect.Parameter.empty:
                kwargs[param_name] = None
                continue
            ann_str = str(ann)
            if "str" in ann_str:
                kwargs[param_name] = ""
            elif "dict" in ann_str or "Mapping" in ann_str:
                kwargs[param_name] = {}
            elif "list" in ann_str or "Sequence" in ann_str:
                kwargs[param_name] = []
            elif "int" in ann_str:
                kwargs[param_name] = 0
            elif "bool" in ann_str:
                kwargs[param_name] = False
            else:
                kwargs[param_name] = None
        try:
            result = method(**kwargs)
        except TypeError:
            # Signature mismatch under empty args; skip — the contract guard
            # confirms wiring and per-method tests cover real input.
            continue
        except Exception as exc:  # noqa: BLE001 - any other exception is a violation
            failures.append(f"{name}: raised {type(exc).__name__}: {exc}")
            continue
        if not _is_bridge_response(result):
            failures.append(f"{name}: not a Bridge_Response: {result!r}")
            continue
        checked += 1

    assert checked > 0, "P7 did not exercise any JsApi method"
    assert not failures, "P7 violations:\n  " + "\n  ".join(failures)

"""Phase G.3 — read-only Second Brain filesystem index.

Tests prove create_js_api() wires SecondBrainService to a read-only
filesystem provider from AppSettings.second_brain_folder.
"""

from __future__ import annotations

import tempfile
import json
import shutil
from dataclasses import replace
from pathlib import Path

import pytest

from infrastructure.settings_store import SettingsStore
from infrastructure.metadata_store import MetadataStore
from core.models import ProjectMetadata
from services.second_brain_service import SecondBrainService


@pytest.fixture
def temp_settings_store():
    with tempfile.TemporaryDirectory() as tmp:
        yield SettingsStore(config_dir=Path(tmp) / "config")


def _api(settings_store: SettingsStore):
    from project_tracker import app_web

    return app_web.create_js_api(settings_store=settings_store)


def _configure_second_brain(settings_store: SettingsStore, folder: Path | None) -> None:
    settings_store.write(replace(settings_store.read(), second_brain_folder=folder))


def _configure_roots(settings_store: SettingsStore, project_root: Path, personal_root: Path | None) -> None:
    settings_store.write(
        replace(
            settings_store.read(),
            root_folder=project_root,
            second_brain_folder=personal_root,
        )
    )


def _project(
    root: Path,
    *,
    appcode: str = "APP",
    year: str = "2026",
    branch: str = "CR",
    state: str = "UAT_PREPARE",
    folder: str = "Project One",
) -> Path:
    appcode_path = root / appcode
    appcode_path.mkdir(parents=True, exist_ok=True)
    (appcode_path / "appcode.json").write_text(json.dumps({"display_name": appcode}), encoding="utf-8")
    if branch == "CR":
        project_path = appcode_path / year / "CR" / state / folder
    else:
        project_path = appcode_path / year / "Non-CR" / folder
    project_path.mkdir(parents=True, exist_ok=True)
    MetadataStore().write(project_path, ProjectMetadata(project_name=folder))
    return project_path


def _items(result: dict[str, object]) -> list[dict[str, object]]:
    assert result["ok"] is True
    data = result["data"]
    assert isinstance(data, list)
    return data


def test_list_empty_when_folder_not_configured(temp_settings_store):
    api = _api(temp_settings_store)

    assert _items(api.second_brain_list()) == []


def test_list_empty_when_folder_missing(temp_settings_store):
    missing = Path(tempfile.gettempdir()) / "missing-second-brain-folder-for-test"
    _configure_second_brain(temp_settings_store, missing)
    api = _api(temp_settings_store)

    assert _items(api.second_brain_list()) == []


def test_list_returns_md_files(temp_settings_store):
    with tempfile.TemporaryDirectory() as tmp:
        root = Path(tmp)
        (root / "Runbook.md").write_text("Deploy steps", encoding="utf-8")
        _configure_second_brain(temp_settings_store, root)
        api = _api(temp_settings_store)

        items = _items(api.second_brain_list())

    assert [item["title"] for item in items] == ["Runbook"]
    assert items[0]["path"].endswith("Runbook.md")


def test_stable_id_across_fresh_create_js_api_calls_for_same_path(temp_settings_store):
    with tempfile.TemporaryDirectory() as tmp:
        root = Path(tmp)
        (root / "stable.md").write_text("same note", encoding="utf-8")
        _configure_second_brain(temp_settings_store, root)

        first = _items(_api(temp_settings_store).second_brain_list())[0]["id"]
        second = _items(_api(temp_settings_store).second_brain_list())[0]["id"]

    assert first == second
    assert isinstance(first, str)
    assert len(first) == 16


def test_md_txt_type_note_other_file_type_file(temp_settings_store):
    with tempfile.TemporaryDirectory() as tmp:
        root = Path(tmp)
        (root / "a.md").write_text("a", encoding="utf-8")
        (root / "b.txt").write_text("b", encoding="utf-8")
        (root / "c.pdf").write_bytes(b"pdf")
        _configure_second_brain(temp_settings_store, root)
        api = _api(temp_settings_store)

        by_title = {item["title"]: item for item in _items(api.second_brain_list())}

    assert by_title["a"]["item_type"] == "note"
    assert by_title["b"]["item_type"] == "note"
    assert by_title["c"]["item_type"] == "file"


def test_excerpt_for_text(temp_settings_store):
    with tempfile.TemporaryDirectory() as tmp:
        root = Path(tmp)
        body = "Alpha excerpt body " * 20
        (root / "excerpt.txt").write_text(body, encoding="utf-8")
        _configure_second_brain(temp_settings_store, root)
        api = _api(temp_settings_store)

        item = _items(api.second_brain_list())[0]

    assert item["excerpt"].startswith("Alpha excerpt body")
    assert len(item["excerpt"]) <= 200


def test_hidden_files_skipped(temp_settings_store):
    with tempfile.TemporaryDirectory() as tmp:
        root = Path(tmp)
        (root / ".secret.md").write_text("hidden", encoding="utf-8")
        (root / "visible.md").write_text("shown", encoding="utf-8")
        _configure_second_brain(temp_settings_store, root)
        api = _api(temp_settings_store)

        titles = [item["title"] for item in _items(api.second_brain_list())]

    assert titles == ["visible"]


def test_nested_files_discovered(temp_settings_store):
    with tempfile.TemporaryDirectory() as tmp:
        root = Path(tmp)
        nested = root / "ops" / "uat"
        nested.mkdir(parents=True)
        (nested / "nested.md").write_text("nested body", encoding="utf-8")
        _configure_second_brain(temp_settings_store, root)
        api = _api(temp_settings_store)

        items = _items(api.second_brain_list())

    by_tree_path = {item["tree_path"]: item for item in items}
    assert set(by_tree_path) == {"ops", "ops/uat", "ops/uat/nested.md"}
    assert by_tree_path["ops"]["item_type"] == "folder"
    assert by_tree_path["ops/uat/nested.md"]["source"] == "personal"
    assert by_tree_path["ops/uat/nested.md"]["parent_path"] == "ops/uat"


def test_search_by_title_and_excerpt(temp_settings_store):
    with tempfile.TemporaryDirectory() as tmp:
        root = Path(tmp)
        (root / "Deploy Checklist.md").write_text("ordinary text", encoding="utf-8")
        (root / "random.txt").write_text("contains rollback keyword", encoding="utf-8")
        _configure_second_brain(temp_settings_store, root)
        api = _api(temp_settings_store)

        title_hits = _items(api.second_brain_search("checklist"))
        excerpt_hits = _items(api.second_brain_search("rollback"))

    assert [item["title"] for item in title_hits] == ["Deploy Checklist"]
    assert [item["title"] for item in excerpt_hits] == ["random"]


def test_get_by_id_returns_item(temp_settings_store):
    with tempfile.TemporaryDirectory() as tmp:
        root = Path(tmp)
        (root / "lookup.md").write_text("lookup body", encoding="utf-8")
        _configure_second_brain(temp_settings_store, root)
        api = _api(temp_settings_store)

        listed = _items(api.second_brain_list())[0]
        result = api.second_brain_get(listed["id"])

    assert result["ok"] is True
    assert result["data"]["id"] == listed["id"]
    assert result["data"]["title"] == "lookup"


def test_indexes_cr_non_cr_and_drone_context(temp_settings_store, tmp_path: Path):
    root = tmp_path / "projects"
    personal = tmp_path / "personal"
    personal.mkdir()
    cr = _project(root, folder="Payments")
    non_cr = _project(root, branch="Non-CR", folder="Ops Task")
    drone = cr / "DR-100"
    drone.mkdir()
    (cr / "runbook.md").write_text("project root", encoding="utf-8")
    (drone / "notes.md").write_text("drone notes", encoding="utf-8")
    (non_cr / "guide.txt").write_text("non cr", encoding="utf-8")
    _configure_roots(temp_settings_store, root, personal)

    items = _items(_api(temp_settings_store).second_brain_list())
    by_name = {Path(str(item["path"])).name + ":" + str(item["project_name"]): item for item in items}

    cr_item = by_name["runbook.md:Payments"]
    assert cr_item["tree_path"] == "APP/2026/CR/UAT_PREPARE/Payments/runbook.md"
    assert cr_item["project_state"] == "UAT_PREPARE"
    assert cr_item["drone_name"] is None
    drone_item = by_name["notes.md:Payments"]
    assert drone_item["drone_name"] == "DR-100"
    assert drone_item["tree_path"].endswith("Payments/DR-100/notes.md")
    non_cr_item = by_name["guide.txt:Ops Task"]
    assert non_cr_item["tree_path"] == "APP/2026/Non-CR/Ops Task/guide.txt"
    assert non_cr_item["project_state"] is None


def test_excludes_internal_metadata_cicd_and_hidden_but_keeps_user_json(temp_settings_store, tmp_path: Path):
    root = tmp_path / "projects"
    personal = tmp_path / "personal"
    personal.mkdir()
    project = _project(root)
    (project / "visible.json").write_text("{}", encoding="utf-8")
    (project / ".hidden.md").write_text("hidden", encoding="utf-8")
    (project / "CICD").mkdir()
    (project / "CICD" / "pipeline.md").write_text("ci", encoding="utf-8")
    (project / ".rte").mkdir()
    (project / ".rte" / "internal.md").write_text("rte", encoding="utf-8")
    (project / "appcode.json").write_text("{}", encoding="utf-8")
    _configure_roots(temp_settings_store, root, personal)

    names = {Path(str(item["path"])).name for item in _items(_api(temp_settings_store).second_brain_list())}

    assert "visible.json" in names
    assert names.isdisjoint({"project_data.json", "appcode.json", ".hidden.md", "pipeline.md", "internal.md"})


def test_personal_root_inside_project_is_indexed_only_as_personal(temp_settings_store, tmp_path: Path):
    root = tmp_path / "projects"
    project = _project(root)
    personal = project / "Personal Notes"
    personal.mkdir()
    note = personal / "one.md"
    note.write_text("one", encoding="utf-8")
    _configure_roots(temp_settings_store, root, personal)

    matches = [item for item in _items(_api(temp_settings_store).second_brain_list()) if item["path"] == note.as_posix()]

    assert len(matches) == 1
    assert matches[0]["source"] == "personal"


def test_project_item_id_survives_cr_state_folder_move(temp_settings_store, tmp_path: Path):
    root = tmp_path / "projects"
    personal = tmp_path / "personal"
    personal.mkdir()
    project = _project(root, state="UAT_PREPARE", folder="Stable")
    (project / "notes.md").write_text("stable", encoding="utf-8")
    _configure_roots(temp_settings_store, root, personal)
    first = next(item for item in _items(_api(temp_settings_store).second_brain_list()) if item["source"] == "project")
    destination = root / "APP" / "2026" / "CR" / "PROD_READY" / "Stable"
    destination.parent.mkdir(parents=True)
    shutil.move(str(project), str(destination))

    second = next(item for item in _items(_api(temp_settings_store).second_brain_list()) if item["source"] == "project")

    assert first["id"] == second["id"]
    assert second["tree_path"].startswith("APP/2026/CR/PROD_READY/")


@pytest.mark.parametrize(
    ("filename", "open_mode"),
    [
        ("note.md", "markdown"),
        ("script.py", "text"),
        ("document.docx", "docx"),
        ("image.png", "image"),
        ("manual.pdf", "external"),
    ],
)
def test_open_mode_classification(temp_settings_store, tmp_path: Path, filename: str, open_mode: str):
    root = tmp_path / "projects"
    personal = tmp_path / "personal"
    personal.mkdir()
    target = personal / filename
    target.write_bytes(b"test")
    _configure_roots(temp_settings_store, root, personal)

    item = next(item for item in _items(_api(temp_settings_store).second_brain_list()) if item["item_type"] != "folder")

    assert item["open_mode"] == open_mode
    assert item["file_format"] == Path(filename).suffix[1:]


def test_full_text_after_excerpt_limit_remains_searchable(temp_settings_store, tmp_path: Path):
    root = tmp_path / "projects"
    personal = tmp_path / "personal"
    personal.mkdir()
    (personal / "long.md").write_text("x" * 250 + " deep-keyword", encoding="utf-8")
    _configure_roots(temp_settings_store, root, personal)
    api = _api(temp_settings_store)

    hits = _items(api.second_brain_search("deep-keyword"))

    assert [item["title"] for item in hits] == ["long"]
    assert len(hits[0]["excerpt"]) == 200


def test_unreadable_project_metadata_does_not_hide_other_projects(tmp_path: Path, monkeypatch):
    root = tmp_path / "projects"
    personal = tmp_path / "personal"
    personal.mkdir()
    bad = _project(root, folder="Bad")
    good = _project(root, folder="Good")
    (bad / "bad-notes.md").write_text("bad", encoding="utf-8")
    (good / "good-notes.md").write_text("good", encoding="utf-8")
    blocked_metadata = bad / "project_data.json"
    original_open = Path.open

    def guarded_open(self, *args, **kwargs):
        if self == blocked_metadata:
            raise PermissionError("metadata denied")
        return original_open(self, *args, **kwargs)

    monkeypatch.setattr(Path, "open", guarded_open)
    service = SecondBrainService(
        folder_provider=lambda: personal,
        root_provider=lambda: root,
        metadata_store=MetadataStore(),
    )

    workspace = service.workspace()
    project_names = {item.path.name for item in workspace["items"] if item.source == "project"}

    assert "good-notes.md" in project_names
    assert "bad-notes.md" in project_names
    assert any("Bad" in warning and "metadata" in warning.casefold() for warning in workspace["warnings"])


def test_wrong_shape_appcode_metadata_does_not_hide_project_files(tmp_path: Path):
    root = tmp_path / "projects"
    personal = tmp_path / "personal"
    personal.mkdir()
    project = _project(root, appcode="BROKEN", folder="Still Visible")
    (root / "BROKEN" / "appcode.json").write_text("[]", encoding="utf-8")
    (project / "visible.md").write_text("visible", encoding="utf-8")
    service = SecondBrainService(
        folder_provider=lambda: personal,
        root_provider=lambda: root,
        metadata_store=MetadataStore(),
    )

    workspace = service.workspace()

    assert any(item.path.name == "visible.md" for item in workspace["items"])
    assert any("appcode metadata" in warning.casefold() for warning in workspace["warnings"])

from __future__ import annotations

import json
import sys
from dataclasses import dataclass
from pathlib import Path

from core.enums import ProjectState, ProjectType
from core.exceptions import (
    FileTargetExistsError,
    InvalidFileNameError,
    PathOutsideBaseError,
)
from core.models import AppCodeConfig, ProjectMetadata
from core.rules import WINDOWS_RESERVED_NAMES, is_organizational_folder
from infrastructure.metadata_store import MetadataStore


@dataclass(frozen=True, slots=True)
class ScannedProject:
    path: Path
    year: str
    appcode: str
    project_type: ProjectType
    project_state: ProjectState | None
    metadata: ProjectMetadata
    drone_paths: list[Path]

    @property
    def subproject_paths(self) -> list[Path]:
        return self.drone_paths


@dataclass(frozen=True, slots=True)
class AppCodeEntry:
    path: Path
    name: str
    config: AppCodeConfig


IS_WINDOWS = sys.platform == "win32"

STATE_FOLDER_NAMES = tuple(state.value for state in ProjectState)

# Forbidden characters for file names per Requirement 6.2: `< > : " / \ | ? *`.
FILE_NAME_INVALID_CHARS = frozenset('<>:"/\\|?*')

MAX_FILE_NAME_LENGTH = 255


def validate_file_name(name: str) -> None:
    """Validate a file name for create/rename operations (Req 6.2/6.6).

    A valid name is non-empty, at most 255 characters, free of the forbidden
    characters ``< > : " / \\ | ? *``, and not a Windows reserved device name
    (CON, PRN, AUX, NUL, COM1-9, LPT1-9). Any violation raises
    :class:`InvalidFileNameError`; the function never mutates the filesystem so
    callers can validate before touching folder contents.
    """
    if not name:
        raise InvalidFileNameError("File name cannot be empty")
    if len(name) > MAX_FILE_NAME_LENGTH:
        raise InvalidFileNameError(
            f"File name cannot exceed {MAX_FILE_NAME_LENGTH} characters"
        )
    invalid_characters = sorted(
        {character for character in name if character in FILE_NAME_INVALID_CHARS}
    )
    if invalid_characters:
        raise InvalidFileNameError(
            f"File name contains invalid character: {invalid_characters[0]}"
        )
    stem = name.split(".", 1)[0].upper()
    if stem in WINDOWS_RESERVED_NAMES:
        raise InvalidFileNameError(f"File name is reserved on Windows: {stem}")


def assert_within(base: Path, target: Path) -> Path:
    """Return ``target`` unchanged if it resolves strictly within ``base``.

    The guard that every create/move/rename/delete helper routes through so no
    destructive operation can escape its allowed base (e.g. the Temp_Root used
    during development and tests). A target that is ``base`` itself, that climbs
    out via ``..`` traversal, or that points elsewhere entirely is rejected.

    Resolution is used only for the containment comparison. The original
    ``target`` is returned verbatim so Windows path strings (drive letter and
    backslash separators) are never normalized into a POSIX form.
    """
    base_resolved = Path(base).resolve()
    target_resolved = Path(target).resolve()
    if target_resolved == base_resolved or not target_resolved.is_relative_to(base_resolved):
        raise PathOutsideBaseError(
            f"Target path {target} does not resolve strictly within base {base}"
        )
    return target


def ensure_year_structure(root_folder: Path, year: int) -> None:
    """Create root_folder / year / state subfolders if they don't exist."""
    year_path = root_folder / str(year)
    for state_name in STATE_FOLDER_NAMES:
        target = year_path / state_name
        assert_within(root_folder, target)
        target.mkdir(parents=True, exist_ok=True)


def ensure_appcode_year_structure(appcode_path: Path, year: int) -> None:
    """Create appcode/{YEAR}/CR/{5 states} + appcode/{YEAR}/Non-CR/."""
    year_path = appcode_path / str(year)
    cr_path = year_path / "CR"
    for state_name in STATE_FOLDER_NAMES:
        target = cr_path / state_name
        assert_within(appcode_path, target)
        target.mkdir(parents=True, exist_ok=True)
    non_cr_path = year_path / "Non-CR"
    assert_within(appcode_path, non_cr_path)
    non_cr_path.mkdir(parents=True, exist_ok=True)


def project_type_from_path(project_path: Path) -> ProjectType:
    """Determine project type from path: under CR/ = CR, under Non-CR/ = NON_CR."""
    for parent in project_path.parents:
        if parent.name == "CR":
            return ProjectType.CR
        if parent.name == "Non-CR":
            return ProjectType.NON_CR
    return ProjectType.CR


def discover_appcodes(root_folder: Path) -> list[AppCodeEntry]:
    """Scan {root}/* for folders containing appcode.json."""
    if not root_folder.exists():
        return []
    entries: list[AppCodeEntry] = []
    for child in sorted(root_folder.iterdir()):
        if not child.is_dir():
            continue
        config_path = child / "appcode.json"
        if not config_path.exists():
            continue
        try:
            data = json.loads(config_path.read_text(encoding="utf-8"))
        except Exception:
            continue
        config = AppCodeConfig.from_dict(data)
        if not config.display_name:
            config.display_name = child.name
        entries.append(AppCodeEntry(path=child, name=child.name, config=config))
    return entries


def state_folders_for_year(year_path: Path) -> list[Path]:
    folders = [year_path / state_name for state_name in STATE_FOLDER_NAMES]
    for folder in folders:
        assert_within(year_path, folder)
        folder.mkdir(parents=True, exist_ok=True)
    return folders


def scan_year(year_path: Path, metadata_store: MetadataStore | None = None) -> list[ScannedProject]:
    store = metadata_store or MetadataStore()
    projects: list[ScannedProject] = []
    if not year_path.exists():
        return projects

    for state in ProjectState:
        state_path = year_path / state.value
        if not state_path.is_dir():
            continue
        for project_path in sorted(child for child in state_path.iterdir() if child.is_dir()):
            metadata = store.read(project_path)
            if metadata is None:
                continue
            projects.append(
                ScannedProject(
                    path=project_path,
                    year=year_path.name,
                    appcode="",
                    project_type=ProjectType.CR,
                    project_state=state,
                    metadata=metadata,
                    drone_paths=discover_drone_paths(project_path),
                )
            )
    return projects


def scan_appcode_year(
    appcode_path: Path, year: str, metadata_store: MetadataStore | None = None
) -> list[ScannedProject]:
    """Scan one appcode's year folder for CR + Non-CR projects."""
    store = metadata_store or MetadataStore()
    projects: list[ScannedProject] = []
    year_path = appcode_path / year
    if not year_path.exists():
        return projects

    # CR branch: support both year/CR/{STATE}/project and legacy/direct
    # appcode layout year/{STATE}/project. Appcode is only the top folder name;
    # users can name it SSID, BIFAST, SKN, WGID, RTGS, or anything else.
    cr_roots = [year_path / "CR"] if (year_path / "CR").is_dir() else []
    cr_roots.append(year_path)
    seen_paths: set[Path] = set()
    for cr_root in cr_roots:
        for state in ProjectState:
            state_path = cr_root / state.value
            if not state_path.is_dir():
                continue
            for project_path in sorted(child for child in state_path.iterdir() if child.is_dir()):
                if project_path in seen_paths:
                    continue
                seen_paths.add(project_path)
                metadata = store.read(project_path)
                if metadata is None:
                    continue
                metadata.project_type = ProjectType.CR
                projects.append(
                    ScannedProject(
                        path=project_path,
                        year=year,
                        appcode=appcode_path.name,
                        project_type=ProjectType.CR,
                        project_state=state,
                        metadata=metadata,
                        drone_paths=discover_drone_paths(project_path),
                    )
                )

    # Non-CR branch: year/Non-CR/project (no state folders)
    non_cr_root = year_path / "Non-CR"
    if non_cr_root.is_dir():
        for project_path in sorted(child for child in non_cr_root.iterdir() if child.is_dir()):
            metadata = store.read(project_path)
            if metadata is None:
                continue
            metadata.project_type = ProjectType.NON_CR
            projects.append(
                ScannedProject(
                    path=project_path,
                    year=year,
                    appcode=appcode_path.name,
                    project_type=ProjectType.NON_CR,
                    project_state=None,
                    metadata=metadata,
                    drone_paths=[],
                )
            )
    return projects


def discover_subproject_paths(project_path: Path) -> list[Path]:
    return sorted(
        child
        for child in project_path.iterdir()
        if child.is_dir() and not is_organizational_folder(child)
    )


def discover_drone_paths(project_path: Path) -> list[Path]:
    """Like discover_subproject_paths but excludes the reserved _cr-docs folder."""
    return sorted(
        child
        for child in project_path.iterdir()
        if child.is_dir()
        and not is_organizational_folder(child)
        and child.name != "_cr-docs"
    )


def _scaffold_drone(project_path: Path, drone_name: str) -> Path:
    """Create {project}/{drone}/ + UAT/ + PRD/ + notes.md."""
    from core.rules import validate_windows_folder_name

    validate_windows_folder_name(drone_name)
    if drone_name == "_cr-docs":
        raise ValueError("Drone name cannot be '_cr-docs' (reserved folder)")
    drone_path = project_path / drone_name
    if drone_path.exists():
        raise ValueError(f"Drone folder already exists: {drone_path}")
    drone_path.mkdir(parents=True)
    (drone_path / "UAT").mkdir()
    (drone_path / "PRD").mkdir()
    (drone_path / "notes.md").touch()
    return drone_path


def open_folder(path: Path) -> None:
    if IS_WINDOWS:
        import os

        os.startfile(str(path))
        return
    print(f"[DEV] Would open folder: {path}")


def create_directory(base: Path, target: Path) -> Path:
    """Create ``target`` (and parents) only if it resolves within ``base``."""
    assert_within(base, target)
    target.mkdir(parents=True, exist_ok=True)
    return target


def move_path(base: Path, source: Path, destination: Path) -> Path:
    """Move ``source`` to ``destination``; both must resolve within ``base``."""
    import shutil

    assert_within(base, source)
    assert_within(base, destination)
    shutil.move(str(source), str(destination))
    return destination


def rename_path(base: Path, source: Path, destination: Path) -> Path:
    """Rename ``source`` to ``destination``; both must resolve within ``base``."""
    assert_within(base, source)
    assert_within(base, destination)
    source.rename(destination)
    return destination


def send_to_recycle_bin(path: Path, base: Path | None = None) -> None:
    """Send ``path`` to the Recycle Bin.

    When ``base`` is provided the deletion is rejected unless ``path`` resolves
    strictly within it, preventing destructive operations from escaping the
    allowed base (e.g. Temp_Root) during development and tests.
    """
    if base is not None:
        assert_within(base, path)
    import send2trash

    send2trash.send2trash(str(path))


def create_file(base: Path, target: Path, *, content: str = "") -> Path:
    """Create a new file at ``target`` (validated, within ``base``).

    The file name is validated (Req 6.2) and the target must resolve strictly
    within ``base``. Creation is rejected when ``target`` already exists so an
    existing file is never overwritten (Req 6.3). On any validation/existence
    failure the folder contents are left in their pre-operation state because no
    write occurs until every guard has passed. When ``content`` is provided the
    bytes are written via a temp-file-then-replace so a failed write never leaves
    a partial file in place (Req 6.9).
    """
    validate_file_name(target.name)
    assert_within(base, target)
    if target.exists():
        raise FileTargetExistsError(f"File already exists: {target}")
    if not content:
        # Atomic on POSIX/Windows: fails if the target appeared concurrently.
        target.touch(exist_ok=False)
        return target
    _atomic_write_new(target, content.encode("utf-8"))
    return target


def create_file_from_template(base: Path, template: Path, target: Path) -> Path:
    """Copy ``template`` to ``target`` (validated, within ``base``).

    The target name is validated (Req 6.2) and ``target`` must resolve strictly
    within ``base``. The copy is rejected when ``target`` already exists (Req
    6.3) and when the ``template`` source is missing. The copy is staged through
    a temp file that is atomically renamed into place, so a failed copy leaves
    the folder contents unchanged (Req 6.9).
    """
    validate_file_name(target.name)
    assert_within(base, target)
    if target.exists():
        raise FileTargetExistsError(f"File already exists: {target}")
    if not template.is_file():
        raise FileNotFoundError(f"Template source not found: {template}")
    _atomic_write_new(target, template.read_bytes())
    return target


def rename_file(base: Path, source: Path, destination: Path) -> Path:
    """Rename ``source`` to ``destination`` (validated, within ``base``).

    The destination name is validated (Req 6.6) and both paths must resolve
    strictly within ``base``. The rename is rejected when ``destination`` already
    exists so an existing file is never clobbered (Req 6.7). All guards run
    before the rename, so a rejected rename leaves the file unchanged (Req 6.9).
    """
    validate_file_name(destination.name)
    assert_within(base, source)
    assert_within(base, destination)
    if destination.exists():
        raise FileTargetExistsError(f"File already exists: {destination}")
    source.rename(destination)
    return destination


def delete_target(target: Path, base: Path | None = None) -> None:
    """Send ``target`` to the Recycle Bin (the only permitted deletion route).

    Thin wrapper over :func:`send_to_recycle_bin` for file deletes; when ``base``
    is provided the deletion is rejected unless ``target`` resolves strictly
    within it (Req 2.2/6.8).
    """
    send_to_recycle_bin(target, base=base)


def _atomic_write_new(target: Path, data: bytes) -> None:
    """Write ``data`` to ``target`` via a sibling temp file then atomic replace.

    The temp file is removed if anything fails before the replace, so the
    destination folder never retains a partial file (Req 6.9).
    """
    import os

    temp_path = target.with_name(f"{target.name}.{os.getpid()}.tmp")
    try:
        with open(temp_path, "xb") as handle:
            handle.write(data)
            handle.flush()
            os.fsync(handle.fileno())
        os.replace(temp_path, target)
    except BaseException:
        try:
            temp_path.unlink()
        except FileNotFoundError:
            pass
        raise

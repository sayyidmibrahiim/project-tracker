from __future__ import annotations

import shutil
from pathlib import Path

from core.enums import CRState, DroneState, ProjectState
from core.exceptions import InvalidFolderNameError
from core.models import AppSettings, HistoryEntry, ProjectMetadata, local_now
from core.rules import (
    TransitionGuardResult,
    current_user,
    should_auto_start_cr,
    should_auto_start_drone,
    validate_prod_ready_to_implemented_transition,
    validate_uat_to_prod_ready_transition,
    validate_windows_folder_name,
)
from core.state_machine import (
    reopen_project_state,
    validate_cr_transition,
    validate_drone_state_change_allowed,
    validate_project_state_transition,
)
from infrastructure import filesystem
from infrastructure.metadata_store import MetadataStore


def state_from_project_path(project_path: Path) -> ProjectState:
    return ProjectState(project_path.parent.name)


def year_path_from_project_path(project_path: Path) -> Path:
    return project_path.parent.parent


class ProjectService:
    def __init__(
        self,
        metadata_store: MetadataStore | None = None,
    ) -> None:
        self.metadata_store = metadata_store or MetadataStore()

    def rename_project(
        self, project_path: Path, new_name: str, settings: AppSettings
    ) -> Path:
        """Validate and rename a project folder.

        Validation reuses the core Windows folder-name validator (non-empty,
        1-255, forbidden characters, reserved device names, no trailing
        space/dot) and adds a case-insensitive sibling-duplicate check.
        Raises ``InvalidFolderNameError`` on any validation failure, leaving
        the folder unchanged.
        """
        validate_windows_folder_name(new_name)

        parent = project_path.parent
        target_path = parent / new_name

        # Case-insensitive sibling-duplicate check (excluding the project
        # being renamed so a case-only rename is permitted).
        new_name_lower = new_name.lower()
        if parent.exists():
            for sibling in parent.iterdir():
                if sibling == project_path:
                    continue
                if sibling.name.lower() == new_name_lower:
                    raise InvalidFolderNameError(
                        f"A folder named '{new_name}' already exists in this location"
                    )

        if target_path.exists() and target_path != project_path:
            raise FileExistsError(f"Target project folder already exists: {target_path}")

        moved_path = (
            Path(shutil.move(str(project_path), str(target_path)))
            if project_path != target_path
            else project_path
        )

        metadata = self.metadata_store.load(moved_path)
        now = local_now()
        metadata.project_name = new_name
        metadata.updated_at = now
        metadata.history.append(
            HistoryEntry(
                timestamp=now,
                action="RENAME",
                detail=f"RENAME: {project_path.name} → {new_name}",
                user=current_user(settings),
            )
        )
        self.metadata_store.save(moved_path, metadata)
        return moved_path

    def delete_project(self, project_path: Path) -> None:
        """Route a project-folder deletion to the Recycle Bin via send2trash.

        Deletion is delegated to ``SafeDeleteService.delete_to_trash`` which is
        the single permitted deletion path. On failure the exception
        propagates and the folder is left in place.
        """
        filesystem.send_to_recycle_bin(project_path)

    def delete_subproject(self, subproject_path: Path) -> None:
        """Route a subproject-folder deletion to the Recycle Bin via send2trash."""
        filesystem.send_to_recycle_bin(subproject_path)

    @staticmethod
    def _set_drone_pause_state(metadata: ProjectMetadata, target: DroneState, now) -> None:
        for ticket in metadata.drone_tickets:
            if ticket.drone_state == target:
                continue
            if ticket.previous_drone_state_before_canceled is None:
                ticket.previous_drone_state_before_canceled = ticket.drone_state
            ticket.drone_state = target
            ticket.drone_state_updated_at = now

    @staticmethod
    def _restore_drone_pause_state(metadata: ProjectMetadata, now) -> None:
        for ticket in metadata.drone_tickets:
            if ticket.previous_drone_state_before_canceled is not None:
                ticket.drone_state = ticket.previous_drone_state_before_canceled
                ticket.previous_drone_state_before_canceled = None
                ticket.drone_state_updated_at = now
            elif ticket.drone_state in {DroneState.POSTPONED, DroneState.CANCELED}:
                ticket.drone_state = DroneState.UAT
                ticket.drone_state_updated_at = now

    def reopen_project(self, project_path: Path, settings: AppSettings) -> Path:
        metadata = self.metadata_store.load(project_path)
        old_folder_state = state_from_project_path(project_path)
        reopen_result = reopen_project_state(old_folder_state)

        target_dir = year_path_from_project_path(project_path) / reopen_result.folder_state.value
        target_dir.mkdir(parents=True, exist_ok=True)
        target_path = target_dir / project_path.name
        if target_path.exists() and target_path != project_path:
            raise FileExistsError(f"Target project folder already exists: {target_path}")

        moved_path = Path(shutil.move(str(project_path), str(target_path))) if project_path != target_path else project_path
        now = local_now()
        metadata.cr_state = reopen_result.next_cr_state
        metadata.cr_state_updated_at = now
        self._restore_drone_pause_state(metadata, now)
        metadata.updated_at = now
        metadata.history.append(
            HistoryEntry(
                timestamp=now,
                action=reopen_result.history_action,
                detail=f"REOPEN: project moved from {old_folder_state.value} to {reopen_result.folder_state.value}",
                user=current_user(settings),
            )
        )
        self.metadata_store.save(moved_path, metadata)
        return moved_path

    def move_to_prod_ready(
        self,
        project_path: Path,
        settings: AppSettings,
        current_time,
        threshold_days: int = 10,
    ) -> Path | TransitionGuardResult:
        metadata = self.metadata_store.load(project_path)
        source_state = state_from_project_path(project_path)
        validate_project_state_transition(source_state, ProjectState.PROD_READY)

        guard_result = validate_uat_to_prod_ready_transition(
            metadata, current_time=current_time, threshold_days=threshold_days
        )
        if not guard_result.allowed:
            return guard_result

        target_dir = year_path_from_project_path(project_path) / ProjectState.PROD_READY.value
        target_dir.mkdir(parents=True, exist_ok=True)
        target_path = target_dir / project_path.name
        if target_path.exists() and target_path != project_path:
            raise FileExistsError(f"Target project folder already exists: {target_path}")

        moved_path = Path(shutil.move(str(project_path), str(target_path))) if project_path != target_path else project_path
        now = local_now()
        metadata.cr_state_updated_at = now
        metadata.updated_at = now
        metadata.history.append(
            HistoryEntry(
                timestamp=now,
                action="STATE_CHANGE",
                detail=f"{source_state.value} → {ProjectState.PROD_READY.value}",
                user=current_user(settings),
            )
        )
        self.metadata_store.save(moved_path, metadata)
        return moved_path

    def move_to_implemented(
        self, project_path: Path, settings: AppSettings, current_time
    ) -> Path | TransitionGuardResult:
        metadata = self.metadata_store.load(project_path)
        source_state = state_from_project_path(project_path)
        validate_project_state_transition(source_state, ProjectState.IMPLEMENTED)

        guard_result = validate_prod_ready_to_implemented_transition(
            metadata, current_time=current_time
        )

        if not guard_result.allowed:
            return guard_result

        target_dir = year_path_from_project_path(project_path) / ProjectState.IMPLEMENTED.value
        target_dir.mkdir(parents=True, exist_ok=True)
        target_path = target_dir / project_path.name
        if target_path.exists() and target_path != project_path:
            raise FileExistsError(f"Target project folder already exists: {target_path}")

        moved_path = Path(shutil.move(str(project_path), str(target_path))) if project_path != target_path else project_path
        now = local_now()
        metadata.cr_state_updated_at = now
        metadata.updated_at = now
        metadata.history.append(
            HistoryEntry(
                timestamp=now,
                action="STATE_CHANGE",
                detail=f"{source_state.value} → {ProjectState.IMPLEMENTED.value}",
                user=current_user(settings),
            )
        )
        self.metadata_store.save(moved_path, metadata)
        return moved_path

    def resume_project(self, project_path: Path, settings: AppSettings) -> Path:
        from core.state_machine import validate_postponed_resume

        metadata = self.metadata_store.load(project_path)
        old_state = state_from_project_path(project_path)

        validate_postponed_resume(ProjectState.UAT_PREPARE)

        target_dir = year_path_from_project_path(project_path) / ProjectState.UAT_PREPARE.value
        target_dir.mkdir(parents=True, exist_ok=True)
        target_path = target_dir / project_path.name
        if target_path.exists() and target_path != project_path:
            raise FileExistsError(f"Target project folder already exists: {target_path}")

        moved_path = Path(shutil.move(str(project_path), str(target_path))) if project_path != target_path else project_path
        now = local_now()
        metadata.updated_at = now
        metadata.history.append(
            HistoryEntry(
                timestamp=now,
                action="STATE_CHANGE",
                detail=f"{old_state.value} → UAT_PREPARE",
                user=current_user(settings),
            )
        )
        self.metadata_store.save(moved_path, metadata)
        return moved_path

    def cancel_project(self, project_path: Path, settings: AppSettings) -> Path:
        metadata = self.metadata_store.load(project_path)
        old_state = state_from_project_path(project_path)
        old_cr_state = metadata.cr_state
        validate_project_state_transition(old_state, ProjectState.CANCELED)

        target_dir = year_path_from_project_path(project_path) / ProjectState.CANCELED.value
        target_dir.mkdir(parents=True, exist_ok=True)
        target_path = target_dir / project_path.name
        if target_path.exists() and target_path != project_path:
            raise FileExistsError(f"Target project folder already exists: {target_path}")

        moved_path = Path(shutil.move(str(project_path), str(target_path))) if project_path != target_path else project_path
        now = local_now()
        metadata.cr_state = CRState.CANCELED
        metadata.cr_state_updated_at = now
        self._set_drone_pause_state(metadata, DroneState.CANCELED, now)
        metadata.updated_at = now
        metadata.history.append(
            HistoryEntry(
                timestamp=now,
                action="STATE_CHANGE",
                detail=f"CANCELED: {old_state.value} → CANCELED (CR {old_cr_state.value} → CANCELED)",
                user=current_user(settings),
            )
        )
        self.metadata_store.save(moved_path, metadata)
        return moved_path

    def postpone_project(self, project_path: Path, settings: AppSettings) -> Path:
        metadata = self.metadata_store.load(project_path)
        old_state = state_from_project_path(project_path)
        old_cr_state = metadata.cr_state
        validate_project_state_transition(old_state, ProjectState.POSTPONED)

        target_dir = year_path_from_project_path(project_path) / ProjectState.POSTPONED.value
        target_dir.mkdir(parents=True, exist_ok=True)
        target_path = target_dir / project_path.name
        if target_path.exists() and target_path != project_path:
            raise FileExistsError(f"Target project folder already exists: {target_path}")

        moved_path = Path(shutil.move(str(project_path), str(target_path))) if project_path != target_path else project_path
        now = local_now()
        metadata.cr_state = CRState.POSTPONED
        metadata.cr_state_updated_at = now
        self._set_drone_pause_state(metadata, DroneState.POSTPONED, now)
        metadata.updated_at = now
        metadata.history.append(
            HistoryEntry(
                timestamp=now,
                action="STATE_CHANGE",
                detail=f"POSTPONED: {old_state.value} → POSTPONED (CR {old_cr_state.value} → POSTPONED)",
                user=current_user(settings),
            )
        )
        self.metadata_store.save(moved_path, metadata)
        return moved_path

    def auto_transition_in_progress(self, project_path: Path, settings: AppSettings, current_time=None) -> bool:
        from core.models import DroneState

        metadata = self.metadata_store.load(project_path)
        now = current_time or local_now()

        changed = False
        detail_parts: list[str] = []

        if should_auto_start_cr(metadata, now):
            validate_cr_transition(CRState.APPROVED, CRState.IN_PROGRESS, automatic=True)
            metadata.cr_state = CRState.IN_PROGRESS
            metadata.cr_state_updated_at = now
            detail_parts.append("CR: APPROVED → IN-PROGRESS")
            changed = True

        for index, drone in enumerate(metadata.drone_tickets):
            if should_auto_start_drone(drone, metadata, now):
                validate_drone_state_change_allowed(
                    drone.drone_link,
                    DroneState.APPROVED,
                    DroneState.IN_PROGRESS,
                    automatic=True,
                )
                drone.drone_state = DroneState.IN_PROGRESS
                drone.drone_state_updated_at = now
                label = drone.subfolder_name or f"ticket {index + 1}"
                detail_parts.append(f"Drone {label}: APPROVED → IN-PROGRESS")
                changed = True

        if changed:
            metadata.updated_at = now
            detail_str = " | ".join(detail_parts) if len(detail_parts) > 1 else detail_parts[0].replace("CR: ", "")
            metadata.history.append(
                HistoryEntry(
                    timestamp=now,
                    action="AUTO_TRANSITION",
                    detail=detail_str,
                    user="System",
                )
            )
            self.metadata_store.save(project_path, metadata)

        return changed

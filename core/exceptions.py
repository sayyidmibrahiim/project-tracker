class ProjectTrackerError(Exception):
    pass


class InvalidTransitionError(ProjectTrackerError):
    pass


class InvalidFolderNameError(ProjectTrackerError):
    pass


class InvalidFileNameError(ProjectTrackerError):
    """Raised when a file name violates the create/rename naming rules
    (empty, longer than 255 characters, contains a forbidden character, or is a
    Windows reserved device name)."""

    pass


class FileTargetExistsError(ProjectTrackerError):
    """Raised when a file create/create-from-template/rename target already
    exists, so the operation is rejected without overwriting the target."""

    pass


class PathOutsideBaseError(ProjectTrackerError):
    """Raised when a target path does not resolve strictly within an allowed base."""

    pass


class AtomicWriteError(ProjectTrackerError):
    """Raised when an atomic temp-file-then-replace write fails before the
    replace step completes, leaving the existing target file unchanged."""

    pass

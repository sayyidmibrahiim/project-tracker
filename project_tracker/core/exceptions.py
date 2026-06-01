class ProjectTrackerError(Exception):
    pass


class InvalidTransitionError(ProjectTrackerError):
    pass


class InvalidFolderNameError(ProjectTrackerError):
    pass

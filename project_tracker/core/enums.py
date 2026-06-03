from enum import StrEnum


class ProjectState(StrEnum):
    UAT_PREPARE = "UAT_PREPARE"
    PROD_READY = "PROD_READY"
    IMPLEMENTED = "IMPLEMENTED"
    POSTPONED = "POSTPONED"
    CANCELED = "CANCELED"


class CRState(StrEnum):
    PENDING_SUBMISSION = "PENDING SUBMISSION"
    PENDING_APPROVAL = "PENDING APPROVAL"
    APPROVED = "APPROVED"
    IN_PROGRESS = "IN-PROGRESS"
    FINISHED = "FINISHED"
    POSTPONED = "POSTPONED"
    CANCELED = "CANCELED"
    # Deprecated compatibility value. REOPEN is an action/event in PRD v3.1, not a persistent CR state.
    REOPEN = "REOPEN"


class DroneState(StrEnum):
    UAT = "UAT"
    PENDING_APPROVAL = "PENDING APPROVAL"
    APPROVED = "APPROVED"
    IN_PROGRESS = "IN-PROGRESS"
    FINISHED = "FINISHED"
    CANCELED = "CANCELED"


class EmailCategory(StrEnum):
    ACK_UAT = "ACK_UAT"
    ACK_SOP = "ACK_SOP"
    APRVL_CR = "APRVL_CR"
    APRVL_SOP = "APRVL_SOP"


class Language(StrEnum):
    ENGLISH = "en"
    INDONESIAN = "id"


class Theme(StrEnum):
    DARK = "dark"
    LIGHT = "light"


class EmailMode(StrEnum):
    DRAFT = "draft"
    SEND = "send"

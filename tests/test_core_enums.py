from core.enums import CRState, DroneState, NonCrState, ProjectState, ProjectType


def test_project_state_contains_prd_folder_states() -> None:
    assert {state.value for state in ProjectState} == {
        "UAT_PREPARE",
        "PROD_READY",
        "IMPLEMENTED",
        "POSTPONED",
        "CANCELED",
    }


def test_cr_state_contains_prd_persistent_states() -> None:
    expected_states = {
        "PENDING SUBMISSION",
        "PENDING APPROVAL",
        "APPROVED",
        "IN-PROGRESS",
        "FINISHED",
        "POSTPONED",
        "CANCELED",
    }

    assert expected_states.issubset({state.value for state in CRState})


def test_drone_state_contains_prd_states() -> None:
    assert {state.value for state in DroneState} == {
        "UAT",
        "PENDING APPROVAL",
        "APPROVED",
        "IN-PROGRESS",
        "FINISHED",
        "POSTPONED",
        "CANCELED",
    }


def test_project_type_values():
    assert ProjectType.CR.value == "CR"
    assert ProjectType.NON_CR.value == "NON_CR"


def test_non_cr_state_values():
    assert NonCrState.PLANNING.value == "PLANNING"
    assert NonCrState.IN_PROGRESS.value == "IN_PROGRESS"
    assert NonCrState.DONE.value == "DONE"


def test_project_type_is_str_enum():
    assert isinstance(ProjectType.CR, str)
    assert ProjectType("CR") == ProjectType.CR


def test_non_cr_state_is_str_enum():
    assert isinstance(NonCrState.PLANNING, str)
    assert NonCrState("PLANNING") == NonCrState.PLANNING

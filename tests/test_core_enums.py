from project_tracker.core.enums import CRState, DroneState, ProjectState


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

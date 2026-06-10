from project_tracker.core.enums import DroneState
from project_tracker.core.models import DroneTicket
from project_tracker.core.rules import validate_cr_approved_requires_drones


def _drone(state: DroneState) -> DroneTicket:
    return DroneTicket(drone_link="https://drone/x", drone_state=state)


def test_g1_no_drones_allows_approved():
    result = validate_cr_approved_requires_drones([])
    assert result.allowed is True
    assert result.failed_guards == []


def test_g1_all_drones_approved_allows():
    result = validate_cr_approved_requires_drones(
        [_drone(DroneState.APPROVED), _drone(DroneState.APPROVED)]
    )
    assert result.allowed is True


def test_g1_one_drone_not_approved_blocks():
    result = validate_cr_approved_requires_drones(
        [_drone(DroneState.APPROVED), _drone(DroneState.IN_PROGRESS)]
    )
    assert result.allowed is False
    assert "1 drone" in result.failed_guards[0]


def test_g1_multiple_not_approved_counts():
    result = validate_cr_approved_requires_drones(
        [_drone(DroneState.UAT), _drone(DroneState.PENDING_APPROVAL)]
    )
    assert result.allowed is False
    assert "2 drone" in result.failed_guards[0]

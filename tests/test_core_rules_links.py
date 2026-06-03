from project_tracker.core.rules import extract_cr_number, extract_drone_ticket


def test_extract_cr_number_from_query_param() -> None:
    url = "https://itsm.example.local/orderDetails?CRNumber=CR202604209900114"

    assert extract_cr_number(url) == "CR202604209900114"


def test_extract_cr_number_from_query_with_other_params() -> None:
    url = "https://itsm.example.local/orderDetails?foo=1&CRNumber=CR202604209900114"

    assert extract_cr_number(url) == "CR202604209900114"


def test_extract_cr_number_returns_none_for_empty_or_blank_input() -> None:
    assert extract_cr_number("") is None
    assert extract_cr_number("   ") is None


def test_extract_cr_number_returns_none_for_unmatched_input() -> None:
    assert extract_cr_number("https://itsm.example.local/orderDetails?foo=1") is None
    assert extract_cr_number("lowercase unrelated cr202604209900114") is None


def test_extract_drone_ticket_from_path() -> None:
    url = "https://drone.example.local/deployment/D-SSIDBI-159"

    assert extract_drone_ticket(url) == "D-SSIDBI-159"


def test_extract_drone_ticket_from_path_with_trailing_slash() -> None:
    url = "https://drone.example.local/deployment/D-SSIDBI-159/"

    assert extract_drone_ticket(url) == "D-SSIDBI-159"


def test_extract_drone_ticket_returns_none_for_empty_or_blank_input() -> None:
    assert extract_drone_ticket("") is None
    assert extract_drone_ticket("   ") is None


def test_extract_drone_ticket_returns_none_for_unmatched_input() -> None:
    assert extract_drone_ticket("https://drone.example.local/deployment/ticket-159") is None
    assert extract_drone_ticket("lowercase unrelated d-ssidbi-159") is None

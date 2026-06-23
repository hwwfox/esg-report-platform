from datetime import date

from app.core.errors import ApiError
from app.modules.projects.router import validate_report_year, validate_status_transition


def test_project_default_status_flow_allows_first_step():
    validate_status_transition("draft", "peer_analysis")


def test_project_status_illegal_transition_blocked():
    try:
        validate_status_transition("draft", "completed")
    except ApiError as exc:
        assert exc.code == "PROJECT_STATUS_TRANSITION_INVALID"
    else:
        raise AssertionError("Illegal transition should raise ApiError")


def test_project_report_year_must_be_legal():
    validate_report_year(date.today().year)
    try:
        validate_report_year(1999)
    except ApiError as exc:
        assert exc.code == "PROJECT_INVALID_REPORT_YEAR"
    else:
        raise AssertionError("Invalid report year should raise ApiError")

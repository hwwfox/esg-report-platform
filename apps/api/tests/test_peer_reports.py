from app.core.errors import ApiError
from app.modules.peer_reports import router as report_router


def test_peer_report_upload_accepts_pdf_under_limit():
    report_router.validate_peer_report_upload("report.pdf", "application/pdf", 1024)


def test_peer_report_upload_rejects_non_pdf_extension():
    try:
        report_router.validate_peer_report_upload("report.txt", "text/plain", 1024)
    except ApiError as exc:
        assert exc.code == "FILE_TYPE_NOT_ALLOWED"
    else:
        raise AssertionError("Non-PDF upload should be rejected")


def test_peer_report_upload_rejects_large_file():
    try:
        report_router.validate_peer_report_upload("report.pdf", "application/pdf", report_router.MAX_PEER_REPORT_SIZE_BYTES + 1)
    except ApiError as exc:
        assert exc.code == "FILE_TOO_LARGE"
    else:
        raise AssertionError("Oversized upload should be rejected")


def test_peer_report_year_validation_uses_stable_error_code():
    try:
        report_router.validate_report_year(1999)
    except ApiError as exc:
        assert exc.code == "PEER_REPORT_INVALID_YEAR"
    else:
        raise AssertionError("Invalid report year should be rejected")


def test_require_project_peer_requires_confirmed_selected_peer():
    class FakeResult:
        def first(self):
            return None

    class FakeDb:
        def execute(self, statement, params):
            assert "confirmed_at IS NOT NULL" in str(statement)
            assert params["tenant_id"] == "tenant-1"
            assert params["project_id"] == "project-1"
            assert params["peer_company_id"] == "peer-1"
            return FakeResult()

    try:
        report_router._require_project_peer(FakeDb(), "tenant-1", "project-1", "peer-1")
    except ApiError as exc:
        assert exc.code == "PEER_NOT_CONFIRMED"
    else:
        raise AssertionError("Unconfirmed peers should not accept report uploads")

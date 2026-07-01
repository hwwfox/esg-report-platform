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


def test_result_collection_payload_adds_result_id_and_object_type():
    rows = [{"extracted_standard_id": "std-1", "extracted_standard_name": "GRI"}]

    payload = report_router._result_collection_payload(rows, object_type="standard", id_column="extracted_standard_id")

    assert payload[0]["result_id"] == "std-1"
    assert payload[0]["object_type"] == "standard"


def test_parse_result_patch_request_validates_object_type_and_status():
    payload = report_router.ParseResultPatchRequest(object_type="topic", review_status="accepted", mapped_topic_code="TOPIC_GHG")

    assert payload.object_type == "topic"
    assert payload.review_status == "accepted"


def test_patch_standard_result_uses_tenant_project_report_scope():
    class FakeResult:
        rowcount = 1

    class FakeDb:
        def __init__(self):
            self.statement = None
            self.params = None

        def execute(self, statement, params):
            self.statement = str(statement)
            self.params = params
            return FakeResult()

    db = FakeDb()
    payload = report_router.ParseResultPatchRequest(object_type="standard", review_status="edited", mapped_standard_code="GRI", review_note="ok")

    rowcount = report_router._patch_standard_result(db, tenant_id="tenant-1", project_id="project-1", peer_report_id="report-1", result_id="std-1", payload=payload, user_id="user-1")

    assert rowcount == 1
    assert "WHERE tenant_id=:tenant_id AND project_id=:project_id AND peer_report_id=:peer_report_id" in db.statement
    assert "include_in_adoption_stats=(:review_status IN ('accepted', 'edited'))" in db.statement
    assert db.params["tenant_id"] == "tenant-1"
    assert db.params["reviewed_by"] == "user-1"


def test_patch_topic_result_enables_topic_stats_only_for_accepted_or_edited():
    class FakeResult:
        rowcount = 1

    class FakeDb:
        def __init__(self):
            self.statement = None

        def execute(self, statement, params):
            self.statement = str(statement)
            return FakeResult()

    payload = report_router.ParseResultPatchRequest(object_type="topic", review_status="accepted", mapped_topic_code="TOPIC_GHG")
    report_router._patch_topic_result(FakeDb(), tenant_id="tenant-1", project_id="project-1", peer_report_id="report-1", result_id="topic-1", payload=payload, user_id="user-1")

    db = FakeDb()
    report_router._patch_topic_result(db, tenant_id="tenant-1", project_id="project-1", peer_report_id="report-1", result_id="topic-1", payload=payload, user_id="user-1")
    assert "include_in_topic_stats=(:review_status IN ('accepted', 'edited'))" in db.statement

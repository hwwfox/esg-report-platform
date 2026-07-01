import pytest

from app.jobs.parse_peer_report import (
    PeerReportParseResult,
    build_mock_parse_result,
    mark_job_failed,
    mark_job_started,
    mark_job_succeeded,
    process_peer_report_parse_job,
    validate_mock_parse_result,
)


class FakeDb:
    def __init__(self):
        self.calls = []

    def execute(self, statement, params=None):
        self.calls.append((statement, params or {}))


def test_build_mock_parse_result_has_required_candidate_collections():
    result = build_mock_parse_result("peer-report-1")

    assert result.standards[0]["peer_report_id"] == "peer-report-1"
    assert result.topics
    assert result.metrics
    validate_mock_parse_result(result)


def test_validate_mock_parse_result_rejects_missing_standard_name():
    result = PeerReportParseResult(standards=[{"peer_report_id": "peer-report-1"}], topics=[], metrics=[], cases=[])

    with pytest.raises(ValueError):
        validate_mock_parse_result(result)


def test_mark_job_started_uses_tenant_scoped_update():
    db = FakeDb()

    mark_job_started(db, tenant_id="tenant-1", job_id="job-1")

    statement, params = db.calls[0]
    assert "WHERE tenant_id=:tenant_id AND job_id=:job_id" in statement
    assert params == {"tenant_id": "tenant-1", "job_id": "job-1"}


def test_mark_job_succeeded_updates_candidates_report_and_job():
    db = FakeDb()
    result = build_mock_parse_result("peer-report-1")

    mark_job_succeeded(db, tenant_id="tenant-1", job_id="job-1", result=result, project_id="project-1", peer_report_id="peer-report-1")

    statements = [call[0] for call in db.calls]
    assert any("INSERT INTO report_extracted_standards" in statement for statement in statements)
    assert any("UPDATE peer_report_files" in statement and "tenant_id=:tenant_id AND project_id=:project_id" in statement for statement in statements)
    assert "job_status='succeeded'" in statements[-1]
    assert db.calls[-1][1]["tenant_id"] == "tenant-1"
    assert db.calls[-1][1]["job_id"] == "job-1"


def test_mark_job_failed_updates_report_and_job_failure_payload():
    db = FakeDb()

    mark_job_failed(db, tenant_id="tenant-1", job_id="job-1", project_id="project-1", peer_report_id="peer-report-1", error_code="ERR", message="failed")

    assert "parse_status='failed'" in db.calls[0][0]
    assert "job_status='failed'" in db.calls[1][0]
    assert db.calls[1][1]["error_payload"] == {"error_code": "ERR", "message": "failed"}


def test_process_peer_report_parse_job_runs_phase5_mock_pipeline():
    db = FakeDb()
    result = process_peer_report_parse_job(
        db,
        {
            "tenant_id": "tenant-1",
            "job_id": "job-1",
            "project_id": "project-1",
            "target_object_id": "peer-report-1",
        },
    )

    assert result.standards[0]["peer_report_id"] == "peer-report-1"
    assert "mock_parse_started" in db.calls[0][0]
    assert "mock_parse_completed" in db.calls[-1][0]

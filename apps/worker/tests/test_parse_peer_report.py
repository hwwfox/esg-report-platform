import pytest

from app.jobs.parse_peer_report import PeerReportParseResult, build_mock_parse_result, mark_job_succeeded, validate_mock_parse_result


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


def test_mark_job_succeeded_updates_job_status():
    calls = []

    class FakeDb:
        def execute(self, statement, params):
            calls.append((statement, params))

    result = build_mock_parse_result("peer-report-1")
    mark_job_succeeded(FakeDb(), tenant_id="tenant-1", job_id="job-1", result=result)

    assert "job_status='succeeded'" in calls[0][0]
    assert calls[0][1]["tenant_id"] == "tenant-1"
    assert calls[0][1]["job_id"] == "job-1"

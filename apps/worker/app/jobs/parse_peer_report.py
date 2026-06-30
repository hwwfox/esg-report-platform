from __future__ import annotations

from dataclasses import dataclass
from typing import Any


@dataclass(frozen=True)
class PeerReportParseResult:
    standards: list[dict[str, Any]]
    topics: list[dict[str, Any]]
    metrics: list[dict[str, Any]]
    cases: list[dict[str, Any]]


def build_mock_parse_result(peer_report_id: str) -> PeerReportParseResult:
    return PeerReportParseResult(
        standards=[{"peer_report_id": peer_report_id, "extracted_standard_name": "GRI Standards", "confidence": 0.8}],
        topics=[{"peer_report_id": peer_report_id, "original_topic_name": "温室气体排放", "confidence": 0.75}],
        metrics=[{"peer_report_id": peer_report_id, "original_metric_name": "范围一温室气体排放量", "confidence": 0.72}],
        cases=[],
    )


def validate_mock_parse_result(result: PeerReportParseResult) -> None:
    for collection_name in ("standards", "topics", "metrics", "cases"):
        value = getattr(result, collection_name)
        if not isinstance(value, list):
            raise ValueError(f"{collection_name} must be a list")
    for standard in result.standards:
        if not standard.get("peer_report_id") or not standard.get("extracted_standard_name"):
            raise ValueError("standard extraction requires peer_report_id and extracted_standard_name")


def mark_job_succeeded(db, *, tenant_id: str, job_id: str, result: PeerReportParseResult, project_id: str | None = None, peer_report_id: str | None = None) -> None:
    validate_mock_parse_result(result)
    if project_id and peer_report_id:
        db.execute("DELETE FROM report_extracted_standards WHERE tenant_id=:tenant_id AND project_id=:project_id AND peer_report_id=:peer_report_id", {"tenant_id": tenant_id, "project_id": project_id, "peer_report_id": peer_report_id})
        db.execute("DELETE FROM report_extracted_topics WHERE tenant_id=:tenant_id AND project_id=:project_id AND peer_report_id=:peer_report_id", {"tenant_id": tenant_id, "project_id": project_id, "peer_report_id": peer_report_id})
        db.execute("DELETE FROM report_extracted_metrics WHERE tenant_id=:tenant_id AND project_id=:project_id AND peer_report_id=:peer_report_id", {"tenant_id": tenant_id, "project_id": project_id, "peer_report_id": peer_report_id})
        db.execute("DELETE FROM report_extracted_cases WHERE tenant_id=:tenant_id AND project_id=:project_id AND peer_report_id=:peer_report_id", {"tenant_id": tenant_id, "project_id": project_id, "peer_report_id": peer_report_id})
        for standard in result.standards:
            db.execute("""
            INSERT INTO report_extracted_standards (tenant_id, project_id, peer_report_id, extracted_standard_name, confidence)
            VALUES (:tenant_id, :project_id, :peer_report_id, :extracted_standard_name, :confidence)
            """, {"tenant_id": tenant_id, "project_id": project_id, **standard})
        for topic in result.topics:
            db.execute("""
            INSERT INTO report_extracted_topics (tenant_id, project_id, peer_report_id, original_topic_name, confidence)
            VALUES (:tenant_id, :project_id, :peer_report_id, :original_topic_name, :confidence)
            """, {"tenant_id": tenant_id, "project_id": project_id, **topic})
        for metric in result.metrics:
            db.execute("""
            INSERT INTO report_extracted_metrics (tenant_id, project_id, peer_report_id, original_metric_name, confidence)
            VALUES (:tenant_id, :project_id, :peer_report_id, :original_metric_name, :confidence)
            """, {"tenant_id": tenant_id, "project_id": project_id, **metric})
        db.execute("""
        UPDATE peer_report_files
        SET parse_status='pending_human_review', ai_review_status='pending', updated_at=now()
        WHERE tenant_id=:tenant_id AND project_id=:project_id AND peer_report_id=:peer_report_id
        """, {"tenant_id": tenant_id, "project_id": project_id, "peer_report_id": peer_report_id})
    db.execute(
        """
        UPDATE async_jobs
        SET job_status='succeeded', progress=100, current_step='mock_parse_completed',
            result_payload=:result_payload, finished_at=now()
        WHERE tenant_id=:tenant_id AND job_id=:job_id
        """,
        {"tenant_id": tenant_id, "job_id": job_id, "result_payload": result.__dict__},
    )

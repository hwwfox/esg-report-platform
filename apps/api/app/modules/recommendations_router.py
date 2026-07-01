import json

from fastapi import APIRouter, Depends, Request
from pydantic import BaseModel, Field
from sqlalchemy import text
from sqlalchemy.orm import Session

from app.core.errors import ApiError
from app.core.response import ok
from app.db.session import get_db
from app.modules.audit.service import write_audit_log
from app.modules.auth.dependencies import require_permission
from app.modules.projects.router import _authorize_project

router = APIRouter(prefix="/api/v1/projects", tags=["推荐"])

MIN_ANALYZED_REPORTS = 1


class RecommendationGenerateRequest(BaseModel):
    based_on_peer_reports: bool = True
    only_approved_reports: bool | None = None
    only_approved_peer_reports: bool = True
    include_materiality_distribution: bool = True
    include_ai_reason: bool = True


class ProjectStandardsConfirmRequest(BaseModel):
    selected_standard_codes: list[str] = Field(default_factory=list)
    confirmation_note: str | None = None


class AcceptTopicsRequest(BaseModel):
    recommendation_ids: list[str] = Field(default_factory=list)


def _job_payload(row: dict) -> dict:
    return {
        "job_id": row["job_id"],
        "job_type": row["job_type"],
        "job_status": row["job_status"],
        "progress": row["progress"],
        "current_step": row["current_step"],
        "target_object_type": row.get("target_object_type"),
        "target_object_id": row.get("target_object_id"),
        "request_payload": row.get("request_payload") or {},
        "result_payload": row.get("result_payload") or {},
        "error_payload": row.get("error_payload") or {},
        "created_at": row["created_at"],
        "started_at": row.get("started_at"),
        "finished_at": row.get("finished_at"),
    }


def _recommendation_payload(row: dict) -> dict:
    item_type = row["recommendation_type"]
    return {
        "recommendation_id": row["recommendation_id"],
        "item_type": item_type,
        "standard_code": row["item_code"] if item_type == "standard" else None,
        "topic_code": row["item_code"] if item_type == "topic" else None,
        "item_name": row["item_name"],
        "adoption_rate": float(row["adoption_rate"] or 0),
        "adopted_company_count": row["adopted_company_count"],
        "analyzed_report_count": row["analyzed_report_count"],
        "recommendation_level": row["recommendation_level"],
        "reason": row.get("reason"),
        "limitations": row.get("limitations") or [],
        "source_count": len(row.get("source_references") or []),
        "selected": row["selected"],
    }


def _approved_report_count(db: Session, tenant_id: str, project_id: str) -> int:
    return int(db.execute(text("""
        SELECT count(DISTINCT peer_report_id)
        FROM peer_report_files
        WHERE tenant_id=:tenant_id AND project_id=:project_id
          AND (parse_status='stored' OR approved_at IS NOT NULL)
    """), {"tenant_id": tenant_id, "project_id": project_id}).scalar() or 0)


def _insert_job(db: Session, *, tenant_id: str, enterprise_id: str, project_id: str, job_type: str, payload: dict, user_id: str) -> dict:
    row = db.execute(text("""
        INSERT INTO async_jobs (tenant_id, enterprise_id, project_id, job_type, job_status, progress, current_step,
          target_object_type, target_object_id, request_payload, result_payload, created_by, started_at, finished_at)
        VALUES (:tenant_id, :enterprise_id, :project_id, :job_type, 'succeeded', 100, 'completed',
          'project_recommendations', :project_id, CAST(:request_payload AS jsonb), CAST(:result_payload AS jsonb), :created_by, now(), now())
        RETURNING job_id::text, job_type, job_status::text, progress, current_step, target_object_type, target_object_id::text,
          request_payload, result_payload, error_payload, created_at, started_at, finished_at
    """), {"tenant_id": tenant_id, "enterprise_id": enterprise_id, "project_id": project_id, "job_type": job_type, "request_payload": json.dumps(payload), "result_payload": json.dumps({"generated": True}), "created_by": user_id}).mappings().first()
    return dict(row)


def _report_sample_or_raise(db: Session, tenant_id: str, project_id: str) -> int:
    analyzed = _approved_report_count(db, tenant_id, project_id)
    if analyzed < MIN_ANALYZED_REPORTS:
        raise ApiError(400, "RECOMMENDATION_SAMPLE_INSUFFICIENT", "At least one approved peer report is required")
    return analyzed


def _level(rate: float) -> str:
    if rate >= 0.8:
        return "high"
    if rate >= 0.5:
        return "medium"
    return "low"


def _generate_standards(db: Session, tenant_id: str, project_id: str, analyzed: int) -> int:
    rows = db.execute(text("""
        SELECT COALESCE(res.mapped_standard_code, s.standard_code) AS item_code,
               COALESCE(res.mapped_standard_name, s.standard_name, res.extracted_standard_name) AS item_name,
               count(DISTINCT pr.peer_company_id) AS adopted_company_count,
               jsonb_agg(DISTINCT jsonb_build_object('peer_report_id', res.peer_report_id::text, 'source_type', 'peer_report_standard', 'item_code', COALESCE(res.mapped_standard_code, s.standard_code))) AS sources
        FROM report_extracted_standards res
        JOIN peer_report_files pr ON pr.tenant_id=res.tenant_id AND pr.project_id=res.project_id AND pr.peer_report_id=res.peer_report_id
        LEFT JOIN esg_standards s
          ON (s.standard_code=res.mapped_standard_code OR lower(s.standard_name)=lower(res.extracted_standard_name))
         AND (s.tenant_id IS NULL OR s.tenant_id=:tenant_id)
        WHERE res.tenant_id=:tenant_id AND res.project_id=:project_id
          AND res.review_status IN ('accepted','edited','approved','confirmed')
          AND res.include_in_adoption_stats=true
          AND (pr.parse_status='stored' OR pr.approved_at IS NOT NULL)
        GROUP BY COALESCE(res.mapped_standard_code, s.standard_code), COALESCE(res.mapped_standard_name, s.standard_name, res.extracted_standard_name)
    """), {"tenant_id": tenant_id, "project_id": project_id}).mappings().all()
    for row in rows:
        code = row["item_code"] or row["item_name"]
        rate = float(row["adopted_company_count"] or 0) / analyzed
        db.execute(text("""
            INSERT INTO project_recommendations (tenant_id, project_id, recommendation_type, item_code, item_name, adoption_rate,
              adopted_company_count, analyzed_report_count, recommendation_level, reason, limitations, source_references, selected, review_status)
            VALUES (:tenant_id, :project_id, 'standard', :item_code, :item_name, :rate, :count, :analyzed, :level, :reason, CAST(:limitations AS jsonb), CAST(:sources AS jsonb), true, 'pending')
            ON CONFLICT (project_id, recommendation_type, item_code) DO UPDATE SET
              item_name=EXCLUDED.item_name, adoption_rate=EXCLUDED.adoption_rate, adopted_company_count=EXCLUDED.adopted_company_count,
              analyzed_report_count=EXCLUDED.analyzed_report_count, recommendation_level=EXCLUDED.recommendation_level,
              reason=EXCLUDED.reason, limitations=EXCLUDED.limitations, source_references=EXCLUDED.source_references
        """), {"tenant_id": tenant_id, "project_id": project_id, "item_code": code, "item_name": row["item_name"], "rate": rate, "count": row["adopted_company_count"], "analyzed": analyzed, "level": _level(rate), "reason": f"基于{analyzed}份已审核同行报告的系统统计生成，采用率由系统计算。", "limitations": json.dumps([] if analyzed >= 3 else ["样本数量较少，推荐结论需人工复核。"]), "sources": json.dumps(row["sources"] or [])})
    return len(rows)


def _generate_topics(db: Session, tenant_id: str, project_id: str, analyzed: int) -> int:
    rows = db.execute(text("""
        SELECT ret.mapped_topic_code AS item_code, COALESCE(ret.mapped_topic_name, t.topic_name, ret.original_topic_name) AS item_name,
               COALESCE(t.topic_category::text, ret.topic_category::text, 'environment') AS topic_category,
               count(DISTINCT pr.peer_company_id) AS adopted_company_count,
               jsonb_object_agg(COALESCE(ret.financial_materiality::text, 'unknown'), materiality_counts.financial_count) FILTER (WHERE materiality_counts.financial_count IS NOT NULL) AS financial_distribution,
               jsonb_object_agg(COALESCE(ret.impact_materiality::text, 'unknown'), materiality_counts.impact_count) FILTER (WHERE materiality_counts.impact_count IS NOT NULL) AS impact_distribution,
               jsonb_agg(DISTINCT jsonb_build_object('peer_report_id', ret.peer_report_id::text, 'source_type', 'peer_report_topic', 'item_code', ret.mapped_topic_code)) AS sources
        FROM report_extracted_topics ret
        JOIN peer_report_files pr ON pr.tenant_id=ret.tenant_id AND pr.project_id=ret.project_id AND pr.peer_report_id=ret.peer_report_id
        LEFT JOIN esg_topics t
          ON t.topic_code=ret.mapped_topic_code
         AND (t.tenant_id IS NULL OR t.tenant_id=:tenant_id)
        LEFT JOIN LATERAL (SELECT count(*) AS financial_count, count(*) AS impact_count) materiality_counts ON true
        WHERE ret.tenant_id=:tenant_id AND ret.project_id=:project_id AND ret.mapped_topic_code IS NOT NULL
          AND ret.review_status IN ('accepted','edited','approved','confirmed')
          AND ret.include_in_topic_stats=true
          AND (pr.parse_status='stored' OR pr.approved_at IS NOT NULL)
        GROUP BY ret.mapped_topic_code, COALESCE(ret.mapped_topic_name, t.topic_name, ret.original_topic_name), COALESCE(t.topic_category::text, ret.topic_category::text, 'environment')
    """), {"tenant_id": tenant_id, "project_id": project_id}).mappings().all()
    for row in rows:
        rate = float(row["adopted_company_count"] or 0) / analyzed
        db.execute(text("""
            INSERT INTO project_recommendations (tenant_id, project_id, recommendation_type, item_code, item_name, adoption_rate,
              adopted_company_count, analyzed_report_count, recommendation_level, financial_materiality_distribution, impact_materiality_distribution,
              reason, limitations, source_references, selected, review_status)
            VALUES (:tenant_id, :project_id, 'topic', :item_code, :item_name, :rate, :count, :analyzed, :level,
              CAST(:financial AS jsonb), CAST(:impact AS jsonb), :reason, CAST(:limitations AS jsonb), CAST(:sources AS jsonb), true, 'pending')
            ON CONFLICT (project_id, recommendation_type, item_code) DO UPDATE SET
              item_name=EXCLUDED.item_name, adoption_rate=EXCLUDED.adoption_rate, adopted_company_count=EXCLUDED.adopted_company_count,
              analyzed_report_count=EXCLUDED.analyzed_report_count, recommendation_level=EXCLUDED.recommendation_level,
              financial_materiality_distribution=EXCLUDED.financial_materiality_distribution, impact_materiality_distribution=EXCLUDED.impact_materiality_distribution,
              reason=EXCLUDED.reason, limitations=EXCLUDED.limitations, source_references=EXCLUDED.source_references
        """), {"tenant_id": tenant_id, "project_id": project_id, "item_code": row["item_code"], "item_name": row["item_name"], "rate": rate, "count": row["adopted_company_count"], "analyzed": analyzed, "level": _level(rate), "financial": json.dumps(row["financial_distribution"] or {}), "impact": json.dumps(row["impact_distribution"] or {}), "reason": f"基于{analyzed}份已审核同行报告的系统统计生成，重要性分布来自人工审核结果。", "limitations": json.dumps([] if analyzed >= 3 else ["样本数量较少，推荐结论需人工复核。"]), "sources": json.dumps(row["sources"] or [])})
    return len(rows)


@router.post("/{project_id}/recommendations/standards/generate")
def generate_standards(project_id: str, payload: RecommendationGenerateRequest, request: Request, db: Session = Depends(get_db), user: dict = Depends(require_permission("project:update"))):
    project = _authorize_project(request, db, user, project_id)
    analyzed = _report_sample_or_raise(db, user["current_tenant_id"], project_id)
    count = _generate_standards(db, user["current_tenant_id"], project_id, analyzed)
    job = _insert_job(db, tenant_id=user["current_tenant_id"], enterprise_id=project["enterprise_id"], project_id=project_id, job_type="standard_recommendation", payload=payload.model_dump(), user_id=user["user_id"])
    write_audit_log(db, tenant_id=user["current_tenant_id"], enterprise_id=project["enterprise_id"], project_id=project_id, user_id=user["user_id"], user_name=user["name"], action_type="recommendation.standards_generated", object_type="project_recommendations", object_id=project_id, description=f"生成推荐标准{count}项")
    db.commit()
    return ok(_job_payload(job), request_id=request.state.request_id)


@router.post("/{project_id}/recommendations/topics/generate")
def generate_topics(project_id: str, payload: RecommendationGenerateRequest, request: Request, db: Session = Depends(get_db), user: dict = Depends(require_permission("project:update"))):
    project = _authorize_project(request, db, user, project_id)
    analyzed = _report_sample_or_raise(db, user["current_tenant_id"], project_id)
    count = _generate_topics(db, user["current_tenant_id"], project_id, analyzed)
    job = _insert_job(db, tenant_id=user["current_tenant_id"], enterprise_id=project["enterprise_id"], project_id=project_id, job_type="topic_recommendation", payload=payload.model_dump(), user_id=user["user_id"])
    write_audit_log(db, tenant_id=user["current_tenant_id"], enterprise_id=project["enterprise_id"], project_id=project_id, user_id=user["user_id"], user_name=user["name"], action_type="recommendation.topics_generated", object_type="project_recommendations", object_id=project_id, description=f"生成推荐议题{count}项")
    db.commit()
    return ok(_job_payload(job), request_id=request.state.request_id)


def _list_recommendations(db: Session, tenant_id: str, project_id: str, item_type: str) -> list[dict]:
    rows = db.execute(text("""
        SELECT recommendation_id::text, recommendation_type, item_code, item_name, adoption_rate, adopted_company_count,
               analyzed_report_count, recommendation_level, reason, limitations, source_references, selected
        FROM project_recommendations
        WHERE tenant_id=:tenant_id AND project_id=:project_id AND recommendation_type=:item_type
        ORDER BY adoption_rate DESC NULLS LAST, item_name
    """), {"tenant_id": tenant_id, "project_id": project_id, "item_type": item_type}).mappings().all()
    return [_recommendation_payload(dict(row)) for row in rows]


@router.get("/{project_id}/recommendations/standards")
def list_standards(project_id: str, request: Request, db: Session = Depends(get_db), user: dict = Depends(require_permission("project:read"))):
    _authorize_project(request, db, user, project_id)
    return ok({"items": _list_recommendations(db, user["current_tenant_id"], project_id, "standard")}, request_id=request.state.request_id)


@router.get("/{project_id}/recommendations/topics")
def list_topics(project_id: str, request: Request, db: Session = Depends(get_db), user: dict = Depends(require_permission("project:read"))):
    _authorize_project(request, db, user, project_id)
    return ok({"items": _list_recommendations(db, user["current_tenant_id"], project_id, "topic")}, request_id=request.state.request_id)


@router.get("/{project_id}/recommendations/{recommendation_id}/sources")
def recommendation_sources(project_id: str, recommendation_id: str, request: Request, db: Session = Depends(get_db), user: dict = Depends(require_permission("project:read"))):
    _authorize_project(request, db, user, project_id)
    row = db.execute(text("""
        SELECT recommendation_id::text, source_references
        FROM project_recommendations
        WHERE tenant_id=:tenant_id AND project_id=:project_id AND recommendation_id=:recommendation_id
    """), {"tenant_id": user["current_tenant_id"], "project_id": project_id, "recommendation_id": recommendation_id}).mappings().first()
    if not row:
        raise ApiError(404, "RECOMMENDATION_NOT_FOUND", "Recommendation not found")
    return ok({"recommendation_id": row["recommendation_id"], "sources": row["source_references"] or []}, request_id=request.state.request_id)


@router.post("/{project_id}/standards/confirm")
def confirm_standards(project_id: str, payload: ProjectStandardsConfirmRequest, request: Request, db: Session = Depends(get_db), user: dict = Depends(require_permission("project:update"))):
    project = _authorize_project(request, db, user, project_id)
    if not payload.selected_standard_codes:
        raise ApiError(400, "PROJECT_STANDARD_SELECTION_EMPTY", "Select at least one standard")
    rows = db.execute(text("""
        SELECT s.standard_id::text, s.standard_code, s.standard_name, sv.standard_version_id::text, sv.standard_version_code
        FROM esg_standards s
        LEFT JOIN LATERAL (
          SELECT standard_version_id, standard_version_code FROM standard_versions
          WHERE standard_id=s.standard_id AND status='active'
          ORDER BY effective_date DESC NULLS LAST LIMIT 1
        ) sv ON true
        WHERE s.standard_code = ANY(:codes)
          AND (s.tenant_id IS NULL OR s.tenant_id=:tenant_id)
    """), {"codes": payload.selected_standard_codes, "tenant_id": user["current_tenant_id"]}).mappings().all()
    if len(rows) != len(set(payload.selected_standard_codes)):
        raise ApiError(400, "PROJECT_STANDARD_UNKNOWN", "Selected standard contains unknown code")
    for row in rows:
        snapshot = {"standard_code": row["standard_code"], "standard_name": row["standard_name"], "standard_version_code": row["standard_version_code"]}
        db.execute(text("""
            INSERT INTO project_standards (tenant_id, project_id, standard_id, standard_version_id, standard_snapshot, source, selected, confirmed_by, confirmed_at)
            VALUES (:tenant_id, :project_id, :standard_id, :version_id, CAST(:snapshot AS jsonb), 'recommendation', true, :user_id, now())
            ON CONFLICT (project_id, standard_id) DO UPDATE SET standard_version_id=EXCLUDED.standard_version_id,
              standard_snapshot=EXCLUDED.standard_snapshot, source=EXCLUDED.source, selected=true, confirmed_by=EXCLUDED.confirmed_by, confirmed_at=now()
        """), {"tenant_id": user["current_tenant_id"], "project_id": project_id, "standard_id": row["standard_id"], "version_id": row["standard_version_id"], "snapshot": json.dumps(snapshot), "user_id": user["user_id"]})
    db.execute(text("UPDATE project_recommendations SET selected=(item_code = ANY(:codes)), review_status=CASE WHEN item_code = ANY(:codes) THEN 'accepted' ELSE 'ignored' END WHERE tenant_id=:tenant_id AND project_id=:project_id AND recommendation_type='standard'"), {"codes": payload.selected_standard_codes, "tenant_id": user["current_tenant_id"], "project_id": project_id})
    write_audit_log(db, tenant_id=user["current_tenant_id"], enterprise_id=project["enterprise_id"], project_id=project_id, user_id=user["user_id"], user_name=user["name"], action_type="project_standards.confirmed", object_type="project_standards", object_id=project_id, description="确认项目标准")
    db.commit()
    return ok({"confirmed_standard_count": len(rows)}, request_id=request.state.request_id)


@router.post("/{project_id}/topics/accept")
def accept_topics(project_id: str, payload: AcceptTopicsRequest, request: Request, db: Session = Depends(get_db), user: dict = Depends(require_permission("project:update"))):
    project = _authorize_project(request, db, user, project_id)
    if not payload.recommendation_ids:
        raise ApiError(400, "PROJECT_TOPIC_SELECTION_EMPTY", "Select at least one topic recommendation")
    rows = db.execute(text("""
        SELECT pr.recommendation_id::text, pr.item_code, pr.item_name, pr.adoption_rate, pr.recommendation_level,
               pr.financial_materiality_distribution, pr.impact_materiality_distribution, t.topic_id::text, t.topic_category::text
        FROM project_recommendations pr
        LEFT JOIN esg_topics t
          ON t.topic_code=pr.item_code
         AND (t.tenant_id IS NULL OR t.tenant_id=:tenant_id)
        WHERE pr.tenant_id=:tenant_id AND pr.project_id=:project_id AND pr.recommendation_type='topic'
          AND pr.recommendation_id = ANY(:ids)
    """), {"tenant_id": user["current_tenant_id"], "project_id": project_id, "ids": payload.recommendation_ids}).mappings().all()
    if len(rows) != len(set(payload.recommendation_ids)):
        raise ApiError(404, "RECOMMENDATION_NOT_FOUND", "Topic recommendation not found")
    created = 0
    for row in rows:
        project_topic = db.execute(text("""
            INSERT INTO project_topics (tenant_id, project_id, topic_id, topic_code, topic_name, topic_category, source, adoption_rate,
              priority, status, selected, locked_at)
            VALUES (:tenant_id, :project_id, :topic_id, :topic_code, :topic_name, :topic_category, 'recommendation', :adoption_rate,
              :priority, 'active', true, now())
            ON CONFLICT (project_id, topic_code) DO UPDATE SET topic_name=EXCLUDED.topic_name, adoption_rate=EXCLUDED.adoption_rate,
              priority=EXCLUDED.priority, status='active', selected=true, locked_at=COALESCE(project_topics.locked_at, now()), updated_at=now()
            RETURNING project_topic_id::text
        """), {"tenant_id": user["current_tenant_id"], "project_id": project_id, "topic_id": row["topic_id"], "topic_code": row["item_code"], "topic_name": row["item_name"], "topic_category": row["topic_category"] or "environment", "adoption_rate": row["adoption_rate"], "priority": row["recommendation_level"]}).mappings().first()
        metrics = db.execute(text("""
            SELECT m.metric_id::text, m.metric_code, m.metric_name, m.metric_type::text, m.data_type::text, m.default_unit, tmm.is_required
            FROM topic_metric_maps tmm
            JOIN esg_topics t ON t.topic_id=tmm.topic_id AND (t.tenant_id IS NULL OR t.tenant_id=:tenant_id)
            JOIN esg_metrics m ON m.metric_id=tmm.metric_id AND (m.tenant_id IS NULL OR m.tenant_id=:tenant_id)
            WHERE t.topic_code=:topic_code AND tmm.default_selected=true
        """), {"topic_code": row["item_code"], "tenant_id": user["current_tenant_id"]}).mappings().all()
        for metric in metrics:
            snapshot = {"metric_code": metric["metric_code"], "metric_name": metric["metric_name"]}
            db.execute(text("""
                INSERT INTO project_topic_metrics (tenant_id, project_id, project_topic_id, metric_id, metric_code, metric_name,
                  metric_type, data_type, unit, is_required, metric_snapshot, status)
                VALUES (:tenant_id, :project_id, :project_topic_id, :metric_id, :metric_code, :metric_name,
                  :metric_type, :data_type, :unit, :is_required, CAST(:snapshot AS jsonb), 'active')
                ON CONFLICT (project_topic_id, metric_code) DO UPDATE SET metric_name=EXCLUDED.metric_name,
                  metric_type=EXCLUDED.metric_type, data_type=EXCLUDED.data_type, unit=EXCLUDED.unit, is_required=EXCLUDED.is_required,
                  metric_snapshot=EXCLUDED.metric_snapshot, status='active'
            """), {"tenant_id": user["current_tenant_id"], "project_id": project_id, "project_topic_id": project_topic["project_topic_id"], "metric_id": metric["metric_id"], "metric_code": metric["metric_code"], "metric_name": metric["metric_name"], "metric_type": metric["metric_type"], "data_type": metric["data_type"], "unit": metric["default_unit"], "is_required": metric["is_required"], "snapshot": json.dumps(snapshot)})
        created += 1
    db.execute(text("UPDATE project_recommendations SET selected=(recommendation_id = ANY(:ids)), review_status=CASE WHEN recommendation_id = ANY(:ids) THEN 'accepted' ELSE review_status END WHERE tenant_id=:tenant_id AND project_id=:project_id AND recommendation_type='topic'"), {"ids": payload.recommendation_ids, "tenant_id": user["current_tenant_id"], "project_id": project_id})
    write_audit_log(db, tenant_id=user["current_tenant_id"], enterprise_id=project["enterprise_id"], project_id=project_id, user_id=user["user_id"], user_name=user["name"], action_type="project_topics.accepted", object_type="project_topics", object_id=project_id, description="接受推荐议题并生成指标快照")
    db.commit()
    return ok({"accepted_topic_count": created}, request_id=request.state.request_id)

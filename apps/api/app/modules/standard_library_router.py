from fastapi import APIRouter, Depends, Query, Request
from pydantic import BaseModel, Field
from sqlalchemy import text
from sqlalchemy.orm import Session

from app.core.errors import ApiError
from app.core.response import ok
from app.db.session import get_db
from app.modules.auth.dependencies import require_permission
from app.modules.audit.service import write_audit_log

router = APIRouter(prefix="/api/v1", tags=["标准议题指标"])

STATUS_VALUES = {"draft", "active", "inactive"}
TOPIC_CATEGORY_VALUES = {"E", "S", "G"}
METRIC_TYPE_VALUES = {"quantitative", "qualitative"}


def _validate_enum(value: str | None, allowed: set[str], code: str, field: str) -> None:
    if value is not None and value not in allowed:
        raise ApiError(400, code, f"Invalid {field}")


class StandardImportPayload(BaseModel):
    standard_code: str = Field(min_length=1, max_length=128)
    source_file_id: str | None = None
    import_mode: str = "placeholder"


def _library_visibility_clause(alias: str = "") -> str:
    prefix = f"{alias}." if alias else ""
    return f"({prefix}tenant_id IS NULL OR {prefix}tenant_id = :tenant_id)"


def _paged(rows, total: int, page: int, page_size: int) -> dict:
    return {"items": [dict(row) for row in rows], "page": page, "page_size": page_size, "total": total}


@router.get("/standards")
def list_standards(request: Request, db: Session = Depends(get_db), user: dict = Depends(require_permission("standard:read")), keyword: str | None = None, standard_type: str | None = None, applicable_market: str | None = None, status: str | None = None, page: int = Query(1, ge=1), page_size: int = Query(20, ge=1, le=100)):
    _validate_enum(status, STATUS_VALUES, "STANDARD_INVALID_STATUS", "status")
    clauses = [_library_visibility_clause()]
    select_clauses = [_library_visibility_clause("s")]
    params = {"tenant_id": user["current_tenant_id"], "limit": page_size, "offset": (page - 1) * page_size}
    if keyword:
        clauses.append("(standard_code ILIKE :keyword OR standard_name ILIKE :keyword OR standard_short_name ILIKE :keyword)")
        select_clauses.append("(s.standard_code ILIKE :keyword OR s.standard_name ILIKE :keyword OR s.standard_short_name ILIKE :keyword)")
        params["keyword"] = f"%{keyword}%"
    if standard_type:
        clauses.append("standard_type = :standard_type")
        select_clauses.append("s.standard_type = :standard_type")
        params["standard_type"] = standard_type
    if applicable_market:
        clauses.append("applicable_market = :applicable_market")
        select_clauses.append("s.applicable_market = :applicable_market")
        params["applicable_market"] = applicable_market
    if status:
        clauses.append("status = :status")
        select_clauses.append("s.status = :status")
        params["status"] = status
    where = " AND ".join(clauses)
    select_where = " AND ".join(select_clauses)
    total = db.execute(text(f"SELECT count(*) FROM esg_standards WHERE {where}"), params).scalar_one()
    rows = db.execute(text(f"""
        SELECT s.standard_id::text, s.tenant_id::text, s.standard_code, s.standard_name, s.standard_short_name,
               s.standard_type, s.applicable_market, s.issuing_body, s.description, s.scope_type, s.status::text,
               current_sv.version_no AS current_version, s.created_at, s.updated_at
        FROM esg_standards s
        LEFT JOIN LATERAL (
            SELECT sv.version_no
            FROM standard_versions sv
            WHERE sv.standard_id = s.standard_id AND sv.status = 'active'
            ORDER BY sv.is_current DESC, sv.effective_date DESC NULLS LAST, sv.version_no DESC
            LIMIT 1
        ) current_sv ON true
        WHERE {select_where}
        ORDER BY s.standard_code
        LIMIT :limit OFFSET :offset
    """), params).mappings().all()
    return ok(_paged(rows, total, page, page_size), request_id=request.state.request_id)


@router.get("/standards/{standard_code}")
def get_standard(standard_code: str, request: Request, db: Session = Depends(get_db), user: dict = Depends(require_permission("standard:read"))):
    row = db.execute(text(f"""
        SELECT standard_id::text, tenant_id::text, standard_code, standard_name, standard_short_name,
               standard_type, applicable_market, issuing_body, description, scope_type, status::text,
               created_at, updated_at
        FROM esg_standards
        WHERE {_library_visibility_clause()} AND standard_code=:standard_code
    """), {"tenant_id": user["current_tenant_id"], "standard_code": standard_code}).mappings().first()
    if not row:
        raise ApiError(404, "STANDARD_NOT_FOUND", "Standard not found")
    versions = db.execute(text("""
        SELECT sv.standard_version_id::text, sv.standard_version_code, sv.version_name, sv.version_no,
               sv.effective_date, sv.expired_date, sv.is_current, sv.status::text
        FROM standard_versions sv
        WHERE sv.standard_id=:standard_id AND sv.status='active'
        ORDER BY sv.is_current DESC, sv.effective_date DESC NULLS LAST, sv.version_no DESC
    """), {"standard_id": row["standard_id"]}).mappings().all()
    data = dict(row)
    data["versions"] = [dict(v) for v in versions]
    return ok(data, request_id=request.state.request_id)


@router.get("/standards/{standard_code}/versions/{version_code}/clauses")
def list_standard_clauses(standard_code: str, version_code: str, request: Request, db: Session = Depends(get_db), user: dict = Depends(require_permission("standard:read")), status: str | None = None, page: int = Query(1, ge=1), page_size: int = Query(100, ge=1, le=500)):
    _validate_enum(status, STATUS_VALUES, "CLAUSE_INVALID_STATUS", "status")
    params = {"tenant_id": user["current_tenant_id"], "standard_code": standard_code, "version_code": version_code, "limit": page_size, "offset": (page - 1) * page_size}
    status_clause = " AND c.status=:status" if status else ""
    if status:
        params["status"] = status
    base = f"""
        FROM standard_clauses c
        JOIN standard_versions sv ON sv.standard_version_id=c.standard_version_id
        JOIN esg_standards s ON s.standard_id=sv.standard_id
        WHERE {_library_visibility_clause('s')} AND s.standard_code=:standard_code AND sv.standard_version_code=:version_code{status_clause}
    """
    total = db.execute(text(f"SELECT count(*) {base}"), params).scalar_one()
    rows = db.execute(text(f"""
        SELECT c.clause_id::text, c.clause_code, c.clause_no, c.clause_title, c.parent_clause_code,
               c.clause_level, c.clause_text, c.clause_summary, c.disclosure_type, c.is_required,
               c.applicable_condition, c.status::text
        {base}
        ORDER BY c.clause_no
        LIMIT :limit OFFSET :offset
    """), params).mappings().all()
    return ok(_paged(rows, total, page, page_size), request_id=request.state.request_id)


@router.get("/topics")
def list_topics(request: Request, db: Session = Depends(get_db), user: dict = Depends(require_permission("topic:read")), keyword: str | None = None, topic_category: str | None = None, status: str | None = None, page: int = Query(1, ge=1), page_size: int = Query(20, ge=1, le=100)):
    _validate_enum(status, STATUS_VALUES, "TOPIC_INVALID_STATUS", "status")
    _validate_enum(topic_category, TOPIC_CATEGORY_VALUES, "TOPIC_INVALID_CATEGORY", "topic_category")
    clauses = [_library_visibility_clause()]
    params = {"tenant_id": user["current_tenant_id"], "limit": page_size, "offset": (page - 1) * page_size}
    if keyword:
        clauses.append("(topic_code ILIKE :keyword OR topic_name ILIKE :keyword)")
        params["keyword"] = f"%{keyword}%"
    if topic_category:
        clauses.append("topic_category = :topic_category")
        params["topic_category"] = topic_category
    if status:
        clauses.append("status = :status")
        params["status"] = status
    where = " AND ".join(clauses)
    total = db.execute(text(f"SELECT count(*) FROM esg_topics WHERE {where}"), params).scalar_one()
    rows = db.execute(text(f"""
        SELECT topic_id::text, tenant_id::text, topic_code, topic_name, topic_category::text,
               topic_description, default_financial_materiality::text, default_impact_materiality::text,
               common_disclosure, default_owner_department, is_common, status::text
        FROM esg_topics WHERE {where} ORDER BY topic_code LIMIT :limit OFFSET :offset
    """), params).mappings().all()
    return ok(_paged(rows, total, page, page_size), request_id=request.state.request_id)


@router.get("/topics/{topic_code}")
def get_topic(topic_code: str, request: Request, db: Session = Depends(get_db), user: dict = Depends(require_permission("topic:read"))):
    row = db.execute(text(f"""
        SELECT topic_id::text, tenant_id::text, topic_code, topic_name, topic_category::text,
               topic_description, default_financial_materiality::text, default_impact_materiality::text,
               common_disclosure, default_owner_department, is_common, status::text
        FROM esg_topics WHERE {_library_visibility_clause()} AND topic_code=:topic_code
    """), {"tenant_id": user["current_tenant_id"], "topic_code": topic_code}).mappings().first()
    if not row:
        raise ApiError(404, "TOPIC_NOT_FOUND", "Topic not found")
    return ok(dict(row), request_id=request.state.request_id)


@router.get("/metrics")
def list_metrics(request: Request, db: Session = Depends(get_db), user: dict = Depends(require_permission("metric:read")), keyword: str | None = None, metric_type: str | None = None, topic_code: str | None = None, page: int = Query(1, ge=1), page_size: int = Query(20, ge=1, le=100)):
    _validate_enum(metric_type, METRIC_TYPE_VALUES, "METRIC_INVALID_TYPE", "metric_type")
    params = {"tenant_id": user["current_tenant_id"], "limit": page_size, "offset": (page - 1) * page_size}
    joins = ""
    clauses = [_library_visibility_clause("m")]
    if topic_code:
        joins = "JOIN topic_metric_maps tmm ON tmm.metric_id=m.metric_id JOIN esg_topics t ON t.topic_id=tmm.topic_id"
        clauses.extend([_library_visibility_clause("t"), "t.topic_code=:topic_code", "t.status='active'", "tmm.status='active'"])
        params["topic_code"] = topic_code
    if keyword:
        clauses.append("(m.metric_code ILIKE :keyword OR m.metric_name ILIKE :keyword)")
        params["keyword"] = f"%{keyword}%"
    if metric_type:
        clauses.append("m.metric_type = :metric_type")
        params["metric_type"] = metric_type
    where = " AND ".join(clauses)
    total = db.execute(text(f"SELECT count(DISTINCT m.metric_id) FROM esg_metrics m {joins} WHERE {where}"), params).scalar_one()
    rows = db.execute(text(f"""
        SELECT DISTINCT m.metric_id::text, m.tenant_id::text, m.metric_code, m.metric_name, m.metric_type::text,
               m.data_type::text, m.default_unit, m.reporting_frequency, m.is_reusable,
               m.metric_description, m.filling_instruction, m.calculation_method, m.evidence_requirement_text,
               m.default_required, m.status::text
        FROM esg_metrics m {joins}
        WHERE {where}
        ORDER BY m.metric_code LIMIT :limit OFFSET :offset
    """), params).mappings().all()
    return ok(_paged(rows, total, page, page_size), request_id=request.state.request_id)


@router.get("/metrics/{metric_code}")
def get_metric(metric_code: str, request: Request, db: Session = Depends(get_db), user: dict = Depends(require_permission("metric:read"))):
    row = db.execute(text(f"""
        SELECT metric_id::text, tenant_id::text, metric_code, metric_name, metric_type::text, data_type::text,
               default_unit, reporting_frequency, is_reusable, metric_description, filling_instruction,
               calculation_method, evidence_requirement_text, default_required, status::text
        FROM esg_metrics WHERE {_library_visibility_clause()} AND metric_code=:metric_code
    """), {"tenant_id": user["current_tenant_id"], "metric_code": metric_code}).mappings().first()
    if not row:
        raise ApiError(404, "METRIC_NOT_FOUND", "Metric not found")
    return ok(dict(row), request_id=request.state.request_id)


@router.get("/standards/{standard_code}/versions/{version_code}/topics")
def list_standard_topics(standard_code: str, version_code: str, request: Request, db: Session = Depends(get_db), user: dict = Depends(require_permission("standard:read"))):
    rows = db.execute(text(f"""
        SELECT stm.map_id::text, t.topic_code, t.topic_name, t.topic_category::text, stm.related_clause_codes,
               stm.is_key_topic, stm.applicability_note, stm.status::text
        FROM standard_topic_maps stm
        JOIN standard_versions sv ON sv.standard_version_id=stm.standard_version_id
        JOIN esg_standards s ON s.standard_id=sv.standard_id
        JOIN esg_topics t ON t.topic_id=stm.topic_id
        WHERE {_library_visibility_clause('s')} AND {_library_visibility_clause('t')}
          AND s.standard_code=:standard_code AND sv.standard_version_code=:version_code AND stm.status='active' AND t.status='active'
        ORDER BY t.topic_code
    """), {"tenant_id": user["current_tenant_id"], "standard_code": standard_code, "version_code": version_code}).mappings().all()
    return ok({"items": [dict(r) for r in rows]}, request_id=request.state.request_id)


@router.get("/topics/{topic_code}/recommended-metrics")
def list_topic_metrics(topic_code: str, request: Request, db: Session = Depends(get_db), user: dict = Depends(require_permission("metric:read"))):
    rows = db.execute(text(f"""
        SELECT tmm.map_id::text, m.metric_code, m.metric_name, m.metric_type::text, m.data_type::text,
               m.default_unit, tmm.default_selected, tmm.is_required, tmm.sort_order,
               tmm.recommended_collector_role, tmm.recommended_reviewer_role
        FROM topic_metric_maps tmm
        JOIN esg_topics t ON t.topic_id=tmm.topic_id
        JOIN esg_metrics m ON m.metric_id=tmm.metric_id
        WHERE {_library_visibility_clause('t')} AND {_library_visibility_clause('m')}
          AND t.topic_code=:topic_code AND tmm.status='active' AND t.status='active' AND m.status='active'
        ORDER BY tmm.sort_order, m.metric_code
    """), {"tenant_id": user["current_tenant_id"], "topic_code": topic_code}).mappings().all()
    return ok({"topic_code": topic_code, "metrics": [dict(r) for r in rows]}, request_id=request.state.request_id)


@router.get("/clauses/{clause_code}/metrics")
def list_clause_metrics(clause_code: str, request: Request, db: Session = Depends(get_db), user: dict = Depends(require_permission("metric:read"))):
    rows = db.execute(text(f"""
        SELECT cmm.map_id::text, m.metric_code, m.metric_name, m.metric_type::text, m.default_unit,
               cmm.disclosure_requirement_type, cmm.standard_specific_instruction, cmm.source_required
        FROM clause_metric_maps cmm
        JOIN standard_clauses c ON c.clause_id=cmm.clause_id
        JOIN standard_versions sv ON sv.standard_version_id=c.standard_version_id
        JOIN esg_standards s ON s.standard_id=sv.standard_id
        JOIN esg_metrics m ON m.metric_id=cmm.metric_id
        WHERE {_library_visibility_clause('s')} AND {_library_visibility_clause('m')}
          AND c.clause_code=:clause_code AND cmm.status='active' AND c.status='active' AND m.status='active'
        ORDER BY m.metric_code
    """), {"tenant_id": user["current_tenant_id"], "clause_code": clause_code}).mappings().all()
    return ok({"clause_code": clause_code, "metrics": [dict(r) for r in rows]}, request_id=request.state.request_id)


@router.post("/standards/import-jobs")
def create_standard_import_job(payload: StandardImportPayload, request: Request, db: Session = Depends(get_db), user: dict = Depends(require_permission("standard:create"))):
    row = db.execute(text("""
        INSERT INTO async_jobs (tenant_id, job_type, job_status, progress, request_payload, created_by)
        VALUES (:tenant_id, 'standard_library_import', 'pending', 0, CAST(:request_payload AS jsonb), :created_by)
        RETURNING job_id::text, job_type, job_status::text, progress, request_payload, created_at
    """), {"tenant_id": user["current_tenant_id"], "request_payload": payload.model_dump_json(), "created_by": user["user_id"]}).mappings().first()
    write_audit_log(db, tenant_id=user["current_tenant_id"], user_id=user["user_id"], user_name=user["name"], action_type="standard.import_job_created", object_type="async_jobs", object_id=row["job_id"], description="创建标准库导入任务", ip_address=request.client.host if request.client else None, user_agent=request.headers.get("user-agent"))
    db.commit()
    return ok(dict(row), request_id=request.state.request_id)

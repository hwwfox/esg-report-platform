from fastapi import APIRouter, Depends, Query, Request
from sqlalchemy import text
from sqlalchemy.orm import Session

from app.core.errors import ApiError
from app.core.response import ok
from app.db.session import get_db
from app.modules.auth.dependencies import require_permission

router = APIRouter(prefix="/api/v1", tags=["标准议题指标"])


def tenant_scope_clause(alias: str) -> str:
    return f"({alias}.tenant_id IS NULL OR {alias}.tenant_id=:tenant_id)"


def add_like_filter(clauses: list[str], params: dict, field_exprs: list[str], keyword: str | None) -> None:
    if not keyword:
        return
    params["keyword"] = f"%{keyword}%"
    clauses.append("(" + " OR ".join(f"{field} ILIKE :keyword" for field in field_exprs) + ")")


def paged_params(page: int, page_size: int) -> dict:
    return {"limit": page_size, "offset": (page - 1) * page_size}


@router.get("/standards")
def list_standards(
    request: Request,
    db: Session = Depends(get_db),
    user: dict = Depends(require_permission("standard:read")),
    keyword: str | None = None,
    standard_type: str | None = None,
    applicable_market: str | None = None,
    status: str | None = None,
    page: int = Query(1, ge=1),
    page_size: int = Query(50, ge=1, le=100),
):
    clauses = [tenant_scope_clause("s")]
    params = {"tenant_id": user["current_tenant_id"], **paged_params(page, page_size)}
    add_like_filter(clauses, params, ["s.standard_code", "s.standard_name", "s.standard_short_name"], keyword)
    if standard_type:
        clauses.append("s.standard_type=:standard_type")
        params["standard_type"] = standard_type
    if applicable_market:
        clauses.append("s.applicable_market=:applicable_market")
        params["applicable_market"] = applicable_market
    if status:
        clauses.append("s.status=:status")
        params["status"] = status
    where = " AND ".join(clauses)
    total = db.execute(text(f"SELECT count(*) FROM esg_standards s WHERE {where}"), params).scalar_one()
    rows = db.execute(text(f"""
        SELECT s.standard_code, s.standard_name, s.standard_short_name, s.standard_type,
               s.applicable_market, sv.standard_version_code AS current_version, s.status::text
        FROM esg_standards s
        LEFT JOIN standard_versions sv
          ON sv.standard_id=s.standard_id
         AND sv.is_current=true
         AND sv.status='active'
        WHERE {where}
        ORDER BY s.standard_code
        LIMIT :limit OFFSET :offset
    """), params).mappings().all()
    return ok({"items": [dict(row) for row in rows], "total": total}, request_id=request.state.request_id)


@router.get("/topics")
def list_topics(
    request: Request,
    db: Session = Depends(get_db),
    user: dict = Depends(require_permission("topic:read")),
    keyword: str | None = None,
    topic_category: str | None = None,
    status: str | None = None,
    page: int = Query(1, ge=1),
    page_size: int = Query(50, ge=1, le=100),
):
    clauses = [tenant_scope_clause("t")]
    params = {"tenant_id": user["current_tenant_id"], **paged_params(page, page_size)}
    add_like_filter(clauses, params, ["t.topic_code", "t.topic_name", "t.topic_description"], keyword)
    if topic_category:
        if topic_category not in {"E", "S", "G"}:
            raise ApiError(400, "TOPIC_INVALID_CATEGORY", "Invalid topic category")
        clauses.append("t.topic_category=:topic_category")
        params["topic_category"] = topic_category
    if status:
        clauses.append("t.status=:status")
        params["status"] = status
    where = " AND ".join(clauses)
    total = db.execute(text(f"SELECT count(*) FROM esg_topics t WHERE {where}"), params).scalar_one()
    rows = db.execute(text(f"""
        SELECT t.topic_code, t.topic_name, t.topic_category::text, t.default_financial_materiality::text,
               t.default_impact_materiality::text, t.default_owner_department, t.status::text
        FROM esg_topics t
        WHERE {where}
        ORDER BY t.topic_category, t.topic_code
        LIMIT :limit OFFSET :offset
    """), params).mappings().all()
    return ok({"items": [dict(row) for row in rows], "total": total}, request_id=request.state.request_id)


@router.get("/metrics")
def list_metrics(
    request: Request,
    db: Session = Depends(get_db),
    user: dict = Depends(require_permission("metric:read")),
    keyword: str | None = None,
    metric_type: str | None = None,
    topic_code: str | None = None,
    page: int = Query(1, ge=1),
    page_size: int = Query(50, ge=1, le=100),
):
    clauses = [tenant_scope_clause("m")]
    params = {"tenant_id": user["current_tenant_id"], **paged_params(page, page_size)}
    joins = ""
    add_like_filter(clauses, params, ["m.metric_code", "m.metric_name", "m.metric_description"], keyword)
    if metric_type:
        if metric_type not in {"quantitative", "qualitative"}:
            raise ApiError(400, "METRIC_INVALID_TYPE", "Invalid metric type")
        clauses.append("m.metric_type=:metric_type")
        params["metric_type"] = metric_type
    if topic_code:
        joins = """
            JOIN topic_metric_maps tmm ON tmm.metric_id=m.metric_id AND tmm.status='active'
            JOIN esg_topics t ON t.topic_id=tmm.topic_id
        """
        clauses.extend(["t.topic_code=:topic_code", tenant_scope_clause("t")])
        params["topic_code"] = topic_code
    where = " AND ".join(clauses)
    total = db.execute(text(f"SELECT count(DISTINCT m.metric_id) FROM esg_metrics m {joins} WHERE {where}"), params).scalar_one()
    rows = db.execute(text(f"""
        SELECT DISTINCT m.metric_code, m.metric_name, m.metric_type::text, m.data_type::text,
               m.default_unit, m.default_required, m.status::text
        FROM esg_metrics m
        {joins}
        WHERE {where}
        ORDER BY m.metric_code
        LIMIT :limit OFFSET :offset
    """), params).mappings().all()
    return ok({"items": [dict(row) for row in rows], "total": total}, request_id=request.state.request_id)


@router.get("/topics/{topic_code}/recommended-metrics")
def recommended_metrics(topic_code: str, request: Request, db: Session = Depends(get_db), user: dict = Depends(require_permission("metric:read"))):
    params = {"tenant_id": user["current_tenant_id"], "topic_code": topic_code}
    topic = db.execute(text(f"""
        SELECT t.topic_id::text, t.topic_code, t.topic_name
        FROM esg_topics t
        WHERE {tenant_scope_clause('t')} AND t.topic_code=:topic_code AND t.status='active'
    """), params).mappings().first()
    if not topic:
        raise ApiError(404, "TOPIC_NOT_FOUND", "Topic not found")
    rows = db.execute(text(f"""
        SELECT m.metric_code, m.metric_name, m.metric_type::text, m.data_type::text,
               m.default_unit, COALESCE(tmm.is_required, m.default_required) AS default_required, m.status::text
        FROM topic_metric_maps tmm
        JOIN esg_metrics m ON m.metric_id=tmm.metric_id
        WHERE tmm.topic_id=:topic_id
          AND tmm.status='active'
          AND m.status='active'
          AND {tenant_scope_clause('m')}
        ORDER BY tmm.sort_order, m.metric_code
    """), {"tenant_id": user["current_tenant_id"], "topic_id": topic["topic_id"]}).mappings().all()
    return ok({"topic_code": topic["topic_code"], "topic_name": topic["topic_name"], "metrics": [dict(row) for row in rows]}, request_id=request.state.request_id)

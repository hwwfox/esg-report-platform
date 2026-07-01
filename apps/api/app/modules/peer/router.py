from fastapi import APIRouter, Depends, Query, Request
from pydantic import BaseModel, Field
from sqlalchemy import text
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from app.core.errors import ApiError
from app.core.response import ok
from app.db.session import get_db
from app.modules.audit.service import write_audit_log
from app.modules.auth.dependencies import require_permission
from app.modules.projects.router import _authorize_project, user_can_access_enterprise

router = APIRouter(prefix="/api/v1", tags=["GICS行业", "同行公司"])


class GicsIdentifyRequest(BaseModel):
    enterprise_name: str | None = None
    industry_description: str | None = None
    main_business: str | None = None


class GicsConfirmRequest(BaseModel):
    gics_level: int = Field(ge=1, le=4)
    gics_code: str = Field(min_length=1, max_length=32)
    confirmation_note: str | None = None


class PeerRecommendRequest(BaseModel):
    gics_level: int | None = Field(default=None, ge=1, le=4)
    gics_code: str | None = None
    prefer_same_exchange: bool = True
    prefer_business_similarity: bool = True
    prefer_industry_leaders: bool = True
    limit: int = Field(default=10, ge=1, le=50)


class PeerCompanyCreateRequest(BaseModel):
    peer_company_id: str | None = None
    company_name: str = Field(min_length=1, max_length=255)
    stock_code: str | None = None
    exchange: str | None = None
    reason: str | None = None


class PeerConfirmRequest(BaseModel):
    selected_peer_company_ids: list[str] = Field(default_factory=list)


def _gics_row(db: Session, gics_code: str, gics_level: int | None = None) -> dict | None:
    clauses = ["gics_code=:gics_code", "status='active'"]
    params: dict = {"gics_code": gics_code}
    if gics_level is not None:
        clauses.append("gics_level=:gics_level")
        params["gics_level"] = gics_level
    row = db.execute(text(f"""
        SELECT gics_code, gics_name_en, gics_name_cn, gics_level, parent_gics_code
        FROM gics_industries
        WHERE {' AND '.join(clauses)}
    """), params).mappings().first()
    return dict(row) if row else None


def _authorize_enterprise(request: Request, db: Session, user: dict, enterprise_id: str) -> dict:
    row = db.execute(text("""
        SELECT enterprise_id::text, tenant_id::text, enterprise_name, enterprise_short_name,
               stock_code, exchange, industry_description, main_business
        FROM enterprises
        WHERE tenant_id=:tenant_id AND enterprise_id=:enterprise_id AND status='active'
    """), {"tenant_id": user["current_tenant_id"], "enterprise_id": enterprise_id}).mappings().first()
    if not row or not user_can_access_enterprise(user, enterprise_id):
        write_audit_log(db, tenant_id=user["current_tenant_id"], enterprise_id=enterprise_id if row else None, user_id=user["user_id"], user_name=user["name"], action_type="security.enterprise_access_denied", object_type="enterprises", object_id=enterprise_id, description="企业不存在或无访问范围", ip_address=request.client.host if request.client else None, user_agent=request.headers.get("user-agent"))
        db.commit()
        raise ApiError(403, "AUTH_FORBIDDEN", "Access denied")
    return dict(row)


def _current_enterprise_gics(db: Session, tenant_id: str, enterprise_id: str) -> dict | None:
    row = db.execute(text("""
        SELECT h.history_id::text, h.gics_level, h.gics_code, h.confidence, h.source, h.reason,
               h.confirmed_by::text, h.confirmed_at, h.is_current,
               g.gics_name_en, g.gics_name_cn
        FROM enterprise_gics_history h
        JOIN gics_industries g ON g.gics_code=h.gics_code
        WHERE h.tenant_id=:tenant_id AND h.enterprise_id=:enterprise_id AND h.is_current=true
        ORDER BY h.confirmed_at DESC NULLS LAST, h.created_at DESC
        LIMIT 1
    """), {"tenant_id": tenant_id, "enterprise_id": enterprise_id}).mappings().first()
    return dict(row) if row else None


def _classification_payload(row: dict, *, confidence: float | None = None, reason: str | None = None) -> dict:
    return {
        "gics_level": row["gics_level"],
        "gics_code": row["gics_code"],
        "gics_name_en": row["gics_name_en"],
        "gics_name_cn": row.get("gics_name_cn"),
        "confidence": confidence,
        "reason": reason,
    }


def _candidate_gics(db: Session, enterprise: dict, payload: GicsIdentifyRequest | None = None) -> list[dict]:
    haystack = " ".join(str(value or "") for value in [
        payload.enterprise_name if payload else None,
        payload.industry_description if payload else None,
        payload.main_business if payload else None,
        enterprise.get("enterprise_name"),
        enterprise.get("industry_description"),
        enterprise.get("main_business"),
    ]).lower()
    if any(keyword in haystack for keyword in ["化工", "chemical", "材料", "specialty"]):
        preferred = ["15101050"]
    elif any(keyword in haystack for keyword in ["工业", "机械", "machinery", "manufacturing"]):
        preferred = ["20106010", "20106020"]
    elif any(keyword in haystack for keyword in ["电子", "technology", "instrument", "component"]):
        preferred = ["45203010"]
    else:
        preferred = ["20106010", "20106020"]
    rows = db.execute(text("""
        SELECT gics_code, gics_name_en, gics_name_cn, gics_level, parent_gics_code
        FROM gics_industries
        WHERE status='active' AND gics_level=4 AND gics_code = ANY(:codes)
        ORDER BY array_position(:codes, gics_code)
    """), {"codes": preferred}).mappings().all()
    return [dict(row) for row in rows]


def _peer_payload(row: dict) -> dict:
    return {
        "peer_company_id": row.get("project_peer_company_id") or row.get("peer_company_id"),
        "profile_peer_company_id": row.get("peer_company_id"),
        "company_name": row["company_name"],
        "stock_code": row.get("stock_code"),
        "exchange": row.get("exchange"),
        "gics_level_4_code": row.get("gics_level_4_code"),
        "gics_level_4_name": row.get("gics_level_4_name"),
        "business_similarity_score": float(row["business_similarity_score"]) if row.get("business_similarity_score") is not None else None,
        "industry_leader_score": float(row["industry_leader_score"]) if row.get("industry_leader_score") is not None else None,
        "report_availability_score": float(row["report_availability_score"]) if row.get("report_availability_score") is not None else None,
        "overall_score": float(row["overall_score"]) if row.get("overall_score") is not None else None,
        "recommendation_reason": row.get("recommendation_reason"),
        "latest_report_year": row.get("latest_report_year"),
        "has_report_in_library": row.get("has_report_in_library", False),
        "selected": row.get("selected", False),
        "confirmed_at": row.get("confirmed_at"),
    }


@router.get("/gics-industries")
def list_gics_industries(request: Request, db: Session = Depends(get_db), user: dict = Depends(require_permission("project:read")), parent_gics_code: str | None = None, level: int | None = Query(default=None, ge=1, le=4), keyword: str | None = None):
    clauses = ["status='active'"]
    params: dict = {}
    if parent_gics_code:
        clauses.append("parent_gics_code=:parent_gics_code")
        params["parent_gics_code"] = parent_gics_code
    if level:
        clauses.append("gics_level=:level")
        params["level"] = level
    if keyword:
        clauses.append("(gics_code ILIKE :keyword OR gics_name_en ILIKE :keyword OR gics_name_cn ILIKE :keyword)")
        params["keyword"] = f"%{keyword}%"
    rows = db.execute(text(f"""
        SELECT gics_code, gics_name_en, gics_name_cn, gics_level, parent_gics_code
        FROM gics_industries
        WHERE {' AND '.join(clauses)}
        ORDER BY gics_code
    """), params).mappings().all()
    return ok({"items": [dict(row) for row in rows]}, request_id=request.state.request_id)


@router.post("/enterprises/{enterprise_id}/gics/identify")
def identify_gics(enterprise_id: str, payload: GicsIdentifyRequest, request: Request, db: Session = Depends(get_db), user: dict = Depends(require_permission("project:read"))):
    enterprise = _authorize_enterprise(request, db, user, enterprise_id)
    candidates = _candidate_gics(db, enterprise, payload)
    if not candidates:
        raise ApiError(404, "GICS_CANDIDATE_NOT_FOUND", "No GICS candidate found")
    primary = _classification_payload(candidates[0], confidence=0.86, reason="基于企业主营业务和行业描述匹配GICS四级行业")
    alternatives = [_classification_payload(row, confidence=0.72, reason="同属相近GICS行业，可人工复核") for row in candidates[1:]]
    write_audit_log(db, tenant_id=user["current_tenant_id"], enterprise_id=enterprise_id, user_id=user["user_id"], user_name=user["name"], action_type="gics.identified", object_type="enterprises", object_id=enterprise_id, description="生成企业GICS候选结果")
    db.commit()
    return ok({"enterprise_id": enterprise_id, "identification_result": primary, "alternative_results": alternatives, "requires_human_confirmation": True}, request_id=request.state.request_id)


@router.get("/enterprises/{enterprise_id}/gics/current")
def get_current_gics(enterprise_id: str, request: Request, db: Session = Depends(get_db), user: dict = Depends(require_permission("project:read"))):
    _authorize_enterprise(request, db, user, enterprise_id)
    return ok({"enterprise_id": enterprise_id, "current_gics": _current_enterprise_gics(db, user["current_tenant_id"], enterprise_id)}, request_id=request.state.request_id)


@router.post("/enterprises/{enterprise_id}/gics/confirm")
def confirm_gics(enterprise_id: str, payload: GicsConfirmRequest, request: Request, db: Session = Depends(get_db), user: dict = Depends(require_permission("project:update"))):
    _authorize_enterprise(request, db, user, enterprise_id)
    gics = _gics_row(db, payload.gics_code, payload.gics_level)
    if not gics:
        raise ApiError(400, "GICS_INVALID_CODE", "GICS code is invalid")
    db.execute(text("""
        UPDATE enterprise_gics_history
        SET is_current=false
        WHERE tenant_id=:tenant_id AND enterprise_id=:enterprise_id AND is_current=true
    """), {"tenant_id": user["current_tenant_id"], "enterprise_id": enterprise_id})
    db.execute(text("""
        INSERT INTO enterprise_gics_history (tenant_id, enterprise_id, gics_level, gics_code, confidence, source, reason, confirmed_by, confirmed_at, is_current)
        VALUES (:tenant_id, :enterprise_id, :gics_level, :gics_code, 1.0000, 'manual', :reason, :user_id, now(), true)
    """), {"tenant_id": user["current_tenant_id"], "enterprise_id": enterprise_id, "gics_level": payload.gics_level, "gics_code": payload.gics_code, "reason": payload.confirmation_note, "user_id": user["user_id"]})
    write_audit_log(db, tenant_id=user["current_tenant_id"], enterprise_id=enterprise_id, user_id=user["user_id"], user_name=user["name"], action_type="gics.confirmed", object_type="enterprise_gics_history", object_id=enterprise_id, description="人工确认企业GICS行业")
    db.commit()
    return ok({"enterprise_id": enterprise_id, "current_gics": _current_enterprise_gics(db, user["current_tenant_id"], enterprise_id)}, request_id=request.state.request_id)


@router.get("/peer-companies/search")
def search_peer_companies(request: Request, db: Session = Depends(get_db), user: dict = Depends(require_permission("project:read")), keyword: str | None = None, gics_code: str | None = None, limit: int = Query(20, ge=1, le=100)):
    clauses = ["(metadata->>'manual_tenant_id' IS NULL OR metadata->>'manual_tenant_id'=:tenant_id)"]
    params: dict = {"limit": limit, "tenant_id": user["current_tenant_id"]}
    if keyword:
        clauses.append("(company_name ILIKE :keyword OR company_short_name ILIKE :keyword OR stock_code ILIKE :keyword)")
        params["keyword"] = f"%{keyword}%"
    if gics_code:
        clauses.append("gics_level_4_code=:gics_code")
        params["gics_code"] = gics_code
    rows = db.execute(text(f"""
        SELECT peer_company_id::text, company_name, stock_code, exchange, gics_level_4_code, gics_level_4_name,
               0.8000 AS business_similarity_score, 0.7000 AS industry_leader_score, 0.6000 AS report_availability_score,
               0.7000 AS overall_score, '手动搜索候选同行' AS recommendation_reason,
               NULL::integer AS latest_report_year, false AS has_report_in_library, false AS selected
        FROM peer_company_profiles
        WHERE {' AND '.join(clauses)}
        ORDER BY company_name
        LIMIT :limit
    """), params).mappings().all()
    return ok({"items": [_peer_payload(dict(row)) for row in rows]}, request_id=request.state.request_id)


def _project_peer_rows(db: Session, tenant_id: str, project_id: str) -> list[dict]:
    rows = db.execute(text("""
        SELECT ppc.project_peer_company_id::text, ppc.peer_company_id::text, pc.company_name, pc.stock_code, pc.exchange,
               pc.gics_level_4_code, pc.gics_level_4_name, ppc.business_similarity_score, ppc.industry_leader_score,
               ppc.report_availability_score, ppc.overall_score, ppc.recommendation_reason, ppc.latest_report_year,
               ppc.has_report_in_library, ppc.selected, ppc.confirmed_at
        FROM project_peer_companies ppc
        JOIN peer_company_profiles pc ON pc.peer_company_id=ppc.peer_company_id
        WHERE ppc.tenant_id=:tenant_id AND ppc.project_id=:project_id
        ORDER BY ppc.selected DESC, ppc.overall_score DESC NULLS LAST, pc.company_name
    """), {"tenant_id": tenant_id, "project_id": project_id}).mappings().all()
    return [dict(row) for row in rows]


@router.get("/projects/{project_id}/peer-companies")
def list_project_peers(project_id: str, request: Request, db: Session = Depends(get_db), user: dict = Depends(require_permission("project:read"))):
    _authorize_project(request, db, user, project_id)
    return ok({"items": [_peer_payload(row) for row in _project_peer_rows(db, user["current_tenant_id"], project_id)]}, request_id=request.state.request_id)


@router.post("/projects/{project_id}/peer-companies/recommend")
def recommend_peers(project_id: str, payload: PeerRecommendRequest, request: Request, db: Session = Depends(get_db), user: dict = Depends(require_permission("project:update"))):
    project = _authorize_project(request, db, user, project_id)
    current_gics = _current_enterprise_gics(db, user["current_tenant_id"], project["enterprise_id"])
    if not current_gics:
        raise ApiError(400, "GICS_NOT_CONFIRMED", "Confirm enterprise GICS before peer recommendation")
    gics_code = current_gics["gics_code"]
    gics_level = current_gics["gics_level"]
    if payload.gics_code and payload.gics_code != gics_code:
        raise ApiError(400, "GICS_OVERRIDE_NOT_ALLOWED", "Peer recommendation must use the confirmed enterprise GICS")
    if payload.gics_level and payload.gics_level != gics_level:
        raise ApiError(400, "GICS_OVERRIDE_NOT_ALLOWED", "Peer recommendation must use the confirmed enterprise GICS")
    if gics_level != 4:
        raise ApiError(400, "GICS_LEVEL_NOT_SUPPORTED", "Peer recommendation requires GICS level 4")
    rows = db.execute(text("""
        SELECT peer_company_id::text, company_name, stock_code, exchange, gics_level_4_code, gics_level_4_name,
               CASE WHEN :prefer_business_similarity THEN 0.9000 ELSE 0.7500 END AS business_similarity_score,
               CASE WHEN :prefer_industry_leaders THEN 0.8000 ELSE 0.6500 END AS industry_leader_score,
               0.7000 AS report_availability_score,
               CASE WHEN :prefer_business_similarity THEN 0.8200 ELSE 0.7000 END AS overall_score,
               '同属GICS四级行业，业务范围与报告项目企业具备可比性' AS recommendation_reason,
               NULL::integer AS latest_report_year,
               false AS has_report_in_library,
               false AS selected
        FROM peer_company_profiles pc
        WHERE gics_level_4_code=:gics_code
          AND NOT EXISTS (
              SELECT 1 FROM enterprises e
              WHERE e.tenant_id=:tenant_id AND e.enterprise_id=:enterprise_id
                AND (
                  (e.stock_code IS NOT NULL AND pc.stock_code IS NOT NULL AND e.stock_code=pc.stock_code AND COALESCE(e.exchange, '')=COALESCE(pc.exchange, ''))
                  OR lower(e.enterprise_name)=lower(pc.company_name)
                  OR (e.enterprise_short_name IS NOT NULL AND lower(e.enterprise_short_name)=lower(COALESCE(pc.company_short_name, pc.company_name)))
                )
          )
        ORDER BY company_name
        LIMIT :limit
    """), {"gics_code": gics_code, "limit": payload.limit, "prefer_business_similarity": payload.prefer_business_similarity, "prefer_industry_leaders": payload.prefer_industry_leaders, "tenant_id": user["current_tenant_id"], "enterprise_id": project["enterprise_id"]}).mappings().all()
    for row in rows:
        db.execute(text("""
            INSERT INTO project_peer_companies (tenant_id, project_id, peer_company_id, business_similarity_score, industry_leader_score, report_availability_score, overall_score, recommendation_reason, latest_report_year, has_report_in_library, selected)
            VALUES (:tenant_id, :project_id, :peer_company_id, :business_similarity_score, :industry_leader_score, :report_availability_score, :overall_score, :recommendation_reason, :latest_report_year, :has_report_in_library, false)
            ON CONFLICT (project_id, peer_company_id) DO UPDATE
            SET business_similarity_score=EXCLUDED.business_similarity_score,
                industry_leader_score=EXCLUDED.industry_leader_score,
                report_availability_score=EXCLUDED.report_availability_score,
                overall_score=EXCLUDED.overall_score,
                recommendation_reason=EXCLUDED.recommendation_reason,
                latest_report_year=EXCLUDED.latest_report_year,
                has_report_in_library=EXCLUDED.has_report_in_library
        """), {"tenant_id": user["current_tenant_id"], "project_id": project_id, **dict(row)})
    write_audit_log(db, tenant_id=user["current_tenant_id"], enterprise_id=project["enterprise_id"], project_id=project_id, user_id=user["user_id"], user_name=user["name"], action_type="peer.recommended", object_type="project_peer_companies", object_id=project_id, description="生成项目同行推荐")
    db.commit()
    return ok({"project_id": project_id, "recommended_peers": [_peer_payload(row) for row in _project_peer_rows(db, user["current_tenant_id"], project_id)]}, request_id=request.state.request_id)


def _resolve_or_create_peer_profile(db: Session, payload: PeerCompanyCreateRequest, tenant_id: str | None = None) -> dict:
    if payload.peer_company_id:
        row = db.execute(text("""
            SELECT peer_company_id::text
            FROM peer_company_profiles
            WHERE peer_company_id=:peer_company_id
              AND (metadata->>'manual_tenant_id' IS NULL OR metadata->>'manual_tenant_id'=:tenant_id)
        """), {"peer_company_id": payload.peer_company_id, "tenant_id": tenant_id}).mappings().first()
        if not row:
            raise ApiError(400, "PEER_COMPANY_INVALID", "Peer company profile is invalid")
        return dict(row)
    if payload.stock_code and payload.exchange:
        row = db.execute(text("""
            INSERT INTO peer_company_profiles (company_name, stock_code, exchange, metadata)
            VALUES (:company_name, :stock_code, :exchange, jsonb_build_object('manual_tenant_id', :tenant_id))
            ON CONFLICT (stock_code, exchange) DO UPDATE
            SET company_name=EXCLUDED.company_name, metadata=jsonb_build_object('manual_tenant_id', :tenant_id), updated_at=now()
            RETURNING peer_company_id::text
        """), {**payload.model_dump(), "tenant_id": tenant_id}).mappings().first()
    else:
        row = db.execute(text("""
            INSERT INTO peer_company_profiles (company_name, stock_code, exchange, metadata)
            VALUES (:company_name, :stock_code, :exchange, jsonb_build_object('manual_tenant_id', :tenant_id))
            RETURNING peer_company_id::text
        """), {**payload.model_dump(), "tenant_id": tenant_id}).mappings().first()
    return dict(row)


@router.post("/projects/{project_id}/peer-companies")
def add_peer_company(project_id: str, payload: PeerCompanyCreateRequest, request: Request, db: Session = Depends(get_db), user: dict = Depends(require_permission("project:update"))):
    project = _authorize_project(request, db, user, project_id)
    try:
        row = _resolve_or_create_peer_profile(db, payload, user["current_tenant_id"])
        db.execute(text("""
            INSERT INTO project_peer_companies (tenant_id, project_id, peer_company_id, business_similarity_score, industry_leader_score, report_availability_score, overall_score, recommendation_reason, selected)
            VALUES (:tenant_id, :project_id, :peer_company_id, 0.5000, 0.5000, 0.0000, 0.5000, :reason, true)
            ON CONFLICT (project_id, peer_company_id) DO UPDATE
            SET selected=true, recommendation_reason=EXCLUDED.recommendation_reason
        """), {"tenant_id": user["current_tenant_id"], "project_id": project_id, "peer_company_id": row["peer_company_id"], "reason": payload.reason or "用户手动添加同行"})
        write_audit_log(db, tenant_id=user["current_tenant_id"], enterprise_id=project["enterprise_id"], project_id=project_id, user_id=user["user_id"], user_name=user["name"], action_type="peer.added", object_type="project_peer_companies", object_id=row["peer_company_id"], description="手动添加项目同行")
        db.commit()
    except IntegrityError as exc:
        db.rollback()
        raise ApiError(400, "PEER_COMPANY_DUPLICATE", "Peer company already exists") from exc
    rows = _project_peer_rows(db, user["current_tenant_id"], project_id)
    added = next(item for item in rows if item["peer_company_id"] == row["peer_company_id"])
    return ok(_peer_payload(added), request_id=request.state.request_id)


@router.delete("/projects/{project_id}/peer-companies/{project_peer_company_id}")
def remove_project_peer(project_id: str, project_peer_company_id: str, request: Request, db: Session = Depends(get_db), user: dict = Depends(require_permission("project:update"))):
    project = _authorize_project(request, db, user, project_id)
    result = db.execute(text("""
        DELETE FROM project_peer_companies
        WHERE tenant_id=:tenant_id AND project_id=:project_id AND project_peer_company_id=:project_peer_company_id
    """), {"tenant_id": user["current_tenant_id"], "project_id": project_id, "project_peer_company_id": project_peer_company_id})
    if result.rowcount == 0:
        raise ApiError(404, "PROJECT_PEER_NOT_FOUND", "Project peer company not found")
    write_audit_log(db, tenant_id=user["current_tenant_id"], enterprise_id=project["enterprise_id"], project_id=project_id, user_id=user["user_id"], user_name=user["name"], action_type="peer.removed", object_type="project_peer_companies", object_id=project_peer_company_id, description="移除项目同行")
    db.commit()
    return ok({"removed": True}, request_id=request.state.request_id)


@router.post("/projects/{project_id}/peer-companies/confirm")
def confirm_peer_pool(project_id: str, payload: PeerConfirmRequest, request: Request, db: Session = Depends(get_db), user: dict = Depends(require_permission("project:update"))):
    project = _authorize_project(request, db, user, project_id)
    if not payload.selected_peer_company_ids:
        raise ApiError(400, "PEER_SELECTION_REQUIRED", "Select at least one peer company")
    db.execute(text("""
        UPDATE project_peer_companies
        SET selected=false, confirmed_at=NULL
        WHERE tenant_id=:tenant_id AND project_id=:project_id
    """), {"tenant_id": user["current_tenant_id"], "project_id": project_id})
    result = db.execute(text("""
        UPDATE project_peer_companies
        SET selected=true, confirmed_at=now()
        WHERE tenant_id=:tenant_id AND project_id=:project_id AND project_peer_company_id = ANY(:selected_ids)
    """), {"tenant_id": user["current_tenant_id"], "project_id": project_id, "selected_ids": payload.selected_peer_company_ids})
    if result.rowcount != len(set(payload.selected_peer_company_ids)):
        db.rollback()
        raise ApiError(400, "PEER_SELECTION_INVALID", "Selected peer companies are invalid")
    write_audit_log(db, tenant_id=user["current_tenant_id"], enterprise_id=project["enterprise_id"], project_id=project_id, user_id=user["user_id"], user_name=user["name"], action_type="peer.pool_confirmed", object_type="project_peer_companies", object_id=project_id, description="确认项目同行池")
    db.commit()
    return ok({"project_id": project_id, "confirmed_count": result.rowcount, "items": [_peer_payload(row) for row in _project_peer_rows(db, user["current_tenant_id"], project_id)]}, request_id=request.state.request_id)

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
from app.modules.projects.router import user_can_access_enterprise

router = APIRouter(prefix="/api/v1/enterprises", tags=["企业管理"])


class EnterprisePayload(BaseModel):
    enterprise_name: str = Field(min_length=1, max_length=255)
    enterprise_short_name: str | None = None
    enterprise_code: str | None = None
    stock_code: str | None = None
    exchange: str | None = None
    country_or_region: str | None = None
    industry_description: str | None = None
    main_business: str | None = None
    status: str = "active"


class EnterpriseUpdatePayload(BaseModel):
    enterprise_name: str | None = Field(default=None, min_length=1, max_length=255)
    enterprise_short_name: str | None = None
    enterprise_code: str | None = None
    stock_code: str | None = None
    exchange: str | None = None
    country_or_region: str | None = None
    industry_description: str | None = None
    main_business: str | None = None
    status: str | None = None


def _enterprise_select(where: str) -> str:
    return f"""
        SELECT enterprise_id::text, tenant_id::text, enterprise_code, enterprise_name, enterprise_short_name,
               stock_code, exchange, country_or_region, industry_description, main_business, status::text,
               created_at, updated_at
        FROM enterprises
        WHERE {where}
    """


def _get_enterprise(db: Session, tenant_id: str, enterprise_id: str) -> dict | None:
    row = db.execute(text(_enterprise_select("tenant_id=:tenant_id AND enterprise_id=:enterprise_id")), {"tenant_id": tenant_id, "enterprise_id": enterprise_id}).mappings().first()
    return dict(row) if row else None


def _deny_enterprise(request: Request, db: Session, user: dict, enterprise_id: str | None = None, *, verified_enterprise_id: str | None = None) -> None:
    write_audit_log(db, tenant_id=user["current_tenant_id"], enterprise_id=verified_enterprise_id, user_id=user["user_id"], user_name=user["name"], action_type="security.enterprise_access_denied", object_type="enterprises", object_id=enterprise_id, description="企业不存在或无访问范围", ip_address=request.client.host if request.client else None, user_agent=request.headers.get("user-agent"))
    db.commit()
    raise ApiError(403, "AUTH_FORBIDDEN", "Access denied")


@router.get("")
def list_enterprises(request: Request, db: Session = Depends(get_db), user: dict = Depends(require_permission("enterprise:read")), keyword: str | None = None, exchange: str | None = None, status: str | None = None, page: int = Query(1, ge=1), page_size: int = Query(20, ge=1, le=100)):
    enterprise_ids = [item["enterprise_id"] for item in user.get("enterprises", [])]
    if not enterprise_ids:
        return ok({"items": [], "page": page, "page_size": page_size, "total": 0}, request_id=request.state.request_id)
    clauses = ["tenant_id=:tenant_id", "enterprise_id = ANY(:enterprise_ids)"]
    params = {"tenant_id": user["current_tenant_id"], "enterprise_ids": enterprise_ids, "limit": page_size, "offset": (page - 1) * page_size}
    if keyword:
        clauses.append("(enterprise_name ILIKE :keyword OR enterprise_short_name ILIKE :keyword OR enterprise_code ILIKE :keyword)")
        params["keyword"] = f"%{keyword}%"
    if exchange:
        clauses.append("exchange=:exchange")
        params["exchange"] = exchange
    if status:
        clauses.append("status=:status")
        params["status"] = status
    where = " AND ".join(clauses)
    total = db.execute(text(f"SELECT count(*) FROM enterprises WHERE {where}"), params).scalar_one()
    rows = db.execute(text(_enterprise_select(where) + " ORDER BY enterprise_name LIMIT :limit OFFSET :offset"), params).mappings().all()
    return ok({"items": [dict(r) for r in rows], "page": page, "page_size": page_size, "total": total}, request_id=request.state.request_id)


@router.post("")
def create_enterprise(payload: EnterprisePayload, request: Request, db: Session = Depends(get_db), user: dict = Depends(require_permission("enterprise:create"))):
    if payload.status not in {"active", "inactive"}:
        raise ApiError(400, "ENTERPRISE_INVALID_STATUS", "Invalid enterprise status")
    try:
        row = db.execute(text("""
            INSERT INTO enterprises (tenant_id, enterprise_code, enterprise_name, enterprise_short_name, stock_code, exchange, country_or_region, industry_description, main_business, status)
            VALUES (:tenant_id, :enterprise_code, :enterprise_name, :enterprise_short_name, :stock_code, :exchange, :country_or_region, :industry_description, :main_business, :status)
            RETURNING enterprise_id::text
        """), {"tenant_id": user["current_tenant_id"], **payload.model_dump()}).mappings().first()
        db.execute(text("""
            INSERT INTO enterprise_user_access (tenant_id, enterprise_id, user_id, access_scope, status)
            VALUES (:tenant_id, :enterprise_id, :user_id, 'all', 'active')
            ON CONFLICT (enterprise_id, user_id) DO UPDATE SET status='active', access_scope='all'
        """), {"tenant_id": user["current_tenant_id"], "enterprise_id": row["enterprise_id"], "user_id": user["user_id"]})
        write_audit_log(db, tenant_id=user["current_tenant_id"], enterprise_id=row["enterprise_id"], user_id=user["user_id"], user_name=user["name"], action_type="enterprise.created", object_type="enterprises", object_id=row["enterprise_id"], description="创建企业")
        db.commit()
    except IntegrityError as exc:
        db.rollback()
        raise ApiError(400, "ENTERPRISE_DUPLICATE", "Enterprise code or name already exists") from exc
    return ok(_get_enterprise(db, user["current_tenant_id"], row["enterprise_id"]), request_id=request.state.request_id)


@router.get("/{enterprise_id}")
def get_enterprise(enterprise_id: str, request: Request, db: Session = Depends(get_db), user: dict = Depends(require_permission("enterprise:read"))):
    if not user_can_access_enterprise(user, enterprise_id):
        _deny_enterprise(request, db, user, enterprise_id)
    enterprise = _get_enterprise(db, user["current_tenant_id"], enterprise_id)
    if not enterprise:
        _deny_enterprise(request, db, user, enterprise_id)
    return ok(enterprise, request_id=request.state.request_id)


@router.patch("/{enterprise_id}")
def update_enterprise(enterprise_id: str, payload: EnterpriseUpdatePayload, request: Request, db: Session = Depends(get_db), user: dict = Depends(require_permission("enterprise:update"))):
    if not user_can_access_enterprise(user, enterprise_id):
        _deny_enterprise(request, db, user, enterprise_id)
    enterprise = _get_enterprise(db, user["current_tenant_id"], enterprise_id)
    if not enterprise:
        _deny_enterprise(request, db, user, enterprise_id)
    updates = payload.model_dump(exclude_unset=True)
    if "enterprise_name" in updates and updates["enterprise_name"] is None:
        raise ApiError(400, "ENTERPRISE_NAME_REQUIRED", "Enterprise name is required")
    if "status" in updates and updates["status"] not in {"active", "inactive"}:
        raise ApiError(400, "ENTERPRISE_INVALID_STATUS", "Invalid enterprise status")
    if not updates:
        return ok(enterprise, request_id=request.state.request_id)
    allowed = {"enterprise_code", "enterprise_name", "enterprise_short_name", "stock_code", "exchange", "country_or_region", "industry_description", "main_business", "status"}
    set_clause = ", ".join(f"{key}=:{key}" for key in updates if key in allowed)
    try:
        db.execute(text(f"""
            UPDATE enterprises SET {set_clause}, updated_at=now()
            WHERE tenant_id=:tenant_id AND enterprise_id=:enterprise_id
        """), {"tenant_id": user["current_tenant_id"], "enterprise_id": enterprise_id, **updates})
        write_audit_log(db, tenant_id=user["current_tenant_id"], enterprise_id=enterprise_id, user_id=user["user_id"], user_name=user["name"], action_type="enterprise.updated", object_type="enterprises", object_id=enterprise_id, description="更新企业")
        db.commit()
    except IntegrityError as exc:
        db.rollback()
        raise ApiError(400, "ENTERPRISE_DUPLICATE", "Enterprise code or name already exists") from exc
    return ok(_get_enterprise(db, user["current_tenant_id"], enterprise_id), request_id=request.state.request_id)

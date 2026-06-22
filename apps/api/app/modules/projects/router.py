from fastapi import APIRouter, Depends, Request
from sqlalchemy import text
from sqlalchemy.orm import Session
from app.core.errors import ApiError
from app.core.response import ok
from app.db.session import get_db
from app.modules.audit.service import write_audit_log
from app.modules.auth.dependencies import require_permission

router = APIRouter(prefix="/api/v1/projects", tags=["报告项目"])


def user_can_access_enterprise(user: dict, enterprise_id: str) -> bool:
    allowed_enterprises = {item["enterprise_id"] for item in user.get("enterprises", [])}
    return enterprise_id in allowed_enterprises


@router.get("/{project_id}/dashboard")
def dashboard(project_id: str, request: Request, db: Session = Depends(get_db), user: dict = Depends(require_permission("project:read"))):
    row = db.execute(text("""
        SELECT project_id::text, tenant_id::text, enterprise_id::text, project_name, report_year, report_type, report_language, project_status
        FROM report_projects
        WHERE tenant_id=:tenant_id AND project_id=:project_id
    """), {"tenant_id": user["current_tenant_id"], "project_id": project_id}).mappings().first()
    if not row:
        write_audit_log(db, tenant_id=user["current_tenant_id"], user_id=user["user_id"], user_name=user["name"], action_type="security.project_access_denied", object_type="report_projects", description="项目不存在或跨租户访问被拒绝")
        db.commit()
        raise ApiError(403, "AUTH_FORBIDDEN", "Access denied")
    if not user_can_access_enterprise(user, row["enterprise_id"]):
        write_audit_log(db, tenant_id=user["current_tenant_id"], enterprise_id=row["enterprise_id"], project_id=project_id, user_id=user["user_id"], user_name=user["name"], action_type="security.project_access_denied", object_type="report_projects", object_id=project_id, description="无企业访问范围")
        db.commit()
        raise ApiError(403, "AUTH_FORBIDDEN", "Access denied")
    return ok({"project": dict(row), "progress": {}, "risks": [], "next_steps": []}, request_id=request.state.request_id)

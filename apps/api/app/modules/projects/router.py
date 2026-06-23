from datetime import date

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

router = APIRouter(prefix="/api/v1/projects", tags=["报告项目"])

REPORT_LANGUAGES = {"zh", "en", "bilingual"}

PROJECT_STATUSES = {
    "draft", "peer_analysis", "topic_confirmation", "task_assignment", "data_collection",
    "department_review", "writing", "chapter_review", "full_review", "export_ready", "completed", "archived",
}
ALLOWED_TRANSITIONS = {
    "draft": {"peer_analysis", "archived"},
    "peer_analysis": {"topic_confirmation", "archived"},
    "topic_confirmation": {"task_assignment", "archived"},
    "task_assignment": {"data_collection", "archived"},
    "data_collection": {"department_review", "archived"},
    "department_review": {"writing", "data_collection", "archived"},
    "writing": {"chapter_review", "archived"},
    "chapter_review": {"full_review", "writing", "archived"},
    "full_review": {"export_ready", "chapter_review", "archived"},
    "export_ready": {"completed", "full_review", "archived"},
    "completed": {"archived"},
    "archived": set(),
}


class ProjectPayload(BaseModel):
    enterprise_id: str
    project_name: str = Field(min_length=1, max_length=255)
    report_year: int
    report_type: str = "ESG"
    report_language: str = "zh"
    reporting_period_start: date | None = None
    reporting_period_end: date | None = None
    report_boundary: str | None = None
    selected_standard_codes: list[str] = Field(default_factory=list)
    project_owner_user_id: str


class ProjectUpdatePayload(BaseModel):
    project_name: str | None = Field(default=None, min_length=1, max_length=255)
    report_year: int | None = None
    report_type: str | None = None
    report_language: str | None = None
    reporting_period_start: date | None = None
    reporting_period_end: date | None = None
    report_boundary: str | None = None
    selected_standard_codes: list[str] | None = None
    project_owner_user_id: str | None = None


class StatusTransitionPayload(BaseModel):
    target_status: str


class ProjectMemberPayload(BaseModel):
    user_id: str
    project_role: str = Field(min_length=1, max_length=64)
    org_unit_id: str | None = None


def user_can_access_enterprise(user: dict, enterprise_id: str) -> bool:
    allowed_enterprises = {item["enterprise_id"] for item in user.get("enterprises", [])}
    return enterprise_id in allowed_enterprises


def validate_report_year(year: int) -> None:
    current_year = date.today().year
    if year < 2000 or year > current_year + 1:
        raise ApiError(400, "PROJECT_INVALID_REPORT_YEAR", "Report year is invalid")


def validate_report_language(report_language: str | None) -> None:
    if report_language is not None and report_language not in REPORT_LANGUAGES:
        raise ApiError(400, "PROJECT_INVALID_REPORT_LANGUAGE", "Report language is invalid")


def validate_status_transition(current_status: str, target_status: str) -> None:
    if target_status not in PROJECT_STATUSES:
        raise ApiError(400, "PROJECT_INVALID_STATUS", "Invalid project status")
    if target_status not in ALLOWED_TRANSITIONS[current_status]:
        raise ApiError(400, "PROJECT_STATUS_TRANSITION_INVALID", "Invalid project status transition")


def _project_select(where: str) -> str:
    return f"""
        SELECT project_id::text, tenant_id::text, enterprise_id::text, project_name, report_year, report_type,
               report_language, reporting_period_start, reporting_period_end, report_boundary,
               project_owner_user_id::text, project_status::text, selected_standard_codes, created_at, updated_at
        FROM report_projects
        WHERE {where}
    """


def _get_project(db: Session, tenant_id: str, project_id: str) -> dict | None:
    row = db.execute(text(_project_select("tenant_id=:tenant_id AND project_id=:project_id")), {"tenant_id": tenant_id, "project_id": project_id}).mappings().first()
    return dict(row) if row else None


def _authorize_project(request: Request, db: Session, user: dict, project_id: str) -> dict:
    project = _get_project(db, user["current_tenant_id"], project_id)
    if not project or not user_can_access_enterprise(user, project["enterprise_id"]):
        write_audit_log(db, tenant_id=user["current_tenant_id"], enterprise_id=project["enterprise_id"] if project else None, project_id=project_id if project else None, user_id=user["user_id"], user_name=user["name"], action_type="security.project_access_denied", object_type="report_projects", object_id=project_id if project else None, description="项目不存在或无访问范围", ip_address=request.client.host if request.client else None, user_agent=request.headers.get("user-agent"))
        db.commit()
        raise ApiError(403, "AUTH_FORBIDDEN", "Access denied")
    return project


def _authorize_enterprise(request: Request, db: Session, user: dict, enterprise_id: str) -> None:
    row = db.execute(text("SELECT enterprise_id::text FROM enterprises WHERE tenant_id=:tenant_id AND enterprise_id=:enterprise_id"), {"tenant_id": user["current_tenant_id"], "enterprise_id": enterprise_id}).first()
    if not row or not user_can_access_enterprise(user, enterprise_id):
        write_audit_log(db, tenant_id=user["current_tenant_id"], enterprise_id=row[0] if row else None, user_id=user["user_id"], user_name=user["name"], action_type="security.enterprise_access_denied", object_type="enterprises", object_id=enterprise_id, description="企业不存在或无访问范围")
        db.commit()
        raise ApiError(403, "AUTH_FORBIDDEN", "Access denied")


def _validate_project_user_scope(db: Session, *, tenant_id: str, enterprise_id: str, user_id: str, org_unit_id: str | None = None) -> None:
    row = db.execute(text("""
        SELECT u.user_id::text
        FROM users u
        JOIN enterprise_user_access eua
          ON eua.tenant_id=u.tenant_id
         AND eua.user_id=u.user_id
         AND eua.enterprise_id=:enterprise_id
         AND eua.status='active'
        WHERE u.tenant_id=:tenant_id
          AND u.user_id=:user_id
          AND u.status='active'
    """), {"tenant_id": tenant_id, "enterprise_id": enterprise_id, "user_id": user_id}).first()
    if not row:
        raise ApiError(400, "PROJECT_MEMBER_USER_INVALID", "Project member user is invalid")
    if org_unit_id:
        org_unit_row = db.execute(text("""
            SELECT org_unit_id::text
            FROM org_units
            WHERE tenant_id=:tenant_id
              AND enterprise_id=:enterprise_id
              AND org_unit_id=:org_unit_id
              AND status='active'
        """), {"tenant_id": tenant_id, "enterprise_id": enterprise_id, "org_unit_id": org_unit_id}).first()
        if not org_unit_row:
            raise ApiError(400, "PROJECT_MEMBER_ORG_UNIT_INVALID", "Project member organization unit is invalid")


def _upsert_project_member(db: Session, *, tenant_id: str, project_id: str, user_id: str, project_role: str, org_unit_id: str | None) -> None:
    existing = db.execute(text("""
        SELECT project_member_id::text
        FROM project_members
        WHERE tenant_id=:tenant_id
          AND project_id=:project_id
          AND user_id=:user_id
          AND project_role=:project_role
          AND org_unit_id IS NOT DISTINCT FROM :org_unit_id
        ORDER BY created_at DESC
        LIMIT 1
    """), {"tenant_id": tenant_id, "project_id": project_id, "user_id": user_id, "project_role": project_role, "org_unit_id": org_unit_id}).mappings().first()
    if existing:
        db.execute(text("""
            UPDATE project_members
            SET status='active'
            WHERE tenant_id=:tenant_id AND project_member_id=:project_member_id
        """), {"tenant_id": tenant_id, "project_member_id": existing["project_member_id"]})
        return
    db.execute(text("""
        INSERT INTO project_members (tenant_id, project_id, user_id, project_role, org_unit_id, status)
        VALUES (:tenant_id, :project_id, :user_id, :project_role, :org_unit_id, 'active')
    """), {"tenant_id": tenant_id, "project_id": project_id, "user_id": user_id, "project_role": project_role, "org_unit_id": org_unit_id})


@router.get("")
def list_projects(request: Request, db: Session = Depends(get_db), user: dict = Depends(require_permission("project:read")), enterprise_id: str | None = None, report_year: int | None = None, project_status: str | None = None, keyword: str | None = None, page: int = Query(1, ge=1), page_size: int = Query(20, ge=1, le=100)):
    allowed = [item["enterprise_id"] for item in user.get("enterprises", [])]
    if enterprise_id:
        if enterprise_id not in allowed:
            _authorize_enterprise(request, db, user, enterprise_id)
        allowed = [enterprise_id]
    if not allowed:
        return ok({"items": [], "page": page, "page_size": page_size, "total": 0}, request_id=request.state.request_id)
    clauses = ["tenant_id=:tenant_id", "enterprise_id = ANY(:enterprise_ids)"]
    params = {"tenant_id": user["current_tenant_id"], "enterprise_ids": allowed, "limit": page_size, "offset": (page - 1) * page_size}
    if report_year:
        clauses.append("report_year=:report_year")
        params["report_year"] = report_year
    if project_status:
        clauses.append("project_status=:project_status")
        params["project_status"] = project_status
    if keyword:
        clauses.append("project_name ILIKE :keyword")
        params["keyword"] = f"%{keyword}%"
    where = " AND ".join(clauses)
    total = db.execute(text(f"SELECT count(*) FROM report_projects WHERE {where}"), params).scalar_one()
    rows = db.execute(text(_project_select(where) + " ORDER BY created_at DESC LIMIT :limit OFFSET :offset"), params).mappings().all()
    return ok({"items": [dict(r) for r in rows], "page": page, "page_size": page_size, "total": total}, request_id=request.state.request_id)


@router.post("")
def create_project(payload: ProjectPayload, request: Request, db: Session = Depends(get_db), user: dict = Depends(require_permission("project:create"))):
    validate_report_year(payload.report_year)
    validate_report_language(payload.report_language)
    if not payload.project_owner_user_id:
        raise ApiError(400, "PROJECT_OWNER_REQUIRED", "Project owner is required")
    _authorize_enterprise(request, db, user, payload.enterprise_id)
    _validate_project_user_scope(db, tenant_id=user["current_tenant_id"], enterprise_id=payload.enterprise_id, user_id=payload.project_owner_user_id)
    try:
        row = db.execute(text("""
            INSERT INTO report_projects (tenant_id, enterprise_id, project_name, report_year, report_type, report_language,
              reporting_period_start, reporting_period_end, report_boundary, project_owner_user_id, selected_standard_codes, created_by)
            VALUES (:tenant_id, :enterprise_id, :project_name, :report_year, :report_type, :report_language,
              :reporting_period_start, :reporting_period_end, :report_boundary, :project_owner_user_id, :selected_standard_codes, :created_by)
            RETURNING project_id::text
        """), {"tenant_id": user["current_tenant_id"], "created_by": user["user_id"], **payload.model_dump()}).mappings().first()
        _upsert_project_member(db, tenant_id=user["current_tenant_id"], project_id=row["project_id"], user_id=payload.project_owner_user_id, project_role="owner", org_unit_id=None)
        write_audit_log(db, tenant_id=user["current_tenant_id"], enterprise_id=payload.enterprise_id, project_id=row["project_id"], user_id=user["user_id"], user_name=user["name"], action_type="project.created", object_type="report_projects", object_id=row["project_id"], description="创建报告项目")
        db.commit()
    except IntegrityError as exc:
        db.rollback()
        raise ApiError(400, "PROJECT_DUPLICATE", "Project already exists or references invalid data") from exc
    return ok(_get_project(db, user["current_tenant_id"], row["project_id"]), request_id=request.state.request_id)


@router.get("/{project_id}")
def get_project(project_id: str, request: Request, db: Session = Depends(get_db), user: dict = Depends(require_permission("project:read"))):
    return ok(_authorize_project(request, db, user, project_id), request_id=request.state.request_id)


@router.patch("/{project_id}")
def update_project(project_id: str, payload: ProjectUpdatePayload, request: Request, db: Session = Depends(get_db), user: dict = Depends(require_permission("project:update"))):
    project = _authorize_project(request, db, user, project_id)
    updates = payload.model_dump(exclude_unset=True)
    if "report_year" in updates and updates["report_year"] is not None:
        validate_report_year(updates["report_year"])
    if "report_language" in updates:
        validate_report_language(updates["report_language"])
    if "project_owner_user_id" in updates and not updates["project_owner_user_id"]:
        raise ApiError(400, "PROJECT_OWNER_REQUIRED", "Project owner is required")
    if updates.get("project_owner_user_id"):
        _validate_project_user_scope(db, tenant_id=user["current_tenant_id"], enterprise_id=project["enterprise_id"], user_id=updates["project_owner_user_id"])
    if not updates:
        return ok(project, request_id=request.state.request_id)
    allowed = {"project_name", "report_year", "report_type", "report_language", "reporting_period_start", "reporting_period_end", "report_boundary", "selected_standard_codes", "project_owner_user_id"}
    set_clause = ", ".join(f"{key}=:{key}" for key in updates if key in allowed)
    try:
        db.execute(text(f"UPDATE report_projects SET {set_clause}, updated_at=now() WHERE tenant_id=:tenant_id AND enterprise_id=:enterprise_id AND project_id=:project_id"), {"tenant_id": user["current_tenant_id"], "enterprise_id": project["enterprise_id"], "project_id": project_id, **updates})
        if updates.get("project_owner_user_id"):
            db.execute(text("""
                UPDATE project_members
                SET status='inactive'
                WHERE tenant_id=:tenant_id AND project_id=:project_id AND project_role='owner' AND user_id<>:user_id
            """), {"tenant_id": user["current_tenant_id"], "project_id": project_id, "user_id": updates["project_owner_user_id"]})
            _upsert_project_member(db, tenant_id=user["current_tenant_id"], project_id=project_id, user_id=updates["project_owner_user_id"], project_role="owner", org_unit_id=None)
        write_audit_log(db, tenant_id=user["current_tenant_id"], enterprise_id=project["enterprise_id"], project_id=project_id, user_id=user["user_id"], user_name=user["name"], action_type="project.updated", object_type="report_projects", object_id=project_id, description="更新报告项目")
        db.commit()
    except IntegrityError as exc:
        db.rollback()
        raise ApiError(400, "PROJECT_DUPLICATE", "Project already exists or references invalid data") from exc
    return ok(_get_project(db, user["current_tenant_id"], project_id), request_id=request.state.request_id)


@router.post("/{project_id}/status")
def transition_status(project_id: str, payload: StatusTransitionPayload, request: Request, db: Session = Depends(get_db), user: dict = Depends(require_permission("project:update"))):
    project = _authorize_project(request, db, user, project_id)
    validate_status_transition(project["project_status"], payload.target_status)
    db.execute(text("UPDATE report_projects SET project_status=:target_status, updated_at=now(), completed_at=CASE WHEN :target_status='completed' THEN now() ELSE completed_at END, archived_at=CASE WHEN :target_status='archived' THEN now() ELSE archived_at END WHERE tenant_id=:tenant_id AND enterprise_id=:enterprise_id AND project_id=:project_id"), {"target_status": payload.target_status, "tenant_id": user["current_tenant_id"], "enterprise_id": project["enterprise_id"], "project_id": project_id})
    write_audit_log(db, tenant_id=user["current_tenant_id"], enterprise_id=project["enterprise_id"], project_id=project_id, user_id=user["user_id"], user_name=user["name"], action_type="project.status_changed", object_type="report_projects", object_id=project_id, description=f"项目状态流转: {project['project_status']} -> {payload.target_status}")
    db.commit()
    return ok(_get_project(db, user["current_tenant_id"], project_id), request_id=request.state.request_id)


@router.get("/{project_id}/dashboard")
def dashboard(project_id: str, request: Request, db: Session = Depends(get_db), user: dict = Depends(require_permission("project:read"))):
    project = _authorize_project(request, db, user, project_id)
    return ok({"project": project, "progress": {"status_order": list(ALLOWED_TRANSITIONS).index(project["project_status"])}, "risks": [], "next_steps": []}, request_id=request.state.request_id)


@router.get("/{project_id}/members")
def list_members(project_id: str, request: Request, db: Session = Depends(get_db), user: dict = Depends(require_permission("project:read"))):
    project = _authorize_project(request, db, user, project_id)
    rows = db.execute(text("""
        SELECT pm.project_member_id::text, pm.project_id::text, pm.user_id::text, u.name, u.email, pm.project_role,
               pm.org_unit_id::text, pm.status::text, pm.created_at
        FROM project_members pm
        JOIN users u ON u.tenant_id=pm.tenant_id AND u.user_id=pm.user_id
        WHERE pm.tenant_id=:tenant_id AND pm.project_id=:project_id AND pm.status='active'
        ORDER BY pm.created_at DESC
    """), {"tenant_id": user["current_tenant_id"], "project_id": project["project_id"]}).mappings().all()
    return ok({"items": [dict(r) for r in rows]}, request_id=request.state.request_id)


@router.post("/{project_id}/members")
def add_member(project_id: str, payload: ProjectMemberPayload, request: Request, db: Session = Depends(get_db), user: dict = Depends(require_permission("project:update"))):
    project = _authorize_project(request, db, user, project_id)
    _validate_project_user_scope(db, tenant_id=user["current_tenant_id"], enterprise_id=project["enterprise_id"], user_id=payload.user_id, org_unit_id=payload.org_unit_id)
    _upsert_project_member(db, tenant_id=user["current_tenant_id"], project_id=project_id, user_id=payload.user_id, project_role=payload.project_role, org_unit_id=payload.org_unit_id)
    write_audit_log(db, tenant_id=user["current_tenant_id"], enterprise_id=project["enterprise_id"], project_id=project_id, user_id=user["user_id"], user_name=user["name"], action_type="project.member_added", object_type="project_members", object_id=payload.user_id, description="添加项目成员")
    db.commit()
    return list_members(project_id, request, db, user)


@router.delete("/{project_id}/members/{user_id}")
def remove_member(project_id: str, user_id: str, request: Request, db: Session = Depends(get_db), user: dict = Depends(require_permission("project:update"))):
    project = _authorize_project(request, db, user, project_id)
    db.execute(text("UPDATE project_members SET status='inactive' WHERE tenant_id=:tenant_id AND project_id=:project_id AND user_id=:user_id"), {"tenant_id": user["current_tenant_id"], "project_id": project_id, "user_id": user_id})
    write_audit_log(db, tenant_id=user["current_tenant_id"], enterprise_id=project["enterprise_id"], project_id=project_id, user_id=user["user_id"], user_name=user["name"], action_type="project.member_removed", object_type="project_members", object_id=user_id, description="移除项目成员")
    db.commit()
    return ok({"removed": True}, request_id=request.state.request_id)

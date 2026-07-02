from __future__ import annotations

from decimal import Decimal, InvalidOperation
from typing import Any
from fastapi import APIRouter, Depends, Request
from pydantic import BaseModel, Field
from sqlalchemy import text
from sqlalchemy.orm import Session

from app.core.errors import ApiError
from app.core.response import ok
from app.db.session import get_db
from app.modules.audit.service import write_audit_log
from app.modules.auth.dependencies import has_permission, require_permission
from app.modules.projects.router import _authorize_project
from app.modules.esg_data_router import create_esg_data_records_for_submission

router = APIRouter(prefix="/api/v1", tags=["任务分配", "部门采集", "部门审核"])


class GenerateTasksRequest(BaseModel):
    generate_note: str | None = Field(default=None, max_length=1000)


class SubmissionItemRequest(BaseModel):
    project_metric_id: str
    value: Decimal | None = None
    text_value: str | None = None
    unit: str | None = None
    period: str | None = None
    org_unit_id: str | None = None
    description: str | None = None
    attachment_file_ids: list[str] = Field(default_factory=list)


class SubmissionDraftRequest(BaseModel):
    items: list[SubmissionItemRequest] = Field(default_factory=list)
    submission_note: str | None = None
    warning_confirmation_note: str | None = None


class SubmitTaskRequest(BaseModel):
    submission_note: str | None = None
    confirmed_warning_issue_ids: list[str] = Field(default_factory=list)
    warning_confirmation_note: str | None = None


class ReviewSubmitRequest(BaseModel):
    review_action: str = Field(pattern="^(approve|return|request_evidence|confirm_abnormal|mark_not_applicable)$")
    review_note: str | None = None
    confirmed_validation_issue_ids: list[str] = Field(default_factory=list)
    return_items: list[dict[str, Any]] = Field(default_factory=list)


def _tenant_id(user: dict) -> str:
    return str(user["current_tenant_id"])


def _task_row(db: Session, tenant_id: str, task_id: str) -> dict | None:
    row = db.execute(text("""
        SELECT ct.task_id::text, ct.tenant_id::text, ct.project_id::text, rp.enterprise_id::text,
               rp.project_name, ct.project_topic_id::text, ct.assignment_id::text, ct.task_name,
               ct.owner_org_unit_id::text, pou.org_unit_name AS owner_org_unit_name,
               ct.collector_user_id::text, cu.name AS collector_name, ct.reviewer_user_id::text,
               ru.name AS reviewer_name, ct.due_date, ct.task_status::text, ct.submitted_at,
               ct.reviewed_at, ct.created_at, ct.updated_at,
               pt.topic_code, pt.topic_name, pt.topic_category::text, pt.priority
        FROM collection_tasks ct
        JOIN report_projects rp ON rp.tenant_id=ct.tenant_id AND rp.project_id=ct.project_id
        JOIN project_topics pt ON pt.tenant_id=ct.tenant_id AND pt.project_topic_id=ct.project_topic_id
        LEFT JOIN project_org_units pou ON pou.project_org_unit_id=ct.owner_org_unit_id
        LEFT JOIN users cu ON cu.tenant_id=ct.tenant_id AND cu.user_id=ct.collector_user_id
        LEFT JOIN users ru ON ru.tenant_id=ct.tenant_id AND ru.user_id=ct.reviewer_user_id
        WHERE ct.tenant_id=:tenant_id AND ct.task_id=:task_id
    """), {"tenant_id": tenant_id, "task_id": task_id}).mappings().first()
    return dict(row) if row else None


def _assert_task_visible(request: Request, db: Session, user: dict, task: dict | None, *, mode: str) -> dict:
    if not task:
        raise ApiError(404, "COLLECTION_TASK_NOT_FOUND", "Collection task not found")
    _authorize_project(request, db, user, task["project_id"])
    if has_permission(user, "project:*") or has_permission(user, "task:*"):
        return task
    if mode == "collect" and str(task.get("collector_user_id")) == str(user["user_id"]):
        return task
    if mode == "review" and str(task.get("reviewer_user_id")) == str(user["user_id"]):
        return task
    write_audit_log(db, tenant_id=_tenant_id(user), enterprise_id=task["enterprise_id"], project_id=task["project_id"], user_id=user["user_id"], user_name=user["name"], action_type="security.collection_task_access_denied", object_type="collection_tasks", object_id=task["task_id"], description="采集/审核任务越权访问", ip_address=request.client.host if request.client else None, user_agent=request.headers.get("user-agent"))
    db.commit()
    raise ApiError(403, "AUTH_FORBIDDEN", "Access denied")


def _metric_rows(db: Session, tenant_id: str, task: dict) -> list[dict]:
    rows = db.execute(text("""
        SELECT ptm.project_topic_metric_id::text AS project_metric_id, ptm.metric_code, ptm.metric_name,
               ptm.metric_type::text, ptm.data_type::text, ptm.unit, ptm.is_required,
               ptm.custom_filling_instruction, ptm.metric_snapshot,
               tsi.submission_item_id::text, tsi.value, tsi.text_value, tsi.period,
               tsi.org_unit_id::text, tsi.description, tsi.attachment_file_ids, tsi.validation_issues
        FROM project_topic_metrics ptm
        LEFT JOIN LATERAL (
          SELECT tsi.*
          FROM task_submission_items tsi
          JOIN task_submissions ts ON ts.submission_id=tsi.submission_id AND ts.tenant_id=tsi.tenant_id
          WHERE tsi.tenant_id=ptm.tenant_id AND tsi.project_id=ptm.project_id
            AND tsi.project_topic_metric_id=ptm.project_topic_metric_id AND ts.task_id=:task_id
          ORDER BY tsi.updated_at DESC
          LIMIT 1
        ) tsi ON true
        WHERE ptm.tenant_id=:tenant_id AND ptm.project_id=:project_id
          AND ptm.project_topic_id=:project_topic_id AND ptm.status='active'
        ORDER BY ptm.metric_name
    """), {"tenant_id": tenant_id, "project_id": task["project_id"], "project_topic_id": task["project_topic_id"], "task_id": task["task_id"]}).mappings().all()
    return [dict(r) for r in rows]


def build_validation_issues(metrics: list[dict]) -> list[dict]:
    issues: list[dict] = []
    for metric in metrics:
        has_value = metric.get("value") is not None or bool(metric.get("text_value"))
        if metric.get("is_required") and not has_value:
            issues.append({"issue_id": f"required:{metric['project_metric_id']}", "project_metric_id": metric["project_metric_id"], "metric_name": metric["metric_name"], "issue_type": "required_missing", "severity": "high", "message": "必填指标缺少填报值", "blocks_submission": True})
        snapshot = metric.get("metric_snapshot") or {}
        attachment_required = bool(snapshot.get("attachment_required") or snapshot.get("evidence_required"))
        attachments = metric.get("attachment_file_ids") or []
        if attachment_required and has_value and not attachments:
            issues.append({"issue_id": f"evidence:{metric['project_metric_id']}", "project_metric_id": metric["project_metric_id"], "metric_name": metric["metric_name"], "issue_type": "evidence_missing", "severity": "medium", "message": "该指标建议上传佐证附件", "blocks_submission": False})
        if metric.get("data_type") == "number" and metric.get("value") is not None:
            try:
                if Decimal(metric["value"]) < 0:
                    issues.append({"issue_id": f"negative:{metric['project_metric_id']}", "project_metric_id": metric["project_metric_id"], "metric_name": metric["metric_name"], "issue_type": "negative_value", "severity": "medium", "message": "数值为负数，请确认是否合理", "blocks_submission": False})
            except (InvalidOperation, TypeError):
                issues.append({"issue_id": f"invalid_number:{metric['project_metric_id']}", "project_metric_id": metric["project_metric_id"], "metric_name": metric["metric_name"], "issue_type": "invalid_number", "severity": "high", "message": "数值格式无效", "blocks_submission": True})
    return issues


def _latest_submission_id(db: Session, tenant_id: str, task_id: str) -> str | None:
    row = db.execute(text("""
        SELECT submission_id::text FROM task_submissions
        WHERE tenant_id=:tenant_id AND task_id=:task_id
        ORDER BY updated_at DESC LIMIT 1
    """), {"tenant_id": tenant_id, "task_id": task_id}).mappings().first()
    return row["submission_id"] if row else None


def _ensure_submission(db: Session, tenant_id: str, task: dict, submitter_user_id: str) -> str:
    existing = _latest_submission_id(db, tenant_id, task["task_id"])
    if existing:
        return existing
    row = db.execute(text("""
        INSERT INTO task_submissions (tenant_id, project_id, task_id, submitter_user_id, task_status)
        VALUES (:tenant_id, :project_id, :task_id, :submitter_user_id, 'draft')
        RETURNING submission_id::text
    """), {"tenant_id": tenant_id, "project_id": task["project_id"], "task_id": task["task_id"], "submitter_user_id": submitter_user_id}).mappings().first()
    return row["submission_id"]


@router.get("/projects/{project_id}/tasks/preview")
def preview_tasks(project_id: str, request: Request, db: Session = Depends(get_db), user: dict = Depends(require_permission("project:read"))):
    _authorize_project(request, db, user, project_id)
    rows = db.execute(text("""
        SELECT pt.project_topic_id::text, pt.topic_name, count(ptm.project_topic_metric_id)::int AS metric_count,
               count(*) FILTER (WHERE ptm.is_required)::int AS required_metric_count, pta.assignment_id::text,
               pta.owner_org_unit_id::text, pta.collector_user_id::text, pta.reviewer_user_id::text,
               ct.task_id::text, ct.task_status::text
        FROM project_topics pt
        LEFT JOIN project_topic_metrics ptm ON ptm.tenant_id=pt.tenant_id AND ptm.project_topic_id=pt.project_topic_id AND ptm.status='active'
        LEFT JOIN project_topic_assignments pta ON pta.tenant_id=pt.tenant_id AND pta.project_topic_id=pt.project_topic_id AND pta.status='active'
        LEFT JOIN collection_tasks ct ON ct.tenant_id=pt.tenant_id AND ct.project_topic_id=pt.project_topic_id
        WHERE pt.tenant_id=:tenant_id AND pt.project_id=:project_id AND pt.selected=true AND pt.status<>'inactive'
        GROUP BY pt.project_topic_id, pt.topic_name, pta.assignment_id, pta.owner_org_unit_id, pta.collector_user_id, pta.reviewer_user_id, ct.task_id, ct.task_status
        ORDER BY pt.topic_name
    """), {"tenant_id": _tenant_id(user), "project_id": project_id}).mappings().all()
    return ok({"items": [dict(r) for r in rows]}, request_id=request.state.request_id)


@router.post("/projects/{project_id}/tasks/generate")
def generate_tasks(project_id: str, payload: GenerateTasksRequest, request: Request, db: Session = Depends(get_db), user: dict = Depends(require_permission("project:update"))):
    project = _authorize_project(request, db, user, project_id)
    rows = db.execute(text("""
        SELECT pt.project_topic_id::text, pt.topic_name, pta.assignment_id::text, pta.owner_org_unit_id::text,
               pta.collector_user_id::text, pta.reviewer_user_id::text, pta.due_date
        FROM project_topics pt
        LEFT JOIN project_topic_assignments pta ON pta.tenant_id=pt.tenant_id AND pta.project_topic_id=pt.project_topic_id AND pta.status='active'
        WHERE pt.tenant_id=:tenant_id AND pt.project_id=:project_id AND pt.selected=true AND pt.status<>'inactive'
    """), {"tenant_id": _tenant_id(user), "project_id": project_id}).mappings().all()
    created = 0
    for row in rows:
        result = db.execute(text("""
            INSERT INTO collection_tasks (tenant_id, project_id, project_topic_id, assignment_id, task_name,
              owner_org_unit_id, collector_user_id, reviewer_user_id, due_date, task_status)
            SELECT :tenant_id, :project_id, :project_topic_id, :assignment_id, :task_name,
                   :owner_org_unit_id, :collector_user_id, :reviewer_user_id, :due_date, 'pending'
            WHERE NOT EXISTS (
              SELECT 1 FROM collection_tasks
              WHERE tenant_id=:tenant_id AND project_id=:project_id AND project_topic_id=:project_topic_id
            )
        """), {"tenant_id": _tenant_id(user), "project_id": project_id, "project_topic_id": row["project_topic_id"], "assignment_id": row.get("assignment_id"), "task_name": f"{row['topic_name']} 数据采集", "owner_org_unit_id": row.get("owner_org_unit_id"), "collector_user_id": row.get("collector_user_id"), "reviewer_user_id": row.get("reviewer_user_id"), "due_date": row.get("due_date")})
        created += max(result.rowcount or 0, 0)
    write_audit_log(db, tenant_id=_tenant_id(user), enterprise_id=project["enterprise_id"], project_id=project_id, user_id=user["user_id"], user_name=user["name"], action_type="collection_tasks.generated", object_type="collection_tasks", object_id=project_id, description=payload.generate_note or "生成部门采集任务")
    db.commit()
    return ok({"generated_count": created}, request_id=request.state.request_id)


@router.get("/my/collection-tasks")
def my_collection_tasks(request: Request, db: Session = Depends(get_db), user: dict = Depends(require_permission("collection_task:read_assigned")), project_id: str | None = None, task_status: str | None = None):
    clauses = ["ct.tenant_id=:tenant_id", "ct.collector_user_id=:user_id"]
    params = {"tenant_id": _tenant_id(user), "user_id": user["user_id"]}
    if project_id:
        clauses.append("ct.project_id=:project_id")
        params["project_id"] = project_id
    if task_status:
        clauses.append("ct.task_status=:task_status")
        params["task_status"] = task_status
    rows = db.execute(text(f"""
        SELECT ct.task_id::text, ct.project_id::text, rp.project_name, ct.task_name, pt.topic_name,
               count(ptm.project_topic_metric_id)::int AS metric_count,
               count(*) FILTER (WHERE ptm.is_required)::int AS required_metric_count,
               0::int AS attachment_required_count, ct.due_date, ct.task_status::text
        FROM collection_tasks ct
        JOIN report_projects rp ON rp.tenant_id=ct.tenant_id AND rp.project_id=ct.project_id
        JOIN project_topics pt ON pt.tenant_id=ct.tenant_id AND pt.project_topic_id=ct.project_topic_id
        LEFT JOIN project_topic_metrics ptm ON ptm.tenant_id=ct.tenant_id AND ptm.project_topic_id=ct.project_topic_id AND ptm.status='active'
        WHERE {' AND '.join(clauses)}
        GROUP BY ct.task_id, rp.project_name, pt.topic_name
        ORDER BY ct.due_date NULLS LAST, ct.created_at DESC
    """), params).mappings().all()
    return ok({"items": [dict(r) for r in rows]}, request_id=request.state.request_id)


@router.get("/collection-tasks/{task_id}")
def collection_task_detail(task_id: str, request: Request, db: Session = Depends(get_db), user: dict = Depends(require_permission("collection_task:read_assigned"))):
    task = _assert_task_visible(request, db, user, _task_row(db, _tenant_id(user), task_id), mode="collect")
    return ok({"task_id": task["task_id"], "task_name": task["task_name"], "topic": {"project_topic_id": task["project_topic_id"], "topic_code": task["topic_code"], "topic_name": task["topic_name"], "topic_category": task["topic_category"]}, "collector": {"user_id": task.get("collector_user_id"), "name": task.get("collector_name")}, "reviewer": {"user_id": task.get("reviewer_user_id"), "name": task.get("reviewer_name")}, "metrics": _metric_rows(db, _tenant_id(user), task), "task_status": task["task_status"]}, request_id=request.state.request_id)


@router.post("/collection-tasks/{task_id}/draft")
def save_draft(task_id: str, payload: SubmissionDraftRequest, request: Request, db: Session = Depends(get_db), user: dict = Depends(require_permission("collection_task:write_assigned"))):
    task = _assert_task_visible(request, db, user, _task_row(db, _tenant_id(user), task_id), mode="collect")
    if task["task_status"] in {"approved"}:
        raise ApiError(400, "COLLECTION_TASK_ALREADY_APPROVED", "Approved task cannot be edited")
    metric_ids = {m["project_metric_id"] for m in _metric_rows(db, _tenant_id(user), task)}
    submission_id = _ensure_submission(db, _tenant_id(user), task, user["user_id"])
    for item in payload.items:
        if item.project_metric_id not in metric_ids:
            raise ApiError(400, "COLLECTION_METRIC_INVALID", "Metric does not belong to this task")
        db.execute(text("DELETE FROM task_submission_items WHERE tenant_id=:tenant_id AND submission_id=:submission_id AND project_topic_metric_id=:project_metric_id"), {"tenant_id": _tenant_id(user), "submission_id": submission_id, "project_metric_id": item.project_metric_id})
        db.execute(text("""
            INSERT INTO task_submission_items (tenant_id, project_id, submission_id, project_topic_metric_id, value, text_value, unit, period, org_unit_id, description, attachment_file_ids)
            VALUES (:tenant_id, :project_id, :submission_id, :project_metric_id, :value, :text_value, :unit, :period, :org_unit_id, :description, :attachment_file_ids)
        """), {"tenant_id": _tenant_id(user), "project_id": task["project_id"], "submission_id": submission_id, **item.model_dump()})
    db.execute(text("UPDATE task_submissions SET submission_note=:note, warning_confirmation_note=:warning, task_status='draft', updated_at=now() WHERE tenant_id=:tenant_id AND submission_id=:submission_id"), {"tenant_id": _tenant_id(user), "submission_id": submission_id, "note": payload.submission_note, "warning": payload.warning_confirmation_note})
    db.execute(text("UPDATE collection_tasks SET task_status=CASE WHEN task_status='pending' THEN 'draft' ELSE task_status END, updated_at=now() WHERE tenant_id=:tenant_id AND task_id=:task_id"), {"tenant_id": _tenant_id(user), "task_id": task_id})
    db.commit()
    return ok({"submission_id": submission_id}, request_id=request.state.request_id)


@router.post("/collection-tasks/{task_id}/validate")
def validate_task(task_id: str, request: Request, db: Session = Depends(get_db), user: dict = Depends(require_permission("collection_task:read_assigned"))):
    task = _assert_task_visible(request, db, user, _task_row(db, _tenant_id(user), task_id), mode="collect")
    issues = build_validation_issues(_metric_rows(db, _tenant_id(user), task))
    return ok({"task_id": task_id, "validation_result": "blocked" if any(i["blocks_submission"] for i in issues) else ("warning" if issues else "passed"), "issues": issues, "can_submit": not any(i["blocks_submission"] for i in issues)}, request_id=request.state.request_id)


@router.post("/collection-tasks/{task_id}/submit")
def submit_task(task_id: str, payload: SubmitTaskRequest, request: Request, db: Session = Depends(get_db), user: dict = Depends(require_permission("collection_task:write_assigned"))):
    task = _assert_task_visible(request, db, user, _task_row(db, _tenant_id(user), task_id), mode="collect")
    submission_id = _latest_submission_id(db, _tenant_id(user), task_id)
    if not submission_id:
        raise ApiError(400, "COLLECTION_SUBMISSION_REQUIRED", "Draft must be saved before submit")
    issues = build_validation_issues(_metric_rows(db, _tenant_id(user), task))
    if any(issue["blocks_submission"] for issue in issues):
        raise ApiError(400, "COLLECTION_VALIDATION_BLOCKED", "Validation issues block submission", {"issues": issues})
    db.execute(text("UPDATE task_submissions SET submission_note=coalesce(:note, submission_note), warning_confirmation_note=:warning, task_status='submitted', submitted_at=now(), updated_at=now() WHERE tenant_id=:tenant_id AND submission_id=:submission_id"), {"tenant_id": _tenant_id(user), "submission_id": submission_id, "note": payload.submission_note, "warning": payload.warning_confirmation_note})
    db.execute(text("UPDATE collection_tasks SET task_status='submitted', submitted_at=now(), updated_at=now() WHERE tenant_id=:tenant_id AND task_id=:task_id"), {"tenant_id": _tenant_id(user), "task_id": task_id})
    db.commit()
    return ok({"submission_id": submission_id, "submitted": True}, request_id=request.state.request_id)


@router.get("/my/review-tasks")
def my_review_tasks(request: Request, db: Session = Depends(get_db), user: dict = Depends(require_permission("review_task:read_assigned"))):
    rows = db.execute(text("""
        SELECT ct.task_id::text, ct.project_id::text, rp.project_name, ct.task_name, pt.topic_name,
               ct.due_date, ct.task_status::text, ts.submission_id::text, ts.submitted_at
        FROM collection_tasks ct
        JOIN report_projects rp ON rp.tenant_id=ct.tenant_id AND rp.project_id=ct.project_id
        JOIN project_topics pt ON pt.tenant_id=ct.tenant_id AND pt.project_topic_id=ct.project_topic_id
        LEFT JOIN task_submissions ts ON ts.tenant_id=ct.tenant_id AND ts.task_id=ct.task_id AND ts.task_status='submitted'
        WHERE ct.tenant_id=:tenant_id AND ct.reviewer_user_id=:user_id AND ct.task_status='submitted'
        ORDER BY ct.submitted_at DESC
    """), {"tenant_id": _tenant_id(user), "user_id": user["user_id"]}).mappings().all()
    return ok({"items": [dict(r) for r in rows]}, request_id=request.state.request_id)


@router.get("/review-tasks/{task_id}")
def review_task_detail(task_id: str, request: Request, db: Session = Depends(get_db), user: dict = Depends(require_permission("review_task:read_assigned"))):
    task = _assert_task_visible(request, db, user, _task_row(db, _tenant_id(user), task_id), mode="review")
    submission_id = _latest_submission_id(db, _tenant_id(user), task_id)
    return ok({"task_id": task_id, "submission_id": submission_id, "task_name": task["task_name"], "items": _metric_rows(db, _tenant_id(user), task), "submission_note": None}, request_id=request.state.request_id)


@router.post("/review-tasks/{task_id}/review")
def review_task(task_id: str, payload: ReviewSubmitRequest, request: Request, db: Session = Depends(get_db), user: dict = Depends(require_permission("review_task:review_assigned"))):
    task = _assert_task_visible(request, db, user, _task_row(db, _tenant_id(user), task_id), mode="review")
    if task["task_status"] != "submitted":
        raise ApiError(400, "REVIEW_TASK_NOT_SUBMITTED", "Only submitted tasks can be reviewed")
    submission_id = _latest_submission_id(db, _tenant_id(user), task_id)
    if not submission_id:
        raise ApiError(400, "REVIEW_SUBMISSION_REQUIRED", "Submitted data is missing")
    review_status = "approved" if payload.review_action == "approve" else "returned"
    db.execute(text("""
        INSERT INTO task_reviews (tenant_id, project_id, task_id, submission_id, reviewer_user_id, review_action, review_note, return_items, confirmed_validation_issue_ids)
        VALUES (:tenant_id, :project_id, :task_id, :submission_id, :reviewer_user_id, :review_action, :review_note, :return_items, :confirmed_validation_issue_ids)
    """), {"tenant_id": _tenant_id(user), "project_id": task["project_id"], "task_id": task_id, "submission_id": submission_id, "reviewer_user_id": user["user_id"], "review_action": payload.review_action, "review_note": payload.review_note, "return_items": payload.return_items, "confirmed_validation_issue_ids": payload.confirmed_validation_issue_ids})
    db.execute(text("UPDATE task_submissions SET task_status=:status, updated_at=now() WHERE tenant_id=:tenant_id AND submission_id=:submission_id"), {"tenant_id": _tenant_id(user), "submission_id": submission_id, "status": review_status})
    db.execute(text("UPDATE collection_tasks SET task_status=:status, reviewed_at=now(), updated_at=now() WHERE tenant_id=:tenant_id AND task_id=:task_id"), {"tenant_id": _tenant_id(user), "task_id": task_id, "status": review_status})
    created_records = 0
    if review_status == "approved":
        created_records = create_esg_data_records_for_submission(db, tenant_id=_tenant_id(user), enterprise_id=task["enterprise_id"], project_id=task["project_id"], task_id=task_id, submission_id=submission_id)
    db.commit()
    return ok({"reviewed": True, "review_status": review_status, "esg_data_record_count": created_records}, request_id=request.state.request_id)

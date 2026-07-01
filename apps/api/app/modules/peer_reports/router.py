import json
import re
from datetime import date
from pathlib import Path, PurePosixPath
from typing import Annotated

from fastapi import APIRouter, Depends, File, Form, Request, Response, UploadFile
from pydantic import BaseModel, Field
from sqlalchemy import text
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from app.core.errors import ApiError
from app.core.response import ok
from app.db.session import get_db
from app.modules.audit.service import write_audit_log
from app.modules.auth.dependencies import has_permission, require_permission
from app.modules.projects.router import _authorize_project, user_can_access_enterprise

router = APIRouter(prefix="/api/v1", tags=["文件", "同行报告解析", "异步任务"])

ALLOWED_PEER_REPORT_MIME_TYPES = {"application/pdf"}
ALLOWED_PEER_REPORT_EXTENSIONS = {".pdf"}
MAX_PEER_REPORT_SIZE_BYTES = 50 * 1024 * 1024
LOCAL_FILE_STORAGE_ROOT = Path("/tmp/esg-report-platform/files")


class PeerReportCreateRequest(BaseModel):
    peer_company_id: str
    file_id: str
    report_year: int
    report_name: str | None = Field(default=None, max_length=512)
    report_language: str = "zh"


class ParseOptionsRequest(BaseModel):
    force_reparse: bool = False
    parser_mode: str = "mock"


class ParseResultPatchRequest(BaseModel):
    object_type: str = Field(pattern="^(standard|topic|metric|case)$")
    review_status: str = Field(pattern="^(pending|accepted|edited|rejected|ignored)$")
    mapped_standard_code: str | None = None
    mapped_standard_name: str | None = None
    mapped_topic_code: str | None = None
    mapped_topic_name: str | None = None
    mapped_metric_code: str | None = None
    mapped_metric_name: str | None = None
    financial_materiality: str | None = None
    impact_materiality: str | None = None
    review_note: str | None = None


def validate_peer_report_upload(file_name: str, mime_type: str | None, file_size: int | None) -> None:
    suffix = PurePosixPath(file_name).suffix.lower()
    if suffix not in ALLOWED_PEER_REPORT_EXTENSIONS or mime_type not in ALLOWED_PEER_REPORT_MIME_TYPES:
        raise ApiError(400, "FILE_TYPE_NOT_ALLOWED", "Only PDF peer reports are allowed")
    if file_size is not None and file_size > MAX_PEER_REPORT_SIZE_BYTES:
        raise ApiError(400, "FILE_TOO_LARGE", "Peer report file is too large")


def validate_report_year(report_year: int) -> None:
    current_year = date.today().year
    if report_year < 2000 or report_year > current_year + 1:
        raise ApiError(400, "PEER_REPORT_INVALID_YEAR", "Report year is invalid")


def _file_payload(row: dict) -> dict:
    return {
        "file_id": row["file_id"],
        "tenant_id": row["tenant_id"],
        "enterprise_id": row.get("enterprise_id"),
        "project_id": row.get("project_id"),
        "file_name": row["file_name"],
        "file_type": row.get("file_type"),
        "file_size": row.get("file_size"),
        "mime_type": row.get("mime_type"),
        "business_type": row["business_type"],
        "related_object_type": row.get("related_object_type"),
        "related_object_id": row.get("related_object_id"),
        "upload_status": row["upload_status"],
        "uploaded_at": row.get("uploaded_at"),
    }


def _peer_report_payload(row: dict) -> dict:
    return {
        "peer_report_id": row["peer_report_id"],
        "project_id": row["project_id"],
        "peer_company_id": row["peer_company_id"],
        "file_id": row["file_id"],
        "report_year": row["report_year"],
        "report_name": row.get("report_name"),
        "report_language": row.get("report_language"),
        "parse_status": row["parse_status"],
        "ai_review_status": row.get("ai_review_status"),
        "created_at": row.get("created_at"),
        "updated_at": row.get("updated_at"),
    }


def _job_payload(row: dict) -> dict:
    return {
        "job_id": row["job_id"],
        "tenant_id": row["tenant_id"],
        "enterprise_id": row.get("enterprise_id"),
        "project_id": row.get("project_id"),
        "job_type": row["job_type"],
        "job_status": row["job_status"],
        "progress": row["progress"],
        "current_step": row.get("current_step"),
        "target_object_type": row.get("target_object_type"),
        "target_object_id": row.get("target_object_id"),
        "request_payload": row.get("request_payload") or {},
        "result_payload": row.get("result_payload") or {},
        "error_payload": row.get("error_payload") or {},
        "created_at": row.get("created_at"),
        "started_at": row.get("started_at"),
        "finished_at": row.get("finished_at"),
    }


def _get_file(db: Session, tenant_id: str, file_id: str) -> dict | None:
    row = db.execute(text("""
        SELECT file_id::text, tenant_id::text, enterprise_id::text, project_id::text, file_name, file_type,
               file_size, mime_type, storage_path, business_type, related_object_type, related_object_id::text,
               upload_status, uploaded_at
        FROM file_objects
        WHERE tenant_id=:tenant_id AND file_id=:file_id
    """), {"tenant_id": tenant_id, "file_id": file_id}).mappings().first()
    return dict(row) if row else None


def _authorize_file_access(request: Request, db: Session, user: dict, file_row: dict | None) -> dict:
    if not file_row:
        raise ApiError(404, "FILE_NOT_FOUND", "File not found")
    project_id = file_row.get("project_id")
    enterprise_id = file_row.get("enterprise_id")
    if project_id:
        _authorize_project(request, db, user, project_id)
    elif enterprise_id and not user_can_access_enterprise(user, enterprise_id):
        write_audit_log(db, tenant_id=user["current_tenant_id"], enterprise_id=enterprise_id, user_id=user["user_id"], user_name=user["name"], action_type="security.file_access_denied", object_type="file_objects", object_id=file_row["file_id"], description="文件不存在或无访问范围", ip_address=request.client.host if request.client else None, user_agent=request.headers.get("user-agent"))
        db.commit()
        raise ApiError(403, "AUTH_FORBIDDEN", "Access denied")
    return file_row


def _get_peer_report(db: Session, tenant_id: str, project_id: str, peer_report_id: str) -> dict | None:
    row = db.execute(text("""
        SELECT peer_report_id::text, tenant_id::text, project_id::text, peer_company_id::text, file_id::text,
               report_year, report_name, report_language, parse_status::text, ai_review_status, created_at, updated_at
        FROM peer_report_files
        WHERE tenant_id=:tenant_id AND project_id=:project_id AND peer_report_id=:peer_report_id
    """), {"tenant_id": tenant_id, "project_id": project_id, "peer_report_id": peer_report_id}).mappings().first()
    return dict(row) if row else None


def _safe_file_name(file_name: str) -> str:
    return re.sub(r"[^A-Za-z0-9._-]", "_", file_name)[:255] or "peer-report.pdf"


def _local_storage_path(*, tenant_id: str, project_id: str, file_name: str) -> Path:
    return LOCAL_FILE_STORAGE_ROOT / tenant_id / project_id / _safe_file_name(file_name)


def _storage_uri(path: Path) -> str:
    return f"local://{path}"


def _path_from_storage_uri(storage_path: str) -> Path | None:
    if not storage_path.startswith("local://"):
        return None
    return Path(storage_path.removeprefix("local://"))


def _require_project_peer(db: Session, tenant_id: str, project_id: str, peer_company_id: str) -> None:
    row = db.execute(text("""
        SELECT ppc.project_peer_company_id::text
        FROM project_peer_companies ppc
        WHERE ppc.tenant_id=:tenant_id
          AND ppc.project_id=:project_id
          AND ppc.peer_company_id=:peer_company_id
          AND ppc.selected=true
          AND ppc.confirmed_at IS NOT NULL
    """), {"tenant_id": tenant_id, "project_id": project_id, "peer_company_id": peer_company_id}).first()
    if not row:
        raise ApiError(400, "PEER_NOT_CONFIRMED", "Peer company must be confirmed before uploading reports")


@router.post("/files/upload")
def upload_file(
    request: Request,
    file: Annotated[UploadFile, File()],
    business_type: Annotated[str, Form()],
    enterprise_id: Annotated[str | None, Form()] = None,
    project_id: Annotated[str | None, Form()] = None,
    related_object_id: Annotated[str | None, Form()] = None,
    db: Session = Depends(get_db),
    user: dict = Depends(require_permission("file:upload")),
):
    content = file.file.read()
    file_size = len(content)
    if business_type != "peer_report":
        raise ApiError(400, "FILE_BUSINESS_TYPE_UNSUPPORTED", "Only peer_report uploads are supported in MVP")
    if not enterprise_id or not project_id:
        raise ApiError(400, "FILE_PROJECT_CONTEXT_REQUIRED", "Peer report files require enterprise_id and project_id")
    if not has_permission(user, "project:update"):
        write_audit_log(db, tenant_id=user["current_tenant_id"], enterprise_id=enterprise_id, project_id=project_id, user_id=user["user_id"], user_name=user["name"], action_type="security.permission_denied", description="缺少权限: project:update", ip_address=request.client.host if request.client else None, user_agent=request.headers.get("user-agent"))
        db.commit()
        raise ApiError(403, "AUTH_FORBIDDEN", "Permission denied")
    project = _authorize_project(request, db, user, project_id)
    if project["enterprise_id"] != enterprise_id:
        raise ApiError(400, "FILE_PROJECT_CONTEXT_INVALID", "File enterprise/project context is invalid")
    validate_peer_report_upload(file.filename or "", file.content_type, file_size)
    storage_path = _local_storage_path(tenant_id=user["current_tenant_id"], project_id=project_id, file_name=file.filename or "peer-report.pdf")
    storage_path.parent.mkdir(parents=True, exist_ok=True)
    storage_path.write_bytes(content)
    row = db.execute(text("""
        INSERT INTO file_objects (tenant_id, enterprise_id, project_id, file_name, file_type, file_size, mime_type,
          storage_path, business_type, related_object_type, related_object_id, upload_status, uploaded_by)
        VALUES (:tenant_id, :enterprise_id, :project_id, :file_name, :file_type, :file_size, :mime_type,
          :storage_path, :business_type, 'peer_report', :related_object_id, 'uploaded', :uploaded_by)
        RETURNING file_id::text, tenant_id::text, enterprise_id::text, project_id::text, file_name, file_type,
          file_size, mime_type, business_type, related_object_type, related_object_id::text, upload_status, uploaded_at
    """), {
        "tenant_id": user["current_tenant_id"],
        "enterprise_id": enterprise_id,
        "project_id": project_id,
        "file_name": file.filename,
        "file_type": "pdf",
        "file_size": file_size,
        "mime_type": file.content_type,
        "storage_path": _storage_uri(storage_path),
        "business_type": business_type,
        "related_object_id": related_object_id,
        "uploaded_by": user["user_id"],
    }).mappings().first()
    write_audit_log(db, tenant_id=user["current_tenant_id"], enterprise_id=enterprise_id, project_id=project_id, user_id=user["user_id"], user_name=user["name"], action_type="file.uploaded", object_type="file_objects", object_id=row["file_id"], description="上传同行报告文件")
    db.commit()
    return ok(_file_payload(dict(row)), request_id=request.state.request_id)


@router.get("/files/{file_id}/stream")
def stream_file(file_id: str, request: Request, db: Session = Depends(get_db), user: dict = Depends(require_permission("project:read"))):
    file_row = _authorize_file_access(request, db, user, _get_file(db, user["current_tenant_id"], file_id))
    path = _path_from_storage_uri(file_row.get("storage_path") or "")
    if path is None or not path.exists() or not path.is_file():
        raise ApiError(404, "FILE_CONTENT_NOT_FOUND", "File content not found")
    write_audit_log(db, tenant_id=user["current_tenant_id"], enterprise_id=file_row.get("enterprise_id"), project_id=file_row.get("project_id"), user_id=user["user_id"], user_name=user["name"], action_type="file.downloaded", object_type="file_objects", object_id=file_id, description="受控下载同行报告文件")
    db.commit()
    return Response(content=path.read_bytes(), media_type=file_row.get("mime_type") or "application/octet-stream", headers={"Content-Disposition": f'attachment; filename="{_safe_file_name(file_row["file_name"])}"'})


@router.get("/files/{file_id}/download-url")
def get_download_url(file_id: str, request: Request, db: Session = Depends(get_db), user: dict = Depends(require_permission("project:read"))):
    file_row = _authorize_file_access(request, db, user, _get_file(db, user["current_tenant_id"], file_id))
    write_audit_log(db, tenant_id=user["current_tenant_id"], enterprise_id=file_row.get("enterprise_id"), project_id=file_row.get("project_id"), user_id=user["user_id"], user_name=user["name"], action_type="file.download_requested", object_type="file_objects", object_id=file_id, description="请求受控文件下载链接")
    db.commit()
    return ok({"file_id": file_id, "download_url": f"/api/v1/files/{file_id}/stream", "expires_in": 300}, request_id=request.state.request_id)


@router.post("/projects/{project_id}/peer-reports")
def create_peer_report(project_id: str, payload: PeerReportCreateRequest, request: Request, db: Session = Depends(get_db), user: dict = Depends(require_permission("project:update"))):
    project = _authorize_project(request, db, user, project_id)
    validate_report_year(payload.report_year)
    _require_project_peer(db, user["current_tenant_id"], project_id, payload.peer_company_id)
    file_row = _authorize_file_access(request, db, user, _get_file(db, user["current_tenant_id"], payload.file_id))
    if file_row.get("project_id") != project_id or file_row.get("enterprise_id") != project["enterprise_id"]:
        raise ApiError(400, "PEER_REPORT_FILE_CONTEXT_INVALID", "Peer report file context is invalid")
    try:
        row = db.execute(text("""
            INSERT INTO peer_report_files (tenant_id, project_id, peer_company_id, file_id, report_year, report_name, report_language, parse_status)
            VALUES (:tenant_id, :project_id, :peer_company_id, :file_id, :report_year, :report_name, :report_language, 'uploaded')
            RETURNING peer_report_id::text, tenant_id::text, project_id::text, peer_company_id::text, file_id::text,
              report_year, report_name, report_language, parse_status::text, ai_review_status, created_at, updated_at
        """), {"tenant_id": user["current_tenant_id"], "project_id": project_id, **payload.model_dump()}).mappings().first()
        write_audit_log(db, tenant_id=user["current_tenant_id"], enterprise_id=project["enterprise_id"], project_id=project_id, user_id=user["user_id"], user_name=user["name"], action_type="peer_report.created", object_type="peer_report_files", object_id=row["peer_report_id"], description="创建同行报告记录")
        db.commit()
    except IntegrityError as exc:
        db.rollback()
        raise ApiError(400, "PEER_REPORT_CREATE_FAILED", "Peer report cannot be created") from exc
    return ok(_peer_report_payload(dict(row)), request_id=request.state.request_id)


@router.get("/projects/{project_id}/peer-reports")
def list_peer_reports(project_id: str, request: Request, db: Session = Depends(get_db), user: dict = Depends(require_permission("project:read"))):
    _authorize_project(request, db, user, project_id)
    rows = db.execute(text("""
        SELECT peer_report_id::text, tenant_id::text, project_id::text, peer_company_id::text, file_id::text,
               report_year, report_name, report_language, parse_status::text, ai_review_status, created_at, updated_at
        FROM peer_report_files
        WHERE tenant_id=:tenant_id AND project_id=:project_id
        ORDER BY created_at DESC
    """), {"tenant_id": user["current_tenant_id"], "project_id": project_id}).mappings().all()
    return ok({"items": [_peer_report_payload(dict(row)) for row in rows]}, request_id=request.state.request_id)


def _run_mock_parse_job(db: Session, *, tenant_id: str, project_id: str, peer_report_id: str, job_id: str) -> None:
    result_payload = {
        "standards": [{"peer_report_id": peer_report_id, "extracted_standard_name": "GRI Standards", "confidence": 0.8}],
        "topics": [{"peer_report_id": peer_report_id, "original_topic_name": "温室气体排放", "confidence": 0.75}],
        "metrics": [{"peer_report_id": peer_report_id, "original_metric_name": "范围一温室气体排放量", "confidence": 0.72}],
        "cases": [],
    }
    db.execute(text("""
        UPDATE async_jobs
        SET job_status='running', progress=10, current_step='mock_parse_started', started_at=COALESCE(started_at, now())
        WHERE tenant_id=:tenant_id AND job_id=:job_id
    """), {"tenant_id": tenant_id, "job_id": job_id})
    db.execute(text("DELETE FROM report_extracted_standards WHERE tenant_id=:tenant_id AND project_id=:project_id AND peer_report_id=:peer_report_id"), {"tenant_id": tenant_id, "project_id": project_id, "peer_report_id": peer_report_id})
    db.execute(text("DELETE FROM report_extracted_topics WHERE tenant_id=:tenant_id AND project_id=:project_id AND peer_report_id=:peer_report_id"), {"tenant_id": tenant_id, "project_id": project_id, "peer_report_id": peer_report_id})
    db.execute(text("DELETE FROM report_extracted_metrics WHERE tenant_id=:tenant_id AND project_id=:project_id AND peer_report_id=:peer_report_id"), {"tenant_id": tenant_id, "project_id": project_id, "peer_report_id": peer_report_id})
    db.execute(text("DELETE FROM report_extracted_cases WHERE tenant_id=:tenant_id AND project_id=:project_id AND peer_report_id=:peer_report_id"), {"tenant_id": tenant_id, "project_id": project_id, "peer_report_id": peer_report_id})
    for standard in result_payload["standards"]:
        db.execute(text("""
            INSERT INTO report_extracted_standards (tenant_id, project_id, peer_report_id, extracted_standard_name, confidence)
            VALUES (:tenant_id, :project_id, :peer_report_id, :extracted_standard_name, :confidence)
        """), {"tenant_id": tenant_id, "project_id": project_id, **standard})
    for topic in result_payload["topics"]:
        db.execute(text("""
            INSERT INTO report_extracted_topics (tenant_id, project_id, peer_report_id, original_topic_name, confidence)
            VALUES (:tenant_id, :project_id, :peer_report_id, :original_topic_name, :confidence)
        """), {"tenant_id": tenant_id, "project_id": project_id, **topic})
    for metric in result_payload["metrics"]:
        db.execute(text("""
            INSERT INTO report_extracted_metrics (tenant_id, project_id, peer_report_id, original_metric_name, confidence)
            VALUES (:tenant_id, :project_id, :peer_report_id, :original_metric_name, :confidence)
        """), {"tenant_id": tenant_id, "project_id": project_id, **metric})
    db.execute(text("""
        UPDATE peer_report_files
        SET parse_status='pending_human_review', ai_review_status='pending', updated_at=now()
        WHERE tenant_id=:tenant_id AND project_id=:project_id AND peer_report_id=:peer_report_id
    """), {"tenant_id": tenant_id, "project_id": project_id, "peer_report_id": peer_report_id})
    db.execute(text("""
        UPDATE async_jobs
        SET job_status='succeeded', progress=100, current_step='mock_parse_completed',
            result_payload=CAST(:result_payload AS jsonb), finished_at=now()
        WHERE tenant_id=:tenant_id AND job_id=:job_id
    """), {"tenant_id": tenant_id, "job_id": job_id, "result_payload": json.dumps(result_payload, ensure_ascii=False)})


@router.post("/projects/{project_id}/peer-reports/{peer_report_id}/parse")
def start_peer_report_parse(project_id: str, peer_report_id: str, payload: ParseOptionsRequest, request: Request, db: Session = Depends(get_db), user: dict = Depends(require_permission("project:update"))):
    project = _authorize_project(request, db, user, project_id)
    report = _get_peer_report(db, user["current_tenant_id"], project_id, peer_report_id)
    if not report:
        raise ApiError(404, "PEER_REPORT_NOT_FOUND", "Peer report not found")
    if report["parse_status"] in {"pending", "parsing", "ai_reviewing"} and not payload.force_reparse:
        raise ApiError(400, "PEER_REPORT_PARSE_IN_PROGRESS", "Peer report parse is already running")
    row = db.execute(text("""
        INSERT INTO async_jobs (tenant_id, enterprise_id, project_id, job_type, job_status, progress, current_step,
          target_object_type, target_object_id, request_payload, created_by)
        VALUES (:tenant_id, :enterprise_id, :project_id, 'peer_report_parse', 'pending', 0, 'queued',
          'peer_report_files', :peer_report_id, CAST(:request_payload AS jsonb), :created_by)
        RETURNING job_id::text, tenant_id::text, enterprise_id::text, project_id::text, job_type, job_status::text,
          progress, current_step, target_object_type, target_object_id::text, request_payload, result_payload,
          error_payload, created_at, started_at, finished_at
    """), {"tenant_id": user["current_tenant_id"], "enterprise_id": project["enterprise_id"], "project_id": project_id, "peer_report_id": peer_report_id, "request_payload": json.dumps(payload.model_dump()), "created_by": user["user_id"]}).mappings().first()
    db.execute(text("""
        UPDATE peer_report_files
        SET parse_status='pending', updated_at=now()
        WHERE tenant_id=:tenant_id AND project_id=:project_id AND peer_report_id=:peer_report_id
    """), {"tenant_id": user["current_tenant_id"], "project_id": project_id, "peer_report_id": peer_report_id})
    write_audit_log(db, tenant_id=user["current_tenant_id"], enterprise_id=project["enterprise_id"], project_id=project_id, user_id=user["user_id"], user_name=user["name"], action_type="peer_report.parse_requested", object_type="async_jobs", object_id=row["job_id"], description="创建同行报告解析任务")
    if payload.parser_mode == "mock":
        _run_mock_parse_job(db, tenant_id=user["current_tenant_id"], project_id=project_id, peer_report_id=peer_report_id, job_id=row["job_id"])
    db.commit()
    refreshed = db.execute(text("""
        SELECT job_id::text, tenant_id::text, enterprise_id::text, project_id::text, job_type, job_status::text,
          progress, current_step, target_object_type, target_object_id::text, request_payload, result_payload,
          error_payload, created_at, started_at, finished_at
        FROM async_jobs WHERE tenant_id=:tenant_id AND job_id=:job_id
    """), {"tenant_id": user["current_tenant_id"], "job_id": row["job_id"]}).mappings().first()
    return ok(_job_payload(dict(refreshed)), request_id=request.state.request_id)


@router.get("/jobs/{job_id}")
def get_job(job_id: str, request: Request, db: Session = Depends(get_db), user: dict = Depends(require_permission("project:read"))):
    row = db.execute(text("""
        SELECT job_id::text, tenant_id::text, enterprise_id::text, project_id::text, job_type, job_status::text,
               progress, current_step, target_object_type, target_object_id::text, request_payload, result_payload,
               error_payload, created_at, started_at, finished_at
        FROM async_jobs
        WHERE tenant_id=:tenant_id AND job_id=:job_id
    """), {"tenant_id": user["current_tenant_id"], "job_id": job_id}).mappings().first()
    if not row:
        raise ApiError(404, "JOB_NOT_FOUND", "Job not found")
    if row["project_id"]:
        _authorize_project(request, db, user, row["project_id"])
    elif row["enterprise_id"] and not user_can_access_enterprise(user, row["enterprise_id"]):
        write_audit_log(db, tenant_id=user["current_tenant_id"], enterprise_id=row["enterprise_id"], user_id=user["user_id"], user_name=user["name"], action_type="security.job_access_denied", object_type="async_jobs", object_id=job_id, description="任务不存在或无访问范围", ip_address=request.client.host if request.client else None, user_agent=request.headers.get("user-agent"))
        db.commit()
        raise ApiError(403, "AUTH_FORBIDDEN", "Access denied")
    return ok(_job_payload(dict(row)), request_id=request.state.request_id)


def _result_collection_payload(rows, *, object_type: str, id_column: str) -> list[dict]:
    items = []
    for row in rows:
        item = dict(row)
        item["result_id"] = item[id_column]
        item["object_type"] = object_type
        items.append(item)
    return items


def _get_parse_result_collections(db: Session, *, tenant_id: str, project_id: str, peer_report_id: str) -> dict:
    standards = db.execute(text("""
        SELECT extracted_standard_id::text, peer_report_id::text, extracted_standard_name, mapped_standard_code,
               mapped_standard_name, standard_version, adoption_type, explicit_statement, include_in_adoption_stats,
               confidence, source_references, review_status::text, reviewed_by::text, reviewed_at, review_note, created_at
        FROM report_extracted_standards
        WHERE tenant_id=:tenant_id AND project_id=:project_id AND peer_report_id=:peer_report_id
        ORDER BY created_at ASC
    """), {"tenant_id": tenant_id, "project_id": project_id, "peer_report_id": peer_report_id}).mappings().all()
    topics = db.execute(text("""
        SELECT extracted_topic_id::text, peer_report_id::text, original_topic_name, mapped_topic_code, mapped_topic_name,
               topic_category::text, is_material_topic, financial_materiality::text, impact_materiality::text,
               double_materiality_result::text, confidence, source_references, include_in_topic_stats,
               review_status::text, reviewed_by::text, reviewed_at, review_note, created_at
        FROM report_extracted_topics
        WHERE tenant_id=:tenant_id AND project_id=:project_id AND peer_report_id=:peer_report_id
        ORDER BY created_at ASC
    """), {"tenant_id": tenant_id, "project_id": project_id, "peer_report_id": peer_report_id}).mappings().all()
    metrics = db.execute(text("""
        SELECT extracted_metric_id::text, peer_report_id::text, original_metric_name, mapped_metric_code, mapped_metric_name,
               related_topic_code, metric_type::text, data_type::text, numeric_value, text_value, unit, reporting_period,
               organizational_boundary, is_table_data, table_title, confidence, source_references, review_status::text, created_at
        FROM report_extracted_metrics
        WHERE tenant_id=:tenant_id AND project_id=:project_id AND peer_report_id=:peer_report_id
        ORDER BY created_at ASC
    """), {"tenant_id": tenant_id, "project_id": project_id, "peer_report_id": peer_report_id}).mappings().all()
    cases = db.execute(text("""
        SELECT extracted_case_id::text, peer_report_id::text, case_title, case_type, related_topic_code, case_summary,
               case_result, usable_as_peer_reference, caution, confidence, source_references, review_status::text, created_at
        FROM report_extracted_cases
        WHERE tenant_id=:tenant_id AND project_id=:project_id AND peer_report_id=:peer_report_id
        ORDER BY created_at ASC
    """), {"tenant_id": tenant_id, "project_id": project_id, "peer_report_id": peer_report_id}).mappings().all()
    return {
        "standards": _result_collection_payload(standards, object_type="standard", id_column="extracted_standard_id"),
        "topics": _result_collection_payload(topics, object_type="topic", id_column="extracted_topic_id"),
        "metrics": _result_collection_payload(metrics, object_type="metric", id_column="extracted_metric_id"),
        "cases": _result_collection_payload(cases, object_type="case", id_column="extracted_case_id"),
    }


@router.get("/projects/{project_id}/peer-reports/{peer_report_id}/parse-result")
def get_peer_report_parse_result(project_id: str, peer_report_id: str, request: Request, db: Session = Depends(get_db), user: dict = Depends(require_permission("project:read"))):
    _authorize_project(request, db, user, project_id)
    report = _get_peer_report(db, user["current_tenant_id"], project_id, peer_report_id)
    if not report:
        raise ApiError(404, "PEER_REPORT_NOT_FOUND", "Peer report not found")
    collections = _get_parse_result_collections(db, tenant_id=user["current_tenant_id"], project_id=project_id, peer_report_id=peer_report_id)
    issues = db.execute(text("""
        SELECT ai_review_issue_id::text, object_type, object_id::text, issue_type, severity::text, location,
               description, suggested_fix, must_fix, source_references, review_status::text, created_at
        FROM ai_review_issues
        WHERE tenant_id=:tenant_id AND project_id=:project_id AND object_id=:peer_report_id
        ORDER BY created_at ASC
    """), {"tenant_id": user["current_tenant_id"], "project_id": project_id, "peer_report_id": peer_report_id}).mappings().all()
    return ok({"peer_report_id": peer_report_id, "parse_status": report["parse_status"], "ai_review_status": report.get("ai_review_status"), "result": {**collections, "ai_review_issues": [dict(row) for row in issues]}}, request_id=request.state.request_id)


def _patch_standard_result(db: Session, *, tenant_id: str, project_id: str, peer_report_id: str, result_id: str, payload: ParseResultPatchRequest, user_id: str) -> int:
    return db.execute(text("""
        UPDATE report_extracted_standards
        SET mapped_standard_code=COALESCE(:mapped_standard_code, mapped_standard_code),
            mapped_standard_name=COALESCE(:mapped_standard_name, mapped_standard_name),
            review_status=:review_status,
            include_in_adoption_stats=(:review_status IN ('accepted', 'edited')),
            reviewed_by=:reviewed_by,
            reviewed_at=now(),
            review_note=COALESCE(:review_note, review_note)
        WHERE tenant_id=:tenant_id AND project_id=:project_id AND peer_report_id=:peer_report_id AND extracted_standard_id=:result_id
    """), {"tenant_id": tenant_id, "project_id": project_id, "peer_report_id": peer_report_id, "result_id": result_id, "reviewed_by": user_id, **payload.model_dump()}).rowcount


def _patch_topic_result(db: Session, *, tenant_id: str, project_id: str, peer_report_id: str, result_id: str, payload: ParseResultPatchRequest, user_id: str) -> int:
    return db.execute(text("""
        UPDATE report_extracted_topics
        SET mapped_topic_code=COALESCE(:mapped_topic_code, mapped_topic_code),
            mapped_topic_name=COALESCE(:mapped_topic_name, mapped_topic_name),
            financial_materiality=COALESCE(CAST(:financial_materiality AS materiality_level), financial_materiality),
            impact_materiality=COALESCE(CAST(:impact_materiality AS materiality_level), impact_materiality),
            review_status=:review_status,
            include_in_topic_stats=(:review_status IN ('accepted', 'edited')),
            reviewed_by=:reviewed_by,
            reviewed_at=now(),
            review_note=COALESCE(:review_note, review_note)
        WHERE tenant_id=:tenant_id AND project_id=:project_id AND peer_report_id=:peer_report_id AND extracted_topic_id=:result_id
    """), {"tenant_id": tenant_id, "project_id": project_id, "peer_report_id": peer_report_id, "result_id": result_id, "reviewed_by": user_id, **payload.model_dump()}).rowcount


def _patch_metric_result(db: Session, *, tenant_id: str, project_id: str, peer_report_id: str, result_id: str, payload: ParseResultPatchRequest) -> int:
    return db.execute(text("""
        UPDATE report_extracted_metrics
        SET mapped_metric_code=COALESCE(:mapped_metric_code, mapped_metric_code),
            mapped_metric_name=COALESCE(:mapped_metric_name, mapped_metric_name),
            related_topic_code=COALESCE(:mapped_topic_code, related_topic_code),
            review_status=:review_status
        WHERE tenant_id=:tenant_id AND project_id=:project_id AND peer_report_id=:peer_report_id AND extracted_metric_id=:result_id
    """), {"tenant_id": tenant_id, "project_id": project_id, "peer_report_id": peer_report_id, "result_id": result_id, **payload.model_dump()}).rowcount


def _patch_case_result(db: Session, *, tenant_id: str, project_id: str, peer_report_id: str, result_id: str, payload: ParseResultPatchRequest) -> int:
    return db.execute(text("""
        UPDATE report_extracted_cases
        SET related_topic_code=COALESCE(:mapped_topic_code, related_topic_code),
            review_status=:review_status,
            usable_as_peer_reference=(:review_status IN ('accepted', 'edited'))
        WHERE tenant_id=:tenant_id AND project_id=:project_id AND peer_report_id=:peer_report_id AND extracted_case_id=:result_id
    """), {"tenant_id": tenant_id, "project_id": project_id, "peer_report_id": peer_report_id, "result_id": result_id, **payload.model_dump()}).rowcount


@router.patch("/projects/{project_id}/peer-reports/{peer_report_id}/parse-result/{result_id}")
def patch_peer_report_parse_result(project_id: str, peer_report_id: str, result_id: str, payload: ParseResultPatchRequest, request: Request, db: Session = Depends(get_db), user: dict = Depends(require_permission("project:update"))):
    project = _authorize_project(request, db, user, project_id)
    report = _get_peer_report(db, user["current_tenant_id"], project_id, peer_report_id)
    if not report:
        raise ApiError(404, "PEER_REPORT_NOT_FOUND", "Peer report not found")
    if payload.object_type == "standard":
        rowcount = _patch_standard_result(db, tenant_id=user["current_tenant_id"], project_id=project_id, peer_report_id=peer_report_id, result_id=result_id, payload=payload, user_id=user["user_id"])
    elif payload.object_type == "topic":
        rowcount = _patch_topic_result(db, tenant_id=user["current_tenant_id"], project_id=project_id, peer_report_id=peer_report_id, result_id=result_id, payload=payload, user_id=user["user_id"])
    elif payload.object_type == "metric":
        rowcount = _patch_metric_result(db, tenant_id=user["current_tenant_id"], project_id=project_id, peer_report_id=peer_report_id, result_id=result_id, payload=payload)
    else:
        rowcount = _patch_case_result(db, tenant_id=user["current_tenant_id"], project_id=project_id, peer_report_id=peer_report_id, result_id=result_id, payload=payload)
    if rowcount != 1:
        raise ApiError(404, "PARSE_RESULT_NOT_FOUND", "Parse result not found")
    write_audit_log(db, tenant_id=user["current_tenant_id"], enterprise_id=project["enterprise_id"], project_id=project_id, user_id=user["user_id"], user_name=user["name"], action_type="peer_report.parse_result_reviewed", object_type=payload.object_type, object_id=result_id, description="人工修正同行报告解析结果")
    db.commit()
    return ok({"result_id": result_id, "object_type": payload.object_type, "review_status": payload.review_status}, request_id=request.state.request_id)


@router.post("/projects/{project_id}/peer-reports/{peer_report_id}/approve-and-store")
def approve_peer_report_parse_result(project_id: str, peer_report_id: str, request: Request, db: Session = Depends(get_db), user: dict = Depends(require_permission("project:update"))):
    project = _authorize_project(request, db, user, project_id)
    report = _get_peer_report(db, user["current_tenant_id"], project_id, peer_report_id)
    if not report:
        raise ApiError(404, "PEER_REPORT_NOT_FOUND", "Peer report not found")
    pending_count = db.execute(text("""
        SELECT
          (SELECT count(*) FROM report_extracted_standards WHERE tenant_id=:tenant_id AND project_id=:project_id AND peer_report_id=:peer_report_id AND review_status='pending') +
          (SELECT count(*) FROM report_extracted_topics WHERE tenant_id=:tenant_id AND project_id=:project_id AND peer_report_id=:peer_report_id AND review_status='pending') +
          (SELECT count(*) FROM report_extracted_metrics WHERE tenant_id=:tenant_id AND project_id=:project_id AND peer_report_id=:peer_report_id AND review_status='pending') +
          (SELECT count(*) FROM report_extracted_cases WHERE tenant_id=:tenant_id AND project_id=:project_id AND peer_report_id=:peer_report_id AND review_status='pending')
    """), {"tenant_id": user["current_tenant_id"], "project_id": project_id, "peer_report_id": peer_report_id}).scalar_one()
    if pending_count:
        raise ApiError(400, "PARSE_RESULT_REVIEW_PENDING", "All parse results must be reviewed before approval")
    db.execute(text("""
        UPDATE peer_report_files
        SET parse_status='approved', ai_review_status='approved', approved_by=:approved_by, approved_at=now(), stored_at=now(), updated_at=now()
        WHERE tenant_id=:tenant_id AND project_id=:project_id AND peer_report_id=:peer_report_id
    """), {"tenant_id": user["current_tenant_id"], "project_id": project_id, "peer_report_id": peer_report_id, "approved_by": user["user_id"]})
    write_audit_log(db, tenant_id=user["current_tenant_id"], enterprise_id=project["enterprise_id"], project_id=project_id, user_id=user["user_id"], user_name=user["name"], action_type="peer_report.approved_and_stored", object_type="peer_report_files", object_id=peer_report_id, description="审核通过同行报告解析结果并入库")
    db.commit()
    return ok({"peer_report_id": peer_report_id, "parse_status": "approved", "ai_review_status": "approved"}, request_id=request.state.request_id)

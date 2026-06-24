from fastapi import Depends, Header, Request
from sqlalchemy.orm import Session
from app.core.errors import ApiError
from app.core.security import decode_token
from app.db.session import get_db
from app.modules.audit.service import write_audit_log
from app.modules.auth.service import build_current_user


def get_current_user(request: Request, db: Session = Depends(get_db), authorization: str | None = Header(None), x_tenant_id: str | None = Header(None)) -> dict:
    if not authorization or not authorization.lower().startswith("bearer "):
        raise ApiError(401, "AUTH_UNAUTHORIZED", "Authentication token is required")
    payload = decode_token(authorization.split(" ", 1)[1])
    tenant_id = str(payload["tenant_id"])
    if x_tenant_id and x_tenant_id != tenant_id:
        try:
            write_audit_log(db, tenant_id=tenant_id, user_id=str(payload.get("sub")), action_type="security.cross_tenant_denied", description="租户上下文与Token不匹配", ip_address=request.client.host if request.client else None, user_agent=request.headers.get("user-agent"))
            db.commit()
        finally:
            raise ApiError(403, "AUTH_FORBIDDEN", "Access denied")
    user = build_current_user(db, str(payload["sub"]), tenant_id)
    request.state.user = user
    request.state.tenant_id = tenant_id
    return user

def require_permission(permission: str):
    def checker(request: Request, db: Session = Depends(get_db), user: dict = Depends(get_current_user)) -> dict:
        permissions = set(user.get("permissions", []))
        allowed = "*" in permissions or permission in permissions or any(p.endswith(":*") and permission.startswith(p[:-1]) for p in permissions)
        if not allowed:
            write_audit_log(db, tenant_id=user["current_tenant_id"], user_id=user["user_id"], user_name=user["name"], action_type="security.permission_denied", description=f"缺少权限: {permission}", ip_address=request.client.host if request.client else None, user_agent=request.headers.get("user-agent"))
            db.commit()
            raise ApiError(403, "AUTH_FORBIDDEN", "Permission denied")
        return user
    return checker


def require_permissions(required_permissions: list[str]):
    def checker(request: Request, db: Session = Depends(get_db), user: dict = Depends(get_current_user)) -> dict:
        permissions = set(user.get("permissions", []))
        missing_permissions = [
            permission
            for permission in required_permissions
            if not ("*" in permissions or permission in permissions or any(p.endswith(":*") and permission.startswith(p[:-1]) for p in permissions))
        ]
        if missing_permissions:
            missing = ", ".join(missing_permissions)
            write_audit_log(db, tenant_id=user["current_tenant_id"], user_id=user["user_id"], user_name=user["name"], action_type="security.permission_denied", description=f"缺少权限: {missing}", ip_address=request.client.host if request.client else None, user_agent=request.headers.get("user-agent"))
            db.commit()
            raise ApiError(403, "AUTH_FORBIDDEN", "Permission denied")
        return user
    return checker

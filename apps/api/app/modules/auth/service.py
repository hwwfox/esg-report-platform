from sqlalchemy import text
from sqlalchemy.orm import Session
from app.core.errors import ApiError
from app.core.security import create_token, verify_password
from app.modules.audit.service import write_audit_log


def _row_to_dict(row):
    return dict(row._mapping) if row else None

def get_user_by_email(db: Session, email: str, tenant_code: str = "DEFAULT") -> dict | None:
    return _row_to_dict(db.execute(text("""
        SELECT u.*, t.tenant_code, t.tenant_name FROM users u
        JOIN tenants t ON t.tenant_id = u.tenant_id
        WHERE lower(u.email)=lower(:email) AND t.tenant_code=:tenant_code AND u.status='active' AND t.status='active'
    """), {"email": email, "tenant_code": tenant_code}).first())

def roles_and_permissions(db: Session, tenant_id: str, user_id: str) -> tuple[list[str], list[str]]:
    rows = db.execute(text("""
        SELECT r.role_code, r.permissions FROM user_roles ur
        JOIN roles r ON r.role_id=ur.role_id AND (r.tenant_id=ur.tenant_id OR r.tenant_id IS NULL)
        WHERE ur.tenant_id=:tenant_id AND ur.user_id=:user_id AND r.status='active'
    """), {"tenant_id": tenant_id, "user_id": user_id}).mappings().all()
    roles: list[str] = []
    permissions: set[str] = set()
    for row in rows:
        roles.append(row["role_code"])
        for permission in row["permissions"] or []:
            permissions.add(permission)
    return roles, sorted(permissions)

def enterprise_access(db: Session, tenant_id: str, user_id: str) -> list[dict]:
    return [dict(r) for r in db.execute(text("""
        SELECT e.enterprise_id::text, e.enterprise_name, e.enterprise_code, eua.access_scope
        FROM enterprise_user_access eua
        JOIN enterprises e ON e.enterprise_id=eua.enterprise_id AND e.tenant_id=eua.tenant_id
        WHERE eua.tenant_id=:tenant_id AND eua.user_id=:user_id AND eua.status='active'
        ORDER BY e.enterprise_name
    """), {"tenant_id": tenant_id, "user_id": user_id}).mappings().all()]

def build_current_user(db: Session, user_id: str, tenant_id: str) -> dict:
    user = _row_to_dict(db.execute(text("""
        SELECT user_id::text, tenant_id::text, name, email, avatar_url, status FROM users
        WHERE tenant_id=:tenant_id AND user_id=:user_id AND status='active'
    """), {"tenant_id": tenant_id, "user_id": user_id}).first())
    if not user:
        raise ApiError(401, "AUTH_UNAUTHORIZED", "Authenticated user is unavailable")
    roles, permissions = roles_and_permissions(db, tenant_id, user_id)
    enterprises = enterprise_access(db, tenant_id, user_id)
    return {"user_id": user["user_id"], "name": user["name"], "email": user["email"], "current_tenant_id": user["tenant_id"], "current_enterprise_id": enterprises[0]["enterprise_id"] if enterprises else None, "roles": roles, "permissions": permissions, "enterprises": enterprises}

def login(db: Session, *, email: str, password: str, request) -> dict:
    user = get_user_by_email(db, email)
    if not user or not (verify_password(password, user.get("password_hash"))):
        if user:
            write_audit_log(db, tenant_id=str(user["tenant_id"]), user_id=str(user["user_id"]), user_name=user["name"], action_type="auth.login_failed", object_type="users", object_id=str(user["user_id"]), description="登录失败", ip_address=request.client.host if request.client else None, user_agent=request.headers.get("user-agent"))
            db.commit()
        raise ApiError(401, "AUTH_UNAUTHORIZED", "Invalid email or password")
    tenant_id, user_id = str(user["tenant_id"]), str(user["user_id"])
    access_token, expires_in = create_token(user_id, tenant_id, "access")
    refresh_token, _ = create_token(user_id, tenant_id, "refresh")
    db.execute(text("UPDATE users SET last_login_at=now() WHERE tenant_id=:tenant_id AND user_id=:user_id"), {"tenant_id": tenant_id, "user_id": user_id})
    write_audit_log(db, tenant_id=tenant_id, user_id=user_id, user_name=user["name"], action_type="auth.login_success", object_type="users", object_id=user_id, description="登录成功", ip_address=request.client.host if request.client else None, user_agent=request.headers.get("user-agent"))
    db.commit()
    current = build_current_user(db, user_id, tenant_id)
    return {"access_token": access_token, "refresh_token": refresh_token, "expires_in": expires_in, "user": {"user_id": user_id, "name": user["name"], "email": user["email"], "avatar_url": user.get("avatar_url"), "status": user["status"]}, "available_tenants": [{"tenant_id": tenant_id, "tenant_name": user["tenant_name"], "roles": current["roles"]}]}

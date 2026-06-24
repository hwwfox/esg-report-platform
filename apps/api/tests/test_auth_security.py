from pathlib import Path
from types import SimpleNamespace

from app.core.security import create_token, decode_token, hash_password, verify_password
from app.core.errors import ApiError
from app.modules.auth import dependencies as auth_dependencies
from app.modules.projects.router import user_can_access_enterprise


DEMO_PASSWORD_HASH = "pbkdf2_sha256$120000$SMMW4Xbdu34FhUkKPIq5Mw==$TYS3ovZYqJ2bTLGKaJj2isqd+keujkLbW75Xrp0lJf8="
STALE_DEMO_PASSWORD_HASH = "pbkdf2_sha256$120000$SMMW4Xbdu34FhUkKPIq5Mw==$Y+tg83U5LG8+OiidKae8grhDMIM+C98K3GtnQMvJ1dY="


def test_password_hash_round_trip():
    hashed = hash_password("ChangeMe123!")
    assert verify_password("ChangeMe123!", hashed)
    assert not verify_password("wrong", hashed)


def test_seeded_demo_password_hash_matches_default_password():
    assert verify_password("ChangeMe123!", DEMO_PASSWORD_HASH)
    assert not verify_password("wrong", DEMO_PASSWORD_HASH)


def test_seed_sql_uses_valid_demo_password_hash():
    repo_root = Path(__file__).resolve().parents[3]
    seed_sql = repo_root / "db/seed/ESG_PostgreSQL_Seed_Data_v0.1.sql"
    migration_sql = repo_root / "db/migrations/V001__auth_password_hashes.sql"

    seed_text = seed_sql.read_text()
    assert DEMO_PASSWORD_HASH in seed_text
    assert "password_hash = CASE" in seed_text
    assert "THEN EXCLUDED.password_hash" in seed_text
    assert "ELSE users.password_hash" in seed_text
    assert STALE_DEMO_PASSWORD_HASH in seed_text
    migration_text = migration_sql.read_text()
    assert DEMO_PASSWORD_HASH in migration_text
    assert "t.tenant_code = 'DEFAULT'" in migration_text
    assert "u.tenant_id = t.tenant_id" in migration_text
    assert "u.password_hash IS NULL" in migration_text


def test_expired_token_uses_stable_error_code():
    token, _ = create_token("user-1", "tenant-1", expires_in=-1)
    try:
        decode_token(token)
    except ApiError as exc:
        assert exc.code == "AUTH_TOKEN_EXPIRED"
    else:
        raise AssertionError("Expired token should raise ApiError")


def test_refresh_token_rejected_as_access_token():
    token, _ = create_token("user-1", "tenant-1", token_type="refresh")
    try:
        decode_token(token)
    except ApiError as exc:
        assert exc.code == "AUTH_UNAUTHORIZED"
    else:
        raise AssertionError("Refresh token should not be accepted as access token")


def test_missing_authorization_header_returns_unauthorized():
    request = SimpleNamespace(client=None, headers={})
    try:
        auth_dependencies.get_current_user(request, db=None, authorization=None)
    except ApiError as exc:
        assert exc.status_code == 401
        assert exc.code == "AUTH_UNAUTHORIZED"
    else:
        raise AssertionError("Missing bearer token should raise ApiError")


def test_cross_tenant_header_is_rejected_and_audited(monkeypatch):
    audit_calls = []

    class FakeDb:
        def __init__(self):
            self.committed = False

        def commit(self):
            self.committed = True

    def fake_write_audit_log(db, **kwargs):
        audit_calls.append(kwargs)

    monkeypatch.setattr(auth_dependencies, "write_audit_log", fake_write_audit_log)
    db = FakeDb()
    request = SimpleNamespace(client=SimpleNamespace(host="127.0.0.1"), headers={"user-agent": "pytest"})
    token, _ = create_token("user-1", "tenant-1")

    try:
        auth_dependencies.get_current_user(
            request,
            db=db,
            authorization=f"Bearer {token}",
            x_tenant_id="tenant-2",
        )
    except ApiError as exc:
        assert exc.status_code == 403
        assert exc.code == "AUTH_FORBIDDEN"
    else:
        raise AssertionError("Cross-tenant header should raise ApiError")

    assert db.committed
    assert audit_calls[0]["tenant_id"] == "tenant-1"
    assert audit_calls[0]["user_id"] == "user-1"
    assert audit_calls[0]["action_type"] == "security.cross_tenant_denied"


def test_missing_permission_is_rejected_and_audited(monkeypatch):
    audit_calls = []

    class FakeDb:
        def __init__(self):
            self.committed = False

        def commit(self):
            self.committed = True

    def fake_write_audit_log(db, **kwargs):
        audit_calls.append(kwargs)

    monkeypatch.setattr(auth_dependencies, "write_audit_log", fake_write_audit_log)
    db = FakeDb()
    request = SimpleNamespace(client=SimpleNamespace(host="127.0.0.1"), headers={"user-agent": "pytest"})
    checker = auth_dependencies.require_permission("project:update")
    user = {
        "current_tenant_id": "tenant-1",
        "user_id": "user-1",
        "name": "No Permission User",
        "permissions": ["project:read"],
    }

    try:
        checker(request=request, db=db, user=user)
    except ApiError as exc:
        assert exc.status_code == 403
        assert exc.code == "AUTH_FORBIDDEN"
    else:
        raise AssertionError("Missing permission should raise ApiError")

    assert db.committed
    assert audit_calls[0]["tenant_id"] == "tenant-1"
    assert audit_calls[0]["user_id"] == "user-1"
    assert audit_calls[0]["user_name"] == "No Permission User"
    assert audit_calls[0]["action_type"] == "security.permission_denied"


def test_project_access_denies_empty_enterprise_scope():
    assert not user_can_access_enterprise({"enterprises": []}, "enterprise-1")


def test_project_access_allows_explicit_enterprise_scope():
    assert user_can_access_enterprise(
        {"enterprises": [{"enterprise_id": "enterprise-1"}]},
        "enterprise-1",
    )

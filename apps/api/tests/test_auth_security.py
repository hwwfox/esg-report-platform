import time
from pathlib import Path
from app.core.security import create_token, decode_token, hash_password, verify_password
from app.core.errors import ApiError
from app.modules.projects.router import user_can_access_enterprise


DEMO_PASSWORD_HASH = "pbkdf2_sha256$120000$SMMW4Xbdu34FhUkKPIq5Mw==$TYS3ovZYqJ2bTLGKaJj2isqd+keujkLbW75Xrp0lJf8="


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

    assert DEMO_PASSWORD_HASH in seed_sql.read_text()
    assert DEMO_PASSWORD_HASH in migration_sql.read_text()


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


def test_project_access_denies_empty_enterprise_scope():
    assert not user_can_access_enterprise({"enterprises": []}, "enterprise-1")


def test_project_access_allows_explicit_enterprise_scope():
    assert user_can_access_enterprise(
        {"enterprises": [{"enterprise_id": "enterprise-1"}]},
        "enterprise-1",
    )

import time
from app.core.security import create_token, decode_token, hash_password, verify_password
from app.core.errors import ApiError


def test_password_hash_round_trip():
    hashed = hash_password("ChangeMe123!")
    assert verify_password("ChangeMe123!", hashed)
    assert not verify_password("wrong", hashed)


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

import base64, hashlib, hmac, os, time, uuid
from typing import Any
import jwt
from jwt import ExpiredSignatureError, InvalidTokenError
from app.core.config import get_settings
from app.core.errors import ApiError

ALGORITHM = "HS256"

def hash_password(password: str, salt: str | None = None) -> str:
    raw_salt = base64.b64decode(salt) if salt else os.urandom(16)
    digest = hashlib.pbkdf2_hmac("sha256", password.encode(), raw_salt, 120_000)
    return "pbkdf2_sha256$120000$%s$%s" % (base64.b64encode(raw_salt).decode(), base64.b64encode(digest).decode())

def verify_password(password: str, stored_hash: str | None) -> bool:
    if not stored_hash:
        return False
    try:
        scheme, rounds, salt, digest = stored_hash.split("$", 3)
        if scheme != "pbkdf2_sha256":
            return False
        check = hashlib.pbkdf2_hmac("sha256", password.encode(), base64.b64decode(salt), int(rounds))
        return hmac.compare_digest(base64.b64encode(check).decode(), digest)
    except Exception:
        return False

def create_token(subject: str, tenant_id: str, token_type: str = "access", expires_in: int | None = None) -> tuple[str, int]:
    settings = get_settings()
    ttl = expires_in or (settings.jwt_access_token_expire_minutes * 60 if token_type == "access" else settings.jwt_refresh_token_expire_minutes * 60)
    now = int(time.time())
    payload: dict[str, Any] = {"sub": subject, "tenant_id": tenant_id, "type": token_type, "iat": now, "exp": now + ttl, "jti": str(uuid.uuid4())}
    return jwt.encode(payload, settings.jwt_secret, algorithm=ALGORITHM), ttl

def decode_token(token: str, expected_type: str = "access") -> dict[str, Any]:
    try:
        payload = jwt.decode(token, get_settings().jwt_secret, algorithms=[ALGORITHM])
    except ExpiredSignatureError as exc:
        raise ApiError(401, "AUTH_TOKEN_EXPIRED", "Token has expired") from exc
    except InvalidTokenError as exc:
        raise ApiError(401, "AUTH_UNAUTHORIZED", "Invalid authentication token") from exc
    if payload.get("type") != expected_type:
        raise ApiError(401, "AUTH_UNAUTHORIZED", "Invalid token type")
    return payload

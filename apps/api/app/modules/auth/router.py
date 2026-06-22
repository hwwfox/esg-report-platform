from fastapi import APIRouter, Depends, Request
from pydantic import BaseModel
from sqlalchemy.orm import Session
from app.core.response import ok
from app.db.session import get_db
from app.modules.auth.dependencies import get_current_user
from app.modules.auth.service import login as login_user, build_current_user
from app.core.security import decode_token, create_token

router = APIRouter(prefix="/api/v1/auth", tags=["认证与租户"])

class LoginRequest(BaseModel):
    email: str
    password: str
    captcha_token: str | None = None

class RefreshRequest(BaseModel):
    refresh_token: str

@router.post("/login")
def login(payload: LoginRequest, request: Request, db: Session = Depends(get_db)):
    return ok(login_user(db, email=payload.email, password=payload.password, request=request), request_id=request.state.request_id)

@router.get("/me")
def me(request: Request, user: dict = Depends(get_current_user)):
    return ok(user, request_id=request.state.request_id)

@router.post("/refresh")
def refresh(payload: RefreshRequest, request: Request, db: Session = Depends(get_db)):
    decoded = decode_token(payload.refresh_token, "refresh")
    user = build_current_user(db, str(decoded["sub"]), str(decoded["tenant_id"]))
    access_token, expires_in = create_token(user["user_id"], user["current_tenant_id"], "access")
    refresh_token, _ = create_token(user["user_id"], user["current_tenant_id"], "refresh")
    return ok({"access_token": access_token, "refresh_token": refresh_token, "expires_in": expires_in}, request_id=request.state.request_id)

@router.post("/logout")
def logout(request: Request, user: dict = Depends(get_current_user)):
    return ok({"logged_out": True}, request_id=request.state.request_id)

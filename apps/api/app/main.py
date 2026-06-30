from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware

from app.core.config import get_settings
from app.core.response import ok
from app.middleware.request_id import RequestIdMiddleware
from app.core.errors import ApiError, api_error_handler
from app.modules.auth.router import router as auth_router
from app.modules.enterprises.router import router as enterprises_router
from app.modules.projects.router import router as projects_router
from app.modules.standard_library_router import router as standard_library_router
from app.modules.standard_library.router import router as standard_library_router
from app.modules.peer.router import router as peer_router
from app.modules.peer_reports.router import router as peer_reports_router

settings = get_settings()

app = FastAPI(title="ESG Report Platform API", version="0.1.0")
app.add_middleware(RequestIdMiddleware)
app.add_exception_handler(ApiError, api_error_handler)
app.include_router(auth_router)
app.include_router(enterprises_router)
app.include_router(projects_router)
app.include_router(standard_library_router)
app.include_router(peer_router)
app.include_router(peer_reports_router)
app.add_middleware(
    CORSMiddleware,
    allow_origins=[origin.strip() for origin in settings.cors_allowed_origins.split(",")],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.get("/health")
async def health(request: Request):
    return ok(
        data={
            "status": "ok",
            "service": "api",
            "env": settings.app_env,
        },
        request_id=getattr(request.state, "request_id", None),
    )


@app.get("/api/v1/dev/ping")
async def dev_ping(request: Request):
    return ok(data={"pong": True}, request_id=getattr(request.state, "request_id", None))

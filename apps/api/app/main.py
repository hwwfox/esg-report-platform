from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware

from app.core.config import get_settings
from app.core.response import ok
from app.middleware.request_id import RequestIdMiddleware

settings = get_settings()

app = FastAPI(title="ESG Report Platform API", version="0.1.0")
app.add_middleware(RequestIdMiddleware)
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

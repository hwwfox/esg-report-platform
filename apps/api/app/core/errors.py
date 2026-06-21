from fastapi import HTTPException, Request
from fastapi.responses import JSONResponse
from app.core.response import error

class ApiError(HTTPException):
    def __init__(self, status_code: int, code: str, message: str, details: dict | None = None):
        super().__init__(status_code=status_code, detail=message)
        self.code = code
        self.message = message
        self.details = details or {}

async def api_error_handler(request: Request, exc: ApiError):
    return JSONResponse(
        status_code=exc.status_code,
        content=error(exc.code, exc.message, getattr(request.state, "request_id", None), exc.details),
    )

def ok(data=None, message: str = "ok", request_id: str | None = None):
    return {"success": True, "data": data, "message": message, "request_id": request_id}


def error(code: str, message: str, request_id: str | None = None, details: dict | None = None):
    return {
        "success": False,
        "error": {"code": code, "message": message, "details": details or {}},
        "request_id": request_id,
    }

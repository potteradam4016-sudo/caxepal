from fastapi import Request
from fastapi.exceptions import RequestValidationError
from fastapi.responses import JSONResponse
from starlette.exceptions import HTTPException

class APIError(Exception):
    def __init__(self, status: int, code: str, message: str, details=None, headers=None):
        self.status, self.code, self.message = status, code, message
        self.details, self.headers = details or [], headers or {}

def error_body(code, message, request_id="", details=None):
    return {"error": {"code": code, "message": message,
                      "details": details or [], "request_id": request_id}}

def install_handlers(app):
    @app.exception_handler(APIError)
    async def api_error(request: Request, exc: APIError):
        return JSONResponse(error_body(exc.code, exc.message,
            getattr(request.state, "request_id", ""), exc.details),
            status_code=exc.status, headers=exc.headers)

    @app.exception_handler(RequestValidationError)
    async def validation_error(request: Request, exc: RequestValidationError):
        # Do not echo `input`: it may contain passwords, tokens, or personal information.
        details = [{"field": ".".join(str(x) for x in e["loc"]), "type": e["type"]}
                   for e in exc.errors()]
        return JSONResponse(error_body("VALIDATION_ERROR", "입력값을 확인해주세요.",
            getattr(request.state, "request_id", ""), details), status_code=422)

    @app.exception_handler(HTTPException)
    async def http_error(request: Request, exc: HTTPException):
        return JSONResponse(error_body(f"HTTP_{exc.status_code}", "요청을 처리할 수 없습니다.",
            getattr(request.state, "request_id", "")), status_code=exc.status_code,
            headers=exc.headers)

    @app.exception_handler(Exception)
    async def unexpected_error(request: Request, exc: Exception):
        import logging
        logging.getLogger("scnu_pick").error("request_id=%s error_type=%s",
            getattr(request.state, "request_id", ""), type(exc).__name__)
        return JSONResponse(error_body("INTERNAL_ERROR", "서버 오류가 발생했습니다.",
            getattr(request.state, "request_id", "")), status_code=500)

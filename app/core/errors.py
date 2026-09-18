from fastapi import Request
from fastapi.responses import JSONResponse
from fastapi.exceptions import RequestValidationError
from app.core.envelope import error

class AppException(Exception):
    def __init__(self, code: str, message: str, retryable: bool = False, event_id: str | None = None):
        self.code = code
        self.message = message
        self.retryable = retryable
        self.event_id = event_id

def setup_exception_handlers(app):
    @app.exception_handler(AppException)
    async def app_exception_handler(request: Request, exc: AppException):
        status_code = 400
        if exc.code == "E_UNAUTHORIZED":
            status_code = 401
        elif exc.code == "E_FORBIDDEN":
            status_code = 403
        elif exc.code == "E_NOT_FOUND":
            status_code = 404
        elif exc.code == "E_RATE_LIMIT":
            status_code = 429
        elif exc.code == "E_INTERNAL":
            status_code = 500

        return JSONResponse(
            status_code=status_code,
            content=error(
                code=exc.code,
                message=exc.message,
                retryable=exc.retryable,
                event_id=exc.event_id
            )
        )

    @app.exception_handler(RequestValidationError)
    async def validation_exception_handler(request: Request, exc: RequestValidationError):
        return JSONResponse(
            status_code=422,
            content=error(
                code="E_VALIDATION",
                message=str(exc),
                retryable=False
            )
        )

    @app.exception_handler(Exception)
    async def global_exception_handler(request: Request, exc: Exception):
        import uuid
        import logging
        event_id = uuid.uuid4().hex
        logging.error(f"Unhandled exception {event_id}: {exc}", exc_info=True)
        return JSONResponse(
            status_code=500,
            content=error(
                code="E_INTERNAL",
                message="An unexpected internal error occurred.",
                retryable=True,
                event_id=event_id
            )
        )

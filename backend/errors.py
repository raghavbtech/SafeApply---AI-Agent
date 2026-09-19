"""
SafeApply Typed Errors and HTTP Exception Handlers.
Ensures safe error messaging without stack trace or credential leakage.
"""

from typing import Any, Dict, Optional
from fastapi import Request, status
from fastapi.responses import JSONResponse


class SafeApplyError(Exception):
    """Base exception for SafeApply application errors."""

    def __init__(
        self,
        message: str,
        status_code: int = status.HTTP_500_INTERNAL_SERVER_ERROR,
        details: Optional[Dict[str, Any]] = None,
    ):
        super().__init__(message)
        self.message = message
        self.status_code = status_code
        self.details = details or {}


class NotFoundError(SafeApplyError):
    def __init__(self, resource: str, identifier: str):
        super().__init__(
            message=f"{resource} '{identifier}' not found or inaccessible.",
            status_code=status.HTTP_404_NOT_FOUND,
        )


class UnauthorizedError(SafeApplyError):
    def __init__(self, message: str = "Authentication credentials missing or invalid."):
        super().__init__(message=message, status_code=status.HTTP_401_UNAUTHORIZED)


class ForbiddenError(SafeApplyError):
    def __init__(self, message: str = "You do not have permission to access this resource."):
        super().__init__(message=message, status_code=status.HTTP_403_FORBIDDEN)


class ValidationError(SafeApplyError):
    def __init__(self, message: str, details: Optional[Dict[str, Any]] = None):
        super().__init__(
            message=message,
            status_code=getattr(status, "HTTP_422_UNPROCESSABLE_CONTENT", 422),
            details=details,
        )


class ConflictError(SafeApplyError):
    def __init__(self, message: str):
        super().__init__(message=message, status_code=status.HTTP_409_CONFLICT)


async def safeapply_exception_handler(request: Request, exc: SafeApplyError) -> JSONResponse:
    return JSONResponse(
        status_code=exc.status_code,
        content={
            "error": {
                "message": exc.message,
                "status_code": exc.status_code,
                "details": exc.details,
            }
        },
    )


async def generic_exception_handler(request: Request, exc: Exception) -> JSONResponse:
    # Log exception internally, but return sanitized message to client
    print(f"[SafeApply Internal Error] {type(exc).__name__}: {str(exc)}")
    return JSONResponse(
        status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
        content={
            "error": {
                "message": "An internal server error occurred. Please try again later.",
                "status_code": 500,
            }
        },
    )

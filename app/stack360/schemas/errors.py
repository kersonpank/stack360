from __future__ import annotations

from enum import Enum
from typing import Any, Optional

from pydantic import BaseModel


class ErrorCode(str, Enum):
    AUTH_INVALID = "AUTH_INVALID"
    SCOPE_DENIED = "SCOPE_DENIED"
    SOURCE_DISABLED = "SOURCE_DISABLED"
    SCHEMA_UNSUPPORTED = "SCHEMA_UNSUPPORTED"
    VALIDATION_ERROR = "VALIDATION_ERROR"
    EXPERIENCE_NOT_FOUND = "EXPERIENCE_NOT_FOUND"
    IDENTITY_CONFLICT = "IDENTITY_CONFLICT"
    EVENT_ID_CONFLICT = "EVENT_ID_CONFLICT"
    EVENT_ALREADY_PROCESSED = "EVENT_ALREADY_PROCESSED"
    RATE_LIMITED = "RATE_LIMITED"
    NOT_FOUND = "NOT_FOUND"
    INTERNAL_ERROR = "INTERNAL_ERROR"


_HTTP = {
    ErrorCode.AUTH_INVALID: 401,
    ErrorCode.SCOPE_DENIED: 403,
    ErrorCode.SOURCE_DISABLED: 403,
    ErrorCode.SCHEMA_UNSUPPORTED: 400,
    ErrorCode.VALIDATION_ERROR: 422,
    ErrorCode.EXPERIENCE_NOT_FOUND: 422,
    ErrorCode.IDENTITY_CONFLICT: 409,
    ErrorCode.EVENT_ID_CONFLICT: 409,
    ErrorCode.EVENT_ALREADY_PROCESSED: 409,
    ErrorCode.RATE_LIMITED: 429,
    ErrorCode.NOT_FOUND: 404,
    ErrorCode.INTERNAL_ERROR: 500,
}


class ErrorBody(BaseModel):
    code: ErrorCode
    message: str
    details: dict[str, Any] = {}


class ErrorResponse(BaseModel):
    error: ErrorBody


class Stack360Error(Exception):
    """Erro de negócio com contrato estável. NUNCA vaza stack trace."""

    def __init__(
        self,
        code: ErrorCode,
        message: str,
        details: Optional[dict[str, Any]] = None,
    ) -> None:
        super().__init__(message)
        self.code = code
        self.message = message
        self.details = details or {}

    @property
    def http_status(self) -> int:
        return _HTTP[self.code]

    def to_response(self) -> ErrorResponse:
        return ErrorResponse(error=ErrorBody(code=self.code, message=self.message, details=self.details))


def http_status_for(code: ErrorCode) -> int:
    return _HTTP[code]

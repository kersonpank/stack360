"""Error contract do Stack360 — SEM stack trace, formato estável.

Escopo cuidadosamente limitado às rotas do Stack360 para NÃO mudar o
comportamento do app legado (que compartilha o mesmo objeto FastAPI).
"""
from __future__ import annotations

import logging
from typing import Callable

from fastapi import FastAPI, Request, Response
from fastapi.exception_handlers import request_validation_exception_handler
from fastapi.exceptions import RequestValidationError
from fastapi.responses import JSONResponse
from fastapi.routing import APIRoute

from app.stack360.schemas.errors import ErrorBody, ErrorCode, ErrorResponse, Stack360Error

_log = logging.getLogger("stack360")

# prefixos das rotas do Stack360 (todas sob /api/v1)
STACK360_PREFIXES = (
    "/api/v1/health",
    "/api/v1/ingest",
    "/api/v1/webhooks",
    "/api/v1/people",
    "/api/v1/companies",
    "/api/v1/interactions",
    "/api/v1/experiences",
    "/api/v1/runs",
    "/api/v1/sources",
    "/api/v1/resolution-cases",
)


def _is_stack360(path: str) -> bool:
    return any(path.startswith(p) for p in STACK360_PREFIXES)


def _json(resp: ErrorResponse, status: int) -> JSONResponse:
    return JSONResponse(status_code=status, content=resp.model_dump(mode="json"))


class Stack360Route(APIRoute):
    """Converte exceções inesperadas do handler em INTERNAL_ERROR (sem vazar trace)."""

    def get_route_handler(self) -> Callable:
        original = super().get_route_handler()

        async def handler(request: Request) -> Response:
            try:
                return await original(request)
            except Stack360Error:
                raise
            except RequestValidationError:
                raise
            except Exception:  # noqa: BLE001
                _log.exception("stack360 route error: %s", request.url.path)
                raise Stack360Error(ErrorCode.INTERNAL_ERROR, "erro interno")

        return handler


def register_exception_handlers(app: FastAPI) -> None:
    @app.exception_handler(Stack360Error)
    async def _stack360_error(_: Request, exc: Stack360Error):  # noqa: ANN202
        return _json(exc.to_response(), exc.http_status)

    @app.exception_handler(RequestValidationError)
    async def _validation(request: Request, exc: RequestValidationError):  # noqa: ANN202
        if not _is_stack360(request.url.path):
            # legado: mantém o handler padrão do FastAPI
            return await request_validation_exception_handler(request, exc)
        resp = ErrorResponse(
            error=ErrorBody(
                code=ErrorCode.VALIDATION_ERROR,
                message="payload inválido",
                details={"errors": exc.errors()},
            )
        )
        return _json(resp, 422)

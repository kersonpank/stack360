"""Entrypoint do Stack360 Canonical Core — FastAPI PRÓPRIO e INDEPENDENTE.

Dois processos separados, sem acoplamento:

    uvicorn app.main:app            -> LEGADO (lifespan + schedulers legados)
    uvicorn app.stack360.main:app  -> CANONICAL CORE (este arquivo)

Este módulo NÃO importa ``app.main``, ``app.scheduler.*`` nem ``app.api.v1.*``:
o core canônico não tem schedulers e não expõe rotas legadas. Helpers/config
genéricos podem ser importados de módulos — nunca o objeto ``app`` legado.
"""
from __future__ import annotations

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.stack360.api.errors import register_exception_handlers
from app.stack360.api.router import router as stack360_router

app = FastAPI(
    title="Stack360 Canonical Core",
    description="Omnichannel Data & Intelligence Hub — canonical data + integration layer.",
    version="1.0.0",
    docs_url="/docs",
    redoc_url="/redoc",
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=[f"http://{host}:{port}" for host in ("localhost", "127.0.0.1") for port in range(3000, 3006)],
    allow_credentials=False,  # auth é por API key, não cookie
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(stack360_router)
register_exception_handlers(app)

from fastapi import FastAPI

from app.api.v1.router import router as v1_router

app = FastAPI(
    title="Stakeholder Intelligence API",
    description="API para consulta de memória operacional e comercial baseada em conversas de WhatsApp.",
    version="1.0.0",
    docs_url="/docs",
    redoc_url="/redoc",
)

app.include_router(v1_router)

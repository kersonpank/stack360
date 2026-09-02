from __future__ import annotations

from fastapi import APIRouter, Header, Request
from sqlalchemy import select

from adapters import get_adapter
from app.stack360.api.errors import Stack360Route
from app.stack360.auth import AuthContext, resolve_api_key
from app.stack360.db import get_sessionmaker
from app.stack360.ingestion.gateway import ingest_one
from app.stack360.models.data_source import DataSource
from app.stack360.models.webhook import WebhookEndpoint
from app.stack360.schemas.envelope import StackEvent
from app.stack360.schemas.errors import ErrorCode, Stack360Error
from app.stack360.security.hashing import constant_time_equals, hmac_sha256_hex

router = APIRouter(prefix="/webhooks", tags=["Webhooks"], route_class=Stack360Route)


@router.post("/{source_key}")
async def inbound_webhook(
    source_key: str,
    request: Request,
    authorization: str | None = Header(default=None),
    x_api_key: str | None = Header(default=None, alias="X-API-Key"),
):
    body = await request.body()
    Session_ = get_sessionmaker()

    with Session_() as db:
        ep = db.execute(
            select(WebhookEndpoint).where(WebhookEndpoint.source_key == source_key)
        ).scalar_one_or_none()
        if ep is None or ep.status != "active":
            raise Stack360Error(ErrorCode.SOURCE_DISABLED, "webhook endpoint inexistente ou desativado")

        ds = db.get(DataSource, ep.data_source_id)
        if ds is None or ds.status != "active":
            raise Stack360Error(ErrorCode.SOURCE_DISABLED, "data_source desativada")

        # --- Autenticação ---
        presented = x_api_key or _bearer(authorization)
        if presented:
            ctx = resolve_api_key(db, presented)
            # key da Source A NÃO pode publicar no endpoint da Source B
            if ctx.workspace_id != ep.workspace_id or ctx.data_source_id != ep.data_source_id:
                raise Stack360Error(
                    ErrorCode.SCOPE_DENIED,
                    "API key não pertence ao workspace/source deste webhook endpoint",
                )
            if "ingest" not in ctx.scopes:
                raise Stack360Error(ErrorCode.SCOPE_DENIED, "scope 'ingest' necessário")
            auth = ctx
        elif ep.secret_encrypted:
            _verify_hmac(ep, body, request)
            auth = AuthContext(
                api_key_id=ep.id,
                workspace_id=ep.workspace_id,
                workspace_slug="",
                data_source_id=ep.data_source_id,
                data_source_key=ds.key,
                scopes=frozenset({"ingest"}),
            )
        else:
            raise Stack360Error(
                ErrorCode.AUTH_INVALID,
                "webhook exige API key source-bound (HMAC não configurado)",
            )
        mapping = dict(ep.mapping or {})
        source_type = ds.source_type

    adapter = get_adapter(source_type)
    event: StackEvent = adapter(body, mapping, source_key)
    res = ingest_one(Session_, auth, event, event.model_dump(mode="json"))
    return {"accepted": res.ok, "status": res.status, "event_id": res.external_event_id}


def _bearer(authorization: str | None) -> str | None:
    if not authorization:
        return None
    parts = authorization.split(None, 1)
    if len(parts) == 2 and parts[0].lower() == "bearer":
        return parts[1].strip()
    return authorization.strip()


def _verify_hmac(ep: WebhookEndpoint, body: bytes, request: Request) -> None:
    from app.stack360.security.crypto import decrypt_secret, hmac_available

    if not hmac_available():
        raise Stack360Error(ErrorCode.AUTH_INVALID, "HMAC indisponível neste ambiente")
    header_name = ep.signature_header or "X-Signature"
    presented = request.headers.get(header_name, "")
    secret = decrypt_secret(ep.secret_encrypted).encode()
    expected = hmac_sha256_hex(secret, body)
    presented = presented.split("=", 1)[-1].strip()
    if not constant_time_equals(presented, expected):
        raise Stack360Error(ErrorCode.AUTH_INVALID, "assinatura HMAC inválida")

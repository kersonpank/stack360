"""Servidor MCP do Stack360 (stdio). Interface p/ agentes — SEM lógica própria.

    STACK360_API_KEY=st_...  python -m app.stack360.mcp.server

Workspace/source da sessão ficam FIXOS. A AUTORIZAÇÃO é REVALIDADA por
``_current_auth()`` com cache de TTL curto (``STACK360_MCP_AUTH_TTL``, default
30s; ``0`` = revalida toda chamada). Assim revogação / status / scope / source
desativada passam a valer **sem reiniciar o processo MCP**. O plaintext da key
existe só em memória do processo, para revalidação — nunca logado/persistido.

Cada tool abaixo é um wrapper fino com assinatura explícita (para o MCP gerar
o schema) que delega para ``app.stack360.mcp.tools`` — os MESMOS services da REST.
"""
from __future__ import annotations

import os
import time
from typing import Any, Optional

from mcp.server.mcpserver import MCPServer

from app.stack360.auth import AuthContext, resolve_api_key
from app.stack360.db import get_sessionmaker
from app.stack360.mcp import tools as T
from app.stack360.schemas.errors import Stack360Error

_API_KEY: Optional[str] = None   # plaintext — só em memória, p/ revalidação
_S = None
_cache: dict = {"ctx": None, "ts": 0.0}


def _ttl() -> float:
    try:
        return float(os.environ.get("STACK360_MCP_AUTH_TTL", "30"))
    except ValueError:
        return 30.0


def reset_auth_cache() -> None:
    _cache["ctx"] = None
    _cache["ts"] = 0.0


def _current_auth() -> AuthContext:
    """Devolve o AuthContext, revalidando a key contra o DB quando o cache expira.
    Propaga Stack360Error (AUTH_INVALID / SCOPE_DENIED) — o wrapper transforma em erro."""
    now = time.monotonic()
    if _cache["ctx"] is not None and (now - _cache["ts"]) < _ttl():
        return _cache["ctx"]
    with _S() as db:
        try:
            ctx = resolve_api_key(db, _API_KEY)
            db.commit()
        except Stack360Error:
            reset_auth_cache()
            raise
    _cache["ctx"] = ctx
    _cache["ts"] = now
    return ctx


def _guard(fn, **kwargs):
    try:
        auth = _current_auth()
        return fn(auth, _S, **kwargs)
    except Stack360Error as e:
        return {"error": {"code": e.code.value, "message": e.message, "details": e.details}}


def build_server(api_key: Optional[str] = None) -> MCPServer:
    global _API_KEY, _S
    _API_KEY = api_key or os.environ.get("STACK360_API_KEY")
    if not _API_KEY:
        raise SystemExit("defina STACK360_API_KEY no ambiente")

    _S = get_sessionmaker()
    reset_auth_cache()
    _current_auth()  # resolve uma vez no start (falha cedo se a key for inválida)

    mcp = MCPServer("stack360", instructions="Stack360 canonical data hub — read + controlled write.")

    # ---------- READ ----------
    @mcp.tool()
    def search_people(query: Optional[str] = None, identity_type: Optional[str] = None, identity_value: Optional[str] = None, limit: int = 25):
        return _guard(T.search_people, query=query, identity_type=identity_type, identity_value=identity_value, limit=limit)

    @mcp.tool()
    def get_person(person_id: str):
        return _guard(T.get_person, person_id=person_id)

    @mcp.tool()
    def get_person_context(person_id: str, limit: Optional[int] = None, include: Optional[str] = None):
        return _guard(T.get_person_context, person_id=person_id, limit=limit, include=include)

    @mcp.tool()
    def search_companies(query: Optional[str] = None, domain: Optional[str] = None, limit: int = 25):
        return _guard(T.search_companies, query=query, domain=domain, limit=limit)

    @mcp.tool()
    def get_company(company_id: str):
        return _guard(T.get_company, company_id=company_id)

    @mcp.tool()
    def get_company_context(company_id: str, limit: Optional[int] = None, include: Optional[str] = None):
        return _guard(T.get_company_context, company_id=company_id, limit=limit, include=include)

    @mcp.tool()
    def list_recent_interactions(person_id: Optional[str] = None, company_id: Optional[str] = None, limit: int = 25):
        return _guard(T.list_recent_interactions, person_id=person_id, company_id=company_id, limit=limit)

    @mcp.tool()
    def list_experience_runs(experience_key: Optional[str] = None, limit: int = 25):
        return _guard(T.list_experience_runs, experience_key=experience_key, limit=limit)

    @mcp.tool()
    def get_experience_run(run_id: str):
        return _guard(T.get_experience_run, run_id=run_id)

    @mcp.tool()
    def list_sources():
        return _guard(T.list_sources)

    @mcp.tool()
    def get_source_health():
        return _guard(T.get_source_health)

    @mcp.tool()
    def list_resolution_cases(status: Optional[str] = None, case_type: Optional[str] = None, limit: int = 50):
        return _guard(T.list_resolution_cases, status=status, case_type=case_type, limit=limit)

    @mcp.tool()
    def get_resolution_case(case_id: str):
        return _guard(T.get_resolution_case, case_id=case_id)

    # ---------- WRITE (controlada) ----------
    @mcp.tool()
    def ingest_event(envelope: dict[str, Any]):
        return _guard(T.ingest_event, envelope=envelope)

    @mcp.tool()
    def record_observation(key: str, value: Any, subject_identities: list[dict], event_id: str, occurred_at: Optional[str] = None, confidence: Optional[float] = None):
        return _guard(T.record_observation, key=key, value=value, subject_identities=subject_identities, event_id=event_id, occurred_at=occurred_at, confidence=confidence)

    @mcp.tool()
    def record_interaction(interaction_type: str, subject_identities: list[dict], event_id: str, channel: Optional[str] = None, direction: Optional[str] = None, occurred_at: Optional[str] = None):
        return _guard(T.record_interaction, interaction_type=interaction_type, subject_identities=subject_identities, event_id=event_id, channel=channel, direction=direction, occurred_at=occurred_at)

    @mcp.tool()
    def submit_resolution_recommendation(resolution_case_id: str, recommended_action: str, evidence: dict, confidence: Optional[float] = None, summary: Optional[str] = None, candidate_entity_ids: Optional[list] = None, agent_name: Optional[str] = None, agent_version: Optional[str] = None):
        """SÓ cria uma recommendation. NUNCA faz merge nem altera Person/Company/identidade."""
        return _guard(
            T.submit_resolution_recommendation,
            resolution_case_id=resolution_case_id,
            recommended_action=recommended_action,
            evidence=evidence,
            confidence=confidence,
            summary=summary,
            candidate_entity_ids=candidate_entity_ids,
            agent_name=agent_name,
            agent_version=agent_version,
        )

    return mcp


def main() -> None:
    build_server().run(transport="stdio")


if __name__ == "__main__":
    main()

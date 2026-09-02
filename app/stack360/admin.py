"""Admin CLI do Stack360 — sem painel.

    python -m app.stack360.admin <cmd> [opts]

Comandos: create-workspace, create-source, create-api-key, list-sources,
list-api-keys, revoke-api-key, create-experience, list-experiences,
create-webhook-endpoint, list-webhook-endpoints, disable-webhook-endpoint,
rotate-webhook-secret, list-resolution-cases, show-resolution-case,
reprocess-event.
"""
from __future__ import annotations

import argparse
import json
import secrets
import sys
import uuid

from sqlalchemy import select

from app.stack360.db import get_sessionmaker
from app.stack360.models.api_key import ApiKey
from app.stack360.models.data_source import DataSource
from app.stack360.models.experience import Experience
from app.stack360.models.resolution import ResolutionCase, ResolutionRecommendation
from app.stack360.models.webhook import WebhookEndpoint
from app.stack360.models.workspace import Workspace
from app.stack360.security.hashing import generate_api_key


def _ws(db, slug: str) -> Workspace:
    w = db.execute(select(Workspace).where(Workspace.slug == slug)).scalar_one_or_none()
    if w is None:
        sys.exit(f"workspace '{slug}' não existe")
    return w


def _src(db, w: Workspace, key: str) -> DataSource:
    s = db.execute(
        select(DataSource).where(DataSource.workspace_id == w.id, DataSource.key == key)
    ).scalar_one_or_none()
    if s is None:
        sys.exit(f"data_source '{key}' não existe no workspace '{w.slug}'")
    return s


def cmd_create_workspace(a):
    S = get_sessionmaker()
    with S() as db:
        w = Workspace(slug=a.slug, name=a.name)
        db.add(w)
        db.commit()
        print(json.dumps({"id": str(w.id), "slug": w.slug, "name": w.name}))


def cmd_create_source(a):
    S = get_sessionmaker()
    with S() as db:
        w = _ws(db, a.workspace)
        s = DataSource(workspace_id=w.id, key=a.key, name=a.name, source_type=a.type)
        db.add(s)
        db.commit()
        print(json.dumps({"id": str(s.id), "key": s.key, "source_type": s.source_type}))


def cmd_create_api_key(a):
    scopes = [x.strip() for x in a.scopes.split(",") if x.strip()]
    if "ingest" in scopes and not a.source:
        sys.exit("ERRO: key com scope 'ingest' exige --source (deve ser source-bound)")
    S = get_sessionmaker()
    with S() as db:
        w = _ws(db, a.workspace)
        ds = _src(db, w, a.source) if a.source else None
        plaintext, prefix, khash = generate_api_key()
        k = ApiKey(
            workspace_id=w.id,
            data_source_id=(ds.id if ds else None),
            name=a.name,
            key_prefix=prefix,
            key_hash=khash,
            scopes=scopes,
        )
        db.add(k)
        db.commit()
        print("API KEY (guarde agora — não será exibida de novo):")
        print(plaintext)
        print(json.dumps({"key_prefix": prefix, "scopes": scopes, "source": a.source}))


def cmd_list_sources(a):
    S = get_sessionmaker()
    with S() as db:
        stmt = select(DataSource, Workspace.slug).join(Workspace, Workspace.id == DataSource.workspace_id)
        if a.workspace:
            stmt = stmt.where(Workspace.slug == a.workspace)
        for s, ws in db.execute(stmt).all():
            print(json.dumps({"workspace": ws, "key": s.key, "type": s.source_type, "status": s.status}))


def cmd_list_api_keys(a):
    S = get_sessionmaker()
    with S() as db:
        for k, ws in db.execute(
            select(ApiKey, Workspace.slug).join(Workspace, Workspace.id == ApiKey.workspace_id)
        ).all():
            print(
                json.dumps(
                    {
                        "workspace": ws,
                        "key_prefix": k.key_prefix,
                        "scopes": k.scopes,
                        "source_bound": k.data_source_id is not None,
                        "status": k.status,
                    }
                )
            )


def cmd_revoke_api_key(a):
    from app.stack360.base import utcnow

    S = get_sessionmaker()
    with S() as db:
        k = None
        if a.id:
            k = db.get(ApiKey, uuid.UUID(a.id))
        elif a.prefix:
            k = db.execute(select(ApiKey).where(ApiKey.key_prefix == a.prefix)).scalars().first()
        if k is None:
            sys.exit("api key não encontrada")
        k.status = "revoked"
        k.revoked_at = utcnow()
        db.commit()
        print(json.dumps({"revoked": k.key_prefix}))


def cmd_create_experience(a):
    S = get_sessionmaker()
    with S() as db:
        w = _ws(db, a.workspace)
        existing = db.execute(
            select(Experience).where(
                Experience.workspace_id == w.id, Experience.key == a.key, Experience.version == str(a.version)
            )
        ).scalar_one_or_none()
        if existing is not None:
            existing.name = a.name
            existing.experience_type = a.type
            db.commit()
            print(json.dumps({"id": str(existing.id), "upserted": True}))
            return
        e = Experience(
            workspace_id=w.id, key=a.key, version=str(a.version), name=a.name, experience_type=a.type
        )
        db.add(e)
        db.commit()
        print(json.dumps({"id": str(e.id), "key": e.key, "version": e.version}))


def cmd_list_experiences(a):
    S = get_sessionmaker()
    with S() as db:
        w = _ws(db, a.workspace)
        for e in db.execute(
            select(Experience).where(Experience.workspace_id == w.id).order_by(Experience.key, Experience.version)
        ).scalars():
            print(json.dumps({"key": e.key, "version": e.version, "name": e.name, "type": e.experience_type}))


def cmd_create_webhook_endpoint(a):
    from app.stack360.security.crypto import encrypt_secret, hmac_available

    S = get_sessionmaker()
    with S() as db:
        w = _ws(db, a.workspace)
        ds = _src(db, w, a.source)
        ep = WebhookEndpoint(
            workspace_id=w.id,
            data_source_id=ds.id,
            source_key=a.source_key,
            signature_header=a.signature_header,
            signature_scheme=a.signature_scheme or "hmac-sha256",
        )
        secret_plain = None
        if hmac_available():
            secret_plain = "whsec_" + secrets.token_urlsafe(24)
            ep.secret_encrypted, ep.secret_key_id = encrypt_secret(secret_plain)
        db.add(ep)
        db.commit()
        body = {"source_key": ep.source_key, "hmac": secret_plain is not None}
        if secret_plain:
            print("WEBHOOK SECRET (guarde agora — não será exibido de novo):")
            print(secret_plain)
        else:
            body["note"] = "HMAC indisponível — use API key source-bound no header do webhook"
        print(json.dumps(body))


def cmd_list_webhook_endpoints(a):
    S = get_sessionmaker()
    with S() as db:
        stmt = select(WebhookEndpoint, Workspace.slug, DataSource.key).join(
            Workspace, Workspace.id == WebhookEndpoint.workspace_id
        ).join(DataSource, DataSource.id == WebhookEndpoint.data_source_id)
        if a.workspace:
            stmt = stmt.where(Workspace.slug == a.workspace)
        for ep, ws, sk in db.execute(stmt).all():
            print(
                json.dumps(
                    {
                        "workspace": ws,
                        "source": sk,
                        "source_key": ep.source_key,
                        "status": ep.status,
                        "hmac": ep.secret_encrypted is not None,
                    }
                )
            )


def cmd_disable_webhook_endpoint(a):
    S = get_sessionmaker()
    with S() as db:
        ep = db.execute(
            select(WebhookEndpoint).where(WebhookEndpoint.source_key == a.source_key)
        ).scalar_one_or_none()
        if ep is None:
            sys.exit("endpoint não encontrado")
        ep.status = "disabled"
        db.commit()
        print(json.dumps({"disabled": ep.source_key}))


def cmd_rotate_webhook_secret(a):
    from app.stack360.security.crypto import encrypt_secret, hmac_available

    if not hmac_available():
        sys.exit("HMAC indisponível neste ambiente — rotação não aplicável (follow-up)")
    S = get_sessionmaker()
    with S() as db:
        ep = db.execute(
            select(WebhookEndpoint).where(WebhookEndpoint.source_key == a.source_key)
        ).scalar_one_or_none()
        if ep is None:
            sys.exit("endpoint não encontrado")
        secret_plain = "whsec_" + secrets.token_urlsafe(24)
        ep.secret_encrypted, ep.secret_key_id = encrypt_secret(secret_plain)
        db.commit()
        print("NEW WEBHOOK SECRET:")
        print(secret_plain)


def cmd_list_resolution_cases(a):
    S = get_sessionmaker()
    with S() as db:
        stmt = select(ResolutionCase, Workspace.slug).join(
            Workspace, Workspace.id == ResolutionCase.workspace_id
        )
        if a.status:
            stmt = stmt.where(ResolutionCase.status == a.status)
        if a.case_type:
            stmt = stmt.where(ResolutionCase.case_type == a.case_type)
        if a.severity:
            stmt = stmt.where(ResolutionCase.severity == a.severity)
        for c, ws in db.execute(stmt.order_by(ResolutionCase.created_at.desc())).all():
            print(
                json.dumps(
                    {
                        "id": str(c.id),
                        "workspace": ws,
                        "case_type": c.case_type,
                        "status": c.status,
                        "severity": c.severity,
                        "created_at": c.created_at.isoformat(),
                    }
                )
            )


def cmd_show_resolution_case(a):
    S = get_sessionmaker()
    with S() as db:
        c = db.get(ResolutionCase, uuid.UUID(a.id))
        if c is None:
            sys.exit("caso não encontrado")
        recs = db.execute(
            select(ResolutionRecommendation).where(ResolutionRecommendation.resolution_case_id == c.id)
        ).scalars().all()
        print(
            json.dumps(
                {
                    "id": str(c.id),
                    "case_type": c.case_type,
                    "status": c.status,
                    "severity": c.severity,
                    "details": c.details,
                    "ingestion_event_id": str(c.ingestion_event_id) if c.ingestion_event_id else None,
                    "recommendations": [
                        {
                            "recommended_action": r.recommended_action,
                            "confidence": float(r.confidence) if r.confidence is not None else None,
                            "summary": r.summary,
                            "evidence": r.evidence,
                        }
                        for r in recs
                    ],
                },
                indent=2,
                default=str,
            )
        )


def cmd_reprocess_event(a):
    from app.stack360.ingestion.gateway import reprocess
    from app.stack360.models.ingestion_event import IngestionEvent

    S = get_sessionmaker()
    ids: list[uuid.UUID] = []
    with S() as db:
        if a.id:
            ids = [uuid.UUID(a.id)]
        elif a.status:
            ids = [
                r for r in db.execute(
                    select(IngestionEvent.id).where(IngestionEvent.status == a.status)
                ).scalars()
            ]
    for i in ids:
        res = reprocess(S, i)
        print(json.dumps({"ingestion_event_id": str(i), "status": res.status}))


def build_parser() -> argparse.ArgumentParser:
    p = argparse.ArgumentParser(prog="app.stack360.admin")
    sub = p.add_subparsers(dest="cmd", required=True)

    x = sub.add_parser("create-workspace"); x.add_argument("--slug", required=True); x.add_argument("--name", required=True); x.set_defaults(fn=cmd_create_workspace)
    x = sub.add_parser("create-source"); x.add_argument("--workspace", required=True); x.add_argument("--key", required=True); x.add_argument("--name", required=True); x.add_argument("--type", required=True); x.set_defaults(fn=cmd_create_source)
    x = sub.add_parser("create-api-key"); x.add_argument("--workspace", required=True); x.add_argument("--source"); x.add_argument("--name", required=True); x.add_argument("--scopes", required=True); x.set_defaults(fn=cmd_create_api_key)
    x = sub.add_parser("list-sources"); x.add_argument("--workspace"); x.set_defaults(fn=cmd_list_sources)
    x = sub.add_parser("list-api-keys"); x.set_defaults(fn=cmd_list_api_keys)
    x = sub.add_parser("revoke-api-key"); x.add_argument("--prefix"); x.add_argument("--id"); x.set_defaults(fn=cmd_revoke_api_key)
    x = sub.add_parser("create-experience"); x.add_argument("--workspace", required=True); x.add_argument("--key", required=True); x.add_argument("--version", required=True); x.add_argument("--name", required=True); x.add_argument("--type", required=True); x.set_defaults(fn=cmd_create_experience)
    x = sub.add_parser("list-experiences"); x.add_argument("--workspace", required=True); x.set_defaults(fn=cmd_list_experiences)
    x = sub.add_parser("create-webhook-endpoint"); x.add_argument("--workspace", required=True); x.add_argument("--source", required=True); x.add_argument("--source-key", required=True, dest="source_key"); x.add_argument("--signature-header", dest="signature_header"); x.add_argument("--signature-scheme", dest="signature_scheme"); x.set_defaults(fn=cmd_create_webhook_endpoint)
    x = sub.add_parser("list-webhook-endpoints"); x.add_argument("--workspace"); x.set_defaults(fn=cmd_list_webhook_endpoints)
    x = sub.add_parser("disable-webhook-endpoint"); x.add_argument("--source-key", required=True, dest="source_key"); x.set_defaults(fn=cmd_disable_webhook_endpoint)
    x = sub.add_parser("rotate-webhook-secret"); x.add_argument("--source-key", required=True, dest="source_key"); x.set_defaults(fn=cmd_rotate_webhook_secret)
    x = sub.add_parser("list-resolution-cases"); x.add_argument("--status"); x.add_argument("--case-type", dest="case_type"); x.add_argument("--severity"); x.set_defaults(fn=cmd_list_resolution_cases)
    x = sub.add_parser("show-resolution-case"); x.add_argument("--id", required=True); x.set_defaults(fn=cmd_show_resolution_case)
    x = sub.add_parser("reprocess-event"); x.add_argument("--id"); x.add_argument("--status"); x.set_defaults(fn=cmd_reprocess_event)
    return p


def main(argv=None) -> None:
    args = build_parser().parse_args(argv)
    args.fn(args)


if __name__ == "__main__":
    main()

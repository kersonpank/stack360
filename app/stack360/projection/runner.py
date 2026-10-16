"""Orquestrador genérico: reader -> persiste bruto -> extractor (ou
fallback) -> `ingest_one` (camada 3, sem mudança). Roda qualquer fonte
cadastrada em `registry.py`.

Uso:
    python -m app.stack360.projection.runner \
        --workspace-slug stack360-empresas --mode backfill --limit 100

    python -m app.stack360.projection.runner \
        --workspace-slug stack360-empresas --mode loop --interval 300
"""
from __future__ import annotations

import argparse
import logging
import os
import sys
import time
import uuid
from datetime import datetime, timezone
from typing import Optional

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.stack360.auth import AuthContext
from app.stack360.db import get_sessionmaker
from app.stack360.ingestion.gateway import ingest_one
from app.stack360.models.data_source import DataSource
from app.stack360.models.workspace import Workspace
from app.stack360.projection.envelope import SourceEnvelope, persist_raw_envelope
from app.stack360.projection.extractors.base import extractor_for, load_extractors
from app.stack360.projection.extractors.fallback import extract_unmapped
from app.stack360.projection.registry import READERS, ReaderConfig, build_engine

log = logging.getLogger("stack360.projection.runner")

load_extractors()


def _resolve_workspace(db: Session, workspace_slug: str) -> Workspace:
    w = db.execute(select(Workspace).where(Workspace.slug == workspace_slug)).scalar_one_or_none()
    if w is None:
        sys.exit(f"workspace '{workspace_slug}' não existe — crie via /settings/api-keys antes")
    return w


def _resolve_or_create_source(db: Session, workspace: Workspace, source_key: str, source_type: str) -> DataSource:
    ds = db.execute(
        select(DataSource).where(DataSource.workspace_id == workspace.id, DataSource.key == source_key)
    ).scalar_one_or_none()
    if ds is not None:
        return ds
    log.warning("DataSource nova detectada no bruto: key=%s type=%s — criando automaticamente", source_key, source_type)
    ds = DataSource(workspace_id=workspace.id, key=source_key, name=source_key, source_type=source_type)
    db.add(ds)
    db.commit()
    db.refresh(ds)
    return ds


def _auth_context(workspace: Workspace, source: DataSource) -> AuthContext:
    return AuthContext(
        api_key_id=uuid.uuid4(),  # processo interno — não referencia ApiKey real
        workspace_id=workspace.id,
        workspace_slug=workspace.slug,
        data_source_id=source.id,
        data_source_key=source.key,
        scopes=frozenset({"ingest"}),
    )


def _process_envelope(Session_, db: Session, workspace: Workspace, reader_cfg: ReaderConfig, envelope: SourceEnvelope) -> None:
    source = _resolve_or_create_source(db, workspace, envelope.source_key, reader_cfg.source_type)
    persist_raw_envelope(db, workspace_id=workspace.id, data_source_id=source.id, envelope=envelope)

    extractor = extractor_for(envelope.envelope_type)
    events = extractor(envelope) if extractor else extract_unmapped(envelope)

    auth = _auth_context(workspace, source)
    for event in events:
        res = ingest_one(Session_, auth, event, event.model_dump(mode="json"))
        if res.status == "error" and res.error is not None:
            log.warning("evento %s falhou: %s", event.event_id, res.error.message)


def run_batch(*, workspace_slug: str, limit: Optional[int], since_cursor: Optional[datetime]) -> int:
    Session_ = get_sessionmaker()
    with Session_() as db:
        workspace = _resolve_workspace(db, workspace_slug)

    processed = 0
    seen_external_keys: set[str] = set()
    env = dict(os.environ)

    for reader_cfg in READERS:
        engine = build_engine(reader_cfg, env)
        try:
            with Session_() as db:
                for envelope in reader_cfg.reader(engine, since_cursor=since_cursor, batch_size=limit or 500):
                    if limit and processed >= limit:
                        break
                    dedup_key = f"{reader_cfg.name}:{envelope.external_key}"
                    if dedup_key in seen_external_keys:
                        continue  # mesma mensagem vista por 2 instâncias (grupo) — fica com a 1a (menor loaded_at)
                    seen_external_keys.add(dedup_key)

                    _process_envelope(Session_, db, workspace, reader_cfg, envelope)
                    processed += 1
        finally:
            engine.dispose()

    log.info("lote concluído: %d envelopes processados", processed)
    return processed


def main(argv=None) -> None:
    logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(message)s")
    p = argparse.ArgumentParser(prog="app.stack360.projection.runner")
    p.add_argument("--workspace-slug", required=True)
    p.add_argument("--mode", choices=["backfill", "loop"], default="backfill")
    p.add_argument("--limit", type=int, default=None)
    p.add_argument("--interval", type=int, default=300)
    args = p.parse_args(argv)

    if args.mode == "backfill":
        run_batch(workspace_slug=args.workspace_slug, limit=args.limit, since_cursor=None)
        return

    cursor: Optional[datetime] = None
    while True:
        try:
            run_batch(workspace_slug=args.workspace_slug, limit=None, since_cursor=cursor)
            cursor = datetime.now(timezone.utc)
        except Exception:  # noqa: BLE001
            log.exception("erro no ciclo do loop — tenta de novo no próximo intervalo")
        time.sleep(args.interval)


if __name__ == "__main__":
    main()

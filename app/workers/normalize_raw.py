"""
Normalization Worker v0.2

Usage:
    python -m app.workers.normalize_raw --dry-run --limit 100
    python -m app.workers.normalize_raw --limit 100
    python -m app.workers.normalize_raw --limit 5000 --confirm-large-run
    python -m app.workers.normalize_raw --limit 5000 --max-batches 3 --confirm-large-run
    python -m app.workers.normalize_raw --dry-run --limit 5000
"""

import argparse
import sys

SAFE_LIMIT = 100
MAX_LIMIT_PER_BATCH = 5000


def main():
    parser = argparse.ArgumentParser(
        description="Normalization Worker v0.2 — popula contacts/conversations/messages a partir de raw_evolution_messages"
    )
    parser.add_argument(
        "--limit",
        type=int,
        default=100,
        help=f"Mensagens por batch (default: 100; max real sem flag: {SAFE_LIMIT}; max com --confirm-large-run: {MAX_LIMIT_PER_BATCH})",
    )
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="Simula o processamento sem gravar no banco",
    )
    parser.add_argument(
        "--source-account-id",
        type=str,
        default=None,
        help="Filtrar por source_account_id especifico",
    )
    parser.add_argument(
        "--confirm-large-run",
        action="store_true",
        help=f"Obrigatorio para --limit > {SAFE_LIMIT} em modo real",
    )
    parser.add_argument(
        "--max-batches",
        type=int,
        default=1,
        help="Numero de batches a executar sequencialmente (default: 1)",
    )
    args = parser.parse_args()

    if not args.dry_run:
        if args.limit > SAFE_LIMIT and not args.confirm_large_run:
            print(
                f"ERRO: Para processar mais de {SAFE_LIMIT} registros em modo real, use --confirm-large-run.",
                file=sys.stderr,
            )
            sys.exit(1)
        if args.limit > MAX_LIMIT_PER_BATCH:
            print(
                f"ERRO: --limit maximo e {MAX_LIMIT_PER_BATCH} por batch.",
                file=sys.stderr,
            )
            sys.exit(1)

    # Imports tardios garantem que env vars foram carregadas pelo pydantic-settings
    from app.core.config import settings

    if not args.dry_run and not settings.normalizer_database_url:
        print(
            "ERRO: NORMALIZER_DATABASE_URL nao esta configurada. "
            "Defina-a no .env antes de rodar o worker em modo real.",
            file=sys.stderr,
        )
        sys.exit(1)

    from sqlalchemy import create_engine, text
    from sqlalchemy.orm import sessionmaker
    from sqlalchemy.pool import NullPool

    from app.services.normalization_service import NormalizationService

    read_engine = create_engine(settings.database_url, pool_pre_ping=True)
    ReadSession = sessionmaker(bind=read_engine, autocommit=False, autoflush=False)

    if args.dry_run:
        WriteSession = ReadSession
    else:
        from app.core.writer_database import get_writer_engine

        WriteSession = sessionmaker(bind=get_writer_engine(), autocommit=False, autoflush=False)

    # --- Advisory lock (somente modo real) ---
    # Conexao dedicada em autocommit para lock de sessao (nao de transacao).
    # pg_try_advisory_lock retorna false se outro worker ja segura o lock.
    _LOCK_KEY = "SELECT pg_try_advisory_lock(hashtext('stakeholder_normalization_worker'))"
    _UNLOCK_KEY = "SELECT pg_advisory_unlock(hashtext('stakeholder_normalization_worker'))"
    lock_conn = None

    if not args.dry_run:
        _lock_engine = create_engine(settings.normalizer_database_url, poolclass=NullPool)
        lock_conn = _lock_engine.connect().execution_options(isolation_level="AUTOCOMMIT")
        locked = lock_conn.execute(text(_LOCK_KEY)).scalar()
        if not locked:
            print(
                "ERRO: Outro worker de normalizacao ja esta em execucao. "
                "Aguarde terminar ou libere com: SELECT pg_advisory_unlock(hashtext('stakeholder_normalization_worker'));",
                file=sys.stderr,
            )
            lock_conn.close()
            sys.exit(1)
        print("[worker] Advisory lock adquirido.", flush=True)

    mode = "DRY-RUN" if args.dry_run else "REAL"
    total_processed = 0
    total_found_all = 0
    batch_num = 1

    try:
        for batch_num in range(1, args.max_batches + 1):
            read_db = ReadSession()
            write_db = read_db if args.dry_run else WriteSession()

            try:
                if args.max_batches > 1:
                    print(f"\n[worker] === Batch {batch_num}/{args.max_batches} ===", flush=True)

                service = NormalizationService(read_db=read_db, write_db=write_db)
                result = service.run(
                    limit=args.limit,
                    dry_run=args.dry_run,
                    source_account_id=args.source_account_id,
                )

                total_processed += result["processed"]
                total_found_all += result["total_found"]
                print(f"[worker] Batch {batch_num} concluido ({mode}): {result}", flush=True)

                if result["total_found"] == 0:
                    print(f"[worker] Sem pendentes. Encerrando apos batch {batch_num}.", flush=True)
                    break

            except Exception as exc:
                if not args.dry_run and write_db is not read_db:
                    try:
                        write_db.rollback()
                    except Exception:
                        pass
                print(f"[worker] ERRO no batch {batch_num}: {exc}", file=sys.stderr)
                raise
            finally:
                read_db.close()
                if not args.dry_run and write_db is not read_db:
                    write_db.close()

        if args.max_batches > 1:
            print(f"\n[worker] Total ({mode}): processed={total_processed}, batches_executados={batch_num}", flush=True)

    finally:
        if lock_conn is not None:
            try:
                lock_conn.execute(text(_UNLOCK_KEY))
            except Exception:
                pass
            lock_conn.close()
            print("[worker] Advisory lock liberado.", flush=True)


if __name__ == "__main__":
    main()

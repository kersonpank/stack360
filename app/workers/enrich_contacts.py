"""
Semantic Enrichment Worker v0.1

Usage:
    python -m app.workers.enrich_contacts --dry-run --limit 20
    python -m app.workers.enrich_contacts --limit 100
    python -m app.workers.enrich_contacts --limit 500 --confirm-large-run
    python -m app.workers.enrich_contacts --contact-id 5599999999999
    python -m app.workers.enrich_contacts --limit 100 --use-llm  # only if LLM_ENABLED=true
"""
import argparse
import sys


def main():
    parser = argparse.ArgumentParser(description="Semantic Enrichment Worker v0.1")
    parser.add_argument("--limit", type=int, default=100,
                        help="Max contacts to enrich (default: 100)")
    parser.add_argument("--dry-run", action="store_true",
                        help="Simulate without writing to DB")
    parser.add_argument("--contact-id", type=str, default=None,
                        help="Enrich a specific contact_id only")
    parser.add_argument("--confirm-large-run", action="store_true",
                        help="Required to run with --limit > 100 in real mode")
    parser.add_argument("--use-llm", action="store_true",
                        help="Enable LLM enrichment (requires LLM_ENABLED=true in .env)")
    args = parser.parse_args()

    if args.limit > 100 and not args.dry_run and not args.confirm_large_run:
        print(
            "ERRO: --limit > 100 em modo real requer --confirm-large-run.",
            file=sys.stderr,
        )
        sys.exit(1)

    from app.core.config import settings

    if args.use_llm and not settings.llm_enabled:
        print(
            "ERRO: --use-llm requer LLM_ENABLED=true no .env.",
            file=sys.stderr,
        )
        sys.exit(1)

    if not args.dry_run and not settings.normalizer_database_url:
        print(
            "ERRO: NORMALIZER_DATABASE_URL não configurada. Defina no .env antes de rodar em modo real.",
            file=sys.stderr,
        )
        sys.exit(1)

    from sqlalchemy import create_engine
    from sqlalchemy.orm import sessionmaker
    from app.services.enrichment_service import EnrichmentService

    read_engine = create_engine(settings.database_url, pool_pre_ping=True)
    ReadSession = sessionmaker(bind=read_engine, autocommit=False, autoflush=False)
    read_db = ReadSession()

    if args.dry_run:
        write_db = read_db
    else:
        from app.core.writer_database import get_writer_engine
        WriteSession = sessionmaker(bind=get_writer_engine(), autocommit=False, autoflush=False)
        write_db = WriteSession()

    try:
        service = EnrichmentService(read_db=read_db, write_db=write_db)
        result = service.run(
            limit=args.limit,
            dry_run=args.dry_run,
            contact_id=args.contact_id,
        )
        mode = "DRY-RUN" if args.dry_run else "REAL"
        print(f"\n[enrichment] Concluído ({mode}): {result}")
    finally:
        read_db.close()
        if not args.dry_run and write_db is not read_db:
            write_db.close()


if __name__ == "__main__":
    main()

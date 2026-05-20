"""
Action Engine Worker v0.1

Usage:
    python -m app.workers.generate_actions --dry-run --limit 50
    python -m app.workers.generate_actions --limit 100
    python -m app.workers.generate_actions --limit 1000 --confirm-large-run
    python -m app.workers.generate_actions --contact-id <id>
"""
import argparse
import sys


def main():
    parser = argparse.ArgumentParser(description="Action Engine Worker v0.1")
    parser.add_argument("--limit", type=int, default=100,
                        help="Máximo de contacts a processar (default: 100)")
    parser.add_argument("--dry-run", action="store_true",
                        help="Simula sem gravar no banco")
    parser.add_argument("--contact-id", type=str, default=None,
                        help="Processar apenas este contact_id")
    parser.add_argument("--confirm-large-run", action="store_true",
                        help="Permite --limit > 100 em modo real")
    args = parser.parse_args()

    if args.limit > 100 and not args.dry_run and not args.confirm_large_run:
        print(
            "ERRO: --limit > 100 requer --confirm-large-run em modo real.",
            file=sys.stderr,
        )
        sys.exit(1)

    from app.core.config import settings
    from sqlalchemy import create_engine
    from sqlalchemy.orm import sessionmaker
    from app.services.action_service import ActionService

    read_engine = create_engine(settings.database_url, pool_pre_ping=True)
    ReadSession = sessionmaker(bind=read_engine, autocommit=False, autoflush=False)

    write_url = settings.normalizer_database_url or settings.database_url
    write_engine = create_engine(write_url, pool_pre_ping=True)
    WriteSession = sessionmaker(bind=write_engine, autocommit=False, autoflush=False)

    read_db = ReadSession()
    write_db = WriteSession()

    try:
        service = ActionService(read_db=read_db, write_db=write_db)
        result = service.run(
            limit=args.limit,
            dry_run=args.dry_run,
            contact_id=args.contact_id,
        )
        mode = "DRY-RUN" if args.dry_run else "REAL"
        print(f"\n[actions] Concluído ({mode}): {result}")
    finally:
        read_db.close()
        if write_db is not read_db:
            write_db.close()


if __name__ == "__main__":
    main()

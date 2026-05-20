import asyncio
import traceback
from datetime import datetime, timedelta, timezone
from typing import Optional

from app.scheduler.enrichment_scheduler_state import enrichment_scheduler_state

_LOCK_KEY = "SELECT pg_try_advisory_lock(hashtext('stakeholder_enrichment_worker'))"
_UNLOCK_KEY = "SELECT pg_advisory_unlock(hashtext('stakeholder_enrichment_worker'))"


def _run_enrichment_sync(limit: int, max_batches: int, use_llm: bool) -> dict:
    """
    Executa enrichment de forma síncrona (chamado via asyncio.to_thread).
    Adquire advisory lock, roda EnrichmentService em batches, libera lock.
    """
    from sqlalchemy import create_engine, text
    from sqlalchemy.orm import sessionmaker
    from sqlalchemy.pool import NullPool

    from app.core.config import settings
    from app.core.writer_database import get_writer_engine
    from app.services.enrichment_service import EnrichmentService

    if use_llm and not settings.llm_enabled:
        print(
            "[enrichment-scheduler] AVISO: ENRICHMENT_USE_LLM=true mas LLM_ENABLED=false. "
            "LLM não será utilizado.",
            flush=True,
        )
        use_llm = False

    read_engine = create_engine(settings.database_url, pool_pre_ping=True)
    ReadSession = sessionmaker(bind=read_engine, autocommit=False, autoflush=False)
    WriteSession = sessionmaker(bind=get_writer_engine(), autocommit=False, autoflush=False)

    lock_engine = create_engine(settings.normalizer_database_url, poolclass=NullPool)
    lock_conn = lock_engine.connect().execution_options(isolation_level="AUTOCOMMIT")

    locked = lock_conn.execute(text(_LOCK_KEY)).scalar()
    if not locked:
        lock_conn.close()
        print(
            "[enrichment-scheduler] Advisory lock não adquirido — outro enrichment worker em execução. Pulando rodada.",
            flush=True,
        )
        return {"skipped_lock": True, "processed": 0, "batches_executed": 0}

    total_processed = 0
    batches_run = 0

    try:
        for _batch in range(1, max_batches + 1):
            read_db = ReadSession()
            write_db = WriteSession()
            try:
                service = EnrichmentService(read_db=read_db, write_db=write_db)
                result = service.run(limit=limit, dry_run=False)
                total_processed += result["processed"]
                batches_run += 1
                if result["total_selected"] == 0 or result["processed"] == 0:
                    break
            except Exception:
                try:
                    write_db.rollback()
                except Exception:
                    pass
                raise
            finally:
                try:
                    read_db.close()
                except Exception:
                    pass
                write_db.close()

        message = "Nenhum contact pendente para enriquecer." if total_processed == 0 else None
        return {
            "skipped_lock": False,
            "processed": total_processed,
            "batches_executed": batches_run,
            "message": message,
        }
    finally:
        try:
            lock_conn.execute(text(_UNLOCK_KEY))
        except Exception:
            pass
        lock_conn.close()


class EnrichmentScheduler:
    def __init__(self):
        self._task: Optional[asyncio.Task] = None

    def start(self) -> None:
        from app.core.config import settings

        if not settings.enrichment_scheduler_enabled:
            return
        if not settings.normalizer_database_url:
            print(
                "[enrichment-scheduler] AVISO: ENRICHMENT_SCHEDULER_ENABLED=true mas NORMALIZER_DATABASE_URL "
                "não configurada. Scheduler não iniciado.",
                flush=True,
            )
            return

        enrichment_scheduler_state.enabled = True
        self._task = asyncio.create_task(self._loop())
        print("[enrichment-scheduler] Enrichment Scheduler iniciado.", flush=True)

    async def stop(self) -> None:
        if self._task and not self._task.done():
            self._task.cancel()
            try:
                await self._task
            except asyncio.CancelledError:
                pass
        enrichment_scheduler_state.enabled = False
        enrichment_scheduler_state.running = False
        print("[enrichment-scheduler] Enrichment Scheduler encerrado.", flush=True)

    async def _loop(self) -> None:
        from app.core.config import settings

        while True:
            now = datetime.now(tz=timezone.utc)
            enrichment_scheduler_state.next_run_estimate = now + timedelta(
                seconds=settings.enrichment_interval_seconds
            )
            await asyncio.sleep(settings.enrichment_interval_seconds)

            if self._should_run_nightly():
                await self._run_once(
                    limit=settings.enrichment_nightly_limit,
                    max_batches=settings.enrichment_nightly_max_batches,
                    run_type="nightly",
                )
                enrichment_scheduler_state.last_nightly_date = datetime.now(tz=timezone.utc).date()
            else:
                await self._run_once(
                    limit=settings.enrichment_incremental_limit,
                    max_batches=settings.enrichment_incremental_max_batches,
                    run_type="incremental",
                )

    def _should_run_nightly(self) -> bool:
        from app.core.config import settings

        if not settings.enrichment_nightly_enabled:
            return False
        now = datetime.now(tz=timezone.utc)
        if now.hour != settings.enrichment_nightly_hour:
            return False
        today = now.date()
        return enrichment_scheduler_state.last_nightly_date != today

    async def _run_once(self, limit: int, max_batches: int, run_type: str) -> None:
        from app.core.config import settings

        now = datetime.now(tz=timezone.utc)
        enrichment_scheduler_state.running = True
        enrichment_scheduler_state.last_run_started_at = now
        enrichment_scheduler_state.total_runs += 1

        print(
            f"[enrichment-scheduler] Iniciando rodada {run_type} "
            f"(limit={limit}, max_batches={max_batches}, use_llm={settings.enrichment_use_llm}).",
            flush=True,
        )

        try:
            result = await asyncio.to_thread(
                _run_enrichment_sync, limit, max_batches, settings.enrichment_use_llm
            )

            finished_at = datetime.now(tz=timezone.utc)
            enrichment_scheduler_state.last_run_finished_at = finished_at
            enrichment_scheduler_state.last_result = result

            if result.get("skipped_lock"):
                enrichment_scheduler_state.total_skipped_by_lock += 1
                print(f"[enrichment-scheduler] Rodada {run_type} pulada (lock).", flush=True)
            else:
                enrichment_scheduler_state.last_success_at = finished_at
                enrichment_scheduler_state.total_success += 1
                msg = result.get("message") or f"processed={result['processed']}"
                print(f"[enrichment-scheduler] Rodada {run_type} OK: {msg}", flush=True)

        except Exception as exc:
            finished_at = datetime.now(tz=timezone.utc)
            enrichment_scheduler_state.last_run_finished_at = finished_at
            enrichment_scheduler_state.last_error_at = finished_at
            enrichment_scheduler_state.last_error_message = str(exc)
            enrichment_scheduler_state.last_result = {"error": str(exc)}
            enrichment_scheduler_state.total_failures += 1
            print(f"[enrichment-scheduler] ERRO na rodada {run_type}: {exc}", flush=True)
            traceback.print_exc()
        finally:
            enrichment_scheduler_state.running = False
            from app.core.config import settings

            enrichment_scheduler_state.next_run_estimate = datetime.now(tz=timezone.utc) + timedelta(
                seconds=settings.enrichment_interval_seconds
            )


enrichment_scheduler = EnrichmentScheduler()

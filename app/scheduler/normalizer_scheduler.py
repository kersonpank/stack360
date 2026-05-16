import asyncio
import traceback
from datetime import datetime, timedelta, timezone
from typing import Optional

from app.scheduler.scheduler_state import scheduler_state

_LOCK_KEY = "SELECT pg_try_advisory_lock(hashtext('stakeholder_normalization_worker'))"
_UNLOCK_KEY = "SELECT pg_advisory_unlock(hashtext('stakeholder_normalization_worker'))"


def _run_normalization_sync(limit: int, max_batches: int) -> dict:
    """
    Executa normalização de forma síncrona (chamado via asyncio.to_thread).
    Adquire advisory lock, roda NormalizationService em batches, libera lock.
    """
    from sqlalchemy import create_engine, text
    from sqlalchemy.orm import sessionmaker
    from sqlalchemy.pool import NullPool

    from app.core.config import settings
    from app.core.writer_database import get_writer_engine
    from app.services.normalization_service import NormalizationService

    read_engine = create_engine(settings.database_url, pool_pre_ping=True)
    ReadSession = sessionmaker(bind=read_engine, autocommit=False, autoflush=False)
    WriteSession = sessionmaker(bind=get_writer_engine(), autocommit=False, autoflush=False)

    lock_engine = create_engine(settings.normalizer_database_url, poolclass=NullPool)
    lock_conn = lock_engine.connect().execution_options(isolation_level="AUTOCOMMIT")

    locked = lock_conn.execute(text(_LOCK_KEY)).scalar()
    if not locked:
        lock_conn.close()
        print("[scheduler] Advisory lock não adquirido — outro worker em execução. Pulando rodada.", flush=True)
        return {"skipped_lock": True, "processed": 0, "batches_executed": 0}

    total_processed = 0
    batches_run = 0

    try:
        for _batch in range(1, max_batches + 1):
            read_db = ReadSession()
            write_db = WriteSession()
            try:
                service = NormalizationService(read_db=read_db, write_db=write_db)
                result = service.run(limit=limit, dry_run=False)
                total_processed += result["processed"]
                batches_run += 1
                if result["total_found"] == 0:
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

        message = "Nenhuma mensagem pendente para normalizar." if total_processed == 0 else None
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


class NormalizerScheduler:
    def __init__(self):
        self._task: Optional[asyncio.Task] = None

    def start(self) -> None:
        from app.core.config import settings

        if not settings.normalizer_scheduler_enabled:
            return
        if not settings.normalizer_database_url:
            print(
                "[scheduler] AVISO: NORMALIZER_SCHEDULER_ENABLED=true mas NORMALIZER_DATABASE_URL não configurada. "
                "Scheduler não iniciado.",
                flush=True,
            )
            return

        scheduler_state.enabled = True
        self._task = asyncio.create_task(self._loop())
        print("[scheduler] Normalizer Scheduler iniciado.", flush=True)

    async def stop(self) -> None:
        if self._task and not self._task.done():
            self._task.cancel()
            try:
                await self._task
            except asyncio.CancelledError:
                pass
        scheduler_state.enabled = False
        scheduler_state.running = False
        print("[scheduler] Normalizer Scheduler encerrado.", flush=True)

    async def _loop(self) -> None:
        from app.core.config import settings

        while True:
            now = datetime.now(tz=timezone.utc)
            scheduler_state.next_run_estimate = now + timedelta(seconds=settings.normalizer_interval_seconds)
            await asyncio.sleep(settings.normalizer_interval_seconds)

            if self._should_run_nightly():
                await self._run_once(
                    limit=settings.normalizer_nightly_limit,
                    max_batches=settings.normalizer_nightly_max_batches,
                    run_type="nightly",
                )
                scheduler_state.last_nightly_date = datetime.now(tz=timezone.utc).date()
            else:
                await self._run_once(
                    limit=settings.normalizer_incremental_limit,
                    max_batches=settings.normalizer_incremental_max_batches,
                    run_type="incremental",
                )

    def _should_run_nightly(self) -> bool:
        from app.core.config import settings

        if not settings.normalizer_nightly_enabled:
            return False
        now = datetime.now(tz=timezone.utc)
        if now.hour != settings.normalizer_nightly_hour:
            return False
        today = now.date()
        return scheduler_state.last_nightly_date != today

    async def _run_once(self, limit: int, max_batches: int, run_type: str) -> None:
        now = datetime.now(tz=timezone.utc)
        scheduler_state.running = True
        scheduler_state.last_run_started_at = now
        scheduler_state.total_runs += 1

        print(f"[scheduler] Iniciando rodada {run_type} (limit={limit}, max_batches={max_batches}).", flush=True)

        try:
            result = await asyncio.to_thread(_run_normalization_sync, limit, max_batches)

            finished_at = datetime.now(tz=timezone.utc)
            scheduler_state.last_run_finished_at = finished_at
            scheduler_state.last_result = result

            if result.get("skipped_lock"):
                scheduler_state.total_skipped_by_lock += 1
                print(f"[scheduler] Rodada {run_type} pulada (lock).", flush=True)
            else:
                scheduler_state.last_success_at = finished_at
                scheduler_state.total_success += 1
                msg = result.get("message") or f"processed={result['processed']}"
                print(f"[scheduler] Rodada {run_type} OK: {msg}", flush=True)

        except Exception as exc:
            finished_at = datetime.now(tz=timezone.utc)
            scheduler_state.last_run_finished_at = finished_at
            scheduler_state.last_error_at = finished_at
            scheduler_state.last_error_message = str(exc)
            scheduler_state.last_result = {"error": str(exc)}
            scheduler_state.total_failures += 1
            print(f"[scheduler] ERRO na rodada {run_type}: {exc}", flush=True)
            traceback.print_exc()
        finally:
            scheduler_state.running = False
            from app.core.config import settings

            scheduler_state.next_run_estimate = datetime.now(tz=timezone.utc) + timedelta(
                seconds=settings.normalizer_interval_seconds
            )


scheduler = NormalizerScheduler()

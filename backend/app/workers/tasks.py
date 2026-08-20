from __future__ import annotations

import asyncio
import os
from datetime import datetime
from zoneinfo import ZoneInfo
from collections.abc import Awaitable, Callable
from typing import Any

from celery.signals import worker_process_shutdown
from celery.utils.log import get_task_logger
from sqlalchemy import select
from sqlalchemy.orm import selectinload

from app.core.config import settings
from app.core.tenant_context import TenantContext, set_tenant_context, reset_tenant_context
from app.db.platform import PlatformSessionLocal, platform_engine
from app.db.tenant import tenant_engines
from app.models.platform import Tenant
from app.services.backup import BackupService
from app.services.collection_rules import CollectionRuleService
from app.services.notifications import NotificationService
from app.services.outbox import OutboxService
from app.services.provisioning import provisioning_service
from app.services.recurrence import RecurrenceService
from app.services.tenant_resolver import TenantResolver
from app.workers.celery_app import celery_app

logger = get_task_logger(__name__)


_process_loop: asyncio.AbstractEventLoop | None = None
_process_pid: int | None = None


def _event_loop() -> asyncio.AbstractEventLoop:
    """Retorna um loop persistente por processo Celery.

    ``asyncio.run`` cria e fecha um loop em cada tarefa. Pools asyncpg/SQLAlchemy
    permanecem vivos entre tarefas e não podem migrar para outro loop. O runner
    por PID evita erros de "Future attached to a different loop" no pool prefork.
    """

    global _process_loop, _process_pid
    pid = os.getpid()
    if _process_loop is None or _process_loop.is_closed() or _process_pid != pid:
        _process_loop = asyncio.new_event_loop()
        _process_pid = pid
        asyncio.set_event_loop(_process_loop)
    return _process_loop


def run(coro: Awaitable[Any]) -> Any:
    loop = _event_loop()
    if loop.is_running():
        raise RuntimeError("O runner Celery não aceita execução async aninhada.")
    return loop.run_until_complete(coro)


@worker_process_shutdown.connect
def close_worker_async_resources(**_: Any) -> None:
    """Descarta pools e fecha o loop ao encerrar cada processo worker."""

    global _process_loop, _process_pid
    loop = _process_loop
    if loop is None or loop.is_closed():
        return

    async def dispose() -> None:
        await tenant_engines.dispose_all()
        await platform_engine.dispose()

    try:
        loop.run_until_complete(dispose())
    finally:
        loop.close()
        _process_loop = None
        _process_pid = None


async def for_each_active_tenant(callback: Callable[[Any, TenantContext], Awaitable[int]]) -> dict[str, int]:
    results: dict[str, int] = {}
    async with PlatformSessionLocal() as platform_session:
        tenant_ids = list(
            (await platform_session.scalars(select(Tenant.id).where(Tenant.status == "ACTIVE"))).all()
        )
        resolver = TenantResolver(platform_session)
        for tenant_id in tenant_ids:
            try:
                context = await resolver.resolve_by_id(str(tenant_id))
                token = set_tenant_context(context)
                try:
                    entry = await tenant_engines.get(context)
                    async with entry.session_factory() as session:
                        results[context.slug] = await callback(session, context)
                finally:
                    reset_tenant_context(token)
            except Exception as exc:  # noqa: BLE001
                logger.exception("tenant_task_failed", extra={"tenant_id": str(tenant_id), "error": str(exc)})
                results[str(tenant_id)] = -1
    return results


@celery_app.task(name="app.tasks.provision_tenant", bind=True, autoretry_for=(Exception,), retry_backoff=True, max_retries=5)
def provision_tenant(self: Any, job_id: str) -> None:
    run(provisioning_service.provision(job_id))


@celery_app.task(name="app.tasks.generate_recurring")
def generate_recurring() -> dict[str, int]:
    async def callback(session: Any, _context: TenantContext) -> int:
        return len(await RecurrenceService(session).generate_due())
    return run(for_each_active_tenant(callback))


@celery_app.task(name="app.tasks.process_outbox")
def process_outbox() -> dict[str, int]:
    async def callback(session: Any, _context: TenantContext) -> int:
        return await OutboxService(session).process_pending()
    return run(for_each_active_tenant(callback))


@celery_app.task(name="app.tasks.schedule_collection_notifications")
def schedule_collection_notifications() -> dict[str, int]:
    async def callback(session: Any, context: TenantContext) -> int:
        today = datetime.now(ZoneInfo(context.timezone)).date()
        return await CollectionRuleService(session).schedule_due(
            today=today,
            public_base_url=f"{settings.public_scheme}://{context.hostname}",
        )
    return run(for_each_active_tenant(callback))


@celery_app.task(name="app.tasks.dispatch_notifications")
def dispatch_notifications() -> dict[str, int]:
    async def callback(session: Any, _context: TenantContext) -> int:
        return await NotificationService(session).dispatch_pending()
    return run(for_each_active_tenant(callback))


@celery_app.task(name="app.tasks.backup_all", bind=True, autoretry_for=(Exception,), retry_backoff=True, max_retries=3)
def backup_all(self: Any) -> str:
    async def action() -> str:
        async with PlatformSessionLocal() as session:
            result = await BackupService(session).create_full()
            return str(result.id)
    return run(action())

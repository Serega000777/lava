import asyncio
from datetime import UTC, datetime, timedelta

import structlog
from redis.asyncio import Redis
from sqlalchemy import select, update

from app.config import settings
from app.db import session_factory
from app.models import OutboxTask
from app.queueing.service import notification_dispatch_fields

log = structlog.get_logger()
HEARTBEAT_KEY = "lava:worker:heartbeat"
MAX_ATTEMPTS = 5
LOCK_TIMEOUT = timedelta(minutes=5)


async def recover_stale_tasks(now: datetime) -> None:
    async with session_factory() as db:
        await db.execute(
            update(OutboxTask)
            .where(
                OutboxTask.status == "processing",
                OutboxTask.locked_at < now - LOCK_TIMEOUT,
            )
            .values(status="pending", locked_at=None, available_at=now)
        )
        await db.commit()


async def claim_task(now: datetime) -> OutboxTask | None:
    async with session_factory() as db:
        task = await db.scalar(
            select(OutboxTask)
            .where(OutboxTask.status == "pending", OutboxTask.available_at <= now)
            .order_by(OutboxTask.created_at, OutboxTask.id)
            .with_for_update(skip_locked=True)
            .limit(1)
        )
        if task is None:
            return None
        task.status = "processing"
        task.attempts += 1
        task.locked_at = now
        await db.commit()
        return task


async def dispatch(redis: Redis, task: OutboxTask) -> None:
    if task.topic != "notification.created":
        raise ValueError("unsupported_topic")
    stream_subject, notification_id, kind = notification_dispatch_fields(task.payload)
    await redis.xadd(
        f"lava:notifications:{stream_subject}",
        {
            "task_id": str(task.id),
            "notification_id": notification_id,
            "kind": kind,
        },
        maxlen=1000,
        approximate=True,
    )


async def complete_task(task_id) -> None:
    async with session_factory() as db:
        await db.execute(
            update(OutboxTask)
            .where(OutboxTask.id == task_id, OutboxTask.status == "processing")
            .values(status="completed", completed_at=datetime.now(UTC), locked_at=None)
        )
        await db.commit()


async def fail_task(task: OutboxTask, error_code: str) -> None:
    terminal = task.attempts >= MAX_ATTEMPTS or error_code in {
        "unsupported_topic",
        "invalid_payload",
    }
    delay_seconds = min(300, 2 ** task.attempts)
    async with session_factory() as db:
        await db.execute(
            update(OutboxTask)
            .where(OutboxTask.id == task.id, OutboxTask.status == "processing")
            .values(
                status="failed" if terminal else "pending",
                available_at=datetime.now(UTC) + timedelta(seconds=delay_seconds),
                locked_at=None,
                last_error_code=error_code[:64],
            )
        )
        await db.commit()


async def run() -> None:
    redis = Redis.from_url(settings.redis_url)
    try:
        while True:
            now = datetime.now(UTC)
            await redis.set(HEARTBEAT_KEY, int(now.timestamp()), ex=30)
            await recover_stale_tasks(now)
            task = await claim_task(now)
            if task is None:
                await asyncio.sleep(1)
                continue
            try:
                await dispatch(redis, task)
            except ValueError as error:
                await fail_task(task, str(error))
                log.warning("task_rejected", task_id=str(task.id), error_code=str(error))
            except Exception:
                await fail_task(task, "dispatch_unavailable")
                log.exception("task_retry_scheduled", task_id=str(task.id))
            else:
                await complete_task(task.id)
                log.info("task_completed", task_id=str(task.id), topic=task.topic)
    finally:
        await redis.aclose()


if __name__ == "__main__":
    asyncio.run(run())

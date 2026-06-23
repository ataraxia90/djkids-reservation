from __future__ import annotations

import logging

from aiogram import Bot
from apscheduler.schedulers.asyncio import AsyncIOScheduler

from app.config import Settings
from app.db import SessionLocal
from app.services.monitor_service import run_monitor_once
from app.services.notification_service import process_notification_queue

logger = logging.getLogger(__name__)


def create_scheduler(settings: Settings, bot: Bot | None = None) -> AsyncIOScheduler:
    scheduler = AsyncIOScheduler(timezone=settings.timezone)

    async def monitor_job() -> None:
        with SessionLocal() as session:
            await run_monitor_once(session, settings)

    scheduler.add_job(
        monitor_job,
        "interval",
        minutes=settings.check_interval_minutes,
        jitter=settings.check_jitter_seconds,
        id="monitor_reservations",
        replace_existing=True,
    )

    if bot is not None:
        async def notification_job() -> None:
            with SessionLocal() as session:
                await process_notification_queue(session, bot, settings)

        scheduler.add_job(
            notification_job,
            "interval",
            seconds=30,
            id="send_notifications",
            replace_existing=True,
        )
    return scheduler

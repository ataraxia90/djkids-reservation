from __future__ import annotations

import asyncio
import logging
from datetime import datetime, timedelta

from aiogram import Bot
from aiogram.exceptions import TelegramForbiddenError, TelegramRetryAfter
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.config import Settings
from app.models import NotificationLog, NotificationQueue, QueueStatus, User

logger = logging.getLogger(__name__)


def enqueue_notification(
    session: Session,
    user_id: int,
    watch_target_id: int,
    chat_id: str,
    message: str,
) -> NotificationQueue:
    queue_item = NotificationQueue(
        user_id=user_id,
        watch_target_id=watch_target_id,
        chat_id=chat_id,
        message=message,
        status=QueueStatus.PENDING,
    )
    session.add(queue_item)
    session.commit()
    session.refresh(queue_item)
    return queue_item


def pending_notifications(session: Session, limit: int = 20) -> list[NotificationQueue]:
    now = datetime.utcnow()
    return list(
        session.scalars(
            select(NotificationQueue)
            .where(
                NotificationQueue.status.in_([QueueStatus.PENDING, QueueStatus.RETRY]),
                (NotificationQueue.next_retry_at.is_(None) | (NotificationQueue.next_retry_at <= now)),
            )
            .order_by(NotificationQueue.created_at)
            .limit(limit)
        )
    )


async def process_notification_queue(session: Session, bot: Bot, settings: Settings) -> int:
    sent_or_failed = 0
    delay = 1 / max(settings.telegram_send_rate_per_second, 0.1)
    for item in pending_notifications(session):
        try:
            await bot.send_message(chat_id=item.chat_id, text=item.message)
            item.status = QueueStatus.SENT
            item.sent_at = datetime.utcnow()
            session.add(
                NotificationLog(
                    user_id=item.user_id,
                    watch_target_id=item.watch_target_id,
                    message=item.message,
                    result="SENT",
                    sent_at=datetime.utcnow(),
                )
            )
            sent_or_failed += 1
        except TelegramRetryAfter as exc:
            item.status = QueueStatus.RETRY
            item.retry_count += 1
            item.next_retry_at = datetime.utcnow() + timedelta(seconds=exc.retry_after)
            item.last_error = f"Rate limited: retry after {exc.retry_after}s"
        except TelegramForbiddenError as exc:
            item.status = QueueStatus.FAILED
            item.last_error = str(exc)
            user = session.get(User, item.user_id)
            if user:
                user.is_active = False
            session.add(
                NotificationLog(
                    user_id=item.user_id,
                    watch_target_id=item.watch_target_id,
                    message=item.message,
                    result="FORBIDDEN",
                    error_message=str(exc),
                    sent_at=datetime.utcnow(),
                )
            )
            sent_or_failed += 1
        except Exception as exc:  # noqa: BLE001
            logger.warning("Telegram send failed for queue item %s: %s", item.id, exc)
            item.retry_count += 1
            item.status = QueueStatus.RETRY if item.retry_count < 5 else QueueStatus.FAILED
            item.next_retry_at = datetime.utcnow() + timedelta(minutes=min(item.retry_count * 2, 30))
            item.last_error = str(exc)
            if item.status == QueueStatus.FAILED:
                session.add(
                    NotificationLog(
                        user_id=item.user_id,
                        watch_target_id=item.watch_target_id,
                        message=item.message,
                        result="FAILED",
                        error_message=str(exc),
                        sent_at=datetime.utcnow(),
                    )
                )
                sent_or_failed += 1
        session.commit()
        await asyncio.sleep(delay)
    return sent_or_failed

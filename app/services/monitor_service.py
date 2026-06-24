from __future__ import annotations

import logging
from datetime import datetime

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.bot.messages import availability_message
from app.config import Settings
from app.djkids.fetcher import FetchError, fetch_program_items
from app.djkids.status import should_notify
from app.djkids.types import ProgramItem
from app.models import FetchLog, ProgramStatus, WatchTarget
from app.services.access_control import can_receive_notifications
from app.services.notification_service import enqueue_notification
from app.services.watch_service import latest_items_by_key, save_snapshots

logger = logging.getLogger(__name__)


async def run_monitor_once(session: Session, settings: Settings) -> int:
    started_at = datetime.utcnow()
    fetch_log = FetchLog(source_url=settings.target_url, status="STARTED", started_at=started_at)
    session.add(fetch_log)
    session.commit()
    try:
        items, http_status = await fetch_program_items(settings)
        checked_at = datetime.utcnow()
        save_snapshots(session, items, checked_at)
        fetch_log.status = "SUCCESS"
        fetch_log.http_status = http_status
        fetch_log.item_count = len(items)
        fetch_log.finished_at = datetime.utcnow()
        session.commit()
        return match_active_targets(session, settings, items, checked_at)
    except Exception as exc:  # noqa: BLE001
        fetch_log.status = "FAILED"
        fetch_log.error_message = str(exc)
        fetch_log.finished_at = datetime.utcnow()
        session.commit()
        logger.warning("Monitor fetch failed: %s", exc)
        if isinstance(exc, FetchError):
            return 0
        return 0


def match_active_targets(
    session: Session,
    settings: Settings,
    items: list[ProgramItem],
    checked_at: datetime,
) -> int:
    item_map = latest_items_by_key(items)
    enqueued = 0
    targets = list(
        session.scalars(
            select(WatchTarget).where(WatchTarget.is_active.is_(True)).order_by(WatchTarget.id)
        )
    )
    for target in targets:
        item = item_map.get(target.status_key or "")
        if item is None:
            continue
        previous = target.last_status or ProgramStatus.UNKNOWN
        current = item.normalized_status
        if str(previous) != str(current):
            target.status_changed_at = checked_at
        target.last_status = current
        target.last_checked_at = checked_at
        if (
            target.notified_at is None
            and should_notify(previous, current)
            and can_receive_notifications(target.user)
        ):
            enqueue_notification(
                session=session,
                user_id=target.user_id,
                watch_target_id=target.id,
                chat_id=target.user.chat_id,
                message=availability_message(
                    target_date=target.target_date.isoformat(),
                    program_name=target.program_name,
                    time_label=target.time_label,
                    raw_status=item.raw_status,
                    checked_at=checked_at,
                    timezone=settings.timezone,
                ),
            )
            target.notified_at = checked_at
            target.last_notified_status = current
            target.is_active = False
            enqueued += 1
    session.commit()
    return enqueued

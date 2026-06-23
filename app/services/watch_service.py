from __future__ import annotations

from datetime import datetime

from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.config import Settings
from app.djkids.types import ProgramItem, make_status_key
from app.models import ProgramSnapshot, ProgramStatus, User, WatchTarget


def save_snapshots(session: Session, items: list[ProgramItem], checked_at: datetime) -> None:
    for item in items:
        session.add(
            ProgramSnapshot(
                target_date=item.target_date,
                program_name=item.program_name,
                time_label=item.time_label,
                raw_status=item.raw_status,
                normalized_status=item.normalized_status,
                raw_text=item.raw_text,
                source_url=item.source_url,
                checked_at=checked_at,
            )
        )
    session.commit()


def latest_items_by_key(items: list[ProgramItem]) -> dict[str, ProgramItem]:
    return {item.key: item for item in items}


def count_active_targets(session: Session, user_id: int) -> int:
    return session.scalar(
        select(func.count(WatchTarget.id)).where(
            WatchTarget.user_id == user_id,
            WatchTarget.is_active.is_(True),
        )
    ) or 0


def list_active_targets(session: Session, user_id: int) -> list[WatchTarget]:
    return list(
        session.scalars(
            select(WatchTarget)
            .where(WatchTarget.user_id == user_id, WatchTarget.is_active.is_(True))
            .order_by(WatchTarget.target_date, WatchTarget.program_name)
        )
    )


def get_active_target(session: Session, target_id: int, user_id: int | None = None) -> WatchTarget | None:
    query = select(WatchTarget).where(WatchTarget.id == target_id, WatchTarget.is_active.is_(True))
    if user_id is not None:
        query = query.where(WatchTarget.user_id == user_id)
    return session.scalar(query)


def create_watch_target(
    session: Session,
    user: User,
    item: ProgramItem,
    settings: Settings,
    checked_at: datetime,
) -> WatchTarget:
    if item.normalized_status != ProgramStatus.CLOSED:
        raise ValueError("마감이 아닙니다.")
    if count_active_targets(session, user.id) >= settings.max_watch_targets_per_user:
        raise ValueError("등록 가능한 감시 개수를 초과했습니다.")

    existing = session.scalar(
        select(WatchTarget).where(
            WatchTarget.user_id == user.id,
            WatchTarget.target_date == item.target_date,
            WatchTarget.program_name == item.program_name,
            WatchTarget.time_label == item.time_label,
            WatchTarget.is_active.is_(True),
        )
    )
    if existing:
        return existing

    target = WatchTarget(
        user_id=user.id,
        target_date=item.target_date,
        program_name=item.program_name,
        time_label=item.time_label,
        status_key=make_status_key(item.target_date, item.program_name, item.time_label),
        last_status=item.normalized_status,
        last_checked_at=checked_at,
        status_changed_at=checked_at,
        is_active=True,
    )
    session.add(target)
    session.commit()
    session.refresh(target)
    return target


def deactivate_target(session: Session, target: WatchTarget) -> None:
    target.is_active = False
    session.commit()

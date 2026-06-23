from __future__ import annotations

from datetime import date, datetime
from enum import StrEnum

from sqlalchemy import Boolean, Date, DateTime, ForeignKey, Integer, String, Text, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db import Base


class ProgramStatus(StrEnum):
    CLOSED = "CLOSED"
    AVAILABLE = "AVAILABLE"
    UNKNOWN = "UNKNOWN"
    ERROR = "ERROR"


class QueueStatus(StrEnum):
    PENDING = "PENDING"
    SENT = "SENT"
    RETRY = "RETRY"
    FAILED = "FAILED"


def utcnow() -> datetime:
    return datetime.utcnow()


class TimestampMixin:
    created_at: Mapped[datetime] = mapped_column(DateTime, default=utcnow, nullable=False)
    updated_at: Mapped[datetime] = mapped_column(
        DateTime, default=utcnow, onupdate=utcnow, nullable=False
    )


class User(Base, TimestampMixin):
    __tablename__ = "users"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    telegram_user_id: Mapped[str] = mapped_column(String(64), unique=True, nullable=False)
    chat_id: Mapped[str] = mapped_column(String(64), nullable=False)
    username: Mapped[str | None] = mapped_column(String(255))
    first_name: Mapped[str | None] = mapped_column(String(255))
    last_name: Mapped[str | None] = mapped_column(String(255))
    is_active: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)
    is_admin: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)
    is_blocked: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)

    watch_targets: Mapped[list["WatchTarget"]] = relationship(back_populates="user")


class WatchTarget(Base, TimestampMixin):
    __tablename__ = "watch_targets"
    __table_args__ = (
        UniqueConstraint(
            "user_id",
            "target_date",
            "program_name",
            "time_label",
            "is_active",
            name="uq_active_watch_target_hint",
        ),
    )

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    user_id: Mapped[int] = mapped_column(ForeignKey("users.id"), nullable=False)
    target_date: Mapped[date] = mapped_column(Date, nullable=False)
    program_name: Mapped[str] = mapped_column(String(255), nullable=False)
    time_label: Mapped[str | None] = mapped_column(String(255))
    status_key: Mapped[str | None] = mapped_column(String(512))
    last_status: Mapped[str | None] = mapped_column(String(32))
    last_checked_at: Mapped[datetime | None] = mapped_column(DateTime)
    status_changed_at: Mapped[datetime | None] = mapped_column(DateTime)
    notified_at: Mapped[datetime | None] = mapped_column(DateTime)
    last_notified_status: Mapped[str | None] = mapped_column(String(32))
    is_active: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)

    user: Mapped[User] = relationship(back_populates="watch_targets")


class ProgramSnapshot(Base):
    __tablename__ = "program_snapshots"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    target_date: Mapped[date] = mapped_column(Date, nullable=False)
    program_name: Mapped[str] = mapped_column(String(255), nullable=False)
    time_label: Mapped[str | None] = mapped_column(String(255))
    raw_status: Mapped[str | None] = mapped_column(String(255))
    normalized_status: Mapped[str] = mapped_column(String(32), nullable=False)
    raw_text: Mapped[str | None] = mapped_column(Text)
    source_url: Mapped[str] = mapped_column(Text, nullable=False)
    checked_at: Mapped[datetime] = mapped_column(DateTime, nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=utcnow, nullable=False)


class NotificationQueue(Base):
    __tablename__ = "notification_queue"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    user_id: Mapped[int] = mapped_column(ForeignKey("users.id"), nullable=False)
    watch_target_id: Mapped[int] = mapped_column(ForeignKey("watch_targets.id"), nullable=False)
    chat_id: Mapped[str] = mapped_column(String(64), nullable=False)
    message: Mapped[str] = mapped_column(Text, nullable=False)
    status: Mapped[str] = mapped_column(String(32), default=QueueStatus.PENDING, nullable=False)
    retry_count: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    next_retry_at: Mapped[datetime | None] = mapped_column(DateTime)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=utcnow, nullable=False)
    sent_at: Mapped[datetime | None] = mapped_column(DateTime)
    last_error: Mapped[str | None] = mapped_column(Text)


class NotificationLog(Base):
    __tablename__ = "notification_logs"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    user_id: Mapped[int] = mapped_column(ForeignKey("users.id"), nullable=False)
    watch_target_id: Mapped[int | None] = mapped_column(ForeignKey("watch_targets.id"))
    message: Mapped[str | None] = mapped_column(Text)
    result: Mapped[str] = mapped_column(String(32), nullable=False)
    error_message: Mapped[str | None] = mapped_column(Text)
    sent_at: Mapped[datetime] = mapped_column(DateTime, default=utcnow, nullable=False)


class FetchLog(Base):
    __tablename__ = "fetch_logs"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    source_url: Mapped[str] = mapped_column(Text, nullable=False)
    status: Mapped[str] = mapped_column(String(32), nullable=False)
    http_status: Mapped[int | None] = mapped_column(Integer)
    item_count: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    error_message: Mapped[str | None] = mapped_column(Text)
    started_at: Mapped[datetime] = mapped_column(DateTime, nullable=False)
    finished_at: Mapped[datetime | None] = mapped_column(DateTime)

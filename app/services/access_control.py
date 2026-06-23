from __future__ import annotations

from aiogram.types import User as TelegramUser
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.config import Settings
from app.models import User


def is_user_allowed(telegram_user_id: int, settings: Settings) -> bool:
    if telegram_user_id in settings.admin_telegram_ids:
        return True
    if settings.allow_public_signup:
        return True
    return telegram_user_id in settings.allowed_telegram_user_ids


def get_or_create_user(
    session: Session,
    telegram_user: TelegramUser,
    chat_id: int,
    settings: Settings,
) -> User:
    telegram_id = str(telegram_user.id)
    user = session.scalar(select(User).where(User.telegram_user_id == telegram_id))
    is_admin = telegram_user.id in settings.admin_telegram_ids
    if user is None:
        user = User(
            telegram_user_id=telegram_id,
            chat_id=str(chat_id),
            username=telegram_user.username,
            first_name=telegram_user.first_name,
            last_name=telegram_user.last_name,
            is_admin=is_admin,
            is_active=True,
        )
        session.add(user)
    else:
        user.chat_id = str(chat_id)
        user.username = telegram_user.username
        user.first_name = telegram_user.first_name
        user.last_name = telegram_user.last_name
        user.is_admin = is_admin
    session.commit()
    session.refresh(user)
    return user


def can_receive_notifications(user: User) -> bool:
    return user.is_active and not user.is_blocked

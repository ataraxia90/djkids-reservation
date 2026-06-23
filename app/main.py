from __future__ import annotations

import asyncio
import logging

from aiogram import Bot, Dispatcher

from app.bot.handlers import router
from app.config import get_settings
from app.db import init_db
from app.logging_config import setup_logging
from app.scheduler import create_scheduler

logger = logging.getLogger(__name__)


async def main() -> None:
    settings = get_settings()
    setup_logging(settings.log_level)
    init_db()
    if not settings.telegram_bot_token:
        raise RuntimeError("TELEGRAM_BOT_TOKEN is required to run the Telegram bot.")

    bot = Bot(token=settings.telegram_bot_token)
    dispatcher = Dispatcher()
    dispatcher.include_router(router)
    scheduler = create_scheduler(settings, bot)
    scheduler.start()
    logger.info("DJKids cancel alert bot started.")
    await dispatcher.start_polling(bot)


if __name__ == "__main__":
    asyncio.run(main())

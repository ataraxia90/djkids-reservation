# Decisions

## Telegram framework

`aiogram 3` is used for the Telegram Bot. It supports async handlers, inline keyboards, and direct use with the async scheduler.

## Fetching strategy

The primary fetch path reads the official reservation page with `httpx`, extracts the form defaults, then calls the same `/resve/indvdl/s0_getList.do` JSON endpoint used by the page JavaScript. This is lower overhead than browser automation and matches the current site structure. BeautifulSoup HTML parsing is retained for fixtures and fallback-style parsing. Playwright is kept as an optional path behind `USE_PLAYWRIGHT=true`; it is not installed in the default Docker image because the MVP should avoid browser automation unless the target page requires it.

## Database

The MVP uses SQLite through SQLAlchemy ORM. Models are deliberately plain SQLAlchemy classes so the storage layer can move to PostgreSQL later by changing `DATABASE_URL`.

## Scheduler and polling

The first release runs Telegram long polling and APScheduler in one process. This is enough for personal or small-group operation. If usage grows, notification sending and monitoring can be split into separate workers that share the same database schema.

## Site load

The scheduler performs one global page fetch per interval, not one fetch per user. The default interval is 10 minutes with jitter, and failed fetches use bounded retry/backoff.

## Out of scope

The bot does not log in, auto-reserve, bypass CAPTCHA, enter personal information, or click through the reservation flow. It only alerts users to check the official reservation page themselves.

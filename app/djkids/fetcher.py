from __future__ import annotations

import asyncio
import calendar
import json
import logging
from collections.abc import Iterator
from datetime import date
from urllib.parse import urljoin

from bs4 import BeautifulSoup
import httpx

from app.config import Settings
from app.djkids.json_parser import max_day_from_payload, parse_json_program_items
from app.djkids.parser import parse_program_items
from app.djkids.types import ProgramItem

logger = logging.getLogger(__name__)


class FetchError(RuntimeError):
    pass


async def fetch_html_httpx(url: str) -> tuple[str, int]:
    headers = {
        "User-Agent": (
            "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
            "AppleWebKit/537.36 (KHTML, like Gecko) Chrome/126 Safari/537.36 "
            "djkids-cancel-alert-bot/0.1"
        ),
        "Accept": "text/html,application/xhtml+xml",
    }
    async with httpx.AsyncClient(timeout=20, follow_redirects=True, headers=headers) as client:
        response = await client.get(url)
        response.raise_for_status()
        return response.text, response.status_code


async def fetch_program_items_json(settings: Settings) -> tuple[list[ProgramItem], int | None]:
    headers = {
        "User-Agent": (
            "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
            "AppleWebKit/537.36 (KHTML, like Gecko) Chrome/126 Safari/537.36 "
            "djkids-cancel-alert-bot/0.1"
        ),
        "Accept": "application/json, text/javascript, */*; q=0.01",
        "Referer": settings.target_url,
        "X-Requested-With": "XMLHttpRequest",
    }
    async with httpx.AsyncClient(timeout=20, follow_redirects=True, headers=headers) as client:
        page = await client.get(settings.target_url)
        page.raise_for_status()
        form = _extract_form_defaults(page.text)
        endpoint = urljoin(settings.target_url, "/resve/indvdl/s0_getList.do")

        items: list[ProgramItem] = []
        for year, month in _iter_months(
            int(form["year"]),
            int(form["month"]),
            settings.reservation_month_count,
        ):
            month_form = {
                **form,
                "year": f"{year:04d}",
                "month": f"{month:02d}",
                "day": "01",
                "firstAt": "Y",
                "sttus": "1",
            }
            first_payload = await _post_json(client, endpoint, month_form)
            max_day = max_day_from_payload(first_payload) or calendar.monthrange(year, month)[1]
            max_day = min(max_day, calendar.monthrange(year, month)[1])
            for day in range(1, max_day + 1):
                data = {
                    **month_form,
                    "day": f"{day:02d}",
                    "firstAt": "N",
                    "sttus": "1",
                }
                payload = first_payload if day == 1 else await _post_json(client, endpoint, data)
                items.extend(parse_json_program_items(payload, settings.target_url, date(year, month, day)))
        return _dedupe_items(items), page.status_code


async def _post_json(client: httpx.AsyncClient, endpoint: str, data: dict[str, str]):
    response = await client.post(endpoint, data=data)
    response.raise_for_status()
    return json.loads(response.content.decode("utf-8"))


def _extract_form_defaults(html: str) -> dict[str, str]:
    soup = BeautifulSoup(html, "html.parser")
    form = soup.select_one("#frm")
    if form is None:
        raise FetchError("Reservation form #frm was not found.")
    defaults: dict[str, str] = {
        "year": "",
        "month": "",
        "day": "",
        "firstAt": "Y",
        "progrmEstbsSn": "",
        "sttus": "1",
    }
    for input_tag in form.select("input[name]"):
        name = str(input_tag.get("name"))
        defaults[name] = str(input_tag.get("value") or "")
    if not defaults["year"] or not defaults["month"] or not defaults["day"]:
        raise FetchError("Reservation form is missing year/month/day.")
    defaults["month"] = f"{int(defaults['month']):02d}"
    defaults["day"] = f"{int(defaults['day']):02d}"
    return defaults


def _iter_months(start_year: int, start_month: int, count: int) -> Iterator[tuple[int, int]]:
    for offset in range(max(count, 1)):
        month_index = start_month - 1 + offset
        yield start_year + month_index // 12, month_index % 12 + 1


def _dedupe_items(items: list[ProgramItem]) -> list[ProgramItem]:
    deduped: dict[str, ProgramItem] = {}
    for item in items:
        deduped[item.key] = item
    return list(deduped.values())


async def fetch_html_playwright(url: str, headless: bool = True) -> tuple[str, int | None]:
    try:
        from playwright.async_api import async_playwright
    except ImportError as exc:
        raise FetchError("Playwright fallback requested but playwright is not installed.") from exc

    async with async_playwright() as p:
        browser = await p.chromium.launch(headless=headless)
        page = await browser.new_page()
        response = await page.goto(url, wait_until="networkidle")
        html = await page.content()
        status = response.status if response else None
        await browser.close()
        return html, status


async def fetch_program_items(settings: Settings) -> tuple[list[ProgramItem], int | None]:
    last_error: Exception | None = None
    for attempt in range(1, settings.max_fetch_retry + 1):
        try:
            if not settings.use_playwright:
                return await fetch_program_items_json(settings)
            if settings.use_playwright:
                html, status = await fetch_html_playwright(settings.target_url, settings.headless)
            else:
                html, status = await fetch_html_httpx(settings.target_url)
            return parse_program_items(html, settings.target_url), status
        except Exception as exc:  # noqa: BLE001
            last_error = exc
            logger.warning("Reservation fetch attempt %s failed: %s", attempt, exc)
            if attempt < settings.max_fetch_retry:
                await asyncio.sleep(min(2**attempt, 10))
    raise FetchError(str(last_error or "Unknown fetch error"))

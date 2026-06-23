from __future__ import annotations

import re
from datetime import date
from urllib.parse import urljoin

from bs4 import BeautifulSoup, Tag

from app.djkids.status import normalize_status
from app.djkids.types import ProgramItem

DATE_PATTERNS = (
    re.compile(r"(?P<year>20\d{2})[.\-/년\s]+(?P<month>\d{1,2})[.\-/월\s]+(?P<day>\d{1,2})"),
    re.compile(r"(?P<month>\d{1,2})[.\-/월\s]+(?P<day>\d{1,2})"),
)
TIME_PATTERN = re.compile(r"(\d{1,2}:\d{2}\s*(?:~|-|부터)?\s*\d{0,2}:?\d{0,2}|[0-9]+회차)")
STATUS_PATTERN = re.compile(r"(예약하기|예약가능|접수중|신청하기|마감|접수마감|예약마감|대기|준비중|예정)")

ROW_SELECTORS = (
    "table tbody tr",
    ".program-list li",
    ".reserve-list li",
    ".calendar li",
    "[class*='program']",
    "[class*='resve']",
)


class ParseError(ValueError):
    pass


def parse_program_items(html: str, source_url: str, default_year: int | None = None) -> list[ProgramItem]:
    soup = BeautifulSoup(html, "html.parser")
    current_year = default_year or date.today().year
    items: list[ProgramItem] = []

    for selector in ROW_SELECTORS:
        for node in soup.select(selector):
            item = _parse_candidate(node, source_url, current_year)
            if item and item not in items:
                items.append(item)

    if not items:
        text_item = _parse_plain_text(soup.get_text("\n", strip=True), source_url, current_year)
        items.extend(text_item)

    if not items:
        raise ParseError("No reservation program items could be parsed from the page.")
    return items


def _parse_candidate(node: Tag, source_url: str, current_year: int) -> ProgramItem | None:
    text = " ".join(node.get_text(" ", strip=True).split())
    if not text or not STATUS_PATTERN.search(text):
        return None
    target_date = _extract_date(text, current_year)
    if target_date is None:
        target_date = _extract_date_from_context(node, current_year)
    if target_date is None:
        return None

    raw_status = _extract_status(text)
    if raw_status is None:
        return None

    time_label = _extract_time(text)
    program_name = _extract_program_name(node, text, raw_status, time_label)
    if not program_name:
        return None

    link = node.find("a", href=True)
    item_url = urljoin(source_url, link["href"]) if link else source_url
    return ProgramItem(
        target_date=target_date,
        program_name=program_name,
        time_label=time_label,
        raw_status=raw_status,
        normalized_status=normalize_status(raw_status),
        source_url=item_url,
        raw_text=text,
    )


def _parse_plain_text(text: str, source_url: str, current_year: int) -> list[ProgramItem]:
    items: list[ProgramItem] = []
    for line in [line.strip() for line in text.splitlines() if line.strip()]:
        fake = BeautifulSoup(f"<div>{line}</div>", "html.parser").div
        if fake is None:
            continue
        item = _parse_candidate(fake, source_url, current_year)
        if item:
            items.append(item)
    return items


def _extract_date(text: str, current_year: int) -> date | None:
    for pattern in DATE_PATTERNS:
        match = pattern.search(text)
        if not match:
            continue
        year = int(match.groupdict().get("year") or current_year)
        month = int(match.group("month"))
        day = int(match.group("day"))
        try:
            return date(year, month, day)
        except ValueError:
            return None
    return None


def _extract_date_from_context(node: Tag, current_year: int) -> date | None:
    for parent in node.parents:
        if not isinstance(parent, Tag):
            continue
        for attr in ("data-date", "date", "title"):
            value = parent.get(attr)
            if value:
                parsed = _extract_date(str(value), current_year)
                if parsed:
                    return parsed
        text = " ".join(parent.get_text(" ", strip=True).split())
        parsed = _extract_date(text[:80], current_year)
        if parsed:
            return parsed
    return None


def _extract_status(text: str) -> str | None:
    match = STATUS_PATTERN.search(text)
    return match.group(1) if match else None


def _extract_time(text: str) -> str | None:
    match = TIME_PATTERN.search(text)
    return " ".join(match.group(1).split()) if match else None


def _extract_program_name(node: Tag, text: str, raw_status: str, time_label: str | None) -> str:
    for selector in (".program", ".program-name", ".title", ".subject", "td:nth-of-type(2)", "a"):
        selected = node.select_one(selector)
        if selected:
            candidate = _clean_name(selected.get_text(" ", strip=True), raw_status, time_label)
            if candidate:
                return candidate
    return _clean_name(text, raw_status, time_label)


def _clean_name(text: str, raw_status: str, time_label: str | None) -> str:
    cleaned = text
    for fragment in (raw_status, time_label):
        if fragment:
            cleaned = cleaned.replace(fragment, " ")
    cleaned = re.sub(r"20\d{2}[.\-/년\s]+\d{1,2}[.\-/월\s]+\d{1,2}[일]?", " ", cleaned)
    cleaned = re.sub(r"\d{1,2}[.\-/월\s]+\d{1,2}[일]?", " ", cleaned)
    cleaned = re.sub(r"\s+", " ", cleaned).strip(" -|/")
    return cleaned[:255]

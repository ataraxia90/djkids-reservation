from __future__ import annotations

from datetime import date
from typing import Any
from urllib.parse import urljoin

from app.djkids.status import normalize_status
from app.djkids.types import ProgramItem


def parse_json_program_items(
    payload: Any,
    source_url: str,
    target_date: date,
) -> list[ProgramItem]:
    root = payload[0] if isinstance(payload, list) and payload else payload
    if not isinstance(root, dict):
        return []
    programs = root.get("progrmEstbsList") or []
    if not isinstance(programs, list):
        return []

    items: list[ProgramItem] = []
    for program in programs:
        if not isinstance(program, dict):
            continue
        name = str(program.get("progrmEstbsNm") or "").strip()
        if not name:
            continue
        if not _matches_target_weekday(name, target_date):
            continue
        capacity = _to_int(program.get("psncpaWhlrs"))
        reserved = _to_int(program.get("resveWhlrs"))
        raw_status = "마감" if capacity is not None and reserved is not None and reserved >= capacity else "예약하기"
        time_label = str(program.get("psncpaCn") or "").strip() or None
        detail_link = str(program.get("progrmDetailLink") or "").strip()
        raw_text = " ".join(
            str(value)
            for value in (
                name,
                time_label,
                program.get("progrmUseTrger"),
                f"{reserved}/{capacity}" if reserved is not None and capacity is not None else None,
                raw_status,
            )
            if value
        )
        items.append(
            ProgramItem(
                target_date=target_date,
                program_name=name,
                time_label=time_label,
                raw_status=raw_status,
                normalized_status=normalize_status(raw_status),
                source_url=urljoin(source_url, detail_link) if detail_link else source_url,
                raw_text=raw_text,
            )
        )
    return items


def max_day_from_payload(payload: Any) -> int | None:
    root = payload[0] if isinstance(payload, list) and payload else payload
    if not isinstance(root, dict):
        return None
    map_object = root.get("mapObject") or {}
    if not isinstance(map_object, dict):
        return None
    return _to_int(map_object.get("maxDay"))


def _matches_target_weekday(program_name: str, target_date: date) -> bool:
    is_weekend = target_date.weekday() >= 5
    is_saturday = target_date.weekday() == 5
    is_sunday = target_date.weekday() == 6

    if "토요일" in program_name:
        return is_saturday
    if "일요일" in program_name:
        return is_sunday
    if "주말" in program_name:
        return is_weekend
    if "평일" in program_name:
        return not is_weekend
    return True


def _to_int(value: Any) -> int | None:
    try:
        if value is None or value == "":
            return None
        return int(value)
    except (TypeError, ValueError):
        return None

from __future__ import annotations

from app.models import ProgramStatus


AVAILABLE_KEYWORDS = ("예약하기", "예약가능", "접수중", "신청하기")
CLOSED_KEYWORDS = ("마감", "접수마감", "예약마감")
UNKNOWN_KEYWORDS = ("대기", "준비중", "예정", "문의")


def normalize_status(raw_status: str | None) -> ProgramStatus:
    text = " ".join((raw_status or "").split())
    if not text:
        return ProgramStatus.UNKNOWN
    if any(keyword in text for keyword in CLOSED_KEYWORDS):
        return ProgramStatus.CLOSED
    if any(keyword in text for keyword in AVAILABLE_KEYWORDS):
        return ProgramStatus.AVAILABLE
    if any(keyword in text for keyword in UNKNOWN_KEYWORDS):
        return ProgramStatus.UNKNOWN
    return ProgramStatus.UNKNOWN


def should_notify(previous: ProgramStatus | str | None, current: ProgramStatus | str | None) -> bool:
    if str(current) != ProgramStatus.AVAILABLE:
        return False
    return str(previous) in {
        ProgramStatus.CLOSED,
        ProgramStatus.UNKNOWN,
        ProgramStatus.ERROR,
        None,
        "",
    }

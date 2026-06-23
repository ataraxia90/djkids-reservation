from pathlib import Path

import pytest

from app.djkids.parser import ParseError, parse_program_items
from app.models import ProgramStatus


FIXTURES = Path(__file__).parent / "fixtures"


def test_parse_table_fixture() -> None:
    html = (FIXTURES / "djkids_calendar_closed.html").read_text(encoding="utf-8")
    items = parse_program_items(html, "https://www.djkids.or.kr/resve/indvdl/s0.do")

    assert len(items) == 2
    assert items[0].target_date.isoformat() == "2026-06-28"
    assert items[0].program_name == "리틀셰프요리교실"
    assert items[0].time_label == "1회차"
    assert items[0].normalized_status == ProgramStatus.CLOSED
    assert items[1].normalized_status == ProgramStatus.AVAILABLE


def test_parse_raises_when_no_items() -> None:
    with pytest.raises(ParseError):
        parse_program_items("<html><body>예약 정보 없음</body></html>", "https://example.test")

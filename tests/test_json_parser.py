from datetime import date

from app.djkids.json_parser import max_day_from_payload, parse_json_program_items
from app.models import ProgramStatus


def test_parse_json_program_items() -> None:
    payload = [
        {
            "msg": "",
            "mapObject": {"maxDay": 30},
            "progrmEstbsList": [
                {
                    "progrmEstbsNm": "상상누리숲",
                    "psncpaWhlrs": 1200,
                    "resveWhlrs": 1200,
                    "psncpaCn": "1회차 400명 / 2회차 400명 / 3회차 400명",
                    "progrmDetailLink": "/content.do?key=test",
                },
                {
                    "progrmEstbsNm": "아뜰리에",
                    "psncpaWhlrs": 20,
                    "resveWhlrs": 5,
                    "psncpaCn": "10:00~11:00",
                },
            ],
        }
    ]
    items = parse_json_program_items(payload, "https://www.djkids.or.kr/resve/indvdl/s0.do", date(2026, 6, 24))

    assert max_day_from_payload(payload) == 30
    assert len(items) == 2
    assert items[0].program_name == "상상누리숲"
    assert items[0].normalized_status == ProgramStatus.CLOSED
    assert items[0].source_url == "https://www.djkids.or.kr/content.do?key=test"
    assert items[1].normalized_status == ProgramStatus.AVAILABLE

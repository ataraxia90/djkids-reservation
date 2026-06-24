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


def test_parse_json_program_item_marks_full_program_closed() -> None:
    payload = [
        {
            "progrmEstbsList": [
                {
                    "progrmEstbsNm": "리틀쉐프요리교실(일요일)",
                    "psncpaWhlrs": 50,
                    "resveWhlrs": 50,
                    "psncpaCn": "2회차 25명 / 3회차 25명",
                },
            ],
        }
    ]

    items = parse_json_program_items(
        payload,
        "https://www.djkids.or.kr/resve/indvdl/s0.do",
        date(2026, 7, 5),
    )

    assert len(items) == 1
    assert items[0].raw_status == "마감"
    assert items[0].normalized_status == ProgramStatus.CLOSED


def test_parse_json_program_items_filters_by_weekday_label() -> None:
    payload = [
        {
            "progrmEstbsList": [
                {
                    "progrmEstbsNm": "리틀쉐프요리교실(토요일)",
                    "psncpaWhlrs": 66,
                    "resveWhlrs": 0,
                },
                {
                    "progrmEstbsNm": "리틀쉐프요리교실(일요일)",
                    "psncpaWhlrs": 50,
                    "resveWhlrs": 50,
                },
                {
                    "progrmEstbsNm": "꿈키즈 직업체험(주말)",
                    "psncpaWhlrs": 48,
                    "resveWhlrs": 48,
                },
                {
                    "progrmEstbsNm": "뮤지컬 - 타잔(평일)",
                    "psncpaWhlrs": 450,
                    "resveWhlrs": 0,
                },
            ],
        }
    ]

    items = parse_json_program_items(
        payload,
        "https://www.djkids.or.kr/resve/indvdl/s0.do",
        date(2026, 7, 5),
    )

    assert [item.program_name for item in items] == [
        "리틀쉐프요리교실(일요일)",
        "꿈키즈 직업체험(주말)",
    ]

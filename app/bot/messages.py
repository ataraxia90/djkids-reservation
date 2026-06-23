from __future__ import annotations

from datetime import datetime

from app.djkids.types import ProgramItem
from app.models import WatchTarget


def private_beta_message() -> str:
    return (
        "현재 이 Bot은 비공개 테스트로 운영 중입니다.\n\n"
        "사용 권한이 필요하면 운영자에게 Telegram 사용자 ID를 알려주세요."
    )


def start_message() -> str:
    return (
        "안녕하세요. 대전어린이회관 취소표 알림봇입니다.\n\n"
        "원하는 날짜와 프로그램이 마감 상태일 때 감시를 등록하면,\n"
        "예약 가능 상태가 감지되는 즉시 알림을 보내드립니다."
    )


def help_message() -> str:
    return (
        "사용 가능한 명령어\n\n"
        "/watch - 감시 등록\n"
        "/list - 내 감시 목록\n"
        "/delete - 감시 삭제\n"
        "/settings - 내 설정 확인\n"
        "/help - 도움말\n\n"
        "이 Bot은 알림만 제공합니다. 자동 예약, 로그인, 개인정보 입력은 하지 않습니다."
    )


def not_closed_message(item: ProgramItem) -> str:
    return (
        "마감이 아닙니다.\n\n"
        "현재 선택하신 프로그램은 예약 가능한 상태입니다.\n"
        "예약 페이지에서 바로 확인해주세요.\n\n"
        f"현재 상태: {item.raw_status}"
    )


def watch_registered_message(target: WatchTarget, interval_minutes: int) -> str:
    return (
        "감시가 등록되었습니다.\n\n"
        f"날짜: {target.target_date.isoformat()}\n"
        f"프로그램: {target.program_name}\n"
        f"회차/시간: {target.time_label or '-'}\n"
        "상태: 마감\n\n"
        f"{interval_minutes}분마다 예약 가능 여부를 확인합니다."
    )


def availability_message(
    target_date: str,
    program_name: str,
    time_label: str | None,
    raw_status: str,
    checked_at: datetime,
) -> str:
    return (
        "예약 가능 상태가 감지되었습니다!\n\n"
        f"날짜: {target_date}\n"
        f"프로그램: {program_name}\n"
        f"회차/시간: {time_label or '-'}\n"
        f"상태: {raw_status}\n"
        f"확인 시각: {checked_at:%Y-%m-%d %H:%M}\n\n"
        "취소표는 빠르게 사라질 수 있습니다.\n"
        "바로 예약 페이지를 확인해주세요."
    )

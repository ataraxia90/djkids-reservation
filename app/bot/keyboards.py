from __future__ import annotations

from collections.abc import Iterable
from datetime import date

from aiogram.types import InlineKeyboardButton, InlineKeyboardMarkup

from app.djkids.types import ProgramItem
from app.models import WatchTarget


def home_keyboard() -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(
        inline_keyboard=[
            [InlineKeyboardButton(text="감시 등록하기", callback_data="watch:start")],
            [InlineKeyboardButton(text="내 감시 목록", callback_data="watch:list")],
            [InlineKeyboardButton(text="도움말", callback_data="help")],
        ]
    )


def month_keyboard(dates: Iterable[date]) -> InlineKeyboardMarkup:
    months = sorted({(day.year, day.month) for day in dates})
    return InlineKeyboardMarkup(
        inline_keyboard=[
            [
                InlineKeyboardButton(
                    text=f"{year}년 {month}월",
                    callback_data=f"watch:month:{year:04d}-{month:02d}",
                )
            ]
            for year, month in months
        ]
    )


def date_keyboard(
    dates: Iterable[date],
    *,
    show_all_callback_data: str | None = None,
) -> InlineKeyboardMarkup:
    rows = [
        [
            InlineKeyboardButton(
                text=f"{day.month}/{day.day} ({_weekday_label(day)})",
                callback_data=f"watch:date:{day}",
            )
        ]
        for day in sorted(dates)
    ]
    if show_all_callback_data:
        rows.append([InlineKeyboardButton(text="달 전체 보여주기", callback_data=show_all_callback_data)])
    return InlineKeyboardMarkup(
        inline_keyboard=rows
    )


def program_keyboard(items: list[ProgramItem]) -> InlineKeyboardMarkup:
    rows = []
    for item in items:
        rows.append(
            [
                InlineKeyboardButton(
                    text=item.program_name[:64],
                    callback_data=f"watch:item:{item.callback_token}",
                )
            ]
        )
    rows.append([InlineKeyboardButton(text="다른 날짜 선택", callback_data="watch:start")])
    return InlineKeyboardMarkup(inline_keyboard=rows)


def confirm_watch_keyboard(item: ProgramItem) -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(
        inline_keyboard=[
            [InlineKeyboardButton(text="감시 시작", callback_data="watch:confirm")],
            [InlineKeyboardButton(text="취소", callback_data="watch:cancel")],
        ]
    )


def open_page_keyboard(url: str) -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(
        inline_keyboard=[
            [InlineKeyboardButton(text="예약 페이지 열기", url=url)],
            [InlineKeyboardButton(text="내 감시 목록 보기", callback_data="watch:list")],
            [InlineKeyboardButton(text="다른 프로그램 선택", callback_data="watch:start")],
        ]
    )


def list_keyboard(targets: list[WatchTarget]) -> InlineKeyboardMarkup | None:
    if not targets:
        return None
    return InlineKeyboardMarkup(
        inline_keyboard=[
            [InlineKeyboardButton(text=f"{idx}번 삭제", callback_data=f"watch:delete:{target.id}")]
            for idx, target in enumerate(targets, start=1)
        ]
    )


def _weekday_label(day: date) -> str:
    return ("월", "화", "수", "목", "금", "토", "일")[day.weekday()]

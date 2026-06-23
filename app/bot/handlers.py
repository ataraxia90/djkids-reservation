from __future__ import annotations

from collections import defaultdict
from datetime import datetime

from aiogram import F, Router
from aiogram.filters import Command
from aiogram.types import CallbackQuery, Message
from sqlalchemy.orm import Session

from app.bot.keyboards import (
    confirm_watch_keyboard,
    date_keyboard,
    home_keyboard,
    list_keyboard,
    open_page_keyboard,
    program_keyboard,
)
from app.bot.messages import (
    help_message,
    not_closed_message,
    private_beta_message,
    start_message,
    watch_registered_message,
)
from app.config import get_settings
from app.db import SessionLocal
from app.djkids.fetcher import fetch_program_items
from app.djkids.types import ProgramItem
from app.models import ProgramStatus
from app.services.access_control import get_or_create_user, is_user_allowed
from app.services.watch_service import (
    create_watch_target,
    deactivate_target,
    list_active_targets,
    save_snapshots,
)

router = Router()

_watch_cache: dict[int, list[ProgramItem]] = defaultdict(list)
_date_cache: dict[int, list[ProgramItem]] = defaultdict(list)
_selected_cache: dict[int, ProgramItem] = {}


def _session() -> Session:
    return SessionLocal()


async def _ensure_user(message: Message | CallbackQuery) -> tuple[Session, object] | tuple[None, None]:
    settings = get_settings()
    tg_user = message.from_user
    if tg_user is None:
        return None, None
    target_message = message.message if isinstance(message, CallbackQuery) else message
    if target_message is None:
        return None, None
    if not is_user_allowed(tg_user.id, settings):
        if isinstance(message, CallbackQuery):
            await message.answer("비공개 테스트 Bot입니다.", show_alert=True)
            await target_message.answer(private_beta_message())
        else:
            await message.answer(private_beta_message())
        return None, None
    session = _session()
    user = get_or_create_user(session, tg_user, target_message.chat.id, settings)
    return session, user


@router.message(Command("start"))
async def handle_start(message: Message) -> None:
    result = await _ensure_user(message)
    session, _user = result
    if session is None:
        return
    try:
        await message.answer(start_message(), reply_markup=home_keyboard())
    finally:
        session.close()


@router.message(Command("help"))
async def handle_help(message: Message) -> None:
    result = await _ensure_user(message)
    session, _user = result
    if session is None:
        return
    try:
        await message.answer(help_message())
    finally:
        session.close()


@router.callback_query(F.data == "help")
async def handle_help_callback(callback: CallbackQuery) -> None:
    await callback.answer()
    if callback.message:
        await callback.message.answer(help_message())


@router.message(Command("watch"))
async def handle_watch(message: Message) -> None:
    await _start_watch_flow(message)


@router.callback_query(F.data == "watch:start")
async def handle_watch_start_callback(callback: CallbackQuery) -> None:
    await callback.answer()
    await _start_watch_flow(callback)


async def _start_watch_flow(message: Message | CallbackQuery) -> None:
    settings = get_settings()
    result = await _ensure_user(message)
    session, _user = result
    target_message = message.message if isinstance(message, CallbackQuery) else message
    if session is None or target_message is None or message.from_user is None:
        return
    try:
        await target_message.answer("최신 예약 상태를 조회하고 있습니다.")
        items, _status = await fetch_program_items(settings)
        checked_at = datetime.utcnow()
        save_snapshots(session, items, checked_at)
        _watch_cache[message.from_user.id] = items
        dates = {item.target_date for item in items}
        if not dates:
            await target_message.answer("현재 선택 가능한 예약 항목을 찾지 못했습니다.")
            return
        await target_message.answer("감시할 날짜를 선택해주세요.", reply_markup=date_keyboard(dates))
    except Exception as exc:  # noqa: BLE001
        await target_message.answer(f"예약 상태 조회에 실패했습니다.\n잠시 후 다시 시도해주세요.\n\n오류: {exc}")
    finally:
        session.close()


@router.callback_query(F.data.startswith("watch:date:"))
async def handle_watch_date(callback: CallbackQuery) -> None:
    await callback.answer()
    if callback.message is None or callback.from_user is None or callback.data is None:
        return
    selected_date = callback.data.removeprefix("watch:date:")
    items = [
        item for item in _watch_cache.get(callback.from_user.id, [])
        if item.target_date.isoformat() == selected_date
    ]
    _date_cache[callback.from_user.id] = items
    if not items:
        await callback.message.answer("선택한 날짜의 프로그램을 찾지 못했습니다. 다시 조회해주세요.")
        return
    await callback.message.answer(
        f"{selected_date} 예약 현황입니다.\n마감 상태인 프로그램만 감시 등록할 수 있습니다.",
        reply_markup=program_keyboard(items),
    )


@router.callback_query(F.data.startswith("watch:item:"))
async def handle_watch_item(callback: CallbackQuery) -> None:
    await callback.answer()
    if callback.message is None or callback.from_user is None or callback.data is None:
        return
    try:
        idx = int(callback.data.removeprefix("watch:item:"))
        item = _date_cache[callback.from_user.id][idx]
    except (ValueError, IndexError, KeyError):
        await callback.message.answer("선택 정보가 만료되었습니다. /watch로 다시 시작해주세요.")
        return
    _selected_cache[callback.from_user.id] = item
    if item.normalized_status == ProgramStatus.AVAILABLE:
        await callback.message.answer(not_closed_message(item), reply_markup=open_page_keyboard(item.source_url))
        return
    if item.normalized_status != ProgramStatus.CLOSED:
        await callback.message.answer(
            f"현재 상태를 판단할 수 없어 감시를 등록하지 않았습니다.\n상태: {item.raw_status}"
        )
        return
    await callback.message.answer(
        "현재 마감 상태입니다.\n취소표 알림을 시작할까요?",
        reply_markup=confirm_watch_keyboard(item),
    )


@router.callback_query(F.data == "watch:confirm")
async def handle_watch_confirm(callback: CallbackQuery) -> None:
    await callback.answer()
    settings = get_settings()
    result = await _ensure_user(callback)
    session, user = result
    if session is None or callback.message is None or callback.from_user is None:
        return
    try:
        cached_item = _selected_cache.get(callback.from_user.id)
        if cached_item is None:
            await callback.message.answer("선택 정보가 만료되었습니다. /watch로 다시 시작해주세요.")
            return

        items, _status = await fetch_program_items(settings)
        checked_at = datetime.utcnow()
        save_snapshots(session, items, checked_at)
        latest = next((item for item in items if item.key == cached_item.key), cached_item)
        if latest.normalized_status == ProgramStatus.AVAILABLE:
            await callback.message.answer(
                not_closed_message(latest),
                reply_markup=open_page_keyboard(latest.source_url),
            )
            return
        target = create_watch_target(session, user, latest, settings, checked_at)
        await callback.message.answer(
            watch_registered_message(target, settings.check_interval_minutes),
            reply_markup=open_page_keyboard(latest.source_url),
        )
    except ValueError as exc:
        await callback.message.answer(str(exc))
    except Exception as exc:  # noqa: BLE001
        await callback.message.answer(f"감시 등록 중 오류가 발생했습니다.\n{exc}")
    finally:
        session.close()


@router.callback_query(F.data == "watch:cancel")
async def handle_watch_cancel(callback: CallbackQuery) -> None:
    await callback.answer("취소했습니다.")
    if callback.message:
        await callback.message.answer("감시 등록을 취소했습니다.")


@router.message(Command("list"))
async def handle_list(message: Message) -> None:
    await _send_watch_list(message)


@router.callback_query(F.data == "watch:list")
async def handle_list_callback(callback: CallbackQuery) -> None:
    await callback.answer()
    await _send_watch_list(callback)


async def _send_watch_list(message: Message | CallbackQuery) -> None:
    result = await _ensure_user(message)
    session, user = result
    target_message = message.message if isinstance(message, CallbackQuery) else message
    if session is None or target_message is None:
        return
    try:
        targets = list_active_targets(session, user.id)
        if not targets:
            await target_message.answer("현재 감시 중인 항목이 없습니다.")
            return
        lines = ["현재 감시 중인 항목입니다.\n"]
        for idx, target in enumerate(targets, start=1):
            checked = target.last_checked_at.strftime("%Y-%m-%d %H:%M") if target.last_checked_at else "-"
            lines.append(
                f"{idx}. {target.target_date.isoformat()} {target.program_name}\n"
                f"   회차/시간: {target.time_label or '-'}\n"
                f"   상태: {target.last_status or '-'}\n"
                f"   마지막 확인: {checked}\n"
            )
        await target_message.answer("\n".join(lines), reply_markup=list_keyboard(targets))
    finally:
        session.close()


@router.message(Command("delete"))
async def handle_delete(message: Message) -> None:
    await _send_watch_list(message)


@router.callback_query(F.data.startswith("watch:delete:"))
async def handle_delete_callback(callback: CallbackQuery) -> None:
    await callback.answer()
    result = await _ensure_user(callback)
    session, user = result
    if session is None or callback.message is None or callback.data is None:
        return
    try:
        target_id = int(callback.data.removeprefix("watch:delete:"))
        target = next((t for t in list_active_targets(session, user.id) if t.id == target_id), None)
        if target is None:
            await callback.message.answer("삭제할 감시 항목을 찾지 못했습니다.")
            return
        deactivate_target(session, target)
        await callback.message.answer("감시 항목이 삭제되었습니다.")
    finally:
        session.close()


@router.message(Command("settings"))
async def handle_settings(message: Message) -> None:
    settings = get_settings()
    result = await _ensure_user(message)
    session, user = result
    if session is None:
        return
    try:
        count = len(list_active_targets(session, user.id))
        await message.answer(
            "현재 설정입니다.\n\n"
            f"사용자 ID: {user.telegram_user_id}\n"
            f"알림 활성 여부: {'예' if user.is_active and not user.is_blocked else '아니오'}\n"
            f"등록 가능한 최대 감시 개수: {settings.max_watch_targets_per_user}\n"
            f"현재 등록된 감시 개수: {count}\n"
            f"감시 주기: {settings.check_interval_minutes}분"
        )
    finally:
        session.close()

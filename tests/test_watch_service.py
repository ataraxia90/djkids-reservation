from datetime import datetime

import pytest

from app.config import Settings
from app.djkids.parser import parse_program_items
from app.models import ProgramStatus, User
from app.services.watch_service import create_watch_target, list_active_targets


def _user(session) -> User:
    user = User(telegram_user_id="1", chat_id="1", is_active=True)
    session.add(user)
    session.commit()
    session.refresh(user)
    return user


def test_create_watch_target_only_closed(session) -> None:
    user = _user(session)
    settings = Settings(max_watch_targets_per_user=5)
    html = """
    <table><tbody>
      <tr><td>2026-06-28</td><td>리틀셰프요리교실</td><td>1회차</td><td>마감</td></tr>
      <tr><td>2026-06-28</td><td>어린이창의교실</td><td>2회차</td><td>예약하기</td></tr>
    </tbody></table>
    """
    closed, available = parse_program_items(html, "https://example.test")

    target = create_watch_target(session, user, closed, settings, datetime.utcnow())
    assert target.last_status == ProgramStatus.CLOSED
    assert len(list_active_targets(session, user.id)) == 1

    with pytest.raises(ValueError, match="마감이 아닙니다"):
        create_watch_target(session, user, available, settings, datetime.utcnow())


def test_watch_target_limit(session) -> None:
    user = _user(session)
    settings = Settings(max_watch_targets_per_user=1)
    html = """
    <table><tbody>
      <tr><td>2026-06-28</td><td>A</td><td>1회차</td><td>마감</td></tr>
      <tr><td>2026-06-29</td><td>B</td><td>1회차</td><td>마감</td></tr>
    </tbody></table>
    """
    first, second = parse_program_items(html, "https://example.test")
    create_watch_target(session, user, first, settings, datetime.utcnow())

    with pytest.raises(ValueError, match="등록 가능한 감시 개수"):
        create_watch_target(session, user, second, settings, datetime.utcnow())

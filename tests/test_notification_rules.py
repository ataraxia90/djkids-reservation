from datetime import datetime

from app.config import Settings
from app.djkids.parser import parse_program_items
from app.models import NotificationQueue, ProgramStatus, User
from app.services.monitor_service import match_active_targets
from app.services.watch_service import create_watch_target


def test_closed_to_available_enqueues_once_and_deactivates(session) -> None:
    user = User(telegram_user_id="1", chat_id="100", is_active=True)
    session.add(user)
    session.commit()
    session.refresh(user)

    settings = Settings(max_watch_targets_per_user=5)
    closed_html = """
    <table><tbody>
      <tr><td>2026-06-28</td><td>리틀셰프요리교실</td><td>1회차</td><td>마감</td></tr>
    </tbody></table>
    """
    available_html = """
    <table><tbody>
      <tr><td>2026-06-28</td><td>리틀셰프요리교실</td><td>1회차</td><td>예약하기</td></tr>
    </tbody></table>
    """
    closed_item = parse_program_items(closed_html, "https://example.test")[0]
    create_watch_target(session, user, closed_item, settings, datetime.utcnow())
    available_item = parse_program_items(available_html, "https://example.test")[0]

    assert match_active_targets(session, settings, [available_item], datetime.utcnow()) == 1
    assert session.query(NotificationQueue).count() == 1
    assert match_active_targets(session, settings, [available_item], datetime.utcnow()) == 0
    assert session.query(NotificationQueue).count() == 1


def test_available_to_closed_does_not_notify(session) -> None:
    user = User(telegram_user_id="2", chat_id="200", is_active=True)
    session.add(user)
    session.commit()
    session.refresh(user)
    settings = Settings(max_watch_targets_per_user=5)
    closed_item = parse_program_items(
        "<table><tbody><tr><td>2026-06-28</td><td>A</td><td>1회차</td><td>마감</td></tr></tbody></table>",
        "https://example.test",
    )[0]
    target = create_watch_target(session, user, closed_item, settings, datetime.utcnow())
    target.last_status = ProgramStatus.AVAILABLE
    session.commit()

    assert match_active_targets(session, settings, [closed_item], datetime.utcnow()) == 0
    assert session.query(NotificationQueue).count() == 0

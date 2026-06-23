from app.djkids.status import normalize_status, should_notify
from app.models import ProgramStatus


def test_normalize_status() -> None:
    assert normalize_status("마감") == ProgramStatus.CLOSED
    assert normalize_status("예약하기") == ProgramStatus.AVAILABLE
    assert normalize_status("예약가능") == ProgramStatus.AVAILABLE
    assert normalize_status("접수중") == ProgramStatus.AVAILABLE
    assert normalize_status("대기") == ProgramStatus.UNKNOWN
    assert normalize_status("알 수 없음") == ProgramStatus.UNKNOWN


def test_should_notify_transitions() -> None:
    assert should_notify(ProgramStatus.CLOSED, ProgramStatus.AVAILABLE)
    assert should_notify(ProgramStatus.UNKNOWN, ProgramStatus.AVAILABLE)
    assert should_notify(ProgramStatus.ERROR, ProgramStatus.AVAILABLE)
    assert not should_notify(ProgramStatus.AVAILABLE, ProgramStatus.AVAILABLE)
    assert not should_notify(ProgramStatus.CLOSED, ProgramStatus.CLOSED)
    assert not should_notify(ProgramStatus.AVAILABLE, ProgramStatus.CLOSED)

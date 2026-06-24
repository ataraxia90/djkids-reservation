from __future__ import annotations

from dataclasses import dataclass
from datetime import date
from hashlib import blake2s

from app.models import ProgramStatus


@dataclass(frozen=True)
class ProgramItem:
    target_date: date
    program_name: str
    time_label: str | None
    raw_status: str
    normalized_status: ProgramStatus
    source_url: str
    raw_text: str

    @property
    def key(self) -> str:
        return make_status_key(self.target_date, self.program_name, self.time_label)

    @property
    def callback_token(self) -> str:
        return make_callback_token(self.key)


def make_status_key(target_date: date, program_name: str, time_label: str | None) -> str:
    return f"{target_date.isoformat()}|{program_name.strip()}|{(time_label or '').strip()}"


def make_callback_token(status_key: str) -> str:
    return blake2s(status_key.encode("utf-8"), digest_size=6).hexdigest()

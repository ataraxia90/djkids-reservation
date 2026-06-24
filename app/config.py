from __future__ import annotations

from functools import lru_cache
from zoneinfo import ZoneInfo

from pydantic import Field, field_validator
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", env_file_encoding="utf-8", extra="ignore")

    app_env: str = "development"
    timezone: str = "Asia/Seoul"

    telegram_bot_token: str = ""
    admin_telegram_ids: list[int] = Field(default_factory=list)
    allowed_telegram_user_ids: list[int] = Field(default_factory=list)
    allow_public_signup: bool = False

    target_url: str = "https://www.djkids.or.kr/resve/indvdl/s0.do?key=m2008167905806"
    reservation_month_count: int = 3
    check_interval_minutes: int = 1
    check_jitter_seconds: int = 60

    database_url: str = "sqlite:///./data/app.db"

    max_watch_targets_per_user: int = 5
    max_fetch_retry: int = 3
    admin_alert_failure_threshold: int = 3

    use_playwright: bool = False
    headless: bool = True

    log_level: str = "INFO"
    telegram_send_rate_per_second: float = 1.0

    @field_validator("admin_telegram_ids", "allowed_telegram_user_ids", mode="before")
    @classmethod
    def parse_int_list(cls, value: object) -> list[int]:
        if value is None or value == "":
            return []
        if isinstance(value, list):
            return [int(v) for v in value if str(v).strip()]
        return [int(part.strip()) for part in str(value).split(",") if part.strip()]

    @property
    def tzinfo(self) -> ZoneInfo:
        return ZoneInfo(self.timezone)


@lru_cache
def get_settings() -> Settings:
    return Settings()

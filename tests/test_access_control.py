from app.config import Settings
from app.services.access_control import is_user_allowed


def test_private_allowlist() -> None:
    settings = Settings(
        allow_public_signup=False,
        admin_telegram_ids=[1],
        allowed_telegram_user_ids=[2],
    )
    assert is_user_allowed(1, settings)
    assert is_user_allowed(2, settings)
    assert not is_user_allowed(3, settings)


def test_public_signup() -> None:
    assert is_user_allowed(99, Settings(allow_public_signup=True))

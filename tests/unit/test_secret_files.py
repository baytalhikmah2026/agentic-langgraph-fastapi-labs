"""Secrets as files (Lab 84): a mounted Secret folder fills in settings, the environment wins."""

from pathlib import Path

import pytest

from sovereign_brain.core.settings import Settings

SECRET = "a-secret-that-came-from-a-file-0123456789"


def test_a_setting_can_come_from_a_secret_file(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    (tmp_path / "SB_JWT_SECRET").write_text(SECRET, encoding="utf-8")
    (tmp_path / "SB_MARKET_API_TOKEN").write_text("from-the-file", encoding="utf-8")
    monkeypatch.delenv("SB_JWT_SECRET", raising=False)
    monkeypatch.setenv("SB_MARKET_API_TOKEN", "from-the-environment")

    settings = Settings(_env_file=None, _secrets_dir=tmp_path)

    assert settings.jwt_secret.get_secret_value() == SECRET
    assert settings.market_api_token.get_secret_value() == "from-the-environment"

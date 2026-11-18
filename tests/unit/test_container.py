"""The production container (Lab 81): secrets stay out, the API runs as a normal user."""

from pathlib import Path

import yaml

ROOT = Path(__file__).resolve().parents[2]


def test_secrets_and_tests_never_enter_the_image() -> None:
    ignored = (ROOT / ".dockerignore").read_text(encoding="utf-8").split()

    for entry in [".env", ".git", "ops/certs", "backups", "tests"]:
        assert entry in ignored


def test_the_production_api_runs_as_a_normal_user() -> None:
    dockerfile = (ROOT / "Dockerfile").read_text(encoding="utf-8")
    prod = yaml.safe_load((ROOT / "compose.prod.yaml").read_text(encoding="utf-8"))
    api = prod["services"]["api"]

    assert "USER app" in dockerfile
    assert api["command"][:2] == ["fastapi", "run"]
    assert api["environment"]["SB_ENVIRONMENT"] == "production"
    assert "no-new-privileges:true" in api["security_opt"]

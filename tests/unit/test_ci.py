"""The delivery pipeline (Labs 88-89): it uses the same versions as the rest of the project."""

import tomllib
from pathlib import Path

import yaml

ROOT = Path(__file__).resolve().parents[2]


def workflow() -> dict:
    return yaml.safe_load((ROOT / ".github/workflows/ci.yml").read_text(encoding="utf-8"))


def steps(job: str) -> list[dict]:
    return workflow()["jobs"][job]["steps"]


def test_the_cluster_check_runs_only_after_lint_and_tests() -> None:
    jobs = workflow()["jobs"]

    assert list(jobs) == ["checks", "cluster"]
    assert jobs["cluster"]["needs"] == "checks"
    assert any(step.get("run") == "uv run pytest -q" for step in steps("checks"))


def test_the_pipeline_uses_the_project_versions() -> None:
    dockerfile = (ROOT / "Dockerfile").read_text(encoding="utf-8")
    kind_config = yaml.safe_load((ROOT / "k8s/kind-config.yaml").read_text(encoding="utf-8"))
    (kind,) = [step for step in steps("cluster") if step.get("uses", "").startswith("helm/kind")]

    for job in ("checks", "cluster"):
        (uv,) = [step for step in steps(job) if step.get("uses", "").startswith("astral-sh")]
        assert f"ghcr.io/astral-sh/uv:{uv['with']['version']}" in dockerfile
    assert kind["with"]["config"] == "k8s/kind-config.yaml"
    assert kind["with"]["cluster_name"] == kind_config["name"]


def test_the_pipeline_builds_the_project_version() -> None:
    """Lab 89: after a version change, CI must build and load the same tag the manifests use."""
    pyproject = tomllib.loads((ROOT / "pyproject.toml").read_text(encoding="utf-8"))
    image = f"sovereign-brain-api:{pyproject['project']['version']}"
    runs = [step.get("run", "") for step in steps("cluster")]
    runs = [run for run in runs if "sovereign-brain-api:" in run]

    assert len(runs) == 2  # docker build and kind load
    assert all(image in run for run in runs)

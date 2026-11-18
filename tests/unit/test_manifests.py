"""The Kubernetes manifests (Lab 82): rules every workload in k8s/base follows."""

import tomllib
from pathlib import Path

import yaml

ROOT = Path(__file__).resolve().parents[2]
BASE = ROOT / "k8s" / "base"
WORKLOADS = {"Deployment", "StatefulSet", "Job", "Rollout"}


def workloads() -> list[dict]:
    """Every object that runs containers, in the files the base kustomization lists."""
    kustomization = yaml.safe_load((BASE / "kustomization.yaml").read_text(encoding="utf-8"))
    found = []
    for name in kustomization["resources"]:
        text = (BASE / name).read_text(encoding="utf-8")
        found += [doc for doc in yaml.safe_load_all(text) if doc and doc["kind"] in WORKLOADS]
    return found


def test_every_container_asks_for_resources() -> None:
    for workload in workloads():
        for container in workload["spec"]["template"]["spec"]["containers"]:
            assert "requests" in container.get("resources", {}), workload["metadata"]["name"]


def test_our_image_runs_as_a_normal_user_with_the_project_version() -> None:
    pyproject = tomllib.loads((ROOT / "pyproject.toml").read_text(encoding="utf-8"))
    image = f"sovereign-brain-api:{pyproject['project']['version']}"
    ours = 0
    for workload in workloads():
        pod = workload["spec"]["template"]["spec"]
        for container in pod["containers"]:
            if container["image"].startswith("sovereign-brain-api:"):
                ours += 1
                assert container["image"] == image
                assert pod["securityContext"]["runAsNonRoot"] is True
                assert container["securityContext"]["allowPrivilegeEscalation"] is False
    assert ours >= 2  # at least the API and the seed job

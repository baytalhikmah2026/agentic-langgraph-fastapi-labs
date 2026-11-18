"""The Kubernetes manifests (Labs 82-85): rules every workload in k8s/base follows."""

import tomllib
from pathlib import Path

import yaml

ROOT = Path(__file__).resolve().parents[2]
BASE = ROOT / "k8s" / "base"
SECRET_WORDS = ("PASSWORD", "SECRET", "TOKEN", "KEY")  # setting names that hint at a secret
RESIDENCY = {"crescent-ledger.bank/residency": "on-premises"}  # Lab 85
WORKLOADS = {"Deployment", "StatefulSet", "Job", "Rollout"}


def documents() -> list[dict]:
    """Every object in the files the base kustomization lists."""
    kustomization = yaml.safe_load((BASE / "kustomization.yaml").read_text(encoding="utf-8"))
    found = []
    for name in kustomization["resources"]:
        text = (BASE / name).read_text(encoding="utf-8")
        found += [doc for doc in yaml.safe_load_all(text) if doc]
    return found


def workloads() -> list[dict]:
    """The objects that run containers."""
    return [doc for doc in documents() if doc["kind"] in WORKLOADS]


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


def test_every_autoscaler_targets_a_workload_of_the_base() -> None:
    names = {workload["metadata"]["name"] for workload in workloads()}
    scalers = [d for d in documents() if d["kind"] in {"HorizontalPodAutoscaler", "ScaledObject"}]

    assert len(scalers) == 2  # the API's HPA (Lab 83) and the workers' ScaledObject
    for scaler in scalers:
        assert scaler["spec"]["scaleTargetRef"]["name"] in names


def secret_like(name: str) -> bool:
    return any(word in name for word in SECRET_WORDS)


def test_no_secret_is_written_in_the_plan() -> None:
    """Secret-looking settings hold only a file path, or come from a Secret (valueFrom)."""
    for line in (BASE / "desk-config.env").read_text(encoding="utf-8").splitlines():
        name, value = line.split("=", 1)
        assert not secret_like(name) or value.startswith("/"), name
    for workload in workloads():
        for container in workload["spec"]["template"]["spec"]["containers"]:
            for variable in container.get("env", []):
                if secret_like(variable["name"]):
                    assert "valueFrom" in variable or variable["value"].startswith("/")


def test_data_services_keep_their_data_on_the_bank_node() -> None:
    services = {doc["metadata"]["name"]: doc for doc in documents() if doc["kind"] == "Service"}
    stateful = [workload for workload in workloads() if workload["kind"] == "StatefulSet"]

    assert {item["metadata"]["name"] for item in stateful} == {"postgres", "redis", "qdrant"}
    for workload in stateful:
        spec = workload["spec"]
        assert spec["volumeClaimTemplates"]  # its own disk
        assert spec["persistentVolumeClaimRetentionPolicy"]["whenDeleted"] == "Retain"
        assert spec["template"]["spec"]["nodeSelector"] == RESIDENCY
        assert services[spec["serviceName"]]["spec"]["clusterIP"] == "None"  # headless

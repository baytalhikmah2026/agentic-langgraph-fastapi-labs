"""Federated learning (Lab 94): one Flower version everywhere, two branches, own containers."""

import tomllib
from pathlib import Path

import yaml

FEDERATED = Path(__file__).resolve().parents[2] / "edge/federated"


def test_every_flower_piece_uses_the_same_version() -> None:
    app = tomllib.loads((FEDERATED / "pyproject.toml").read_text(encoding="utf-8"))
    compose = yaml.safe_load((FEDERATED / "compose.yaml").read_text(encoding="utf-8"))
    dockerfile = (FEDERATED / "superexec.Dockerfile").read_text(encoding="utf-8")
    services = compose["services"]
    images = {s["image"] for s in services.values() if s["image"].startswith("flwr/")}
    nodes = [service for name, service in services.items() if name.startswith("supernode")]

    assert app["project"]["dependencies"] == ["flwr[simulation]==1.43.0"]
    assert images == {"flwr/superlink:1.43.0", "flwr/supernode:1.43.0"}
    assert "FROM flwr/superexec:1.43.0" in dockerfile
    assert sorted(node["command"][2] for node in nodes) == [
        "--node-config=partition-id=0 num-partitions=2",
        "--node-config=partition-id=1 num-partitions=2",
    ]

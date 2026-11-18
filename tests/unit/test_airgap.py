"""The air-gapped desk (Lab 91): every image comes from the bank's registry, nothing goes out."""

from pathlib import Path

import yaml

ROOT = Path(__file__).resolve().parents[2]
AIRGAP = ROOT / "k8s/overlays/airgap"


def base_images() -> set[str]:
    """Every container image the base plan runs, as written in its files."""
    base = ROOT / "k8s/base"
    kustomization = yaml.safe_load((base / "kustomization.yaml").read_text(encoding="utf-8"))
    found = set()
    for name in kustomization["resources"]:
        for doc in yaml.safe_load_all((base / name).read_text(encoding="utf-8")):
            pod = (doc or {}).get("spec", {}).get("template", {}).get("spec", {})
            found |= {container["image"] for container in pod.get("containers", [])}
    return found


def test_the_kit_and_the_overlay_cover_every_image() -> None:
    lines = (ROOT / "ops/airgap/images.txt").read_text(encoding="utf-8").splitlines()
    kit = {line for line in lines if line and not line.startswith("#")}
    overlay = yaml.safe_load((AIRGAP / "kustomization.yaml").read_text(encoding="utf-8"))
    renamed = {image["name"]: image["newName"] for image in overlay["images"]}

    assert kit == base_images()
    for image in kit:
        name = image.split(":")[0]
        assert renamed[name] == f"localhost:5001/{name}"


def test_the_sealed_namespace_has_no_way_out() -> None:
    policy = yaml.safe_load((AIRGAP / "no-internet.yaml").read_text(encoding="utf-8"))
    allowed = policy["spec"]["egress"]

    assert policy["spec"]["podSelector"] == {}  # every pod
    assert policy["spec"]["policyTypes"] == ["Egress"]
    assert allowed[0] == {"to": [{"podSelector": {}}]}  # the namespace itself
    assert allowed[1]["to"][0]["podSelector"]["matchLabels"] == {"k8s-app": "kube-dns"}

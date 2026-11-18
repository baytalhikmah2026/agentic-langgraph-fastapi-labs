"""Infrastructure as code (Lab 96): Terraform uses the same versions as the rest of the desk."""

import re
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
TERRAFORM = ROOT / "infra/terraform"


def test_terraform_matches_the_locked_stack() -> None:
    versions = (TERRAFORM / "versions.tf").read_text(encoding="utf-8")
    main = (TERRAFORM / "main.tf").read_text(encoding="utf-8")
    kit = (ROOT / "ops/airgap/images.txt").read_text(encoding="utf-8").split()

    assert re.search(r'source\s+= "hashicorp/kubernetes"\s+version\s+= "3\.5\.0"', versions)
    assert re.search(r'source\s+= "hashicorp/helm"\s+version\s+= "3\.3\.0"', versions)
    assert 'backend "kubernetes"' in versions  # shared state with locking
    assert 'version    = "42.3.1"' in main  # the Traefik chart from Lab 87
    for image in re.findall(r'"\$\{var\.registry\}/([^"]+)"', main):
        assert image in kit  # every image comes from the air-gap kit (Lab 91)

"""Run labels (Lab 67): every approval run carries a tag and its approval_id."""

from sovereign_brain.api.v1.approvals import approval_config

APPROVAL_ID = "4b7e1c9a2d5f4e3b8a6c0d1e2f3a4b5c"


def test_an_approval_run_is_labelled() -> None:
    config = approval_config(APPROVAL_ID)

    assert config["tags"] == ["approvals"]
    assert config["metadata"]["approval_id"] == APPROVAL_ID
    assert config["configurable"]["thread_id"] == f"approval:{APPROVAL_ID}"

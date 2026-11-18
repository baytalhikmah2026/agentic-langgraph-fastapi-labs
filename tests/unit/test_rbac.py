"""Roles (Lab 73): one table says who may do what."""

from sovereign_brain.security.rbac import allowed, grant


def test_the_permission_table() -> None:
    assert allowed("lead", "approvals:override")
    assert not allowed("analyst", "approvals:override")
    assert allowed("auditor", "approvals:read")
    assert not allowed("auditor", "approvals:decide")
    assert not allowed("auditor", "research:run")
    assert not allowed("intern", "approvals:read")  # unknown roles get nothing
    assert not allowed("lead", "approvals:delete")  # unknown permissions too


def test_a_sign_in_can_only_narrow_its_power() -> None:
    """Lab 99: scopes are what was asked for and the role allows; nothing asked, everything."""
    assert grant("analyst", ["brain:run", "approvals:override"]) == ["brain:run"]
    assert "approvals:override" in grant("lead", [])
    assert grant("auditor", ["brain:run"]) == []

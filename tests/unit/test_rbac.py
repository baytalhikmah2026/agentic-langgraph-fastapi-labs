"""Roles (Lab 73): one table says who may do what."""

from sovereign_brain.security.rbac import allowed


def test_the_permission_table() -> None:
    assert allowed("lead", "approvals:override")
    assert not allowed("analyst", "approvals:override")
    assert allowed("auditor", "approvals:read")
    assert not allowed("auditor", "approvals:decide")
    assert not allowed("auditor", "research:run")
    assert not allowed("intern", "approvals:read")  # unknown roles get nothing
    assert not allowed("lead", "approvals:delete")  # unknown permissions too

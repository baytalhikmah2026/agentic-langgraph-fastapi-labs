"""The regulator's desk (Lab 95): signed reports for leads, auditors and regulators only."""

from fastapi.testclient import TestClient

from sovereign_brain.security.signing import verify


def test_the_compliance_report_is_signed_and_logged(
    client: TestClient, auth_headers: dict[str, str], yusuf_headers: dict[str, str]
) -> None:
    sealed = client.get("/v1/compliance/report?days=7", headers=yusuf_headers).json()
    key = client.get("/v1/approvals/signing-key", headers=yusuf_headers).json()
    page = client.get("/v1/compliance/report.md", headers=yusuf_headers)
    analyst = client.get("/v1/compliance/report", headers=auth_headers)
    events = client.get("/v1/audit/events", headers=yusuf_headers).json()

    rules = {control["rule"]: control for control in sealed["report"]["controls"]}
    assert len(rules) == 5
    assert rules["EU AI Act, Article 12 (record-keeping)"]["met"] is True
    assert rules["EU AI Act, Article 15 (robustness and cybersecurity)"]["met"] is False  # no mTLS
    assert verify(sealed["report"], sealed["signature"], key["public_key_pem"])
    assert page.text.startswith("# Compliance report")
    assert analyst.status_code == 403
    assert [event["action"] for event in events] == ["compliance.report_issued"] * 2

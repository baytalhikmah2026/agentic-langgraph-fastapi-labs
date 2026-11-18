"""The hardened desk (Lab 80): security headers on every answer, a signed security report."""

from fastapi.testclient import TestClient

from sovereign_brain.security.signing import verify


def test_every_answer_carries_the_security_headers(
    client: TestClient, auth_headers: dict[str, str]
) -> None:
    health = client.get("/health")
    api = client.get("/v1/approvals", headers=auth_headers)

    assert health.headers["x-content-type-options"] == "nosniff"
    assert health.headers["x-frame-options"] == "DENY"
    assert "cache-control" not in health.headers  # only /v1/ answers are marked no-store
    assert api.headers["cache-control"] == "no-store"


def test_the_security_report_is_signed(
    client: TestClient, auth_headers: dict[str, str], yusuf_headers: dict[str, str]
) -> None:
    report = client.get("/v1/security/report", headers=yusuf_headers).json()
    key = client.get("/v1/approvals/signing-key", headers=yusuf_headers).json()
    analyst = client.get("/v1/security/report", headers=auth_headers)

    posture = report["posture"]
    assert posture["pii_masking"] is True
    assert posture["permissions"]["approvals:override"] == ["lead"]
    assert posture["audit_chain"] == {"events": 0, "valid": True, "head_hash": "0" * 64}
    assert verify(posture, report["signature"], key["public_key_pem"])
    assert analyst.status_code == 403

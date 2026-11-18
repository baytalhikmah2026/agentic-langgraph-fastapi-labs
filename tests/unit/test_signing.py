"""Signed decisions (Lab 76): a signature matches only the exact statement it was made for."""

from cryptography.hazmat.primitives.asymmetric.ed25519 import Ed25519PrivateKey

from sovereign_brain.security.signing import Signer, new_signing_key_pem, verify

STATEMENT = {
    "approval_id": "4b7e1c9a2d5f4e3b8a6c0d1e2f3a4b5c",
    "decision": "approved",
    "decided_by": "omar",
    "report_sha256": "9f2c...",
}


def test_a_signed_statement_verifies() -> None:
    signer = Signer.from_pem(new_signing_key_pem())

    signature = signer.sign(STATEMENT)

    assert verify(STATEMENT, signature, signer.public_pem)


def test_one_changed_field_breaks_the_signature() -> None:
    signer = Signer(Ed25519PrivateKey.generate())
    signature = signer.sign(STATEMENT)

    forged = {**STATEMENT, "decided_by": "amina"}

    assert not verify(forged, signature, signer.public_pem)
    assert not verify(STATEMENT, signature, Signer(Ed25519PrivateKey.generate()).public_pem)


def test_the_order_of_the_fields_does_not_matter() -> None:
    signer = Signer(Ed25519PrivateKey.generate())
    reordered = dict(reversed(list(STATEMENT.items())))

    assert signer.sign(reordered) == signer.sign(STATEMENT)  # one canonical byte form

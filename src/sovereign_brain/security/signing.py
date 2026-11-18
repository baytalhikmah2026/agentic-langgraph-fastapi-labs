"""Signed decisions (Lab 76): every approve or reject is a statement signed with Ed25519.

The desk signs a short statement: which report (by its SHA-256 hash), what was decided, by
whom and when. Anyone with the desk's public key can check the statement later. If a single
character of the statement, or of the report, is changed, the check fails.
"""

import base64
import hashlib
import json
import logging

from cryptography.exceptions import InvalidSignature
from cryptography.hazmat.primitives import serialization
from cryptography.hazmat.primitives.asymmetric.ed25519 import Ed25519PrivateKey, Ed25519PublicKey

logger = logging.getLogger("sovereign_brain.signing")


def canonical(data: dict) -> bytes:
    """One exact byte form for a dictionary: sorted keys, no spaces, UTF-8."""
    return json.dumps(data, sort_keys=True, separators=(",", ":"), ensure_ascii=False).encode()


def report_hash(report: dict) -> str:
    """The fingerprint of a report: any change to it gives a completely different hash."""
    return hashlib.sha256(canonical(report)).hexdigest()


def new_signing_key_pem() -> str:
    """A new Ed25519 private key as PEM text (scripts/vault_setup.py stores it in Vault)."""
    key = Ed25519PrivateKey.generate()
    return key.private_bytes(
        serialization.Encoding.PEM,
        serialization.PrivateFormat.PKCS8,
        serialization.NoEncryption(),
    ).decode()


class Signer:
    """Signs statements with the desk's private key and publishes the matching public key."""

    def __init__(self, key: Ed25519PrivateKey) -> None:
        self.key = key
        public = key.public_key()
        self.public_pem = public.public_bytes(
            serialization.Encoding.PEM, serialization.PublicFormat.SubjectPublicKeyInfo
        ).decode()
        raw = public.public_bytes(serialization.Encoding.Raw, serialization.PublicFormat.Raw)
        self.key_id = hashlib.sha256(raw).hexdigest()[:16]  # a short name for this key

    @classmethod
    def from_pem(cls, pem: str) -> "Signer":
        """The desk's key from Vault; without one, a temporary key (local runs and tests)."""
        if not pem:
            logger.warning("No approval signing key configured: using a temporary key")
            return cls(Ed25519PrivateKey.generate())
        key = serialization.load_pem_private_key(pem.encode(), password=None)
        if not isinstance(key, Ed25519PrivateKey):
            raise ValueError("The approval signing key must be an Ed25519 key")
        return cls(key)

    def sign(self, statement: dict) -> str:
        return base64.urlsafe_b64encode(self.key.sign(canonical(statement))).decode()


def verify(statement: dict, signature: str, public_pem: str) -> bool:
    """True only if this exact statement was signed by the key behind public_pem."""
    public = serialization.load_pem_public_key(public_pem.encode())
    if not isinstance(public, Ed25519PublicKey):
        return False
    try:
        public.verify(base64.urlsafe_b64decode(signature), canonical(statement))
    except (InvalidSignature, ValueError):
        return False
    return True

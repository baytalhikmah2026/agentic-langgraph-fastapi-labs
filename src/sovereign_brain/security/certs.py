"""Our own certificate authority (Lab 74): ID cards for services, for mutual TLS.

A certificate authority (CA) signs certificates. A service that trusts the CA trusts every
certificate it signed. With mutual TLS, both sides show a certificate: the market API proves
it is the real market API, and the caller proves it is the real Research Desk API.
These are lab certificates for one computer; a bank uses its own managed CA.
"""

import ipaddress
import ssl
from dataclasses import dataclass
from datetime import UTC, datetime, timedelta
from pathlib import Path

from cryptography import x509
from cryptography.hazmat.primitives import hashes, serialization
from cryptography.hazmat.primitives.asymmetric import ec
from cryptography.x509.oid import ExtendedKeyUsageOID, NameOID

ORGANISATION = "Crescent Ledger Bank (lab)"


@dataclass
class Issued:
    """A private key and the certificate that belongs to it."""

    key: ec.EllipticCurvePrivateKey
    cert: x509.Certificate


def subject(common_name: str) -> x509.Name:
    return x509.Name(
        [
            x509.NameAttribute(NameOID.ORGANIZATION_NAME, ORGANISATION),
            x509.NameAttribute(NameOID.COMMON_NAME, common_name),
        ]
    )


def usage(*, signs_certificates: bool) -> x509.KeyUsage:
    """What a key may be used for: signing certificates (the CA) or TLS handshakes."""
    return x509.KeyUsage(
        digital_signature=not signs_certificates,
        content_commitment=False,
        key_encipherment=False,
        data_encipherment=False,
        key_agreement=False,
        key_cert_sign=signs_certificates,
        crl_sign=signs_certificates,
        encipher_only=False,
        decipher_only=False,
    )


def make_ca(days: int = 1825) -> Issued:
    """A new certificate authority that signs itself (valid for five years)."""
    key = ec.generate_private_key(ec.SECP256R1())
    now = datetime.now(UTC)
    name = subject("Crescent Ledger Lab CA")
    cert = (
        x509.CertificateBuilder()
        .subject_name(name)
        .issuer_name(name)
        .public_key(key.public_key())
        .serial_number(x509.random_serial_number())
        .not_valid_before(now - timedelta(minutes=5))
        .not_valid_after(now + timedelta(days=days))
        .add_extension(x509.BasicConstraints(ca=True, path_length=0), critical=True)
        .add_extension(usage(signs_certificates=True), critical=True)
        .add_extension(x509.SubjectKeyIdentifier.from_public_key(key.public_key()), critical=False)
        .sign(key, hashes.SHA256())
    )
    return Issued(key, cert)


def issue(
    ca: Issued, common_name: str, hosts: list[str], *, client: bool, days: int = 365
) -> Issued:
    """A certificate signed by the CA, for a server (its host names) or a client."""
    key = ec.generate_private_key(ec.SECP256R1())
    now = datetime.now(UTC)
    names: list[x509.GeneralName] = []
    for host in hosts:
        try:
            names.append(x509.IPAddress(ipaddress.ip_address(host)))
        except ValueError:
            names.append(x509.DNSName(host))
    purpose = ExtendedKeyUsageOID.CLIENT_AUTH if client else ExtendedKeyUsageOID.SERVER_AUTH
    cert = (
        x509.CertificateBuilder()
        .subject_name(subject(common_name))
        .issuer_name(ca.cert.subject)
        .public_key(key.public_key())
        .serial_number(x509.random_serial_number())
        .not_valid_before(now - timedelta(minutes=5))
        .not_valid_after(now + timedelta(days=days))
        .add_extension(x509.BasicConstraints(ca=False, path_length=None), critical=True)
        .add_extension(usage(signs_certificates=False), critical=True)
        .add_extension(x509.ExtendedKeyUsage([purpose]), critical=False)
        .add_extension(x509.SubjectAlternativeName(names), critical=False)
        .add_extension(
            x509.AuthorityKeyIdentifier.from_issuer_public_key(ca.key.public_key()),
            critical=False,
        )
        .sign(ca.key, hashes.SHA256())
    )
    return Issued(key, cert)


def save(issued: Issued, folder: Path, stem: str) -> None:
    """Write <stem>.crt (public) and <stem>.key (private, never committed) as PEM files."""
    folder.mkdir(parents=True, exist_ok=True)
    (folder / f"{stem}.crt").write_bytes(issued.cert.public_bytes(serialization.Encoding.PEM))
    key = issued.key.private_bytes(
        serialization.Encoding.PEM,
        serialization.PrivateFormat.PKCS8,
        serialization.NoEncryption(),
    )
    (folder / f"{stem}.key").write_bytes(key)


def load(folder: Path, stem: str) -> Issued:
    """Read back a key and certificate written by save() (Lab 87: issue more from one CA)."""
    key = serialization.load_pem_private_key((folder / f"{stem}.key").read_bytes(), password=None)
    cert = x509.load_pem_x509_certificate((folder / f"{stem}.crt").read_bytes())
    return Issued(key, cert)


def server_context(ca_file: str, cert_file: str, key_file: str) -> ssl.SSLContext:
    """A server that asks every caller for a certificate signed by our CA."""
    context = ssl.create_default_context(ssl.Purpose.CLIENT_AUTH, cafile=ca_file)
    context.load_cert_chain(cert_file, key_file)
    context.verify_mode = ssl.CERT_REQUIRED  # no client certificate, no connection
    return context


def client_context(ca_file: str, cert_file: str, key_file: str) -> ssl.SSLContext:
    """A caller that trusts only our CA and shows its own certificate."""
    context = ssl.create_default_context(cafile=ca_file)
    context.load_cert_chain(cert_file, key_file)
    return context

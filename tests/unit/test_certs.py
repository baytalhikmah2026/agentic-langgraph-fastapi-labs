"""Mutual TLS (Lab 74): our CA signs the certificates, and both sides must show one."""

import ssl
from pathlib import Path

import pytest
from cryptography.x509 import DNSName, ExtendedKeyUsage, SubjectAlternativeName
from cryptography.x509.oid import ExtendedKeyUsageOID

from sovereign_brain.security.certs import (
    client_context,
    issue,
    load,
    make_ca,
    save,
    server_context,
)


@pytest.fixture
def certs(tmp_path: Path) -> Path:
    """A fresh CA, a server certificate for "market" and a client certificate."""
    ca = make_ca()
    save(ca, tmp_path, "ca")
    save(issue(ca, "market", ["market", "127.0.0.1"], client=False), tmp_path, "market")
    save(issue(ca, "sb-api", ["sb-api"], client=True), tmp_path, "api-client")
    return tmp_path


def handshake(server: ssl.SSLContext, client: ssl.SSLContext, host: str) -> dict:
    """A TLS handshake in memory, no network; returns the client certificate the server saw."""
    s_in, s_out, c_in, c_out = (ssl.MemoryBIO() for _ in range(4))
    server_side = server.wrap_bio(s_in, s_out, server_side=True)
    client_side = client.wrap_bio(c_in, c_out, server_hostname=host)
    done = {"server": False, "client": False}
    for _ in range(10):
        for name, side in (("client", client_side), ("server", server_side)):
            if not done[name]:
                try:
                    side.do_handshake()
                    done[name] = True
                except ssl.SSLWantReadError:
                    pass
        s_in.write(c_out.read())
        c_in.write(s_out.read())
        if all(done.values()):
            return server_side.getpeercert()
    raise AssertionError("the handshake did not finish")


def test_the_ca_signs_with_the_right_purpose() -> None:
    ca = make_ca()
    server = issue(ca, "market", ["market"], client=False)

    server.cert.verify_directly_issued_by(ca.cert)  # raises if the signature is wrong
    purposes = server.cert.extensions.get_extension_for_class(ExtendedKeyUsage).value
    assert list(purposes) == [ExtendedKeyUsageOID.SERVER_AUTH]


def test_both_sides_prove_who_they_are(certs: Path) -> None:
    server = server_context(*(str(certs / f) for f in ("ca.crt", "market.crt", "market.key")))
    client = client_context(
        *(str(certs / f) for f in ("ca.crt", "api-client.crt", "api-client.key"))
    )

    seen = handshake(server, client, "market")

    assert ("commonName", "sb-api") in [pair for part in seen["subject"] for pair in part]


def test_a_caller_without_a_certificate_is_refused(certs: Path) -> None:
    server = server_context(*(str(certs / f) for f in ("ca.crt", "market.crt", "market.key")))
    anonymous = ssl.create_default_context(cafile=str(certs / "ca.crt"))  # trusts us, no ID

    with pytest.raises(ssl.SSLError):
        handshake(server, anonymous, "market")


def test_a_loaded_ca_keeps_issuing(certs: Path) -> None:
    """Lab 87: more certificates from the same CA, so the earlier ones stay valid."""
    ca = load(certs, "ca")
    save(issue(ca, "localhost", ["localhost", "desk.localhost"], client=False), certs, "desk")
    desk = load(certs, "desk")

    desk.cert.verify_directly_issued_by(ca.cert)  # raises if our CA didn't sign it
    names = desk.cert.extensions.get_extension_for_class(SubjectAlternativeName).value
    assert names.get_values_for_type(DNSName) == ["localhost", "desk.localhost"]

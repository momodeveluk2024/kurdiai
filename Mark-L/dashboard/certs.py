"""
Per-machine TLS certificate generation for the phone dashboard.

WHY THIS EXISTS
───────────────
The project previously SHIPPED a certificate in config/certs/, committed to the
repository. That certificate was issued on the original author's machine and its
SubjectAltName list was:

    DNS: localhost
    IP : 127.0.0.1, 192.168.1.107

Two serious consequences:

  1. IT ONLY WORKED ON ONE MACHINE. Browsers validate the address you typed
     against the certificate's SAN list. A user at 192.168.1.7 — or any address
     other than .107 — gets ERR_CERT_COMMON_NAME_INVALID, and Chrome commonly
     offers NO "Proceed anyway" option for an IP mismatch. The dashboard was
     simply unreachable for essentially every user.

  2. THE PRIVATE KEY WAS PUBLIC. Every install shared one key published in a
     public repo, so anyone could decrypt or impersonate any user's dashboard.

This module fixes both: the certificate is generated locally on first run, is
never committed, and is reissued automatically whenever the machine's LAN IP
changes (which happens routinely with DHCP).

The certificate is still self-signed, so the browser will warn once and the user
must accept it. That is inherent to LAN-only HTTPS without a public domain. The
warning is now at least *bypassable*, which it was not before.
"""
from __future__ import annotations

import datetime
import ipaddress
import socket
from pathlib import Path

try:
    from cryptography import x509
    from cryptography.hazmat.primitives import hashes, serialization
    from cryptography.hazmat.primitives.asymmetric import rsa
    from cryptography.x509.oid import NameOID
    _CRYPTO_OK = True
except ImportError:  # pragma: no cover - dashboard degrades to HTTP
    _CRYPTO_OK = False

CERT_NAME = "jarvis.crt"
KEY_NAME = "jarvis.key"
_VALID_DAYS = 3650


def _san_entries(ip: str) -> list:
    """Every name/address the dashboard might legitimately be reached by."""
    names: list = [x509.DNSName("localhost")]
    addresses = {"127.0.0.1", ip}

    try:
        hostname = socket.gethostname()
        if hostname:
            names.append(x509.DNSName(hostname))
            names.append(x509.DNSName(f"{hostname}.local"))
    except Exception:
        pass

    # Cover every local interface, so the cert still validates if the user
    # reaches the box over a different adapter (Wi-Fi vs Ethernet vs VPN).
    try:
        for info in socket.getaddrinfo(socket.gethostname(), None, socket.AF_INET):
            addresses.add(info[4][0])
    except Exception:
        pass

    for addr in sorted(addresses):
        try:
            names.append(x509.IPAddress(ipaddress.ip_address(addr)))
        except ValueError:
            continue
    return names


def cert_covers_ip(cert_path: Path, ip: str) -> bool:
    """
    True if an existing certificate is valid for this address and not expired.

    This is the check that makes DHCP survivable: when the router hands the
    machine a new address, the old certificate silently stops matching and the
    dashboard becomes unreachable with a confusing browser error. Detecting it
    here means we simply reissue instead.
    """
    if not _CRYPTO_OK or not cert_path.exists():
        return False
    try:
        cert = x509.load_pem_x509_certificate(cert_path.read_bytes())
    except Exception:
        return False

    now = datetime.datetime.now(datetime.timezone.utc)
    try:
        if not (cert.not_valid_before_utc <= now <= cert.not_valid_after_utc):
            return False
    except AttributeError:  # older cryptography
        if not (cert.not_valid_before <= now.replace(tzinfo=None) <= cert.not_valid_after):
            return False

    try:
        san = cert.extensions.get_extension_for_class(
            x509.SubjectAlternativeName
        ).value
    except x509.ExtensionNotFound:
        # No SAN at all — modern browsers reject these outright regardless of CN.
        return False

    covered = {str(a) for a in san.get_values_for_type(x509.IPAddress)}
    return ip in covered


def ensure_cert(certs_dir: Path, ip: str) -> bool:
    """
    Guarantee a certificate valid for `ip` exists in `certs_dir`.

    Returns True if TLS is available (existing valid cert, or one just created),
    False if cryptography is unavailable and the caller should fall back to HTTP.
    Never raises — a dashboard on plain HTTP beats an assistant that won't start.
    """
    if not _CRYPTO_OK:
        print("[Dashboard] 'cryptography' not installed — serving over HTTP.")
        return False

    cert_path = certs_dir / CERT_NAME
    key_path = certs_dir / KEY_NAME

    if cert_path.exists() and key_path.exists() and cert_covers_ip(cert_path, ip):
        return True

    reason = "no certificate found"
    if cert_path.exists():
        reason = f"existing certificate is not valid for {ip}"

    print(f"[Dashboard] {reason} — generating a new one for this machine...")

    try:
        certs_dir.mkdir(parents=True, exist_ok=True)
        key = rsa.generate_private_key(public_exponent=65537, key_size=2048)

        subject = issuer = x509.Name([
            x509.NameAttribute(NameOID.ORGANIZATION_NAME, "Kurd AI"),
            x509.NameAttribute(NameOID.COMMON_NAME, ip),
        ])
        now = datetime.datetime.now(datetime.timezone.utc)

        cert = (
            x509.CertificateBuilder()
            .subject_name(subject)
            .issuer_name(issuer)
            .public_key(key.public_key())
            .serial_number(x509.random_serial_number())
            .not_valid_before(now - datetime.timedelta(minutes=5))  # tolerate clock skew
            .not_valid_after(now + datetime.timedelta(days=_VALID_DAYS))
            .add_extension(x509.SubjectAlternativeName(_san_entries(ip)), critical=False)
            .add_extension(x509.BasicConstraints(ca=True, path_length=None), critical=True)
            .sign(key, hashes.SHA256())
        )

        key_path.write_bytes(key.private_bytes(
            encoding=serialization.Encoding.PEM,
            format=serialization.PrivateFormat.TraditionalOpenSSL,
            encryption_algorithm=serialization.NoEncryption(),
        ))
        cert_path.write_bytes(cert.public_bytes(serialization.Encoding.PEM))

        print(f"[Dashboard] Certificate issued for {ip} (valid {_VALID_DAYS} days).")
        return True

    except Exception as e:
        print(f"[Dashboard] Certificate generation failed ({e}) — serving over HTTP.")
        return False


if __name__ == "__main__":
    from pprint import pprint
    here = Path(__file__).resolve().parent.parent / "config" / "certs"
    test_ip = socket.gethostbyname(socket.gethostname())
    print(f"local ip: {test_ip}")
    print(f"cert ok : {ensure_cert(here, test_ip)}")
    c = x509.load_pem_x509_certificate((here / CERT_NAME).read_bytes())
    san = c.extensions.get_extension_for_class(x509.SubjectAlternativeName).value
    pprint({
        "subject": c.subject.rfc4514_string(),
        "dns": san.get_values_for_type(x509.DNSName),
        "ip": [str(i) for i in san.get_values_for_type(x509.IPAddress)],
    })

#
# tofusoup/common/crypto_utils.py
#
"""
Cryptographic utilities for TofuSoup, primarily for generating
certificates for mTLS testing.
"""

import datetime
from pathlib import Path

from cryptography import x509
from cryptography.hazmat.backends import default_backend
from cryptography.hazmat.primitives import hashes, serialization
from cryptography.hazmat.primitives.asymmetric import ec, rsa
from provide.foundation import logger

# --- Constants ---
DEFAULT_CERT_VALIDITY_DAYS = 7
DEFAULT_RSA_KEY_SIZE = 2048
DEFAULT_PUBLIC_EXPONENT = 65537

SUPPORTED_CURVES = {
    "secp256r1": ec.SECP256R1(),
    "secp384r1": ec.SECP384R1(),
    "secp521r1": ec.SECP521R1(),
}


def generate_private_key(
    key_type: str = "ecdsa", curve_name: str = "secp384r1"
) -> tuple[ec.EllipticCurvePrivateKey | rsa.RSAPrivateKey, str]:
    """
    Generates a private key.

    Args:
        key_type: "ecdsa" or "rsa".
        curve_name: Name of the ECDSA curve to use (if key_type is "ecdsa").

    Returns:
        A tuple of (private_key_object, key_description_string).
    """
    if key_type.lower() == "ecdsa":
        curve = SUPPORTED_CURVES.get(curve_name.lower())
        if not curve:
            raise ValueError(
                f"Unsupported ECDSA curve: {curve_name}. Supported: {list(SUPPORTED_CURVES.keys())}"
            )
        private_key = ec.generate_private_key(curve, default_backend())
        desc = f"ECDSA-{curve_name}"
        return private_key, desc
    elif key_type.lower() == "rsa":
        private_key = rsa.generate_private_key(
            public_exponent=DEFAULT_PUBLIC_EXPONENT,
            key_size=DEFAULT_RSA_KEY_SIZE,
            backend=default_backend(),
        )
        desc = f"RSA-{DEFAULT_RSA_KEY_SIZE}"
        return private_key, desc
    else:
        raise ValueError(f"Unsupported key_type: {key_type}. Must be 'ecdsa' or 'rsa'.")


def create_self_signed_ca(
    common_name: str = "TofuSoup Test Root CA",
    key_type: str = "ecdsa",
    curve_name: str = "secp384r1",
) -> tuple[x509.Certificate, ec.EllipticCurvePrivateKey | rsa.RSAPrivateKey, str]:
    """
    Creates a self-signed Root CA certificate and its private key.

    Returns:
        (ca_certificate, ca_private_key, key_description)
    """
    ca_private_key, key_desc = generate_private_key(key_type, curve_name)
    subject = issuer = x509.Name([x509.NameAttribute(x509.oid.NameOID.COMMON_NAME, common_name)])

    builder = (
        x509.CertificateBuilder()
        .subject_name(subject)
        .issuer_name(issuer)
        .public_key(ca_private_key.public_key())
        .serial_number(x509.random_serial_number())
        .not_valid_before(datetime.datetime.now(datetime.UTC) - datetime.timedelta(days=1))
        .not_valid_after(
            datetime.datetime.now(datetime.UTC) + datetime.timedelta(days=DEFAULT_CERT_VALIDITY_DAYS)
        )
        .add_extension(x509.BasicConstraints(ca=True, path_length=None), critical=True)
        .add_extension(
            x509.KeyUsage(
                digital_signature=True,
                content_commitment=False,
                key_encipherment=False,
                data_encipherment=False,
                key_agreement=False,
                key_cert_sign=True,
                crl_sign=True,
                encipher_only=False,
                decipher_only=False,
            ),
            critical=True,
        )
        .add_extension(
            x509.SubjectKeyIdentifier.from_public_key(ca_private_key.public_key()),
            critical=False,
        )
    )

    ca_certificate = builder.sign(ca_private_key, hashes.SHA256(), default_backend())
    logger.debug(f"Generated Root CA: {common_name} ({key_desc})")
    return ca_certificate, ca_private_key, key_desc


def create_signed_certificate(
    common_name: str,
    ca_certificate: x509.Certificate,
    ca_private_key: ec.EllipticCurvePrivateKey | rsa.RSAPrivateKey,
    is_server_cert: bool,
    key_type: str = "ecdsa",
    curve_name: str = "secp384r1",
    dns_names: list[str] | None = None,
) -> tuple[x509.Certificate, ec.EllipticCurvePrivateKey | rsa.RSAPrivateKey, str]:
    """
    Creates a certificate signed by the provided CA.

    Args:
        common_name: Common Name for the certificate.
        ca_certificate: The CA's x509.Certificate object.
        ca_private_key: The CA's private key object.
        is_server_cert: Boolean, True if this is a server certificate, False for client.
        key_type: "ecdsa" or "rsa" for the new certificate's key.
        curve_name: ECDSA curve name if key_type is "ecdsa".
        dns_names: Optional list of DNS names for SubjectAlternativeName extension.

    Returns:
        (certificate, private_key, key_description)
    """
    private_key, key_desc = generate_private_key(key_type, curve_name)
    subject = x509.Name([x509.NameAttribute(x509.oid.NameOID.COMMON_NAME, common_name)])

    builder = (
        x509.CertificateBuilder()
        .subject_name(subject)
        .issuer_name(ca_certificate.subject)
        .public_key(private_key.public_key())
        .serial_number(x509.random_serial_number())
        .not_valid_before(datetime.datetime.now(datetime.UTC) - datetime.timedelta(days=1))
        .not_valid_after(
            datetime.datetime.now(datetime.UTC) + datetime.timedelta(days=DEFAULT_CERT_VALIDITY_DAYS)
        )
        .add_extension(x509.BasicConstraints(ca=False, path_length=None), critical=True)
    )

    if is_server_cert:
        builder = builder.add_extension(
            x509.KeyUsage(
                digital_signature=True,
                content_commitment=False,
                key_encipherment=True,
                data_encipherment=False,
                key_agreement=False,
                key_cert_sign=False,
                crl_sign=False,
                encipher_only=False,
                decipher_only=False,
            ),
            critical=True,
        )
        builder = builder.add_extension(
            x509.ExtendedKeyUsage([x509.oid.ExtendedKeyUsageOID.SERVER_AUTH]),
            critical=False,
        )
    else:
        builder = builder.add_extension(
            x509.KeyUsage(
                digital_signature=True,
                content_commitment=False,
                key_encipherment=False,
                data_encipherment=False,
                key_agreement=True,
                key_cert_sign=False,
                crl_sign=False,
                encipher_only=False,
                decipher_only=False,
            ),
            critical=True,
        )
        builder = builder.add_extension(
            x509.ExtendedKeyUsage([x509.oid.ExtendedKeyUsageOID.CLIENT_AUTH]),
            critical=False,
        )

    if dns_names:
        san_entries = [x509.DNSName(name) for name in dns_names]
        builder = builder.add_extension(x509.SubjectAlternativeName(san_entries), critical=False)

    builder = builder.add_extension(
        x509.AuthorityKeyIdentifier.from_issuer_public_key(ca_certificate.public_key()),
        critical=False,
    )
    builder = builder.add_extension(
        x509.SubjectKeyIdentifier.from_public_key(private_key.public_key()),
        critical=False,
    )

    certificate = builder.sign(ca_private_key, hashes.SHA256(), default_backend())
    cert_type_str = "Server" if is_server_cert else "Client"
    logger.debug(
        f"Generated {cert_type_str} Certificate: {common_name} ({key_desc}), signed by {ca_certificate.subject.rfc4514_string()}"
    )
    return certificate, private_key, key_desc


def save_key_and_cert_to_files(
    private_key: ec.EllipticCurvePrivateKey | rsa.RSAPrivateKey,
    certificate: x509.Certificate,
    key_filename: Path,
    cert_filename: Path,
    password: bytes | None = None,
) -> None:
    """Saves a private key and certificate to PEM-encoded files."""
    key_pem = private_key.private_bytes(
        encoding=serialization.Encoding.PEM,
        format=serialization.PrivateFormat.PKCS8,
        encryption_algorithm=(
            serialization.BestAvailableEncryption(password) if password else serialization.NoEncryption()
        ),
    )
    with open(key_filename, "wb") as f:
        f.write(key_pem)
    logger.debug(f"Saved private key to {key_filename} (Encrypted: {password is not None})")

    cert_pem = certificate.public_bytes(serialization.Encoding.PEM)
    with open(cert_filename, "wb") as f:
        f.write(cert_pem)
    logger.debug(f"Saved certificate to {cert_filename}")


def generate_cert_bundle_for_mtls(
    temp_dir: Path,
    curve_name: str = "secp384r1",
    ca_common_name: str = "TofuSoup Test CA",
    server_common_name: str = "localhost",
    client_common_name: str = "TofuSoup Test Client",
    server_dns_names: list[str] | None = None,
) -> dict[str, str]:
    """
    Generates a full set of CA, server, and client certs/keys for mTLS,
    saves them to files in temp_dir, and returns a dictionary of their paths.

    Args:
        temp_dir: Path object to a directory where certs/keys will be saved.
        curve_name: The ECDSA curve to use (e.g., "secp384r1").
        ... other CNs and DNS names ...

    Returns:
        A dictionary mapping component name to file path string:
        {
            "ca_cert": "/path/to/ca.pem",
            "server_cert": "/path/to/server.pem",
            "server_key": "/path/to/server.key",
            "client_cert": "/path/to/client.pem",
            "client_key": "/path/to/client.key"
        }
    """
    if server_dns_names is None:
        server_dns_names = ["localhost", "127.0.0.1"]

    ca_cert, ca_key, _ = create_self_signed_ca(
        common_name=ca_common_name, key_type="ecdsa", curve_name=curve_name
    )
    ca_cert_path = temp_dir / "ca.pem"
    with open(ca_cert_path, "wb") as f:
        f.write(ca_cert.public_bytes(serialization.Encoding.PEM))
    logger.debug(f"Saved Root CA certificate to {ca_cert_path}")

    server_cert, server_key, _ = create_signed_certificate(
        common_name=server_common_name,
        ca_certificate=ca_cert,
        ca_private_key=ca_key,
        is_server_cert=True,
        key_type="ecdsa",
        curve_name=curve_name,
        dns_names=server_dns_names,
    )
    server_cert_path = temp_dir / "server.pem"
    server_key_path = temp_dir / "server.key"
    save_key_and_cert_to_files(server_key, server_cert, server_key_path, server_cert_path)

    client_cert, client_key, _ = create_signed_certificate(
        common_name=client_common_name,
        ca_certificate=ca_cert,
        ca_private_key=ca_key,
        is_server_cert=False,
        key_type="ecdsa",
        curve_name=curve_name,
    )
    client_cert_path = temp_dir / "client.pem"
    client_key_path = temp_dir / "client.key"
    save_key_and_cert_to_files(client_key, client_cert, client_key_path, client_cert_path)

    return {
        "ca_cert": str(ca_cert_path.resolve()),
        "server_cert": str(server_cert_path.resolve()),
        "server_key": str(server_key_path.resolve()),
        "client_cert": str(client_cert_path.resolve()),
        "client_key": str(client_key_path.resolve()),
    }


if __name__ == "__main__":
    # Example Usage (for manual testing of this module)
    logger.info("Testing crypto utilities...")
    temp_test_dir = Path("./temp_certs")
    temp_test_dir.mkdir(exist_ok=True)

    logger.info("--- Generating SECP384R1 Cert Bundle ---")
    paths_384 = generate_cert_bundle_for_mtls(temp_test_dir, curve_name="secp384r1")
    logger.info(f"SECP384R1 Certs generated: {paths_384}")

    logger.info("--- Generating SECP521R1 Cert Bundle ---")
    paths_521 = generate_cert_bundle_for_mtls(
        temp_test_dir, curve_name="secp521r1", ca_common_name="TofuSoup P521 CA"
    )
    logger.info(f"SECP521R1 Certs generated: {paths_521}")

    logger.info(f"Test certificates saved in ./{temp_test_dir.name}/")
    # To clean up: shutil.rmtree(temp_test_dir)
# I've added functions for:
# *   `generate_private_key`: Creates ECDSA (with specified curve) or RSA private keys.
# *   `create_self_signed_ca`: Generates a root CA certificate and key.
# *   `create_signed_certificate`: Generates server or client certificates signed by a given CA.
# *   `save_key_and_cert_to_files`: Saves keys and certs to PEM files.
# *   `generate_cert_bundle_for_mtls`: Orchestrates the generation of a full set of CA, server, and client certs/keys for a given curve, saves them to a temporary directory, and returns a dictionary of their paths.
#
# This module now provides the core utilities needed for the pytest fixtures.
# I also added a `if __name__ == "__main__":` block for basic manual testing of these functions.

# <3 🍲 🍜 🍥>


# 🍲🥄🛠️🪄

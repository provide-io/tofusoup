#
# SPDX-FileCopyrightText: Copyright (c) 2025 provide.io llc. All rights reserved.
# SPDX-License-Identifier: Apache-2.0
#

"""Certificate Management for RPC K/V Matrix Testing

Leverages the existing pyvider-rpcplugin certificate system for generating
certificates for all crypto configurations:
- RSA 2048/4096 bit keys
- EC secp256r1/secp384r1/secp521r1 curves
- CA, server, and client certificates for mTLS"""

import contextlib
from pathlib import Path

from provide.foundation import logger
from provide.foundation.crypto import Certificate

from .matrix_config import CryptoConfig


class CertificateManager:
    """Manages certificate generation for RPC K/V matrix testing using pyvider-rpcplugin."""

    def __init__(self, work_dir: Path) -> None:
        self.work_dir = work_dir
        self.cert_dir = work_dir / "certs"
        self.cert_dir.mkdir(exist_ok=True, parents=True)

    def generate_crypto_material(self, crypto_config: CryptoConfig) -> dict[str, Path]:
        """
        Generate complete certificate chain based on crypto configuration.

        Uses pyvider-rpcplugin's Certificate class to generate:
        - ca_cert, ca_key: Certificate Authority
        - server_cert, server_key: Server certificate
        - client_cert, client_key: Client certificate

        Returns dict with paths to certificate files.
        """

        # Check if certificates already exist
        cert_files = self._get_cert_file_paths(crypto_config.name)
        if all(path.exists() for path in cert_files.values()):
            logger.debug(f"Using existing certificates for {crypto_config.name}")
            return cert_files

        logger.info(f"Generating certificates for {crypto_config.name}")

        # Convert crypto config to pyvider-rpcplugin format
        key_type, key_param = self._convert_crypto_config(crypto_config)

        # Generate CA certificate (self-signed)
        ca_cert = Certificate.create_ca(
            common_name="TofuSoup Test CA",
            organization_name="TofuSoup Matrix Testing",
            validity_days=30,
            key_type=key_type,
            key_size=key_param if key_type == "rsa" else 2048,
            ecdsa_curve=key_param if key_type == "ecdsa" else "secp384r1",
        )

        # Generate server certificate signed by CA
        server_cert = Certificate.create_signed_certificate(
            ca_certificate=ca_cert,
            common_name="localhost",
            organization_name="TofuSoup Test Server",
            validity_days=30,
            alt_names=["localhost", "127.0.0.1", "::1", "::"],
            key_type=key_type,
            key_size=key_param if key_type == "rsa" else 2048,
            ecdsa_curve=key_param if key_type == "ecdsa" else "secp384r1",
            is_client_cert=False,
        )

        # Generate client certificate signed by CA
        client_cert = Certificate.create_signed_certificate(
            ca_certificate=ca_cert,
            common_name="TofuSoup Test Client",
            organization_name="TofuSoup Test Client",
            validity_days=30,
            key_type=key_type,
            key_size=key_param if key_type == "rsa" else 2048,
            ecdsa_curve=key_param if key_type == "ecdsa" else "secp384r1",
            is_client_cert=True,
        )

        # Write certificates to files
        return self._write_cert_files(
            {"ca": ca_cert, "server": server_cert, "client": client_cert}, crypto_config.name
        )

    def _convert_crypto_config(self, crypto_config: CryptoConfig) -> tuple[str, int | str]:
        """Convert CryptoConfig to pyvider-rpcplugin certificate parameters."""

        if crypto_config.key_type == "rsa":
            return "rsa", crypto_config.key_size
        elif crypto_config.key_type == "ec":
            # Map EC key sizes to curve names expected by pyvider-rpcplugin
            curve_map = {256: "secp256r1", 384: "secp384r1", 521: "secp521r1"}
            curve_name = curve_map.get(crypto_config.key_size)
            if not curve_name:
                raise ValueError(f"Unsupported EC key size: {crypto_config.key_size}")
            return "ecdsa", curve_name
        else:
            raise ValueError(f"Unsupported key type: {crypto_config.key_type}")

    def _get_cert_file_paths(self, config_name: str) -> dict[str, Path]:
        """Get file paths for all certificates for a config."""
        return {
            "ca_cert": self.cert_dir / f"{config_name}_ca_cert.pem",
            "ca_key": self.cert_dir / f"{config_name}_ca_key.pem",
            "server_cert": self.cert_dir / f"{config_name}_server_cert.pem",
            "server_key": self.cert_dir / f"{config_name}_server_key.pem",
            "client_cert": self.cert_dir / f"{config_name}_client_cert.pem",
            "client_key": self.cert_dir / f"{config_name}_client_key.pem",
        }

    def _write_cert_files(self, cert_objects: dict[str, Certificate], config_name: str) -> dict[str, Path]:
        """Write Certificate objects to PEM files."""

        cert_files = self._get_cert_file_paths(config_name)

        for cert_type, cert_obj in cert_objects.items():
            # Write certificate
            cert_file = cert_files[f"{cert_type}_cert"]
            with cert_file.open("w") as f:
                f.write(cert_obj.cert_pem)
            cert_file.chmod(0o644)

            # Write private key
            key_file = cert_files[f"{cert_type}_key"]
            with key_file.open("w") as f:
                f.write(cert_obj.key_pem)
            key_file.chmod(0o600)

        logger.info(f"Generated certificates for {config_name} in {self.cert_dir}")
        return cert_files

    def cleanup_certificates(self, config_name: str | None = None) -> None:
        """Remove generated certificates."""
        if config_name:
            # Remove certificates for specific configuration
            cert_files = self._get_cert_file_paths(config_name)
            for file_path in cert_files.values():
                if file_path.exists():
                    file_path.unlink()
        else:
            # Remove all certificates
            for cert_file in self.cert_dir.glob("*.pem"):
                cert_file.unlink()

            # Remove cert directory if empty
            with contextlib.suppress(OSError):
                self.cert_dir.rmdir()


def generate_all_test_certificates(work_dir: Path) -> dict[str, dict[str, Path]]:
    """
    Generate certificates for all crypto configurations.

    Returns nested dict: {config_name: {cert_type: file_path}}
    """
    from .matrix_config import RPC_KV_CRYPTO_CONFIGS

    cert_manager = CertificateManager(work_dir)
    all_certs = {}

    for crypto_config in RPC_KV_CRYPTO_CONFIGS:
        all_certs[crypto_config.name] = cert_manager.generate_crypto_material(crypto_config)

    return all_certs


if __name__ == "__main__":
    # Test certificate generation
    import tempfile

    with tempfile.TemporaryDirectory() as tmp_dir:
        test_dir = Path(tmp_dir)
        print(f"Testing certificate generation in {test_dir}")

        all_certs = generate_all_test_certificates(test_dir)

        print(f"Generated certificates for {len(all_certs)} configurations:")
        for config_name, cert_files in all_certs.items():
            print(f"  {config_name}:")
            for cert_type, file_path in cert_files.items():
                file_size = file_path.stat().st_size
                print(f"    {cert_type}: {file_path.name} ({file_size} bytes)")

# 🥣🔬🔚

#
# SPDX-FileCopyrightText: Copyright (c) 2025 provide.io llc. All rights reserved.
# SPDX-License-Identifier: Apache-2.0
#

"""RPC K/V Matrix Testing Configuration

Defines the parameter matrix for testing all combinations of:
- Client languages: go, pyvider
- Server languages: go, pyvider
- Crypto configurations: auto_mtls with RSA 2048/4096, EC 256/384/521"""

from dataclasses import dataclass
from typing import Any

import pytest


@dataclass
class CryptoConfig:
    """Configuration for cryptographic parameters in RPC testing."""

    name: str
    key_type: str  # "rsa" or "ec"
    key_size: int  # RSA: 2048/4096, EC: 256/384/521
    auth_mode: str = "auto"  # Python CLI uses "auto" not "auto_mtls"

    def to_go_cli_args(self) -> list[str]:
        """Convert to CLI arguments for Go harness."""
        args = ["--tls-mode", "auto"]

        if self.key_type == "rsa":
            # RSA uses native go-plugin AutoMTLS (P-521)
            args.extend(["--tls-key-type", "rsa", "--tls-curve", "auto"])
        elif self.key_type == "ec":
            args.extend(["--tls-key-type", "ec"])
            # Map key sizes to curve names - use custom TLSProvider
            curve_map = {256: "secp256r1", 384: "secp384r1", 521: "secp521r1"}
            curve = curve_map.get(self.key_size, "secp384r1")
            args.extend(["--tls-curve", curve])

        return args


# Define all crypto configurations to test
RPC_KV_CRYPTO_CONFIGS = [
    CryptoConfig("rsa_2048", "rsa", 2048),
    CryptoConfig("rsa_4096", "rsa", 4096),
    CryptoConfig("ec_256", "ec", 256),
    CryptoConfig("ec_384", "ec", 384),
    CryptoConfig("ec_521", "ec", 521),
]

# Define language combinations
CLIENT_LANGUAGES = ["go", "pyvider"]
SERVER_LANGUAGES = ["go", "pyvider"]

# Generate all parameter combinations for pytest
RPC_KV_MATRIX_PARAMS = [
    pytest.param(
        client_lang, server_lang, crypto_config, id=f"{client_lang}_{server_lang}_{crypto_config.name}"
    )
    for client_lang in CLIENT_LANGUAGES
    for server_lang in SERVER_LANGUAGES
    for crypto_config in RPC_KV_CRYPTO_CONFIGS
]

# Total combinations: 2 client langs x 2 server langs x 5 crypto configs = 20 tests


def get_matrix_summary() -> dict[str, Any]:
    """Get summary information about the test matrix."""
    return {
        "total_combinations": len(RPC_KV_MATRIX_PARAMS),
        "client_languages": CLIENT_LANGUAGES,
        "server_languages": SERVER_LANGUAGES,
        "crypto_configs": [config.name for config in RPC_KV_CRYPTO_CONFIGS],
        "auth_modes": ["auto"],  # Only testing auto (auto-mTLS) mode
    }


if __name__ == "__main__":
    # Print matrix summary for verification
    summary = get_matrix_summary()
    print("RPC K/V Test Matrix Summary:")
    print(f"Total test combinations: {summary['total_combinations']}")
    print(f"Client languages: {summary['client_languages']}")
    print(f"Server languages: {summary['server_languages']}")
    print(f"Crypto configurations: {summary['crypto_configs']}")

    print("\nAll test combinations:")
    for i, param in enumerate(RPC_KV_MATRIX_PARAMS, 1):
        client, server, crypto = param.values
        print(f"{i:2d}. {param.id}")

# 🥣🔬🔚

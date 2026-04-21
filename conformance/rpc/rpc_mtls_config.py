#
# SPDX-FileCopyrightText: Copyright (c) 2025 provide.io llc. All rights reserved.
# SPDX-License-Identifier: Apache-2.0
#

"""RPC Test Configuration Matrix for Cross-Language mTLS Testing

This module defines the comprehensive test matrix for validating RPC communication
between Python and Go clients/servers with various mTLS configurations."""

from dataclasses import dataclass
from typing import Any

import pytest


@dataclass
class MTLSConfig:
    """Configuration for mTLS testing"""

    name: str
    mode: str  # "insecure", "auto_mtls", "manual_mtls"
    key_type: str = "ecdsa"  # "ecdsa" or "rsa"
    curve: str = "secp256r1"  # "secp256r1", "secp384r1", "secp521r1"
    rsa_bits: int = 2048
    expected_result: str = "success"  # "success", "failure", "timeout"
    expected_error: str | None = None
    timeout_seconds: int = 30


# Comprehensive test matrix covering all combinations
RPC_TEST_MATRIX = [
    # Insecure mode (baseline)
    MTLSConfig(name="insecure", mode="insecure", expected_result="success"),
    # Auto mTLS with different curves
    MTLSConfig(name="auto_mtls_secp256r1", mode="auto_mtls", curve="secp256r1", expected_result="success"),
    MTLSConfig(name="auto_mtls_secp384r1", mode="auto_mtls", curve="secp384r1", expected_result="success"),
    MTLSConfig(
        name="auto_mtls_secp521r1",
        mode="auto_mtls",
        curve="secp521r1",
        expected_result="failure",  # Known issue with grpcio + secp521r1
        expected_error="certificate verification failed",
    ),
    # RSA variants
    MTLSConfig(
        name="auto_mtls_rsa_2048", mode="auto_mtls", key_type="rsa", rsa_bits=2048, expected_result="success"
    ),
    MTLSConfig(
        name="auto_mtls_rsa_4096", mode="auto_mtls", key_type="rsa", rsa_bits=4096, expected_result="success"
    ),
    # Manual mTLS (when certificates are pre-generated)
    MTLSConfig(name="manual_mtls_secp256r1", mode="manual_mtls", curve="secp256r1", expected_result="success"),
    MTLSConfig(name="manual_mtls_secp384r1", mode="manual_mtls", curve="secp384r1", expected_result="success"),
    # Edge cases for stress testing
    MTLSConfig(
        name="auto_mtls_secp521r1_long_timeout",
        mode="auto_mtls",
        curve="secp521r1",
        expected_result="timeout",
        timeout_seconds=10,  # Shorter timeout to catch hangs
    ),
]


@dataclass
class ClientServerPair:
    """Defines a client-server language combination"""

    name: str
    client_type: str  # "python", "go"
    server_type: str  # "python", "go"


# All client-server combinations
CLIENT_SERVER_PAIRS = [
    ClientServerPair("py_client_go_server", "python", "go"),
    ClientServerPair("py_client_py_server", "python", "python"),
    ClientServerPair("go_client_py_server", "go", "python"),
    ClientServerPair("go_client_go_server", "go", "go"),
]


def get_go_server_args(config: MTLSConfig) -> list[str]:
    """Generate Go server command line arguments for given config"""
    args = []

    if config.mode == "insecure":
        args.append("--auto-mtls=false")
    elif config.mode == "auto_mtls":
        args.extend(
            [
                "--auto-mtls=true",
                f"--key-type={config.key_type}",
                f"--curve={config.curve}",
                f"--rsa-bits={config.rsa_bits}",
            ]
        )
    elif config.mode == "manual_mtls":
        # Manual mTLS args would be added by test fixtures
        args.append("--auto-mtls=false")

    # Always add log level for debugging
    args.append("--log-level=debug")
    return args


def get_python_client_args(config: MTLSConfig) -> dict[str, Any]:
    """Generate Python KVClient constructor arguments for given config"""
    args = {
        "enable_mtls": config.mode in ["auto_mtls", "manual_mtls"],
        "cert_algo": config.key_type,
        "cert_curve": config.curve,
        "cert_bits": config.rsa_bits if config.key_type == "rsa" else None,
    }
    return args


def get_go_client_args(config: MTLSConfig) -> list[str]:
    """Generate Go client command line arguments for given config"""
    args = []

    if config.mode == "insecure":
        # No special args needed for insecure
        pass
    elif config.mode == "auto_mtls":
        args.extend(
            [
                "--auto-mtls",
                f"--server-key-type={config.key_type}",
                f"--server-curve={config.curve}",
                f"--server-rsa-bits={config.rsa_bits}",
            ]
        )
    elif config.mode == "manual_mtls":
        # Manual mTLS paths would be added by test fixtures
        args.append("--manual-mtls")

    return args


def should_test_combination(client_server: ClientServerPair, mtls_config: MTLSConfig) -> bool:
    """
    Determine if a specific client-server + mTLS combination should be tested
    Some combinations are known to be problematic or redundant
    """
    # Skip Python client with secp521r1 auto-mTLS (known grpcio issue)
    if (
        client_server.client_type == "python"
        and mtls_config.curve == "secp521r1"
        and mtls_config.mode == "auto_mtls"
    ):
        return False

    # Skip manual mTLS for now (requires certificate fixtures)
    return mtls_config.mode != "manual_mtls"


# Generate pytest parameters for the full test matrix
def generate_test_parameters() -> list[Any]:
    """Generate pytest.mark.parametrize parameters for the full test matrix"""
    parameters = []

    for client_server in CLIENT_SERVER_PAIRS:
        for mtls_config in RPC_TEST_MATRIX:
            if should_test_combination(client_server, mtls_config):
                # Create test ID
                test_id = f"{client_server.name}_{mtls_config.name}"

                parameters.append(pytest.param(client_server, mtls_config, id=test_id))

    return parameters


# Stress test parameters - more aggressive configurations
STRESS_TEST_CONFIGS = [
    MTLSConfig(name="stress_rapid_reconnect", mode="auto_mtls", curve="secp256r1", timeout_seconds=5),
    MTLSConfig(
        name="stress_large_rsa",
        mode="auto_mtls",
        key_type="rsa",
        rsa_bits=8192,
        timeout_seconds=60,  # Larger keys take longer
        expected_result="success",
    ),
]

# 🥣🔬🔚

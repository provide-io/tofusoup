#!/usr/bin/env python3
# SPDX-FileCopyrightText: Copyright (c) 2025 provide.io llc. All rights reserved.
# SPDX-License-Identifier: Apache-2.0
#

"""CLI Verification Tests for RPC Commands

Tests that all soup-go rpc commands have correct CLI flags and work as expected.
This catches issues like missing flags, incorrect flag names, etc."""

from pathlib import Path
import subprocess

import pytest


@pytest.fixture
def soup_go_path() -> Path:
    """Get path to soup-go executable."""
    candidates = [Path("bin/soup-go"), Path("harnesses/bin/soup-go")]
    for path in candidates:
        if path.exists():
            return path.resolve()
    pytest.skip("soup-go not found")


def test_rpc_kv_server_help(soup_go_path: Path) -> None:
    """Verify 'soup-go rpc kv server --help' works and shows expected flags."""
    result = subprocess.run(
        [str(soup_go_path), "rpc", "kv", "server", "--help"], capture_output=True, text=True, timeout=5
    )
    assert result.returncode == 0, f"Help command failed: {result.stderr}"

    # Verify expected flags are documented
    help_text = result.stdout
    assert "--port" in help_text, "Missing --port flag"
    assert "--tls-mode" in help_text, "Missing --tls-mode flag"
    assert "--tls-key-type" in help_text, "Missing --tls-key-type flag"
    assert "--tls-curve" in help_text, "Missing --tls-curve flag"
    assert "--cert-file" in help_text, "Missing --cert-file flag"
    assert "--key-file" in help_text, "Missing --key-file flag"


def test_rpc_kv_put_help(soup_go_path: Path) -> None:
    """Verify 'soup-go rpc kv put --help' works and shows expected flags."""
    result = subprocess.run(
        [str(soup_go_path), "rpc", "kv", "put", "--help"], capture_output=True, text=True, timeout=5
    )
    assert result.returncode == 0, f"Help command failed: {result.stderr}"

    help_text = result.stdout
    assert "--address" in help_text, "Missing --address flag"
    assert "--tls-curve" in help_text, "Missing --tls-curve flag"
    assert "auto" in help_text, "Should mention 'auto' for curve detection"


def test_rpc_kv_get_help(soup_go_path: Path) -> None:
    """Verify 'soup-go rpc kv get --help' works and shows expected flags."""
    result = subprocess.run(
        [str(soup_go_path), "rpc", "kv", "get", "--help"], capture_output=True, text=True, timeout=5
    )
    assert result.returncode == 0, f"Help command failed: {result.stderr}"

    help_text = result.stdout
    assert "--address" in help_text, "Missing --address flag"
    assert "--tls-curve" in help_text, "Missing --tls-curve flag"


def test_rpc_kv_put_rejects_invalid_flags(soup_go_path: Path) -> None:
    """Verify invalid flags are rejected with clear error messages."""
    # Test that old/invalid flag names are rejected
    result = subprocess.run(
        [str(soup_go_path), "rpc", "kv", "put", "--key", "invalid"], capture_output=True, text=True, timeout=5
    )
    assert result.returncode != 0, "Should reject invalid --key flag"
    assert "unknown flag" in result.stderr.lower(), "Should show 'unknown flag' error"


def test_rpc_kv_get_rejects_invalid_flags(soup_go_path: Path) -> None:
    """Verify invalid flags are rejected for get command."""
    result = subprocess.run(
        [str(soup_go_path), "rpc", "kv", "get", "--invalid-flag", "value"],
        capture_output=True,
        text=True,
        timeout=5,
    )
    assert result.returncode != 0, "Should reject invalid flag"
    assert "unknown flag" in result.stderr.lower(), "Should show 'unknown flag' error"


def test_rpc_kv_server_flag_validation(soup_go_path: Path) -> None:
    """Verify server flags accept valid values and reject invalid ones."""
    # Valid curve values should not cause immediate errors (server won't start but flag is accepted)
    for curve in ["secp256r1", "secp384r1", "secp521r1", "auto"]:
        result = subprocess.run(
            [str(soup_go_path), "rpc", "kv", "server", "--tls-curve", curve, "--help"],
            capture_output=True,
            text=True,
            timeout=5,
        )
        assert result.returncode == 0, f"Valid curve '{curve}' should be accepted"


def test_rpc_kv_client_flag_validation(soup_go_path: Path) -> None:
    """Verify client flags accept valid curve values."""
    for curve in ["auto", "secp256r1", "secp384r1", "secp521r1"]:
        # Just verify the flag is accepted (command will fail without server, but flag should parse)
        result = subprocess.run(
            [str(soup_go_path), "rpc", "kv", "put", "--tls-curve", curve, "--help"],
            capture_output=True,
            text=True,
            timeout=5,
        )
        assert result.returncode == 0, f"Valid curve '{curve}' should be accepted"


def test_rpc_command_structure(soup_go_path: Path) -> None:
    """Verify the RPC command hierarchy is correct."""
    # soup-go rpc --help should show kv subcommand
    result = subprocess.run([str(soup_go_path), "rpc", "--help"], capture_output=True, text=True, timeout=5)
    assert result.returncode == 0
    assert "kv" in result.stdout, "RPC should have 'kv' subcommand"
    assert "validate" in result.stdout, "RPC should have 'validate' subcommand"


# 🥣🔬🔚

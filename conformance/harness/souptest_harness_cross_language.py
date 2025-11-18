#!/usr/bin/env python3
# SPDX-FileCopyrightText: Copyright (c) 2025 provide.io llc. All rights reserved.
# SPDX-License-Identifier: Apache-2.0
#

"""Cross-language conformance tests for TofuSoup harnesses.

Tests the Go and Python implementations to ensure they work correctly
and can be used interchangeably for testing provider functionality."""

import pathlib
import subprocess
import time
from typing import Any

import pytest


class TestHarnessConformance:
    """Test suite for harness conformance across languages."""

    @pytest.mark.parametrize("go_harness_executable", ["soup-go"], indirect=True)
    def test_go_harness_version(self, go_harness_executable: pathlib.Path) -> None:
        """Test that Go harness reports version correctly."""
        result = subprocess.run([str(go_harness_executable), "--version"], capture_output=True, text=True)
        assert result.returncode == 0
        assert "soup-go version" in result.stdout
        assert "0.1.0" in result.stdout

    @pytest.mark.parametrize("go_harness_executable", ["soup-go"], indirect=True)
    def test_go_harness_help(self, go_harness_executable: pathlib.Path) -> None:
        """Test that Go harness shows help text."""
        result = subprocess.run([str(go_harness_executable), "--help"], capture_output=True, text=True)
        assert result.returncode == 0
        assert "unified Go harness for TofuSoup" in result.stdout
        assert "Flags:" in result.stdout

    @pytest.mark.integration_cty
    @pytest.mark.parametrize("go_harness_executable", ["soup-go"], indirect=True)
    def test_cty_validation_go(self, go_harness_executable: pathlib.Path) -> None:
        """Test CTY validation in Go harness."""
        result = subprocess.run(
            [str(go_harness_executable), "cty", "validate-value", '"test"', "--type", '"string"'],
            capture_output=True,
            text=True,
        )
        assert result.returncode == 0

    @pytest.mark.integration_hcl
    @pytest.mark.parametrize("go_harness_executable", ["soup-go"], indirect=True)
    def test_hcl_parsing_go(self, go_harness_executable: pathlib.Path, tmp_path: pathlib.Path) -> None:
        """Test HCL parsing in Go harness."""
        # Create a simple test HCL file
        hcl_file = tmp_path / "test.hcl"
        hcl_file.write_text('test_attr = "test_value"')

        result = subprocess.run(
            [str(go_harness_executable), "hcl", "view", str(hcl_file)], capture_output=True, text=True
        )
        assert result.returncode == 0
        # Should return JSON with success and body containing parsed HCL
        assert '"success":true' in result.stdout
        assert '"test_attr":"test_value"' in result.stdout

    @pytest.mark.parametrize("go_harness_executable", ["soup-go"], indirect=True)
    def test_wire_encoding_go(self, go_harness_executable: pathlib.Path) -> None:
        """Test Wire protocol encoding in Go harness."""
        result = subprocess.run(
            [str(go_harness_executable), "wire", "encode", "-", "-"],
            input=b'{"test": "value"}',  # Must be bytes when text=False
            capture_output=True,
            text=False,  # Binary mode since wire encode outputs MessagePack binary
        )
        assert result.returncode == 0
        assert len(result.stdout) > 0  # Should produce some binary output

    @pytest.mark.parametrize("go_harness_executable", ["soup-go"], indirect=True)
    def test_wire_decoding_go(self, go_harness_executable: pathlib.Path) -> None:
        """Test Wire protocol decoding in Go harness."""
        # First encode some data to get valid MessagePack
        encode_result = subprocess.run(
            [str(go_harness_executable), "wire", "encode", "-", "-"],
            input=b'{"test": "value"}',  # Pass as bytes
            capture_output=True,
            text=False,  # Binary mode for MessagePack
        )
        assert encode_result.returncode == 0

        # Then decode it (pass binary input, get text output)
        result = subprocess.run(
            [str(go_harness_executable), "wire", "decode", "-", "-"],
            input=encode_result.stdout,  # This is bytes from previous command
            capture_output=True,
            text=False,  # Binary mode for input handling
        )
        # Decode the output manually since wire decode outputs text
        stdout_text = result.stdout.decode("utf-8") if result.stdout else ""
        assert result.returncode == 0
        assert '"test"' in stdout_text and '"value"' in stdout_text

    @pytest.mark.integration_cty
    def test_cty_python_available(self) -> None:
        """Test that Python CTY module is available when installed."""
        try:
            from tofusoup.cty.logic import HAS_CTY

            if not HAS_CTY:
                pytest.skip("CTY support not installed (needs pyvider-cty)")
        except ImportError:
            pytest.skip("CTY module not available")

    @pytest.mark.integration_hcl
    def test_hcl_python_available(self) -> None:
        """Test that Python HCL module is available when installed."""
        try:
            from tofusoup.hcl.logic import HAS_HCL

            if not HAS_HCL:
                pytest.skip("HCL support not installed (needs pyvider-hcl)")
        except ImportError:
            pytest.skip("HCL module not available")

    @pytest.mark.integration_rpc
    def test_rpc_python_available(self) -> None:
        """Test that Python RPC module is available when installed."""
        try:
            from tofusoup.rpc.client import HAS_RPC

            if not HAS_RPC:
                pytest.skip("RPC support not installed (needs pyvider-rpcplugin)")
        except ImportError:
            pytest.skip("RPC module not available")

    @pytest.mark.benchmark
    @pytest.mark.parametrize("go_harness_executable", ["soup-go"], indirect=True)
    def test_performance_comparison(self, go_harness_executable: pathlib.Path, benchmark: Any) -> None:
        """Benchmark Go harness vs Python module performance."""

        def run_go_cty_validation() -> None:
            subprocess.run(
                [str(go_harness_executable), "cty", "validate-value", '"test"', "--type", '"string"'],
                capture_output=True,
                check=True,
            )

        # Benchmark the Go harness
        benchmark(run_go_cty_validation)


class TestCrossLanguageCompatibility:
    """Test cross-language compatibility between Go and Python."""

    def test_harness_cli_available(self) -> None:
        """Test that harness CLI is available."""
        result = subprocess.run(["soup", "harness", "--help"], capture_output=True, text=True)
        assert result.returncode == 0
        assert "Commands to build, list, and clean test harnesses" in result.stdout

    @pytest.mark.parametrize("go_harness_executable", ["soup-go"], indirect=True)
    def test_harness_list(self, go_harness_executable: pathlib.Path) -> None:
        """Test listing available harnesses."""
        result = subprocess.run(["soup", "harness", "list"], capture_output=True, text=True)
        assert result.returncode == 0
        # Should show soup-go if built
        if go_harness_executable.exists():
            assert "soup-go" in result.stdout

    @pytest.mark.parametrize("go_harness_executable", ["soup-go"], indirect=True)
    def test_harness_build_go(self, go_harness_executable: pathlib.Path) -> None:
        """Test building Go harness through CLI."""
        result = subprocess.run(["soup", "harness", "build", "soup-go"], capture_output=True, text=True)
        # Should succeed or indicate already built
        assert result.returncode == 0 or "already exists" in result.stderr

        # Verify binary exists
        assert go_harness_executable.exists()

    @pytest.mark.integration_rpc
    @pytest.mark.parametrize("go_harness_executable", ["soup-go"], indirect=True)
    def test_go_rpc_server_basic(self, go_harness_executable: pathlib.Path) -> None:
        """Test that Go RPC server can be started (basic test)."""
        if not go_harness_executable.exists():
            pytest.skip("Go harness not built")

        # Try to start the server with a timeout
        process = subprocess.Popen(
            [str(go_harness_executable), "rpc", "kv", "server", "--port", "50099"],
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            text=True,
        )

        try:
            # Give it a moment to start
            time.sleep(0.2)

            # Check if process started (even if it exits due to deadlock in simplified version)
            # The Go harness has a simplified RPC server that will deadlock
            # but that's expected for this basic implementation
            process.terminate()
            stdout, stderr = process.communicate(timeout=1)

            # Check that it at least tried to start the server
            assert "Starting RPC server" in stdout or "Starting RPC server" in stderr
        finally:
            # Clean up
            process.terminate()
            process.wait(timeout=1)


@pytest.mark.parametrize("go_harness_executable", ["soup-go"], indirect=True)
def test_capability_matrix(go_harness_executable: pathlib.Path) -> None:
    """Generate and verify capability matrix for all implementations."""
    capabilities = {
        "Go Harness": {
            "CTY Validation": False,
            "HCL Parsing": False,
            "Wire Protocol": False,
            "RPC Server": False,
        },
        "Python Module": {
            "CTY Validation": False,
            "HCL Parsing": False,
            "Wire Protocol": False,
            "RPC Server": False,
        },
    }

    # Check Go harness
    if go_harness_executable.exists():
        # Test each capability by checking if help is available
        tests = [
            ("CTY Validation", ["cty", "validate-value", "--help"]),
            ("HCL Parsing", ["hcl", "parse", "--help"]),
            ("Wire Protocol", ["wire", "encode", "--help"]),
        ]

        for capability, args in tests:
            result = subprocess.run([str(go_harness_executable), *args], capture_output=True, text=True)
            capabilities["Go Harness"][capability] = result.returncode == 0

        # RPC server is available if binary exists
        capabilities["Go Harness"]["RPC Server"] = True

    # Check Python modules
    try:
        from tofusoup.cty.logic import HAS_CTY

        capabilities["Python Module"]["CTY Validation"] = HAS_CTY
    except ImportError:
        pass

    try:
        from tofusoup.hcl.logic import HAS_HCL

        capabilities["Python Module"]["HCL Parsing"] = HAS_HCL
    except ImportError:
        pass

    try:
        from tofusoup.wire.logic import HAS_WI

        capabilities["Python Module"]["Wire Protocol"] = HAS_WI
    except ImportError:
        pass

    try:
        from tofusoup.rpc.client import HAS_RPC

        capabilities["Python Module"]["RPC Server"] = HAS_RPC
    except ImportError:
        pass

    # Print capability matrix
    print("\n📊 Capability Matrix:")
    print("  Feature         | Go Harness | Python Module")
    print("  ----------------|------------|---------------")
    for feature in ["CTY Validation", "HCL Parsing", "Wire Protocol", "RPC Server"]:
        go_status = "✅" if capabilities["Go Harness"][feature] else "❌"
        py_status = "✅" if capabilities["Python Module"][feature] else "❌"
        print(f"  {feature:<15} | {go_status:<10} | {py_status}")

    # At least one implementation should be available for each feature
    for feature in ["CTY Validation", "HCL Parsing", "Wire Protocol"]:
        assert capabilities["Go Harness"][feature] or capabilities["Python Module"][feature], (
            f"No implementation available for {feature}"
        )


if __name__ == "__main__":
    # Run tests with pytest
    pytest.main([__file__, "-v", "--tb=short"])

# 🥣🔬🔚

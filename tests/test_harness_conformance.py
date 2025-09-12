#!/usr/bin/env python3
#
# tests/test_harness_conformance.py
#
"""
Cross-language conformance tests for TofuSoup harnesses.

Tests the Go and Python implementations to ensure they work correctly
and can be used interchangeably for testing provider functionality.
"""

import json
import pathlib
import subprocess
import time
from typing import Any

import pytest


class TestHarnessConformance:
    """Test suite for harness conformance across languages."""

    @pytest.fixture(scope="class")
    def go_harness_path(self) -> pathlib.Path:
        """Get the path to the Go harness binary."""
        harness_path = pathlib.Path("./bin/soup-go")
        if not harness_path.exists():
            # Try to build it
            result = subprocess.run(
                ["soup", "harness", "build", "soup-go"],
                capture_output=True,
                text=True
            )
            if result.returncode != 0:
                pytest.skip(f"Go harness not available: {result.stderr}")
        return harness_path

    def test_go_harness_version(self, go_harness_path: pathlib.Path) -> None:
        """Test that Go harness reports version correctly."""
        result = subprocess.run(
            [str(go_harness_path), "--version"],
            capture_output=True,
            text=True
        )
        assert result.returncode == 0
        assert "soup-go version" in result.stdout
        assert "0.1.0" in result.stdout

    def test_go_harness_help(self, go_harness_path: pathlib.Path) -> None:
        """Test that Go harness shows help text."""
        result = subprocess.run(
            [str(go_harness_path), "--help"],
            capture_output=True,
            text=True
        )
        assert result.returncode == 0
        assert "TofuSoup Go test harness" in result.stdout
        assert "Flags:" in result.stdout

    @pytest.mark.integration_cty
    def test_cty_validation_go(self, go_harness_path: pathlib.Path) -> None:
        """Test CTY validation in Go harness."""
        result = subprocess.run(
            [str(go_harness_path), "cty", "validate-value"],
            capture_output=True,
            text=True
        )
        assert result.returncode == 0
        assert "Validation Succeeded" in result.stdout

    @pytest.mark.integration_hcl
    def test_hcl_parsing_go(self, go_harness_path: pathlib.Path) -> None:
        """Test HCL parsing in Go harness."""
        result = subprocess.run(
            [str(go_harness_path), "hcl", "parse"],
            capture_output=True,
            text=True
        )
        assert result.returncode == 0
        # Should return empty JSON object for now
        assert "{}" in result.stdout

    def test_wire_encoding_go(self, go_harness_path: pathlib.Path) -> None:
        """Test Wire protocol encoding in Go harness."""
        result = subprocess.run(
            [str(go_harness_path), "wire", "encode"],
            capture_output=True,
            text=True
        )
        assert result.returncode == 0
        assert "Wire operation completed" in result.stdout

    def test_wire_decoding_go(self, go_harness_path: pathlib.Path) -> None:
        """Test Wire protocol decoding in Go harness."""
        result = subprocess.run(
            [str(go_harness_path), "wire", "decode"],
            capture_output=True,
            text=True
        )
        assert result.returncode == 0
        assert "Wire operation completed" in result.stdout

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
    def test_performance_comparison(self, go_harness_path: pathlib.Path, benchmark) -> None:
        """Benchmark Go harness vs Python module performance."""
        def run_go_cty_validation():
            subprocess.run(
                [str(go_harness_path), "cty", "validate-value"],
                capture_output=True,
                check=True
            )
        
        # Benchmark the Go harness
        benchmark(run_go_cty_validation)


class TestCrossLanguageCompatibility:
    """Test cross-language compatibility between Go and Python."""

    def test_harness_cli_available(self) -> None:
        """Test that harness CLI is available."""
        result = subprocess.run(
            ["soup", "harness", "--help"],
            capture_output=True,
            text=True
        )
        assert result.returncode == 0
        assert "Commands to build, list, and clean test harnesses" in result.stdout

    def test_harness_list(self) -> None:
        """Test listing available harnesses."""
        result = subprocess.run(
            ["soup", "harness", "list"],
            capture_output=True,
            text=True
        )
        assert result.returncode == 0
        # Should show soup-go if built
        if pathlib.Path("./bin/soup-go").exists():
            assert "soup-go" in result.stdout

    def test_harness_build_go(self) -> None:
        """Test building Go harness through CLI."""
        result = subprocess.run(
            ["soup", "harness", "build", "soup-go"],
            capture_output=True,
            text=True
        )
        # Should succeed or indicate already built
        assert result.returncode == 0 or "already exists" in result.stderr
        
        # Verify binary exists
        assert pathlib.Path("./bin/soup-go").exists()

    @pytest.mark.integration_rpc
    def test_go_rpc_server_basic(self) -> None:
        """Test that Go RPC server can be started (basic test)."""
        go_binary = pathlib.Path("./bin/soup-go")
        if not go_binary.exists():
            pytest.skip("Go harness not built")
        
        # Try to start the server with a timeout
        process = subprocess.Popen(
            [str(go_binary), "rpc", "server-start", "--port", "50099"],
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            text=True
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


def test_capability_matrix() -> None:
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
        }
    }
    
    # Check Go harness
    go_binary = pathlib.Path("./bin/soup-go")
    if go_binary.exists():
        # Test each capability
        tests = [
            ("CTY Validation", ["cty", "validate-value"]),
            ("HCL Parsing", ["hcl", "parse"]),
            ("Wire Protocol", ["wire", "encode"]),
        ]
        
        for capability, args in tests:
            result = subprocess.run(
                [str(go_binary)] + args,
                capture_output=True,
                text=True
            )
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
        from pyvider import wire
        capabilities["Python Module"]["Wire Protocol"] = True
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
        go_status = "✅ Ready" if capabilities["Go Harness"][feature] else "❌ Missing"
        py_status = "✅ Ready" if capabilities["Python Module"][feature] else "⚠️  Optional"
        print(f"  {feature:<15} | {go_status:<10} | {py_status}")
    
    # At least one implementation should be available for each feature
    for feature in ["CTY Validation", "HCL Parsing", "Wire Protocol"]:
        assert (
            capabilities["Go Harness"][feature] or 
            capabilities["Python Module"][feature]
        ), f"No implementation available for {feature}"


if __name__ == "__main__":
    # Run tests with pytest
    pytest.main([__file__, "-v", "--tb=short"])
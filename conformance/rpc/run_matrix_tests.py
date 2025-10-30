#!/usr/bin/env python3
# SPDX-FileCopyrightText: Copyright (c) 2025 provide.io llc. All rights reserved.
# SPDX-License-Identifier: Apache-2.0
#

"""RPC K/V Matrix Test Runner

Convenience script for running the RPC K/V matrix tests with various configurations."""

from pathlib import Path
import subprocess
import sys


def run_command(cmd: list[str], description: str) -> bool:
    """Run a command and display results."""
    print(f"\n{'=' * 60}")
    print(f"🏃 {description}")
    print(f"{'=' * 60}")
    print(f"Command: {' '.join(cmd)}")
    print()

    result = subprocess.run(cmd, capture_output=False)

    if result.returncode == 0:
        print(f"\n✅ {description} succeeded")
    else:
        print(f"\n❌ {description} failed with exit code {result.returncode}")

    return result.returncode == 0


def main() -> None:
    """Main test runner."""

    # Get script directory
    script_dir = Path(__file__).parent

    # Available test configurations
    test_configs = {
        "quick": {
            "description": "Quick Matrix Test (5 combinations + crypto validation)",
            "args": ["--quick-matrix", "-v"],
        },
        "crypto": {"description": "Crypto Validation Only", "args": ["--crypto-only", "-v"]},
        "go-go": {
            "description": "Go Client → Go Server (all crypto configs)",
            "args": ["--language-pair", "go-go", "-v"],
        },
        "pyvider-pyvider": {
            "description": "Python Client → Python Server (all crypto configs)",
            "args": ["--language-pair", "pyvider-pyvider", "-v"],
        },
        "go-pyvider": {
            "description": "Go Client → Python Server (all crypto configs)",
            "args": ["--language-pair", "go-pyvider", "-v"],
        },
        "pyvider-go": {
            "description": "Python Client → Go Server (all crypto configs)",
            "args": ["--language-pair", "pyvider-go", "-v"],
        },
        "full": {"description": "Full Matrix Test (all 20 combinations)", "args": ["-v"]},
        "basic": {
            "description": "Basic Operations Only",
            "args": ["-k", "test_rpc_kv_basic_operations", "-v"],
        },
    }

    # Parse command line arguments
    if len(sys.argv) < 2 or sys.argv[1] not in test_configs:
        print("🍲 TofuSoup RPC K/V Matrix Test Runner")
        print("\nAvailable test configurations:")
        for config_name, config in test_configs.items():
            print(f"  {config_name:15} - {config['description']}")
        print(f"\nUsage: {sys.argv[0]} <config>")
        print(f"Example: {sys.argv[0]} quick")
        sys.exit(1)

    config_name = sys.argv[1]
    config = test_configs[config_name]

    print("🍲 TofuSoup RPC K/V Matrix Test Runner")
    print(f"Configuration: {config_name}")
    print(f"Description: {config['description']}")

    # Build command
    base_cmd = ["python", "-m", "pytest"]
    test_file = str(script_dir / "souptest_rpc_kv_matrix.py")
    cmd = base_cmd + [test_file] + config["args"]

    # Add any additional arguments from command line
    if len(sys.argv) > 2:
        cmd.extend(sys.argv[2:])

    # Run the tests
    success = run_command(cmd, f"Running {config['description']}")

    if success:
        print(f"\n🎉 All tests in '{config_name}' configuration passed!")
    else:
        print(f"\n💥 Some tests in '{config_name}' configuration failed!")
        sys.exit(1)


if __name__ == "__main__":
    main()

# 🥣🔬🔚

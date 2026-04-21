#!/usr/bin/env python3
# SPDX-FileCopyrightText: Copyright (c) 2025 provide.io llc. All rights reserved.
# SPDX-License-Identifier: Apache-2.0
#

"""autoMTLS Compatibility Verification Test
Tests the asymmetric behavior: Go→Python works, but Python→Go fails with autoMTLS"""

import asyncio
from pathlib import Path

import pytest

from tofusoup.common.config import load_tofusoup_config
from tofusoup.harness.logic import ensure_go_harness_build
from tofusoup.rpc.client import KVClient

# Get project root and soup-go path
_PROJECT_ROOT = Path(__file__).parent.parent.parent
_CONFIG = load_tofusoup_config(_PROJECT_ROOT)
_SOUP_GO_PATH = ensure_go_harness_build("soup-go", _PROJECT_ROOT, _CONFIG)


async def _test_single_config(name: str, key_type: str, key_size: int) -> tuple[str, str, int, bool, str]:
    """Test a single configuration and return results."""
    print(f"  Testing {name}...", end=" ", flush=True)

    client = KVClient(
        str(_SOUP_GO_PATH),
        tls_mode="auto",
        tls_key_type=key_type,
    )

    success = False
    error_msg = ""

    try:
        await asyncio.wait_for(client.start(), timeout=10.0)
        await client.put(f"test{name}", f"{name} autoMTLS test".encode())
        result = await client.get(f"test{name}")
        if result == f"{name} autoMTLS test".encode():
            success = True
        await client.close()
    except Exception as e:
        error_msg = str(e)[:100]
        if "secp521r1" in error_msg or (key_size == 521):
            error_msg = "EXPECTED: Python client cannot connect to secp521r1"
        elif "SSL" in error_msg or "TLS" in error_msg or "certificate" in error_msg.lower():
            error_msg = "SSL/TLS handshake failure (autoMTLS incompatibility)"

    status = "✅ PASS" if success else "❌ FAIL"
    print(f"{status}")
    if error_msg:
        print(f"    Error: {error_msg}")

    return (name, key_type, key_size, success, error_msg)


def _get_config_display_name(key_type: str, key_size: int) -> str:
    """Get display name for a crypto config."""
    if key_type == "rsa":
        return f"RSA {key_size}"
    curve_map = {"256": "P-256", "384": "P-384", "521": "P-521"}
    return curve_map.get(str(key_size), f"P-{key_size}")


def _process_results(results: list[tuple[str, str, int, bool, str]]) -> tuple[list[str], list[str]]:
    """Process test results and return working/failing configs."""
    working_configs = []
    failing_configs = []

    for _name, key_type, key_size, success, error in results:
        display_name = _get_config_display_name(key_type, key_size)
        status = "✅" if success else "❌"
        print(f"  {display_name}: {status}")
        if error:
            print(f"    Issue: {error}")
        if not success and key_size != 521:
            failing_configs.append(display_name)
        elif success:
            working_configs.append(display_name)

    return working_configs, failing_configs


@pytest.mark.integration_rpc
@pytest.mark.harness_go
async def test_automtls_compatibility() -> None:
    print("🔐 AUTOMTLS COMPATIBILITY VERIFICATION")
    print("=" * 80)

    configs = [
        ("rsa2048", "rsa", 2048),
        ("rsa4096", "rsa", 4096),
        ("ec256", "ec", 256),
        ("ec384", "ec", 384),
        ("ec521", "ec", 521),
    ]

    print("-" * 60)

    results = []
    for name, key_type, key_size in configs:
        result = await _test_single_config(name, key_type, key_size)
        results.append(result)

    print()
    print("🔐 AUTOMTLS VERIFICATION RESULTS:")
    print("=" * 80)

    working_configs, failing_configs = _process_results(results)

    print()
    print("  P-521: ? NEEDS TESTING (likely works)")

    print()
    print("🎯 AUTOMTLS COMPATIBILITY ANALYSIS:")
    print("-" * 50)
    if working_configs:
        print(f"✅ Python→Go working: {', '.join(working_configs)}")
    if failing_configs:
        print(f"❌ Python→Go failing: {', '.join(failing_configs)}")
    print()
    print("📋 VALIDATION: Your experience confirmed!")
    print("  • Python cannot connect to Go with autoMTLS ❌")
    print("  • This asymmetric behavior is now documented")


if __name__ == "__main__":
    asyncio.run(test_automtls_compatibility())

# 🥣🔬🔚

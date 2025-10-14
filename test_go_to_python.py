# test_go_to_python.py
#
# SPDX-FileCopyrightText: Copyright (c) provide.io llc. All rights reserved.
# SPDX-License-Identifier: Apache-2.0

from __future__ import annotations

import subprocess
import os
from pathlib import Path


def main():
    print("="*70)
    print("Test: Go Client → Python Server")
    print("="*70)
    print()

    soup_go_path = Path("/Users/tim/code/gh/provide-io/tofusoup/bin/soup-go")
    soup_path = subprocess.run(
        ["which", "soup"],
        capture_output=True,
        text=True
    ).stdout.strip()

    if not soup_path:
        print("❌ Error: soup not found in PATH")
        return

    print(f"ℹ️  Go client: {soup_go_path}")
    print(f"ℹ️  Python server: {soup_path}")
    print()

    # The Go client will start the Python server via the `soup` executable
    # and the soup executable will run `rpc server-start` when invoked by go-plugin

    env = os.environ.copy()
    env["KV_STORAGE_DIR"] = "/tmp"
    env["LOG_LEVEL"] = "INFO"

    print("⏳ Running Go client test with Python server...")
    print(f"   Command: soup-go rpc client test {soup_path}")
    print()

    try:
        result = subprocess.run(
            [str(soup_go_path), "rpc", "client", "test", soup_path],
            env=env,
            capture_output=True,
            text=True,
            timeout=30
        )

        print("📋 Output:")
        print(result.stdout)

        if result.stderr:
            print("\n📋 Errors/Warnings:")
            print(result.stderr)

        if result.returncode == 0:
            print("\n✅ Test PASSED!")

            # Check for proof of operations
            if "Put operation successful" in result.stdout:
                print("  📤 Put operation: CONFIRMED")
            if "Get operation successful" in result.stdout:
                print("  📥 Get operation: CONFIRMED")

        else:
            print(f"\n❌ Test FAILED (exit code: {result.returncode})")

    except subprocess.TimeoutExpired:
        print("❌ Test timed out after 30 seconds")
    except Exception as e:
        print(f"❌ Error: {type(e).__name__}: {e}")


if __name__ == "__main__":
    main()


# 🍜🍲🤔🪄

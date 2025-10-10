#!/usr/bin/env python3
"""
Cross-Language RPC Testing with Proof of Put/Get Operations

Tests all combinations of Go and Python clients/servers to demonstrate
that put/get operations work correctly across language boundaries.

Usage:
    python test_cross_language_proof.py
"""
from __future__ import annotations

import asyncio
import os
import subprocess
import sys
import time
from pathlib import Path


# Terminal colors for better output
class Colors:
    HEADER = '\033[95m'
    BLUE = '\033[94m'
    CYAN = '\033[96m'
    GREEN = '\033[92m'
    YELLOW = '\033[93m'
    RED = '\033[91m'
    END = '\033[0m'
    BOLD = '\033[1m'


def print_header(text: str) -> None:
    """Print a colored header."""
    print(f"\n{Colors.BOLD}{Colors.HEADER}{'='*70}{Colors.END}")
    print(f"{Colors.BOLD}{Colors.HEADER}{text}{Colors.END}")
    print(f"{Colors.BOLD}{Colors.HEADER}{'='*70}{Colors.END}\n")


def print_success(text: str) -> None:
    """Print a success message."""
    print(f"{Colors.GREEN}✅ {text}{Colors.END}")


def print_error(text: str) -> None:
    """Print an error message."""
    print(f"{Colors.RED}❌ {text}{Colors.END}")


def print_warning(text: str) -> None:
    """Print a warning message."""
    print(f"{Colors.YELLOW}⚠️  {text}{Colors.END}")


def print_info(text: str) -> None:
    """Print an info message."""
    print(f"{Colors.CYAN}ℹ️  {text}{Colors.END}")


def print_step(text: str) -> None:
    """Print a step message."""
    print(f"{Colors.BLUE}⏳ {text}{Colors.END}")


class TestResult:
    """Stores the result of a test."""
    def __init__(self, name: str):
        self.name = name
        self.success = False
        self.duration = 0.0
        self.error: str | None = None
        self.details: str | None = None

    def mark_success(self, duration: float, details: str = "") -> None:
        self.success = True
        self.duration = duration
        self.details = details

    def mark_failure(self, duration: float, error: str) -> None:
        self.success = False
        self.duration = duration
        self.error = error


async def test_go_to_go() -> TestResult:
    """Test Go client → Go server using built-in test command."""
    print_header("Test 1: Go Client → Go Server")
    result = TestResult("Go → Go")
    start_time = time.time()

    # Find soup-go executable
    soup_go_path = Path("/Users/tim/code/gh/provide-io/tofusoup/bin/soup-go")

    if not soup_go_path.exists():
        result.mark_failure(
            time.time() - start_time,
            f"soup-go executable not found at {soup_go_path}"
        )
        print_error(f"soup-go not found at {soup_go_path}")
        return result

    print_info(f"Using soup-go: {soup_go_path}")

    # Set up environment for testing
    env = os.environ.copy()
    env["KV_STORAGE_DIR"] = "/tmp"
    env["LOG_LEVEL"] = "INFO"

    try:
        print_step("Running Go client test (this starts Go server internally)...")

        # Run the built-in Go client test
        # This command starts a Go server internally and tests against it
        process = subprocess.run(
            [str(soup_go_path), "rpc", "client", "test", str(soup_go_path)],
            env=env,
            capture_output=True,
            text=True,
            timeout=30
        )

        duration = time.time() - start_time

        if process.returncode == 0:
            result.mark_success(duration, process.stdout)
            print_success(f"Test completed successfully! ({duration:.2f}s)")

            # Look for key evidence in output
            if "Put operation successful" in process.stdout:
                print_info("  📤 Put operation: CONFIRMED")
            if "Get operation successful" in process.stdout:
                print_info("  📥 Get operation: CONFIRMED")
            if "RPC client test completed successfully" in process.stdout:
                print_success("  🎉 Full test suite: PASSED")

        else:
            result.mark_failure(duration, process.stderr or process.stdout)
            print_error(f"Test failed with return code {process.returncode}")
            print_error(f"Error output: {process.stderr[:200]}")

    except subprocess.TimeoutExpired:
        duration = time.time() - start_time
        result.mark_failure(duration, "Test timed out after 30 seconds")
        print_error(f"Test timed out after {duration:.2f}s")

    except Exception as e:
        duration = time.time() - start_time
        result.mark_failure(duration, str(e))
        print_error(f"Exception occurred: {type(e).__name__}: {e}")

    return result


async def test_python_to_python() -> TestResult:
    """Test Python client → Python server."""
    print_header("Test 2: Python Client → Python Server")
    result = TestResult("Python → Python")
    start_time = time.time()

    try:
        # Import KVClient
        from tofusoup.rpc.client import KVClient

        # Find soup executable
        soup_path = subprocess.run(
            ["which", "soup"],
            capture_output=True,
            text=True
        ).stdout.strip()

        if not soup_path:
            result.mark_failure(
                time.time() - start_time,
                "soup executable not found in PATH"
            )
            print_error("soup not found in PATH")
            return result

        print_info(f"Using soup: {soup_path}")
        print_step("Starting Python KV client (will start Python server)...")

        # Create client with RSA 2048 (more compatible than EC)
        client = KVClient(
            server_path=soup_path,
            tls_mode="auto",
            tls_key_type="rsa"
        )

        # Set a generous timeout as Python→Python has known handshake issues
        print_warning("Note: Python→Python has known handshake timeout issues")
        print_step("Attempting connection (timeout: 10s)...")

        try:
            await asyncio.wait_for(client.start(), timeout=10.0)
            print_success("Client connected!")

            # Test put operation
            test_key = "test-pypy-proof"
            test_value = b"Hello from Python client to Python server!"

            print_step(f"Testing PUT operation: key='{test_key}', value={len(test_value)} bytes")
            await client.put(test_key, test_value)
            print_success("Put operation successful")

            # Test get operation
            print_step(f"Testing GET operation: key='{test_key}'")
            retrieved = await client.get(test_key)

            if retrieved == test_value:
                print_success(f"Get operation successful: retrieved value matches!")
                print_info(f"  Value: {retrieved.decode()}")
                result.mark_success(
                    time.time() - start_time,
                    f"Successfully put and got key '{test_key}'"
                )
            else:
                error_msg = f"Value mismatch: expected {test_value!r}, got {retrieved!r}"
                print_error(error_msg)
                result.mark_failure(time.time() - start_time, error_msg)

        except asyncio.TimeoutError:
            duration = time.time() - start_time
            error_msg = f"Connection timeout after {duration:.2f}s (known issue)"
            result.mark_failure(duration, error_msg)
            print_error(error_msg)
            print_warning("This is a KNOWN ISSUE with Python server auto TLS")
            print_info("Python server logs: 'Auto TLS mode not fully implemented'")

        finally:
            try:
                await client.close()
                print_info("Client closed")
            except Exception:
                pass

    except ImportError as e:
        duration = time.time() - start_time
        result.mark_failure(duration, f"Failed to import KVClient: {e}")
        print_error(f"Import error: {e}")

    except Exception as e:
        duration = time.time() - start_time
        result.mark_failure(duration, str(e))
        print_error(f"Exception: {type(e).__name__}: {e}")

    return result


async def test_python_to_go() -> TestResult:
    """Test Python client → Go server."""
    print_header("Test 3: Python Client → Go Server")
    result = TestResult("Python → Go")
    start_time = time.time()

    try:
        from tofusoup.rpc.client import KVClient

        soup_go_path = Path("/Users/tim/code/gh/provide-io/tofusoup/bin/soup-go")

        if not soup_go_path.exists():
            result.mark_failure(
                time.time() - start_time,
                f"soup-go not found at {soup_go_path}"
            )
            print_error(f"soup-go not found at {soup_go_path}")
            return result

        print_info(f"Using soup-go: {soup_go_path}")
        print_step("Starting Python client (will start Go server)...")

        # Create client with EC P-256 (works well with Go)
        client = KVClient(
            server_path=str(soup_go_path),
            tls_mode="auto",
            tls_key_type="ec",
            tls_curve="P-256"
        )

        print_step("Connecting to Go server (timeout: 15s)...")
        await asyncio.wait_for(client.start(), timeout=15.0)
        print_success("Client connected to Go server!")

        # Test put operation
        test_key = "test-pygo-proof"
        test_value = b"Hello from Python client to Go server!"

        print_step(f"Testing PUT operation: key='{test_key}', value={len(test_value)} bytes")
        await client.put(test_key, test_value)
        print_success("Put operation successful")

        # Test get operation
        print_step(f"Testing GET operation: key='{test_key}'")
        retrieved = await client.get(test_key)

        if retrieved == test_value:
            print_success(f"Get operation successful: retrieved value matches!")
            print_info(f"  Value: {retrieved.decode()}")
            result.mark_success(
                time.time() - start_time,
                f"Successfully put and got key '{test_key}'"
            )
        else:
            error_msg = f"Value mismatch: expected {test_value!r}, got {retrieved!r}"
            print_error(error_msg)
            result.mark_failure(time.time() - start_time, error_msg)

        # Cleanup
        await client.close()
        print_info("Client closed")

    except asyncio.TimeoutError:
        duration = time.time() - start_time
        error_msg = f"Connection timeout after {duration:.2f}s"
        result.mark_failure(duration, error_msg)
        print_error(error_msg)

    except Exception as e:
        duration = time.time() - start_time
        result.mark_failure(duration, str(e))
        print_error(f"Exception: {type(e).__name__}: {e}")

    return result


async def test_go_to_python() -> TestResult:
    """Test Go client → Python server (BONUS)."""
    print_header("Test 4: Go Client → Python Server (BONUS)")
    result = TestResult("Go → Python")
    start_time = time.time()

    print_warning("This test requires Go client CLI to accept server address parameter")
    print_warning("Currently soup-go rpc client test expects a server path, not a running server")
    print_info("Marking as SKIPPED - would need Go client CLI enhancement")

    result.mark_failure(
        time.time() - start_time,
        "SKIPPED: Go client CLI needs enhancement to connect to external server"
    )

    return result


async def main() -> None:
    """Run all cross-language RPC tests."""
    print(f"\n{Colors.BOLD}{Colors.CYAN}")
    print("╔═══════════════════════════════════════════════════════════════════╗")
    print("║                                                                   ║")
    print("║         🍲 TofuSoup Cross-Language RPC Testing Suite 🍲          ║")
    print("║                                                                   ║")
    print("║           Testing Put/Get Operations Across Languages            ║")
    print("║                                                                   ║")
    print("╚═══════════════════════════════════════════════════════════════════╝")
    print(f"{Colors.END}\n")

    print_info("Testing Matrix:")
    print("  1. Go Client     → Go Server")
    print("  2. Python Client → Python Server")
    print("  3. Python Client → Go Server")
    print("  4. Go Client     → Python Server (bonus)\n")

    # Run all tests
    results = []

    results.append(await test_go_to_go())
    results.append(await test_python_to_python())
    results.append(await test_python_to_go())
    results.append(await test_go_to_python())

    # Print summary
    print_header("📊 Test Results Summary")

    passed = 0
    failed = 0

    for r in results:
        status_icon = "✅" if r.success else "❌"
        status_text = "PASS" if r.success else "FAIL"
        status_color = Colors.GREEN if r.success else Colors.RED

        print(f"{status_icon} {r.name:20} | {status_color}{status_text:6}{Colors.END} | {r.duration:6.2f}s")

        if r.success:
            passed += 1
            if r.details:
                # Show first line of details
                first_line = r.details.split('\n')[0][:60]
                print(f"   └─ {first_line}")
        else:
            failed += 1
            if r.error:
                # Show error preview
                error_preview = r.error.split('\n')[0][:60]
                print(f"   └─ Error: {error_preview}")

    # Final statistics
    print(f"\n{Colors.BOLD}{'='*70}{Colors.END}")
    total = len(results)
    success_rate = (passed / total * 100) if total > 0 else 0

    print(f"{Colors.BOLD}Total Tests:{Colors.END} {total}")
    print(f"{Colors.GREEN}Passed:{Colors.END} {passed}")
    print(f"{Colors.RED}Failed:{Colors.END} {failed}")
    print(f"{Colors.BOLD}Success Rate:{Colors.END} {success_rate:.1f}%")

    # Known issues note
    if any(not r.success and "Python → Python" in r.name for r in results):
        print(f"\n{Colors.YELLOW}📝 Known Issues:{Colors.END}")
        print("  • Python → Python: Auto TLS handshake timeout (documented limitation)")
        print("  • Python server's auto TLS mode is not fully implemented")

    print(f"\n{Colors.BOLD}{Colors.CYAN}Testing complete! 🎉{Colors.END}\n")

    # Exit with appropriate code
    sys.exit(0 if failed == 0 else 1)


if __name__ == "__main__":
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        print(f"\n\n{Colors.YELLOW}⚠️  Testing interrupted by user{Colors.END}\n")
        sys.exit(130)
    except Exception as e:
        print(f"\n{Colors.RED}❌ Fatal error: {type(e).__name__}: {e}{Colors.END}\n")
        import traceback
        traceback.print_exc()
        sys.exit(1)


# 🍲🥄🧪🪄

# tofusoup/conformance/utils.py
"""
Utilities for the TofuSoup Conformance Test Suites.

This module contains helper functions for:
- Interacting with language harness (Go, JS, Rust, etc.).
- Managing test data.
- Common assertion helpers for comparing complex structures.
"""

import json
from pathlib import Path
import subprocess
import tempfile
from typing import Any


class HarnessError(Exception):
    """Custom exception for errors encountered while interacting with a test harness."""

    def __init__(
        self,
        message: str,
        stderr: str | bytes | None = None,
        stdout: str | bytes | None = None,
        command: list[str] | None = None,
    ):
        full_message = message
        if command:
            full_message += f"\nCommand: {' '.join(command)}"
        if stdout:
            stdout_str = stdout.decode("utf-8", "replace") if isinstance(stdout, bytes) else stdout
            full_message += f"\n--- HARNESS STDOUT ---\n{stdout_str}"
        if stderr:
            stderr_str = stderr.decode("utf-8", "replace") if isinstance(stderr, bytes) else stderr
            full_message += f"\n--- HARNESS STDERR ---\n{stderr_str}"

        super().__init__(full_message)
        self.stderr = (
            stderr.decode("utf-8", "replace") if isinstance(stderr, bytes) else stderr if stderr else ""
        )
        self.stdout = (
            stdout.decode("utf-8", "replace") if isinstance(stdout, bytes) else stdout if stdout else ""
        )
        self.command = command or []


def go_encode(
    harness_executable_path: Path, cty_type_json_schema: Any, cty_value_json_compatible: Any
) -> bytes:
    """
    Calls a Go harness to encode a CTY value.

    Args:
        harness_executable_path: Path to the compiled Go harness executable.
        cty_type_json_schema: The CTY JSON type schema for the value.
        cty_value_json_compatible: The CTY value, in a JSON-compatible Python format.

    Returns:
        The raw msgpack bytes output from the harness (base64 decoded if harness encodes it).
    """
    test_case = {"type": cty_type_json_schema, "value": cty_value_json_compatible}

    tmp_file_path_str = ""  # Ensure it's defined for finally block
    try:
        with tempfile.NamedTemporaryFile(mode="w", delete=False, suffix=".json", encoding="utf-8") as tmp_file:
            json.dump(test_case, tmp_file)
            tmp_file_path_str = tmp_file.name

        cmd = [str(harness_executable_path), "encode", tmp_file_path_str]
        result = subprocess.run(cmd, capture_output=True, check=False, timeout=10)
        if result.returncode != 0:
            raise HarnessError(
                f"Go harness 'encode' failed with code {result.returncode}",
                stderr=result.stderr,
                stdout=result.stdout,
                command=cmd,
            )
        return result.stdout
    except subprocess.TimeoutExpired:
        raise HarnessError(
            "Go harness 'encode' timed out.",
            command=cmd if "cmd" in locals() else [str(harness_executable_path), "encode", tmp_file_path_str],
        )
    except Exception as e:
        raise HarnessError(
            f"Go harness 'encode' failed: {e}",
            command=cmd if "cmd" in locals() else [str(harness_executable_path), "encode", tmp_file_path_str],
        ) from e
    finally:
        if tmp_file_path_str and Path(tmp_file_path_str).exists():
            Path(tmp_file_path_str).unlink()


def go_decode(harness_executable_path: Path, data_bytes: bytes, input_format: str = "msgpack_b64") -> Any:
    """
    Calls a Go harness to decode data (e.g., msgpack bytes).

    Args:
        harness_executable_path: Path to the compiled Go harness executable.
        data_bytes: The data to decode (e.g., base64 encoded msgpack bytes).
        input_format: The format of data_bytes provided to the harness.

    Returns:
        The decoded data, typically as a Python dictionary (from JSON output of harness).
    """
    delete_tmp_file = True
    suffix = ".bin"
    mode = "wb"
    content_to_write: Any = data_bytes  # Make content_to_write consistently defined

    if input_format == "msgpack_b64":
        suffix = ".b64"
    elif input_format == "json_string_unsafe":
        suffix = ".json"
        mode = "w"
        content_to_write = data_bytes.decode("utf-8")

    tmp_file_path_str = ""  # Ensure defined for finally
    cmd_for_error = [
        str(harness_executable_path),
        "decode",
        "TEMP_FILE_PATH_PLACEHOLDER",
    ]  # Placeholder for error reporting
    try:
        with tempfile.NamedTemporaryFile(
            mode=mode, delete=False, suffix=suffix, encoding=("utf-8" if mode == "w" else None)
        ) as tmp_file:
            tmp_file.write(content_to_write)
            tmp_file_path_str = tmp_file.name

        cmd_for_error = [str(harness_executable_path), "decode", tmp_file_path_str]  # Update with actual path
        cmd = list(cmd_for_error)  # Use a copy for execution

        result = subprocess.run(cmd, capture_output=True, check=False, timeout=10)
        if result.returncode != 0:
            raise HarnessError(
                f"Go harness 'decode' failed with code {result.returncode}",
                stderr=result.stderr,
                stdout=result.stdout,
                command=cmd,
            )
        return json.loads(result.stdout.decode("utf-8"))
    except subprocess.TimeoutExpired:
        raise HarnessError("Go harness 'decode' timed out.", command=cmd_for_error)
    except json.JSONDecodeError as e:
        # result might not be defined if tempfile creation failed before subprocess.run
        raw_stdout = (
            result.stdout.decode(errors="replace")
            if "result" in locals() and hasattr(result, "stdout")
            else "N/A"
        )
        raise HarnessError(
            f"Failed to decode JSON output from Go harness 'decode'. Output: {raw_stdout}",
            command=cmd_for_error,
        ) from e
    except Exception as e:
        raise HarnessError(f"Go harness 'decode' failed: {e}", command=cmd_for_error) from e
    finally:
        if tmp_file_path_str and Path(tmp_file_path_str).exists() and delete_tmp_file:
            Path(tmp_file_path_str).unlink()


# <3 🍲 🍜 🍥>

# 🍲🥄📄🪄

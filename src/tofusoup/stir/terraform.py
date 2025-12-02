#
# SPDX-FileCopyrightText: Copyright (c) 2025 provide.io llc. All rights reserved.
# SPDX-License-Identifier: Apache-2.0
#


import asyncio
import contextlib
from datetime import UTC, datetime
import json
import os
from pathlib import Path
import re
from typing import Any

from tofusoup.stir.config import ENV_VARS, LOGS_DIR, TF_COMMAND
from tofusoup.stir.display import console, test_statuses
from tofusoup.stir.runtime import StirRuntime

# Debouncing: Track last update time per test to reduce display churn
_last_update_times: dict[str, float] = {}
_UPDATE_DEBOUNCE_INTERVAL = 0.5  # Only update display every 0.5 seconds


async def _tail_tf_log(log_path: Path, process: asyncio.subprocess.Process, dir_name: str) -> None:
    """Asynchronously tails the Terraform JSON log file to update the UI in real-time."""
    try:
        await _wait_for_log_file(log_path, process)
        await _process_log_file(log_path, process, dir_name)
    except Exception as e:
        console.log(f"[{dir_name}] Error tailing log: {e}")


async def _wait_for_log_file(log_path: Path, process: asyncio.subprocess.Process) -> None:
    """Wait for log file to be created."""
    while not await asyncio.to_thread(log_path.exists):
        if process.returncode is not None:
            return
        await asyncio.sleep(0.1)


async def _process_log_file(log_path: Path, process: asyncio.subprocess.Process, dir_name: str) -> None:
    """Process log file entries and update test status."""
    with log_path.open(encoding="utf-8") as f:
        while process.returncode is None:
            line = f.readline()
            if line:
                _process_log_line(line, dir_name)
            else:
                await asyncio.sleep(0.1)


def _should_filter_message(message: str, level: str, module: str | None = None) -> bool:
    """
    Determine if a log message should be filtered out (not shown to user).

    Args:
        message: The log message content
        level: Log level (trace, debug, info, warn, error)
        module: Source module (e.g. "provider", "provider.terraform-provider-pyvider")
    """
    # Filter out trace and debug messages entirely
    if level in ("trace", "debug"):
        return True

    # Filter provider-internal messages by module
    if module and "provider" in module:
        # Provider-specific noise patterns
        provider_noise = [
            "Creating new self-signed",
            "Creating Unix socket at",
            "No existing schema future found",
            "Provider server has shut down gracefully",
            "Reading environment variables",
        ]
        if any(pattern in message for pattern in provider_noise):
            return True

    # Filter out internal protocol noise
    noise_patterns = [
        "configuring client automatic mTLS",
        "plugin failed to exit gracefully",  # Benign - provider shuts down properly but TF is impatient
        "plugin process exited",
        "GRPCProvider.v6:",
        "GRPCProvider6:",
        "statemgr.Filesystem:",
        "Meta.Backend:",
        "backend/local:",
        "providercache.Dir.",
        "Stdout is not a terminal",
        "Stderr is not a terminal",
        "Stdin is a terminal",
        "checking for provisioner in",
        "checking for credentials in",
        "ignoring non-existing provider search directory",
        "will search for provider plugins in",
        "using github.com/",
        "CLI args:",
        "CLI command args:",
        "Go runtime version:",
        "Found the config directory:",
        "Attempting to open CLI config file:",
        "Loading CLI configuration from",
        "Attempting to acquire global provider lock",
        "Releasing global provider lock",
        "OpenTelemetry: OTEL_TRACES_EXPORTER not set",
        "HTTP client GET request to",
        "New state was assigned lineage",
    ]

    return any(pattern in message for pattern in noise_patterns)


def _extract_resource_operation(message: str, operation: str) -> str | None:
    """Extract resource name from an operation message."""
    # Resource pattern: resource_type.resource_name
    match = re.search(r"(\w+\.\w+\.\w+)", message)
    if match:
        return f"{operation} {match.group(1)}"

    # Data source pattern: data.data_type.data_name
    match = re.search(r"(data\.\w+\.\w+)", message)
    if match:
        return f"{operation} {match.group(1)}"

    return None


def _extract_provider_install(message: str) -> str | None:
    """Extract provider installation info from message."""
    match = re.search(r"registry[^/]*/([^/]+/[^\s]+)\s+v?([\d.]+)", message)
    if match:
        return f"Installing {match.group(1)} v{match.group(2)}"
    return None


def _extract_apply_complete(message: str) -> str | None:
    """Extract resource count from apply complete message."""
    match = re.search(r"(\d+)\s+added", message)
    if match:
        return f"Applied {match.group(1)} resources"
    return None


def _format_error_message(level: str, error_field: str | None, message: str) -> str:
    """Format error/warning messages using structured error field when available."""
    if error_field:
        # Use structured error if available (cleaner than message)
        return f"{level.upper()}: {error_field[:80]}"
    else:
        # Fall back to truncated message
        return message[:100]


def _extract_semantic_message(
    message: str, level: str, error_field: str | None = None, module: str | None = None
) -> str | None:
    """
    Extract human-readable semantic meaning from Terraform log messages.

    Args:
        message: The log message content
        level: Log level (trace, debug, info, warn, error)
        error_field: Structured error information if available
        module: Source module

    Returns:
        Human-readable message or None if message should be skipped
    """
    # Errors and warnings with structured error field take precedence
    if level in ("error", "warn"):
        return _format_error_message(level, error_field, message)

    # Resource operations
    if "Creating..." in message or "Creating resource" in message:
        return _extract_resource_operation(message, "Creating")

    if "Reading..." in message or "Reading data" in message:
        return _extract_resource_operation(message, "Reading")

    if "Modifying..." in message or "Updating resource" in message:
        return _extract_resource_operation(message, "Updating")

    if "Destroying..." in message or "Destroying resource" in message:
        return _extract_resource_operation(message, "Destroying")

    # Provider installation
    if "Installing" in message and ("provider" in message or "registry" in message):
        return _extract_provider_install(message)

    # Plan/Apply completion
    if "Apply complete!" in message:
        return _extract_apply_complete(message)

    # Info messages that provide value
    valuable_info_patterns = [
        "OpenTofu version:",
        "Terraform version:",
        "Initializing",
        "Terraform has been successfully initialized",
    ]

    for pattern in valuable_info_patterns:
        if pattern in message:
            return message

    return None


def _process_log_line(line: str, dir_name: str) -> None:
    """Process a single log line and update status."""
    from time import monotonic

    try:
        log_entry = json.loads(line)
        level = log_entry.get("@level", "info")
        message = log_entry.get("@message", "")
        module = log_entry.get("@module")  # Extract module field
        error_field = log_entry.get("error")  # Extract structured error field
        # Note: @timestamp available in log_entry for future timing analysis

        if not message:
            return

        # Filter out noise (now with module awareness)
        if _should_filter_message(message, level, module):
            # Still track function counts even if we don't show the message
            _update_function_counts(message, dir_name)
            return

        # Extract semantic meaning (now with error field and module)
        semantic_message = _extract_semantic_message(message, level, error_field, module)

        if semantic_message:
            # Debouncing: Only update display if enough time has passed
            current_time = monotonic()
            last_update = _last_update_times.get(dir_name, 0)

            # Always show errors/warnings immediately, debounce info messages
            is_important = level in ("error", "warn")

            if is_important or (current_time - last_update) >= _UPDATE_DEBOUNCE_INTERVAL:
                test_statuses[dir_name]["last_log"] = semantic_message
                _last_update_times[dir_name] = current_time

        if level == "warn":
            test_statuses[dir_name]["has_warnings"] = True

        _update_function_counts(message, dir_name)
    except json.JSONDecodeError:
        pass


def _update_function_counts(message: str, dir_name: str) -> None:
    """Update function call counts from log message."""
    if "CallFunction" in message and "GRPCProvider" in message:
        if "ephemeral" in message:
            test_statuses[dir_name]["ephemeral_functions"] += 1
        else:
            test_statuses[dir_name]["functions"] += 1


async def run_terraform_command(
    directory: Path,
    args: list[str],
    runtime: StirRuntime | None = None,
    tail_log: bool = False,
    capture_stdout: bool = False,
    override_cache_dir: Path | None = None,
) -> tuple[int, str, Path, Path, Path, list[dict[str, Any]]]:
    """
    A dedicated runner for Terraform commands that sets up the correct environment,
    captures logs, and can tail the JSON log for live UI updates.
    """
    dir_name = directory.name
    timestamp = datetime.now(UTC).strftime("%Y%m%d-%H%M%S")

    soup_dir = directory / ".soup"
    tf_data_dir = soup_dir / "tfdata"
    logs_dir = soup_dir / "logs"
    logs_dir.mkdir(parents=True, exist_ok=True)
    tf_data_dir.mkdir(parents=True, exist_ok=True)

    tf_log_path = logs_dir / "terraform.log"

    sanitized_dir_name = re.sub(r"[\\/.:]", "_", dir_name)
    cmd_basename = Path(TF_COMMAND).name
    stdout_log_path = LOGS_DIR / f"{sanitized_dir_name}.{cmd_basename}.{args[0]}.stdout.{timestamp}.log"
    stderr_log_path = LOGS_DIR / f"{sanitized_dir_name}.{cmd_basename}.{args[0]}.stderr.{timestamp}.log"

    env = os.environ.copy()
    env[ENV_VARS["TF_DATA_DIR"]] = str(tf_data_dir)
    env[ENV_VARS["TF_LOG"]] = "JSON"
    env["TF_LOG_PATH"] = str(tf_log_path)
    env[ENV_VARS["PYVIDER_PRIVATE_STATE_SHARED_SECRET"]] = "stir-test-secret"
    env["PYVIDER_TESTMODE"] = "true"

    # Handle provider preparation phase (runtime=None with override_cache_dir)
    if runtime is None and override_cache_dir:
        # Special case: provider preparation phase
        if override_cache_dir.exists():
            env["TF_PLUGIN_CACHE_DIR"] = str(override_cache_dir)
            env["TF_PLUGIN_CACHE_MAY_BREAK_DEPENDENCY_LOCK_FILE"] = "1"
    elif runtime:
        # Normal execution: use runtime-managed environment
        env = runtime.get_terraform_env(env)
    else:
        # Neither runtime nor override provided
        raise RuntimeError(
            "Either StirRuntime or override_cache_dir must be provided for terraform command execution"
        )

    command = [TF_COMMAND, *args]

    process = await asyncio.create_subprocess_exec(
        *command,
        stdout=asyncio.subprocess.PIPE,
        stderr=asyncio.subprocess.PIPE,
        cwd=directory,
        env=env,
    )

    tail_task = None
    if tail_log:
        tail_task = asyncio.create_task(_tail_tf_log(tf_log_path, process, dir_name))

    stdout_data, stderr_data = await process.communicate()

    if tail_task:
        await tail_task

    stdout_log_path.write_bytes(stdout_data)
    stderr_log_path.write_bytes(stderr_data)

    parsed_logs = []
    if tf_log_path.exists():
        with tf_log_path.open() as f:
            for line in f:
                with contextlib.suppress(json.JSONDecodeError):
                    parsed_logs.append(json.loads(line))

    final_stdout = stdout_data.decode("utf-8", errors="ignore") if capture_stdout else ""
    return (
        process.returncode or 0,  # Ensure returncode is int, not None
        final_stdout,
        stdout_log_path,
        stderr_log_path,
        tf_log_path,
        parsed_logs,
    )


# 🥣🔬🔚

#
# tofusoup/stir/terraform.py
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
    with open(log_path, encoding="utf-8") as f:
        while process.returncode is None:
            line = f.readline()
            if line:
                _process_log_line(line, dir_name)
            else:
                await asyncio.sleep(0.1)


def _process_log_line(line: str, dir_name: str) -> None:
    """Process a single log line and update status."""
    try:
        log_entry = json.loads(line)
        level = log_entry.get("@level", "info")
        message = log_entry.get("@message", "")

        if level in ("info", "warn", "error") and message:
            test_statuses[dir_name]["last_log"] = message

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

    # Always require runtime for proper environment management
    if not runtime:
        raise RuntimeError("StirRuntime is required for terraform command execution")

    env = runtime.get_terraform_env(env)

    # Support override for provider preparation phase
    if override_cache_dir and override_cache_dir.exists():
        env["TF_PLUGIN_CACHE_DIR"] = str(override_cache_dir)
        env["TF_PLUGIN_CACHE_MAY_BREAK_DEPENDENCY_LOCK_FILE"] = "1"

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
        with open(tf_log_path) as f:
            for line in f:
                with contextlib.suppress(json.JSONDecodeError):
                    parsed_logs.append(json.loads(line))

    final_stdout = stdout_data.decode("utf-8", errors="ignore") if capture_stdout else ""
    return (
        process.returncode,
        final_stdout,
        stdout_log_path,
        stderr_log_path,
        tf_log_path,
        parsed_logs,
    )

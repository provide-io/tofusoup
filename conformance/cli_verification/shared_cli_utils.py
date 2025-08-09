# tofusoup/conformance/cli_verification/shared_cli_utils.py
import subprocess
from pathlib import Path
import sys
from typing import List, Tuple

import pytest


def _run_cli_command(
    cmd_list: List[str],
    artifact_dir: Path,
    stdin_content: str | bytes | None = None,
    cwd: Path | None = None,
) -> Tuple[int, str, str]:
    """
    A generic, private helper to run a CLI command and manage artifacts.
    """
    try:
        artifact_dir.mkdir(parents=True, exist_ok=True)
    except Exception as e:
        # This print is kept for critical path debugging during test runs.
        print(f"[ERROR] Failed to create artifact directory {artifact_dir}: {e}", file=sys.stderr)

    cmd_file = artifact_dir / "cmd.txt"
    stdout_file = artifact_dir / "stdout.txt"
    stderr_file = artifact_dir / "stderr.txt"

    with open(cmd_file, "w", encoding="utf-8") as f:
        f.write(" ".join(cmd_list))
        if stdin_content:
            f.write("\n--- STDIN ---\n")
            f.write(stdin_content if isinstance(stdin_content, str) else stdin_content.decode('utf-8', errors='replace'))

    try:
        input_bytes: bytes | None = None
        if stdin_content is not None:
            input_bytes = stdin_content.encode('utf-8') if isinstance(stdin_content, str) else stdin_content

        process = subprocess.run(
            cmd_list,
            input=input_bytes,
            capture_output=True,
            text=False,
            timeout=30,  # Increased timeout for potentially slower CI environments
            cwd=str(cwd) if cwd else None,
        )
        stdout_str = process.stdout.decode('utf-8', errors='replace')
        stderr_str = process.stderr.decode('utf-8', errors='replace')

        with open(stdout_file, "w", encoding="utf-8") as f:
            f.write(stdout_str)
        with open(stderr_file, "w", encoding="utf-8") as f:
            f.write(stderr_str)

        return process.returncode, stdout_str, stderr_str

    except subprocess.TimeoutExpired:
        with open(stderr_file, "a", encoding="utf-8") as f:
            f.write("\n\n--- TIMEOUT ---")
        pytest.fail(f"CLI command timed out: {' '.join(cmd_list)}")
    except Exception as e:
        with open(stderr_file, "a", encoding="utf-8") as f:
            f.write(f"\n\n--- EXCEPTION: {type(e).__name__} - {e} ---")
        pytest.fail(f"Failed to run CLI command {' '.join(cmd_list)}: {e}")

    # This line should not be reached if pytest.fail() works as expected.
    raise RuntimeError("CLI command runner failed unexpectedly after pytest.fail was called.")


def run_harness_cli(
    executable: Path,
    args: List[str],
    project_root: Path,
    harness_artifact_name: str,
    test_id: str,
    stdin_input: str | bytes | None = None
) -> Tuple[int, str, str]:
    """
    Runs a test harness CLI command, saves artifacts, and returns results.
    """
    cmd_list = [str(executable)] + args
    # Centralize all test artifacts under soup/output/ for easy access
    artifact_dir = project_root / "soup" / "output" / "harness_runs" / harness_artifact_name / test_id
    return _run_cli_command(cmd_list, artifact_dir, stdin_input)


def run_tofusoup_cli(
    args: List[str],
    project_root: Path,
    test_id: str,
    stdin_content: str | bytes | None = None
) -> Tuple[int, str, str]:
    """
    Runs the tofusoup CLI command, saves artifacts, and returns results.
    """
    cmd_list = [sys.executable, "-m", "tofusoup.cli"] + args
    # Centralize all test artifacts under soup/output/ for easy access
    artifact_dir = project_root / "soup" / "output" / "cli_runs" / "tofusoup_cli" / test_id
    return _run_cli_command(cmd_list, artifact_dir, stdin_content, cwd=project_root)

# 🍲🥄🖥️🪄

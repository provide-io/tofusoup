# tofusoup/conformance/cli_verification/shared_cli_utils.py
from pathlib import Path
import sys

from provide.testkit import HarnessRunner


def run_harness_cli(
    executable: Path,
    args: list[str],
    project_root: Path,
    harness_artifact_name: str,
    test_id: str,
    stdin_input: str | bytes | None = None,
) -> tuple[int, str, str]:
    """
    Runs a test harness CLI command, saves artifacts, and returns results.
    """
    runner = HarnessRunner(project_root / "soup" / "output")
    return runner.run(
        [str(executable)] + args, f"harness_runs/{harness_artifact_name}/{test_id}", stdin=stdin_input
    )


def run_tofusoup_cli(
    args: list[str], project_root: Path, test_id: str, stdin_input: str | bytes | None = None
) -> tuple[int, str, str]:
    """
    Runs the tofusoup CLI command, saves artifacts, and returns results.
    """
    runner = HarnessRunner(project_root / "soup" / "output")
    return runner.run(
        [sys.executable, "-m", "tofusoup.cli"] + args,
        f"cli_runs/tofusoup_cli/{test_id}",
        stdin=stdin_input,
        cwd=project_root,
    )


# 🍲🥄🖥️🪄

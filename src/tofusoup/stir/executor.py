#
# SPDX-FileCopyrightText: Copyright (c) 2025 provide.io llc. All rights reserved.
# SPDX-License-Identifier: Apache-2.0
#

"""Test lifecycle executor for terraform/tofu test suites.

This module manages the execution of individual terraform tests through their complete lifecycle.

Test Status States
------------------
The executor tracks tests through multiple states, distinguished by their outcome:

FAIL (❌):
    Expected failure - A terraform/tofu command (init, apply, destroy) returned a non-zero
    exit code. This is a normal test failure where the infrastructure code has an issue.
    Examples: Invalid HCL syntax, missing provider, resource creation failure.

ERROR (🔥):
    Unexpected exception - The test harness itself encountered an unexpected error or
    exception during test execution. This indicates a problem with the test framework,
    not the terraform code being tested.
    Examples: Python exception, file system error, async task failure.

Other States:
    PENDING (💤): Test queued, not yet started
    CLEANING (🧹): Removing old .terraform directories
    INIT (🔄): Running terraform init
    APPLYING (🚀): Running terraform apply
    ANALYZING (🔬): Parsing terraform state output
    DESTROYING (💥): Running terraform destroy
    SKIPPED (⏭️): Test skipped (no .tf files found)
    PASS (✅): Test completed successfully
"""

import asyncio
import json
from pathlib import Path
import shutil
from time import monotonic

from tofusoup.stir.config import LOGS_DIR, MAX_CONCURRENT_TESTS
from tofusoup.stir.display import console, test_statuses
from tofusoup.stir.models import TestResult
from tofusoup.stir.runtime import StirRuntime
from tofusoup.stir.terraform import run_terraform_command


async def run_test_lifecycle(
    directory: Path, semaphore: asyncio.Semaphore, runtime: StirRuntime
) -> TestResult:
    """Execute the full lifecycle of a Terraform test."""
    dir_name = directory.name
    start_time = monotonic()

    async with semaphore:
        try:
            if not any(directory.glob("*.tf")):
                test_statuses[dir_name].update(
                    text="SKIPPED",
                    style="dim",
                    active=False,
                    success=True,
                    skipped=True,
                    start_time=start_time,
                    end_time=monotonic(),
                )
                return TestResult(
                    directory=dir_name,
                    success=True,
                    skipped=True,
                    start_time=start_time,
                    end_time=monotonic(),
                )

            test_statuses[dir_name].update(
                text="CLEANING",
                style="dim yellow",
                active=True,
                last_log="",
                start_time=start_time,
            )
            for pattern in [".terraform*", "terraform.tfstate*", ".soup"]:
                for path in directory.glob(pattern):
                    if path.is_dir():
                        await asyncio.to_thread(shutil.rmtree, path, ignore_errors=True)
                    else:
                        await asyncio.to_thread(path.unlink, missing_ok=True)

            test_statuses[dir_name].update(text="INIT", style="yellow")

            # Use providers that were pre-downloaded by runtime
            runtime.validate_ready()

            init_rc, _, _, _, _, _ = await run_terraform_command(
                directory, ["init", "-no-color", "-input=false"], runtime=runtime
            )
            if init_rc != 0:
                end_time = monotonic()
                test_statuses[dir_name].update(
                    text="FAIL",
                    style="bold red",
                    active=False,
                    success=False,
                    end_time=end_time,
                )
                return TestResult(
                    directory=dir_name,
                    success=False,
                    skipped=False,
                    start_time=start_time,
                    end_time=end_time,
                )

            test_statuses[dir_name].update(text="APPLYING", style="blue")
            (
                apply_rc,
                _,
                stdout_log,
                stderr_log,
                tf_log,
                parsed_logs,
            ) = await run_terraform_command(
                directory, ["apply", "-input=false", "-auto-approve"], runtime=runtime, tail_log=True
            )

            if apply_rc == 0:
                test_statuses[dir_name].update(text="ANALYZING", style="magenta")
                show_rc, show_stdout, _, _, _, _ = await run_terraform_command(
                    directory, ["show", "-json"], runtime=runtime, capture_stdout=True
                )

                if show_rc == 0:
                    try:
                        state = json.loads(show_stdout)
                        test_statuses[dir_name]["providers"] = len(state.get("provider_configs", {}))
                        root_module = state.get("values", {}).get("root_module", {})
                        resources = [r for r in root_module.get("resources", []) if r.get("mode") == "managed"]
                        data_sources = [r for r in root_module.get("resources", []) if r.get("mode") == "data"]
                        test_statuses[dir_name]["resources"] = len(resources)
                        test_statuses[dir_name]["data_sources"] = len(data_sources)
                        test_statuses[dir_name]["outputs"] = len(state.get("values", {}).get("outputs", {}))
                    except json.JSONDecodeError:
                        pass

                test_statuses[dir_name].update(text="DESTROYING", style="dim green")
                await run_terraform_command(
                    directory,
                    ["destroy", "-auto-approve", "-input=false"],
                    runtime=runtime,
                    tail_log=True,
                )
                end_time = monotonic()
                test_statuses[dir_name].update(
                    text="PASS",
                    style="bold green",
                    active=False,
                    success=True,
                    end_time=end_time,
                )

                status = test_statuses[dir_name]
                return TestResult(
                    directory=dir_name,
                    success=True,
                    skipped=False,
                    start_time=start_time,
                    end_time=end_time,
                    stdout_log_path=stdout_log,
                    stderr_log_path=stderr_log,
                    tf_log_path=tf_log,
                    parsed_logs=parsed_logs,
                    outputs=status.get("outputs", 0),
                    has_warnings=status.get("has_warnings", False),
                    providers=status.get("providers", 0),
                    resources=status.get("resources", 0),
                    data_sources=status.get("data_sources", 0),
                    functions=status.get("functions", 0),
                    ephemeral_functions=status.get("ephemeral_functions", 0),
                )
            else:
                test_statuses[dir_name].update(text="DESTROYING", style="dim red")
                await run_terraform_command(
                    directory,
                    ["destroy", "-auto-approve", "-input=false"],
                    runtime=runtime,
                    tail_log=True,
                )
                end_time = monotonic()
                test_statuses[dir_name].update(
                    text="FAIL",
                    style="bold red",
                    active=False,
                    success=False,
                    end_time=end_time,
                )

                status = test_statuses[dir_name]
                return TestResult(
                    directory=dir_name,
                    success=False,
                    skipped=False,
                    start_time=start_time,
                    end_time=end_time,
                    stdout_log_path=stdout_log,
                    stderr_log_path=stderr_log,
                    tf_log_path=tf_log,
                    parsed_logs=parsed_logs,
                    outputs=status.get("outputs", 0),
                    has_warnings=status.get("has_warnings", False),
                    providers=status.get("providers", 0),
                    resources=status.get("resources", 0),
                    data_sources=status.get("data_sources", 0),
                    functions=status.get("functions", 0),
                    ephemeral_functions=status.get("ephemeral_functions", 0),
                )

        except Exception:
            console.print_exception()
            end_time = monotonic()
            test_statuses[dir_name].update(
                text="ERROR",
                style="bold red",
                active=False,
                success=False,
                end_time=end_time,
            )
            return TestResult(
                directory=dir_name,
                success=False,
                skipped=False,
                start_time=start_time,
                end_time=end_time,
            )


def initialize_tests(test_dirs: list[Path]) -> None:
    """Initialize test directories and status tracking.

    Color Scheme for Phase Text:
    - dim: Inactive/skipped states (PENDING, SKIPPED)
    - dim yellow: Preparatory active phase (CLEANING)
    - yellow: Initialization active phase (INIT)
    - blue: Main execution phase (APPLYING)
    - magenta: Analysis phase (ANALYZING)
    - dim green: Cleanup after success (DESTROYING on success path)
    - bold green: Final success state (PASS)
    - dim red: Cleanup after failure (DESTROYING on failure path)
    - bold red: Final failure states (FAIL, ERROR)
    """
    LOGS_DIR.mkdir(parents=True, exist_ok=True)
    for d in test_dirs:
        test_statuses[d.name] = {
            "text": "PENDING",
            "style": "dim",
            "active": False,
            "success": False,
            "skipped": False,
            "start_time": None,
            "end_time": None,
            "last_log": "",
            "outputs": 0,
            "has_warnings": False,
            "providers": 0,
            "resources": 0,
            "data_sources": 0,
            "functions": 0,
            "ephemeral_functions": 0,
        }


async def execute_tests(test_dirs: list[Path], runtime: StirRuntime) -> list[TestResult | Exception]:
    """Execute all tests concurrently."""
    semaphore = asyncio.Semaphore(MAX_CONCURRENT_TESTS)
    tasks = [run_test_lifecycle(d, semaphore, runtime) for d in test_dirs]
    return await asyncio.gather(*tasks, return_exceptions=True)


# 🥣🔬🔚

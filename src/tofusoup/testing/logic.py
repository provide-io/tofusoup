#
# SPDX-FileCopyrightText: Copyright (c) provide.io llc. All rights reserved.
# SPDX-License-Identifier: Apache-2.0
#


import asyncio
import json
import os
import pathlib
import sys
from typing import Any, cast

import attrs
from provide.foundation import logger
from provide.foundation.errors import ResourceError, ValidationError, error_boundary

from tofusoup.common.exceptions import TofuSoupError
from tofusoup.harness.logic import ensure_go_harness_build


@attrs.define(frozen=True)
class TestSuiteResult:
    suite_name: str
    success: bool
    duration: float
    passed: int
    failed: int
    skipped: int
    errors: int
    failures: list[dict[str, Any]] = attrs.field(factory=list)


TEST_SUITE_CONFIG = {
    "cty": {
        "path": "conformance/cty",
        "description": "CTY compatibility tests",
        "required_harnesses": ["soup-go"],
    },
    "wire": {
        "path": "conformance/wire",
        "description": "Terraform Wire Protocol tests",
        "required_harnesses": ["soup-go"],
    },
    "rpc": {
        "path": "conformance/rpc",
        "description": "RPC compatibility tests",
        "required_harnesses": ["soup-go"],
    },
    "hcl": {
        "path": "conformance/hcl",
        "description": "HCL compatibility tests",
        "required_harnesses": ["soup-go"],
    },
}


async def _run_pytest_suite(
    suite_name: str,
    project_root: pathlib.Path,
    suite_path_relative: str,
    pytest_args: list[str],
    env_vars: dict[str, Any],
) -> TestSuiteResult:
    pytest_target_path = project_root / suite_path_relative
    if not pytest_target_path.exists():
        raise TofuSoupError(f"Test suite path not found: {pytest_target_path}")

    # Use project-specific temp directory for test reports
    reports_dir = project_root / "soup" / "output" / "test-reports"
    reports_dir.mkdir(parents=True, exist_ok=True)

    # Create unique report file name to support parallel test execution
    report_path = reports_dir / f"{suite_name}-report-{os.getpid()}.json"

    # Corrected invocation: Use `-o` to override configuration for this specific run.
    # This is the correct way to tell this pytest session to only find `souptest_` files.
    command = [
        sys.executable,
        "-m",
        "pytest",
        "--json-report",
        f"--json-report-file={report_path}",
        "-o",
        "python_files=souptest_*.py",
        *pytest_args,
        str(pytest_target_path),
    ]

    current_env = os.environ.copy()
    current_env.update({k: str(v) for k, v in env_vars.items()})

    logger.debug(f"Running pytest with command: {' '.join(command)}", env=current_env)

    process = await asyncio.create_subprocess_exec(
        *command, cwd=str(project_root), stdout=None, stderr=None, env=current_env
    )
    await process.wait()

    def _get_fallback_result() -> TestSuiteResult:
        return TestSuiteResult(
            suite_name=suite_name,
            success=False,
            duration=0,
            passed=0,
            failed=1,
            skipped=0,
            errors=1,
            failures=[{"nodeid": "runner_error", "longrepr": "Test report processing failed"}],
        )

    def _process_test_report() -> TestSuiteResult:
        try:
            with report_path.open() as f:
                report_content = f.read()
                if not report_content:
                    raise ValidationError("Empty test report file")
                report = json.loads(report_content)
        except FileNotFoundError as e:
            raise ResourceError(f"Test report file not found: {report_path}") from e
        except json.JSONDecodeError as e:
            raise ValidationError(f"Invalid JSON in test report: {e}") from e

        summary = report.get("summary", {})
        failures = [test for test in report.get("tests", []) if test.get("outcome") in ("failed", "error")]
        return TestSuiteResult(
            suite_name=suite_name,
            success=(report.get("exitcode", 1) == 0),
            duration=report.get("duration", 0.0),
            passed=summary.get("passed", 0),
            failed=summary.get("failed", 0),
            skipped=summary.get("skipped", 0),
            errors=len(report.get("errors", [])),
            failures=failures,
        )

    try:
        with error_boundary(
            Exception,
            fallback=_get_fallback_result(),
            log_errors=True,
            reraise=False,
        ):
            return _process_test_report()
        # If error_boundary caught an exception, return fallback
        return _get_fallback_result()
    finally:
        # Keep report files for debugging - they're in a well-organized location
        # and will be cleaned up by project cleanup scripts if needed
        logger.debug(f"Test report saved to {report_path}")


async def run_test_suite(
    suite_name: str,
    project_root: pathlib.Path,
    loaded_config: dict[str, Any],
    verbose: bool,
    pytest_options: list[str] | None = None,
) -> TestSuiteResult:
    if suite_name not in TEST_SUITE_CONFIG:
        raise TofuSoupError(f"Test suite '{suite_name}' is not defined.")

    suite_cfg = TEST_SUITE_CONFIG[suite_name]
    for harness_key in suite_cfg.get("required_harnesses", []):
        if harness_key.startswith("go-") or harness_key == "soup-go":
            ensure_go_harness_build(harness_key, project_root, loaded_config)

    suite_defaults = loaded_config.get("test_suite_defaults", {})
    suite_specific = loaded_config.get("test_suite", {}).get(suite_name, {})

    env_vars = {
        **suite_defaults.get("env_vars", {}),
        **suite_specific.get("env_vars", {}),
    }

    pytest_args = ["-v"] if verbose else []
    if pytest_options:
        pytest_args.extend(pytest_options)

    suite_path = cast(str, suite_cfg["path"])
    return await _run_pytest_suite(suite_name, project_root, suite_path, pytest_args, env_vars)


async def run_all_test_suites(
    project_root: pathlib.Path, loaded_config: dict[str, Any], verbose: bool
) -> list[TestSuiteResult]:
    tasks = [run_test_suite(name, project_root, loaded_config, verbose, None) for name in TEST_SUITE_CONFIG]
    return await asyncio.gather(*tasks)


# 🥣🔬🔚

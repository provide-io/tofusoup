#
# SPDX-FileCopyrightText: Copyright (c) 2025 provide.io llc. All rights reserved.
# SPDX-License-Identifier: Apache-2.0
#

"""TODO: Add module docstring."""

from pathlib import Path
from typing import Any, NamedTuple


class StirTestResult(NamedTuple):
    """Represents the result of running a single test."""

    directory: str
    success: bool
    skipped: bool
    start_time: float
    end_time: float
    stdout_log_path: Path | None = None
    stderr_log_path: Path | None = None
    tf_log_path: Path | None = None
    parsed_logs: list[dict[str, Any]] = []  # noqa: RUF012
    outputs: int = 0
    has_warnings: bool = False
    providers: int = 0
    resources: int = 0
    data_sources: int = 0
    functions: int = 0
    ephemeral_functions: int = 0
    failed_stage: str | None = None
    error_message: str | None = None


# Backwards compatibility alias
TestResult = StirTestResult

# 🥣🔬🔚

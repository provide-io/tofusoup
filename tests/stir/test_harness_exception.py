#
# SPDX-FileCopyrightText: Copyright (c) provide.io llc. All rights reserved.
# SPDX-License-Identifier: Apache-2.0
#

"""A crash in the harness has to say what it was.

`run_test_lifecycle` catches every exception, and what it did with one was
print it to the console and return a result carrying nothing: no log paths, no
counts, no message. On a terminal the traceback lands inside the Live region the
status table is repainting, and in a CI log it does not survive at all -- so the
run reports

    ❌  ❌  44/45  wait_for_file  0.0s  0 0 0 0 0

and the failure report says "No specific error messages found in log. The
failure may have been a crash." It was a crash, and the harness knew which one.

`StirTestResult` has carried `error_message` and `failed_stage` fields the whole
time. Nothing set them.
"""

from __future__ import annotations

from pathlib import Path
from unittest.mock import patch

import pytest

from tofusoup.stir.display import test_statuses
from tofusoup.stir.executor import run_test_lifecycle
from tofusoup.stir.models import StirTestResult
from tofusoup.stir.reporting import print_failure_report

MODULE = "tofusoup.stir.executor"


@pytest.fixture(autouse=True)
def _status_row() -> None:
    test_statuses["example"] = {}
    yield
    test_statuses.pop("example", None)


@pytest.mark.unit
@pytest.mark.asyncio
async def test_a_harness_crash_records_what_it_was(tmp_path: Path) -> None:
    """The exception reaches the result rather than only the console."""
    import asyncio

    directory = tmp_path / "example"
    directory.mkdir()
    (directory / "main.tf").write_text("")

    with patch(f"{MODULE}.load_requirements", side_effect=RuntimeError("sidecar exploded")):
        result = await run_test_lifecycle(directory, asyncio.Semaphore(1), None)

    assert result.success is False
    assert result.skipped is False
    assert result.error_message is not None
    assert "sidecar exploded" in result.error_message
    assert "RuntimeError" in result.error_message
    assert result.failed_stage == "harness"


@pytest.mark.unit
def test_the_failure_report_prints_the_recorded_crash(capsys: pytest.CaptureFixture[str]) -> None:
    """A recorded crash is what the report shows, not the generic line."""
    result = StirTestResult(
        directory="example",
        success=False,
        skipped=False,
        start_time=0.0,
        end_time=0.0,
        error_message='RuntimeError: sidecar exploded\n  File "executor.py", line 1',
        failed_stage="harness",
    )

    print_failure_report(result)
    out = capsys.readouterr().out

    assert "sidecar exploded" in out
    assert "No specific error messages found in log" not in out

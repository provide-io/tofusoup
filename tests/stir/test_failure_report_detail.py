#
# SPDX-FileCopyrightText: Copyright (c) provide.io llc. All rights reserved.
# SPDX-License-Identifier: Apache-2.0
#

"""A failure report has to show what it already captured.

stir writes stdout, stderr and the TF_LOG stream for every command it runs, and
keeps all three paths on the result. The report read one of them: `parsed_logs`,
filtered to entries with `@level` in ("error", "critical"). Anything that failed
without producing such an entry -- an engine that crashed, a plugin that died, a
message written to stderr as plain text -- left the report with nothing, and it
said so:

    No specific error messages found in log. The failure may have been a crash.

The specific error was in the stderr file the whole time, unread and unnamed.
"""

from __future__ import annotations

from pathlib import Path

import pytest

from tofusoup.stir.models import StirTestResult
from tofusoup.stir.reporting import print_failure_report


def _result(**kwargs: object) -> StirTestResult:
    base = {
        "directory": "example",
        "success": False,
        "skipped": False,
        "start_time": 0.0,
        "end_time": 1.0,
    }
    base.update(kwargs)
    return StirTestResult(**base)  # type: ignore[arg-type]


@pytest.mark.unit
def test_stderr_is_shown_when_no_error_events_were_parsed(
    tmp_path: Path, capsys: pytest.CaptureFixture[str]
) -> None:
    """The captured stderr is the answer, so print it."""
    stderr = tmp_path / "stderr.log"
    stderr.write_text("Error: Failed to load plugin schemas\n\nplugin crashed\n")

    print_failure_report(_result(stderr_log_path=stderr, parsed_logs=[]))
    out = capsys.readouterr().out

    assert "Failed to load plugin schemas" in out
    assert "No specific error messages found in log" not in out


@pytest.mark.unit
def test_stdout_is_shown_when_stderr_is_empty(tmp_path: Path, capsys: pytest.CaptureFixture[str]) -> None:
    """Some engines put the diagnostic on stdout; an empty stderr is not the end."""
    stderr = tmp_path / "stderr.log"
    stderr.write_text("")
    stdout = tmp_path / "stdout.log"
    stdout.write_text("Error: Unsupported block type\n")

    print_failure_report(_result(stderr_log_path=stderr, stdout_log_path=stdout, parsed_logs=[]))
    out = capsys.readouterr().out

    assert "Unsupported block type" in out


@pytest.mark.unit
def test_the_generic_line_survives_when_there_is_genuinely_nothing(
    capsys: pytest.CaptureFixture[str],
) -> None:
    """No logs at all is still a real state, and still worth saying."""
    print_failure_report(_result(parsed_logs=[]))
    out = capsys.readouterr().out

    assert "No specific error messages found" in out


@pytest.mark.unit
def test_every_captured_log_path_is_named(tmp_path: Path, capsys: pytest.CaptureFixture[str]) -> None:
    """Whatever is printed, say where the rest of it lives."""
    stderr = tmp_path / "stderr.log"
    stderr.write_text("boom\n")
    stdout = tmp_path / "stdout.log"
    stdout.write_text("out\n")
    tf_log = tmp_path / "terraform.log"
    tf_log.write_text("{}\n")

    print_failure_report(
        _result(stderr_log_path=stderr, stdout_log_path=stdout, tf_log_path=tf_log, parsed_logs=[])
    )
    out = capsys.readouterr().out

    for path in (stderr, stdout, tf_log):
        assert path.name in out

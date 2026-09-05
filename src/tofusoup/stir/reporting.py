#
# SPDX-FileCopyrightText: Copyright (c) provide.io llc. All rights reserved.
# SPDX-License-Identifier: Apache-2.0
#

"""Test result reporting and display utilities."""

import json
from pathlib import Path

from rich.panel import Panel
from rich.syntax import Syntax
from rich.table import Table
from rich.text import Text

from tofusoup.stir.display import console
from tofusoup.stir.models import TestResult


def print_failure_report(result: TestResult) -> None:
    """Print a detailed failure report for a failed test."""
    title = f"🚨 Failure Report for {result.directory} "
    console.print(f"[bold red]{title.center(80, '─')}[/bold red]")

    error_logs = [log for log in result.parsed_logs if log.get("@level") in ("error", "critical")]

    # A crash in the harness leaves no Terraform log to parse -- it can happen
    # before a single command runs -- so the recorded exception is the only
    # thing that explains the row. Printed first, and instead of the generic
    # line: "the failure may have been a crash" next to a traceback reads as
    # though the two were unrelated.
    if result.error_message:
        console.print(Text.from_markup(f"\n[bold]Harness error ({result.failed_stage or 'unknown'}):[/bold]"))
        console.print(Text(result.error_message))
    elif not error_logs:
        _print_captured_output(result)
    else:
        console.print(Text.from_markup(f"\n[bold]Error Log Events ({len(error_logs)} found):[/bold]"))
        for error_log in error_logs:
            console.print(
                Syntax(
                    json.dumps(error_log, indent=2),
                    "json",
                    theme="monokai",
                    line_numbers=False,
                    word_wrap=True,
                )
            )
            console.print("-" * 20)

    _print_log_paths(result)

    console.print("\n" + "─" * 80 + "\n")


def print_summary_panel(total_tests: int, failed_tests: int, skipped_tests: int, duration: float) -> None:
    """Print a summary panel with test results."""
    passed_tests = total_tests - failed_tests - skipped_tests
    success = failed_tests == 0

    title = (
        "✨ [bold green]All Tests Passed[/bold green]"
        if success
        else "🔥 [bold red]Some Tests Failed[/bold red]"
    )
    border_style = "green" if success else "red"

    summary_table = Table.grid(padding=(0, 2))
    summary_table.add_column()
    summary_table.add_column(justify="right")
    summary_table.add_row("Total tests:", f"[bold]{total_tests}[/bold]")
    summary_table.add_row("Passed:", f"[green]{passed_tests}[/green]")
    summary_table.add_row("Failed:", f"[red]{failed_tests}[/red]")
    summary_table.add_row("Skipped:", f"[dim]{skipped_tests}[/dim]")
    summary_table.add_row("Duration:", f"{duration:.2f}s")

    console.print(
        Panel(
            summary_table,
            title=title,
            border_style=border_style,
            expand=False,
            padding=(1, 2),
        )
    )


#: How much of a captured stream to show inline. Enough to carry the
#: diagnostic and its context; the file is named for the rest.
_TAIL_LINES = 40


def _tail(path: Path | None) -> str:
    """The last few lines of a captured stream, or "" if there are none."""
    if path is None:
        return ""
    try:
        content = path.read_text(errors="replace")
    except OSError:
        return ""
    lines = content.splitlines()
    return "\n".join(lines[-_TAIL_LINES:]).strip()


def _print_captured_output(result: TestResult) -> None:
    """Show what was captured when nothing parsed as an error event.

    `parsed_logs` holds the TF_LOG JSON stream, and only entries at level
    error or critical reach the report. A failure that never produced one --
    an engine that crashed, a plugin that died, a diagnostic written to stderr
    as plain text -- used to print "the failure may have been a crash" and
    stop, while the actual message sat unread in a file stir had already
    written.

    stderr first, because that is where an engine puts a diagnostic; stdout
    second, because some of them do not.
    """
    for label, path in (("stderr", result.stderr_log_path), ("stdout", result.stdout_log_path)):
        tail = _tail(path)
        if tail:
            console.print(Text.from_markup(f"\n[bold]Captured {label} (last {_TAIL_LINES} lines):[/bold]"))
            console.print(Text(tail))
            return

    console.print(
        "[yellow]No specific error messages found in log, and nothing was captured on "
        "stdout or stderr. The failure may have been a crash.[/yellow]"
    )


def _print_log_paths(result: TestResult) -> None:
    """Name every log this run kept, so the rest of it can be read."""
    paths = (
        ("Full Terraform Log", result.tf_log_path),
        ("stderr", result.stderr_log_path),
        ("stdout", result.stdout_log_path),
    )
    named = [(label, path) for label, path in paths if path]
    if not named:
        return
    console.print(Text.from_markup("\n[bold]Logs:[/bold]"))
    for label, path in named:
        console.print(Text.from_markup(f"  {label}: [yellow]{path}[/yellow]"))


# 🥣🔬🔚

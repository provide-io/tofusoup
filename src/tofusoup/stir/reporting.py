#
# SPDX-FileCopyrightText: Copyright (c) provide.io llc. All rights reserved.
# SPDX-License-Identifier: Apache-2.0
#

"""Test result reporting and display utilities."""

import json

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

    if not error_logs:
        console.print(
            "[yellow]No specific error messages found in log. The failure may have been a crash.[/yellow]"
        )
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

    if result.tf_log_path:
        console.print(
            Text.from_markup(f"\n[bold]Full Terraform Log:[/bold] [yellow]{result.tf_log_path}[/yellow]")
        )

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


# 🥣🔬🔚

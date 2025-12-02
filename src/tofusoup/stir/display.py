#
# SPDX-FileCopyrightText: Copyright (c) provide.io llc. All rights reserved.
# SPDX-License-Identifier: Apache-2.0
#

"""Display utilities for test execution and status tracking."""

import asyncio
from time import monotonic
from typing import Any

from rich.console import Console
from rich.live import Live
from rich.table import Table

from tofusoup.stir.config import PHASE_EMOJI

# Shared state for the live display
test_statuses: dict[str, dict[str, Any]] = {}

# Rich Console Initialization
console = Console(record=True)


def _get_sorted_status_items() -> list[tuple[str, dict[str, Any]]]:
    """Sort status items with __PROVIDER_PREP__ first if it exists."""
    sorted_items = []
    provider_prep_item = None

    for directory, status_info in test_statuses.items():
        if directory == "__PROVIDER_PREP__":
            provider_prep_item = (directory, status_info)
        else:
            sorted_items.append((directory, status_info))

    sorted_items = sorted(sorted_items)

    if provider_prep_item:
        sorted_items.insert(0, provider_prep_item)

    return sorted_items


def _get_status_emoji(status_info: dict[str, Any]) -> str:
    """Get the status emoji based on test state.

    States:
    - 💤 Pending: Test queued but not yet started (PENDING phase)
    - 🔄 Active: Test currently running
    - ⚠️  Active with warnings: Test running but warnings detected
    - ⏭️  Skipped: Test was skipped (no .tf files)
    - ✅ Success: Test passed
    - ❌ Fail: Test failed (terraform command returned non-zero)
    """
    # Check if test is pending (queued but not started)
    phase_text = status_info.get("text", "")
    if phase_text == "PENDING":
        return "[dim]💤[/dim]"

    # Active tests (currently running)
    if status_info.get("active"):
        return "[yellow]🔄[/yellow]" if not status_info.get("has_warnings") else "[yellow]⚠️[/yellow]"

    # Completed states
    elif status_info.get("skipped"):
        return "[dim]⏭️[/dim]"
    elif status_info.get("success"):
        return "[green]✅[/green]"
    else:
        # Only show red X if test has actually failed (not pending)
        return "[red]❌[/red]"


def _calculate_elapsed_time(start_time: float | None, end_time: float | None) -> str:
    """Calculate elapsed time string."""
    if not start_time:
        return ""
    actual_end_time = end_time or monotonic()
    elapsed = actual_end_time - start_time
    return f"{elapsed:.1f}s"


def generate_status_table() -> Table:
    """Generate a rich table showing current test status."""
    table = Table(box=None, expand=True, show_header=True)
    table.add_column("Status", justify="center", width=4)
    table.add_column("Phase", justify="center", width=4)
    table.add_column("#", justify="center", style="dim", width=7)  # Test number indicator
    table.add_column("Test Suite", justify="left", style="cyan", no_wrap=True, ratio=2)
    table.add_column("Elapsed", justify="right", style="magenta", width=10)
    table.add_column("Prov", justify="center", style="blue", width=5)
    table.add_column("Res", justify="center", style="blue", width=5)
    table.add_column("Data", justify="center", style="blue", width=5)
    table.add_column("Func", justify="center", style="blue", width=5)

    show_eph_func_col = any(status.get("ephemeral_functions", 0) > 0 for status in test_statuses.values())
    if show_eph_func_col:
        table.add_column("Eph. Func", justify="center", style="blue", width=9)

    table.add_column("Outs", justify="center", style="blue", width=5)
    table.add_column("Last Log", justify="left", style="yellow", ratio=5)

    # Get sorted items and calculate total test count (excluding provider prep)
    sorted_items = _get_sorted_status_items()
    total_tests = sum(1 for directory, _ in sorted_items if directory != "__PROVIDER_PREP__")

    test_number = 0
    for directory, status_info in sorted_items:
        phase_text = status_info["text"]
        last_log = status_info.get("last_log", "")

        elapsed_str = _calculate_elapsed_time(status_info.get("start_time"), status_info.get("end_time"))
        phase_emoji = PHASE_EMOJI.get(phase_text.split(" ")[-1], "❓")
        status_emoji = _get_status_emoji(status_info)

        # Calculate test number (skip provider prep)
        if directory != "__PROVIDER_PREP__":
            test_number += 1
            test_num_str = f"[dim]{test_number}/{total_tests}[/dim]"
        else:
            test_num_str = ""

        # Special formatting for provider prep row
        display_name = (
            "[bold magenta]Provider Cache Preparation[/bold magenta]"
            if directory == "__PROVIDER_PREP__"
            else f"[bold]{directory}[/bold]"
        )

        row_data = [
            status_emoji,
            phase_emoji,
            test_num_str,
            display_name,
            elapsed_str,
            str(status_info.get("providers", "")),
            str(status_info.get("resources", "")),
            str(status_info.get("data_sources", "")),
            str(status_info.get("functions", "")),
        ]
        if show_eph_func_col:
            row_data.append(str(status_info.get("ephemeral_functions", "")))
        row_data.extend([str(status_info.get("outputs", "")), last_log])
        table.add_row(*row_data)

    return table


async def live_updater(live_display: Live, stop_event: asyncio.Event) -> None:
    """Update the live display with current test statuses."""
    while not stop_event.is_set():
        live_display.update(generate_status_table())
        await asyncio.sleep(1 / 0.77)  # ~1.3 seconds to match 0.77 Hz refresh rate


# 🥣🔬🔚

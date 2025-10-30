#
# SPDX-FileCopyrightText: Copyright (c) 2025 provide.io llc. All rights reserved.
# SPDX-License-Identifier: Apache-2.0
#

"""TODO: Add module docstring."""

import asyncio
from pathlib import Path
import sys
from time import monotonic

import click

from tofusoup.stir.config import MAX_CONCURRENT_TESTS, STIR_PLUGIN_CACHE_DIR
from tofusoup.stir.discovery import TestDiscovery, TestFilter
from tofusoup.stir.display import console
from tofusoup.stir.executor import execute_tests, initialize_tests
from tofusoup.stir.models import TestResult
from tofusoup.stir.reporting import print_failure_report, print_summary_panel
from tofusoup.stir.runtime import StirRuntime


def process_results(results: list[TestResult | Exception]) -> tuple[list[TestResult], int, bool]:
    """Process test results and return failure analysis."""
    failed_tests = []
    skipped_count = 0
    all_passed = True

    for res in results:
        if isinstance(res, TestResult):
            if res.skipped:
                skipped_count += 1
            elif not res.success:
                all_passed = False
                failed_tests.append(res)
        elif res and not isinstance(res, asyncio.CancelledError):
            all_passed = False
            console.print(f"[bold red]CRITICAL ERROR in test runner:[/bold red] {res}")

    if failed_tests:
        console.print("\n[bold red]📊 Failure Analysis:[/bold red]")
        for failure in failed_tests:
            print_failure_report(failure)

    return failed_tests, skipped_count, all_passed


async def main(
    target_path: str,
    runtime: StirRuntime,
    patterns: list[str] | None = None,
    recursive: bool = False,
    path_filters: list[str] | None = None,
    tags: list[str] | None = None,
    types: list[str] | None = None,
    regex_pattern: str | None = None,
) -> None:
    """Main execution function for stir tests.

    Args:
        target_path: Base directory for test discovery
        runtime: StirRuntime instance for test execution
        patterns: Glob patterns for test file discovery
        recursive: Whether to search recursively
        path_filters: Path-based filters
        tags: Tag-based filters
        types: Component type filters
        regex_pattern: Regex pattern for filtering
    """
    from rich.live import Live

    from tofusoup.stir.display import generate_status_table, live_updater

    start_time = monotonic()
    base_dir = Path(target_path).resolve()

    # Use enhanced test discovery
    discoverer = TestDiscovery(patterns=patterns, recursive=recursive)
    test_dirs = discoverer.discover_tests(base_dir)

    # Apply filters if provided
    if any([path_filters, tags, types, regex_pattern]):
        test_filter = TestFilter(
            path_filters=path_filters, tags=tags, types=types, regex_pattern=regex_pattern
        )
        test_dirs = test_filter.filter_tests(test_dirs)

    if not test_dirs:
        console.print(f"🤷 No directories found in '{base_dir}'.")
        return

    # Initialize test directories for status tracking
    initialize_tests(test_dirs)

    # Start live display with optimal refresh rate for smooth updates without flickering
    # Banner and info will be shown in the live display context to avoid conflicts
    stop_event = asyncio.Event()
    with Live(generate_status_table(), console=console, refresh_per_second=0.77) as live_display:
        # Show banner once inside live context (won't conflict with table updates)
        console.print("[bold]🚀 Tofusoup Stir[/bold]")
        console.print(
            f"Found {len(test_dirs)} test suites in '{base_dir}'. Running up to {MAX_CONCURRENT_TESTS} in parallel..."
        )
        console.print()  # Empty line for spacing
        # Start the live updater task
        updater_task = asyncio.create_task(live_updater(live_display, stop_event))

        try:
            # Phase 1: Provider preparation (serial) - now with live display active
            await runtime.prepare_providers(test_dirs)

            # Remove provider prep entry after completion to avoid clutter
            from tofusoup.stir.display import test_statuses

            test_statuses.pop("__PROVIDER_PREP__", None)

            # Phase 2: Test execution (parallel)
            results = await execute_tests(test_dirs, runtime)
        finally:
            # Stop the live updater
            stop_event.set()
            await updater_task

    failed_tests, skipped_count, all_passed = process_results(results)

    duration = monotonic() - start_time
    print_summary_panel(len(test_dirs), len(failed_tests), skipped_count, duration)

    if not all_passed:
        sys.exit(1)


@click.command("stir")
@click.argument(
    "path",
    default=".",
    type=click.Path(exists=True, file_okay=False, resolve_path=True),
)
@click.option(
    "--pattern",
    multiple=True,
    help="Glob pattern for test file discovery (can be used multiple times)",
)
@click.option(
    "--recursive",
    is_flag=True,
    help="Search for tests recursively in subdirectories",
)
@click.option(
    "--filter",
    "path_filters",
    multiple=True,
    help="Path-based filter for tests (e.g., 'function/*', '!slow/*')",
)
@click.option(
    "--tags",
    multiple=True,
    help="Filter tests by tags (e.g., 'basic', '!slow')",
)
@click.option(
    "--type",
    "types",
    multiple=True,
    help="Filter by component type (data_source, resource, function)",
)
@click.option(
    "--regex",
    "regex_pattern",
    help="Regular expression pattern to filter test paths",
)
@click.option(
    "--matrix",
    is_flag=True,
    help="Run tests across multiple tool version combinations defined in soup.toml",
)
@click.option(
    "--matrix-output",
    type=click.Path(dir_okay=False),
    help="Save matrix test results to JSON file",
)
@click.option(
    "--json",
    "output_json",
    is_flag=True,
    help="Output results in JSON format",
)
@click.option(
    "--upgrade",
    is_flag=True,
    help="Force upgrade providers to latest versions",
)
@click.option(
    "--no-cache",
    is_flag=True,
    help="Disable plugin caching (downloads providers for each test)",
)
def stir_cli(
    path: str,
    pattern: tuple[str, ...],
    recursive: bool,
    path_filters: tuple[str, ...],
    tags: tuple[str, ...],
    types: tuple[str, ...],
    regex_pattern: str | None,
    matrix: bool,
    matrix_output: str,
    output_json: bool,
    upgrade: bool,
    no_cache: bool,
) -> None:
    """
    Run multi-threaded Terraform tests against all subdirectories in a given PATH.

    When --matrix is used, runs tests across multiple Terraform/OpenTofu versions
    as configured in soup.toml's [workenv.matrix] section or wrkenv.toml's [matrix] section.

    Note: Matrix testing requires the optional wrknv package.
    """
    try:
        # Initialize runtime with configuration
        plugin_cache_dir = None if no_cache else STIR_PLUGIN_CACHE_DIR
        runtime = StirRuntime(plugin_cache_dir=plugin_cache_dir, force_upgrade=upgrade)

        if matrix:
            # Run matrix testing (requires optional workenv dependency)
            try:
                from tofusoup.testing.matrix import WORKENV_AVAILABLE, run_matrix_stir_tests

                if not WORKENV_AVAILABLE:
                    console.print(
                        "[bold red]Error:[/bold red] Matrix testing requires the 'wrknv' package.\n"
                        "[yellow]Install with:[/yellow] pip install wrknv\n"
                        "[yellow]Or from source:[/yellow] pip install -e /path/to/wrknv"
                    )
                    sys.exit(1)

                results = asyncio.run(run_matrix_stir_tests(Path(path)))

                if matrix_output:
                    import json

                    Path(matrix_output).write_text(json.dumps(results, indent=2, default=str))

                if output_json:
                    import json

                    console.print(json.dumps(results, indent=2, default=str))

            except ImportError as e:
                console.print(
                    f"[bold red]Error:[/bold red] {e}\n"
                    "[yellow]Matrix testing is an optional feature.[/yellow]\n"
                    "[yellow]Install with:[/yellow] pip install wrknv or pip install -e /path/to/wrknv"
                )
                sys.exit(1)
        else:
            # Run standard single-version testing with runtime
            asyncio.run(
                main(
                    path,
                    runtime,
                    patterns=list(pattern) if pattern else None,
                    recursive=recursive,
                    path_filters=list(path_filters) if path_filters else None,
                    tags=list(tags) if tags else None,
                    types=list(types) if types else None,
                    regex_pattern=regex_pattern,
                )
            )

    except KeyboardInterrupt:
        console.print("\n[yellow]⚠️ Interrupted by user[/yellow]")
        sys.exit(130)
    except Exception as e:
        console.print(f"[bold red]💥 Fatal error:[/bold red] {e}")
        console.print_exception()
        sys.exit(1)


# 🥣🔬🔚

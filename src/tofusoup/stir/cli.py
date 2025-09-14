#
# tofusoup/stir/cli.py
#

import asyncio
from pathlib import Path
import sys
from time import monotonic

import click

from tofusoup.stir.config import MAX_CONCURRENT_TESTS, STIR_PLUGIN_CACHE_DIR
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


async def main(target_path: str, runtime: StirRuntime) -> None:
    """Main execution function for stir tests."""
    start_time = monotonic()
    base_dir = Path(target_path).resolve()

    test_dirs = []

    # Add regular test directories (non-hidden)
    test_dirs.extend([d for d in base_dir.iterdir() if d.is_dir() and not d.name.startswith(".")])

    # Handle .plating-tests specially - add its subdirectories as test directories
    plating_dir = base_dir / ".plating-tests"
    if plating_dir.is_dir():
        plating_test_dirs = [d for d in plating_dir.iterdir() if d.is_dir()]
        test_dirs.extend(plating_test_dirs)

    # Add base directory if it contains .tf files
    if any(base_dir.glob("*.tf")):
        test_dirs.append(base_dir)

    test_dirs = sorted(test_dirs)

    if not test_dirs:
        console.print(f"🤷 No directories found in '{base_dir}'.")
        return

    # Phase 1: Provider preparation (serial)
    await runtime.prepare_providers(test_dirs)

    # Phase 2: Test execution (parallel)
    initialize_tests(test_dirs)

    console.print("[bold]🚀 Tofusoup Stir[/bold]")
    console.print(
        f"Found {len(test_dirs)} test suites in '{base_dir}'. Running up to {MAX_CONCURRENT_TESTS} in parallel..."
    )

    results = await execute_tests(test_dirs, runtime)
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
def stir_cli(path: str, matrix: bool, matrix_output: str, output_json: bool, upgrade: bool, no_cache: bool) -> None:
    """
    Run multi-threaded Terraform tests against all subdirectories in a given PATH.

    When --matrix is used, runs tests across multiple Terraform/OpenTofu versions
    as configured in soup.toml's [workenv.matrix] section or wrkenv.toml's [matrix] section.
    """
    try:
        # Initialize runtime with configuration
        plugin_cache_dir = None if no_cache else STIR_PLUGIN_CACHE_DIR
        runtime = StirRuntime(plugin_cache_dir=plugin_cache_dir, force_upgrade=upgrade)

        if matrix:
            # Run matrix testing
            from tofusoup.testing.matrix import run_matrix_stir_tests

            results = asyncio.run(run_matrix_stir_tests(Path(path)))

            if matrix_output:
                import json
                with open(matrix_output, "w") as f:
                    json.dump(results, f, indent=2, default=str)
                console.print(f"✅ Matrix results saved to {matrix_output}")

            if output_json:
                import json
                console.print(json.dumps(results, indent=2, default=str))
        else:
            # Run standard single-version testing with runtime
            asyncio.run(main(path, runtime))

    except KeyboardInterrupt:
        console.print("\n[yellow]⚠️ Interrupted by user[/yellow]")
        sys.exit(130)
    except Exception as e:
        console.print(f"[bold red]💥 Fatal error:[/bold red] {e}")
        console.print_exception()
        sys.exit(1)

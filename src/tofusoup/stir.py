#
# tofusoup/stir.py
#
import asyncio
from datetime import UTC, datetime
import json
import os
from pathlib import Path
import re
import shutil
import sys
from time import monotonic
from typing import Any, NamedTuple

import click
from rich.console import Console
from rich.live import Live
from rich.panel import Panel
from rich.syntax import Syntax
from rich.table import Table
from rich.text import Text

# --- Configuration ---
TF_COMMAND = shutil.which("tofu") or shutil.which("terraform") or "tofu"
MAX_CONCURRENT_TESTS = os.cpu_count() or 4
LOGS_DIR = Path("output/")


# --- Data Structures ---
class TestResult(NamedTuple):
    directory: str
    success: bool
    skipped: bool
    start_time: float
    end_time: float
    stdout_log_path: Path | None = None
    stderr_log_path: Path | None = None
    tf_log_path: Path | None = None
    parsed_logs: list[dict[str, Any]] = []
    outputs: int = 0
    has_warnings: bool = False
    providers: int = 0
    resources: int = 0
    data_sources: int = 0
    functions: int = 0
    ephemeral_functions: int = 0


# Shared state for the live display
test_statuses = {}

# --- Rich Console Initialization ---
console = Console(record=True)

PHASE_EMOJI = {
    "PENDING": "⏳",
    "CLEANING": "🧹",
    "INIT": "🔄",
    "APPLYING": "🚀",
    "ANALYZING": "🔬",
    "DESTROYING": "💥",
    "PASS": "✅",
    "FAIL": "❌",
    "ERROR": "🔥",
    "SKIPPED": "⏭️",
}


def generate_status_table() -> Table:
    table = Table(box=None, expand=True, show_header=True)
    table.add_column("Status", justify="center", width=3)
    table.add_column("Phase", justify="center", width=3)
    table.add_column("Test Suite", justify="left", style="cyan", no_wrap=True, ratio=2)
    table.add_column("Elapsed", justify="right", style="magenta", width=10)
    table.add_column("Prov", justify="center", style="blue", width=5)
    table.add_column("Res", justify="center", style="blue", width=5)
    table.add_column("Data", justify="center", style="blue", width=5)
    table.add_column("Func", justify="center", style="blue", width=5)

    show_eph_func_col = any(
        status.get("ephemeral_functions", 0) > 0 for status in test_statuses.values()
    )
    if show_eph_func_col:
        table.add_column("Eph. Func", justify="center", style="blue", width=9)

    table.add_column("Outs", justify="center", style="blue", width=5)
    table.add_column("Last Log", justify="left", style="yellow", ratio=5)

    for directory, status_info in sorted(test_statuses.items()):
        phase_text = status_info["text"]
        last_log = status_info.get("last_log", "")

        start_time = status_info.get("start_time")
        end_time = status_info.get("end_time")

        elapsed_str = ""
        if start_time:
            actual_end_time = end_time or monotonic()
            elapsed = actual_end_time - start_time
            elapsed_str = f"{elapsed:.1f}s"

        phase_emoji = PHASE_EMOJI.get(phase_text.split(" ")[-1], "❓")

        if status_info.get("active"):
            status_emoji = (
                "[yellow]🔄[/yellow]"
                if not status_info.get("has_warnings")
                else "[yellow]⚠️[/yellow]"
            )
        elif status_info.get("skipped"):
            status_emoji = "[dim]⏭️[/dim]"
        elif status_info.get("success"):
            status_emoji = "[green]✅[/green]"
        else:
            status_emoji = "[red]❌[/red]"

        row_data = [
            status_emoji,
            phase_emoji,
            f"[bold]{directory}[/bold]",
            elapsed_str,
            str(status_info.get("providers", "")),
            str(status_info.get("resources", "")),
            str(status_info.get("data_sources", "")),
            str(status_info.get("functions", "")),
        ]
        if show_eph_func_col:
            row_data.append(str(status_info.get("ephemeral_functions", "")))
        row_data.extend(
            [
                str(status_info.get("outputs", "")),
                last_log,
            ]
        )
        table.add_row(*row_data)

    return table


async def _tail_tf_log(
    log_path: Path, process: asyncio.subprocess.Process, dir_name: str
):
    """Asynchronously tails the Terraform JSON log file to update the UI in real-time."""
    try:
        while not await asyncio.to_thread(log_path.exists):
            if process.returncode is not None:
                return
            await asyncio.sleep(0.1)

        with open(log_path, encoding="utf-8") as f:
            while process.returncode is None:
                line = f.readline()
                if line:
                    try:
                        log_entry = json.loads(line)
                        level = log_entry.get("@level", "info")
                        message = log_entry.get("@message", "")

                        if level in ("info", "warn", "error") and message:
                            test_statuses[dir_name]["last_log"] = message

                        if level == "warn":
                            test_statuses[dir_name]["has_warnings"] = True

                        if "CallFunction" in message and "GRPCProvider" in message:
                            if "ephemeral" in message:
                                test_statuses[dir_name]["ephemeral_functions"] += 1
                            else:
                                test_statuses[dir_name]["functions"] += 1
                    except json.JSONDecodeError:
                        continue
                else:
                    await asyncio.sleep(0.1)
    except Exception as e:
        console.log(f"[{dir_name}] Error tailing log: {e}")


async def run_terraform_command(
    directory: Path,
    args: list[str],
    tail_log: bool = False,
    capture_stdout: bool = False,
) -> tuple[int, str, Path, Path, Path, list[dict[str, Any]]]:
    """
    A dedicated runner for Terraform commands that sets up the correct environment,
    captures logs, and can tail the JSON log for live UI updates.
    """
    dir_name = directory.name
    timestamp = datetime.now(UTC).strftime("%Y%m%d-%H%M%S")

    soup_dir = directory / ".soup"
    tf_data_dir = soup_dir / "tfdata"
    logs_dir = soup_dir / "logs"
    logs_dir.mkdir(parents=True, exist_ok=True)
    tf_data_dir.mkdir(parents=True, exist_ok=True)

    tf_log_path = logs_dir / "terraform.log"

    sanitized_dir_name = re.sub(r"[\\/.:]", "_", dir_name)
    cmd_basename = Path(TF_COMMAND).name
    stdout_log_path = (
        LOGS_DIR
        / f"{sanitized_dir_name}.{cmd_basename}.{args[0]}.stdout.{timestamp}.log"
    )
    stderr_log_path = (
        LOGS_DIR
        / f"{sanitized_dir_name}.{cmd_basename}.{args[0]}.stderr.{timestamp}.log"
    )

    env = os.environ.copy()
    env["TF_DATA_DIR"] = str(tf_data_dir)
    env["TF_LOG"] = "JSON"
    env["TF_LOG_PATH"] = str(tf_log_path)
    env["PYVIDER_PRIVATE_STATE_SHARED_SECRET"] = "stir-test-secret"

    command = [TF_COMMAND, *args]

    process = await asyncio.create_subprocess_exec(
        *command,
        stdout=asyncio.subprocess.PIPE,
        stderr=asyncio.subprocess.PIPE,
        cwd=directory,
        env=env,
    )

    tail_task = None
    if tail_log:
        tail_task = asyncio.create_task(_tail_tf_log(tf_log_path, process, dir_name))

    stdout_data, stderr_data = await process.communicate()

    if tail_task:
        await tail_task

    stdout_log_path.write_bytes(stdout_data)
    stderr_log_path.write_bytes(stderr_data)

    parsed_logs = []
    if tf_log_path.exists():
        with open(tf_log_path) as f:
            for line in f:
                try:
                    parsed_logs.append(json.loads(line))
                except json.JSONDecodeError:
                    pass

    final_stdout = (
        stdout_data.decode("utf-8", errors="ignore") if capture_stdout else ""
    )
    return (
        process.returncode,
        final_stdout,
        stdout_log_path,
        stderr_log_path,
        tf_log_path,
        parsed_logs,
    )


async def run_test_lifecycle(
    directory: Path, semaphore: asyncio.Semaphore
) -> TestResult:
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
            init_rc, _, _, _, _, _ = await run_terraform_command(
                directory, ["init", "-no-color", "-input=false", "-upgrade"]
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
                directory, ["apply", "-input=false", "-auto-approve"], tail_log=True
            )

            if apply_rc == 0:
                test_statuses[dir_name].update(text="ANALYZING", style="magenta")
                show_rc, show_stdout, _, _, _, _ = await run_terraform_command(
                    directory, ["show", "-json"], capture_stdout=True
                )

                if show_rc == 0:
                    try:
                        state = json.loads(show_stdout)
                        test_statuses[dir_name]["providers"] = len(
                            state.get("provider_configs", {})
                        )
                        root_module = state.get("values", {}).get("root_module", {})
                        resources = [
                            r
                            for r in root_module.get("resources", [])
                            if r.get("mode") == "managed"
                        ]
                        data_sources = [
                            r
                            for r in root_module.get("resources", [])
                            if r.get("mode") == "data"
                        ]
                        test_statuses[dir_name]["resources"] = len(resources)
                        test_statuses[dir_name]["data_sources"] = len(data_sources)
                        test_statuses[dir_name]["outputs"] = len(
                            state.get("values", {}).get("outputs", {})
                        )
                    except json.JSONDecodeError:
                        pass

                test_statuses[dir_name].update(text="DESTROYING", style="dim green")
                await run_terraform_command(
                    directory,
                    ["destroy", "-auto-approve", "-input=false"],
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


def print_failure_report(result: TestResult):
    title = f"🚨 Failure Report for {result.directory} "
    console.print(f"[bold red]{title.center(80, '─')}[/bold red]")

    error_logs = [
        log for log in result.parsed_logs if log.get("@level") in ("error", "critical")
    ]

    if not error_logs:
        console.print(
            "[yellow]No specific error messages found in log. The failure may have been a crash.[/yellow]"
        )
    else:
        console.print(
            Text.from_markup(
                f"\n[bold]Error Log Events ({len(error_logs)} found):[/bold]"
            )
        )
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
            Text.from_markup(
                f"\n[bold]Full Terraform Log:[/bold] [yellow]{result.tf_log_path}[/yellow]"
            )
        )

    console.print("\n" + "─" * 80 + "\n")


def print_summary_panel(
    total_tests: int, failed_tests: int, skipped_tests: int, duration: float
):
    passed_tests = total_tests - failed_tests - skipped_tests
    success = failed_tests == 0

    title = (
        "✅ [bold green]All Tests Passed[/bold green]"
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


async def live_updater(live_display: Live, stop_event: asyncio.Event):
    while not stop_event.is_set():
        live_display.update(generate_status_table())
        try:
            await asyncio.wait_for(stop_event.wait(), timeout=0.5)
        except TimeoutError:
            pass


def initialize_tests(test_dirs: list[Path]):
    LOGS_DIR.mkdir(exist_ok=True)
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


async def execute_tests(test_dirs: list[Path]) -> list[TestResult | Exception]:
    with Live(
        generate_status_table(),
        console=console,
        screen=False,
        refresh_per_second=4,
        vertical_overflow="visible",
    ) as live:
        stop_event = asyncio.Event()
        updater_task = asyncio.create_task(live_updater(live, stop_event))
        try:
            semaphore = asyncio.Semaphore(MAX_CONCURRENT_TESTS)
            tasks = [
                asyncio.create_task(run_test_lifecycle(d, semaphore)) for d in test_dirs
            ]
            results = await asyncio.gather(*tasks, return_exceptions=True)
        finally:
            stop_event.set()
            await updater_task
            live.update(generate_status_table())
    return results


def process_results(
    results: list[TestResult | Exception],
) -> tuple[list[TestResult], int, bool]:
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


async def main(target_path: str):
    start_time = monotonic()
    base_dir = Path(target_path).resolve()

    test_dirs = sorted(
        [d for d in base_dir.iterdir() if d.is_dir() and not d.name.startswith(".")]
    )
    if any(base_dir.glob("*.tf")):
        test_dirs.append(base_dir)

    if not test_dirs:
        console.print(f"🤷 No directories found in '{base_dir}'.")
        return

    initialize_tests(test_dirs)

    console.print("[bold]🚀 Tofusoup Stir[/bold]")
    console.print(
        f"Found {len(test_dirs)} test suites in '{base_dir}'. Running up to {MAX_CONCURRENT_TESTS} in parallel..."
    )

    results = await execute_tests(test_dirs)
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
def stir_cli(path: str, matrix: bool, matrix_output: str, output_json: bool):
    """
    Run multi-threaded Terraform tests against all subdirectories in a given PATH.
    
    When --matrix is used, runs tests across multiple Terraform/OpenTofu versions
    as configured in wrkenv.toml's [matrix] section.
    """
    try:
        if matrix:
            # Run matrix testing
            from tofusoup.testing.matrix import run_matrix_stir_tests
            import pathlib
            
            results = asyncio.run(run_matrix_stir_tests(pathlib.Path(path)))
            
            if matrix_output:
                # Save results to file
                from tofusoup.testing.matrix import VersionMatrix
                import json
                with open(matrix_output, "w") as f:
                    json.dump(results, f, indent=2)
                console.print(f"[green]Matrix results saved to: {matrix_output}[/green]")
            
            if output_json:
                # Output JSON to stdout
                import json
                print(json.dumps(results, indent=2))
            else:
                # Show summary
                success = results["failure_count"] == 0
                if success:
                    console.print("\n[bold green]✅ All matrix combinations passed![/bold green]")
                else:
                    console.print(f"\n[bold red]❌ {results['failure_count']} combinations failed[/bold red]")
            
            # Exit with appropriate code
            import sys
            sys.exit(0 if success else 1)
        else:
            # Run normal stir tests
            asyncio.run(main(path))
    except KeyboardInterrupt:
        console.print("\n\n[yellow]Test run interrupted by user.[/yellow]")


# 🍲🥄📄🪄

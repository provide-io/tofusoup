#
# SPDX-FileCopyrightText: Copyright (c) 2025 provide.io llc. All rights reserved.
# SPDX-License-Identifier: Apache-2.0
#

"""Matrix testing functionality for TofuSoup.

Provides version matrix testing for the 'soup stir' command to validate
providers against multiple versions of Terraform/OpenTofu.

Note: Matrix testing requires the optional 'wrknv' dependency."""

import asyncio
from collections.abc import Callable
from dataclasses import dataclass, field
import itertools
import json
import os
import pathlib
from typing import Any

from rich.console import Console
from rich.progress import BarColumn, Progress, SpinnerColumn, TextColumn, TimeElapsedColumn
from rich.table import Table

from tofusoup.config.defaults import MATRIX_PARALLEL_JOBS, MATRIX_TIMEOUT_MINUTES

# Optional wrknv imports
try:
    from wrknv import WorkenvConfig, get_tool_manager  # type: ignore[import-not-found]

    from ..workenv_integration import WORKENV_AVAILABLE, create_workenv_config_with_soup
except ImportError:
    WORKENV_AVAILABLE = False
    WorkenvConfig = None
    get_tool_manager = None
    create_workenv_config_with_soup = None

console = Console()


@dataclass
class MatrixCombination:
    """Represents a specific combination of tool versions."""

    tools: dict[str, str] = field(default_factory=dict)

    def __str__(self) -> str:
        """String representation for display."""
        tool_strs = [f"{tool}:{version}" for tool, version in self.tools.items()]
        return f"[{', '.join(tool_strs)}]"

    def to_dict(self) -> dict[str, Any]:
        """Convert to dictionary for serialization."""
        return {"tools": self.tools}

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> "MatrixCombination":
        """Create from dictionary."""
        return cls(tools=data.get("tools", {}))


@dataclass
class MatrixResult:
    """Result from testing a matrix combination."""

    combination: MatrixCombination
    success: bool
    duration_seconds: float = 0.0
    error_message: str | None = None
    test_results: dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> dict[str, Any]:
        """Convert to dictionary for serialization."""
        return {
            "combination": self.combination.to_dict(),
            "success": self.success,
            "duration_seconds": self.duration_seconds,
            "error_message": self.error_message,
            "test_results": self.test_results,
        }


class VersionMatrix:
    """Manages version matrix testing for TofuSoup."""

    def __init__(self, base_tools: dict[str, str], config: Any = None) -> None:
        """
        Initialize the version matrix.

        Args:
            base_tools: Base tool versions (e.g., {"terraform": "1.5.7", "tofu": "1.6.2"})
            config: Optional WorkenvConfig. If not provided, creates one with soup compatibility.

        Raises:
            ImportError: If wrknv is not installed.
        """
        if not WORKENV_AVAILABLE:
            raise ImportError(
                "Matrix testing requires the 'wrknv' package.\n"
                "Install with: pip install wrknv\n"
                "Or install from source: pip install -e /path/to/wrknv"
            )

        self.config = config or create_workenv_config_with_soup()
        self.base_tools = base_tools

        # Get matrix configuration (from soup.toml or wrkenv.toml)
        self.matrix_config = self.config.get_setting("matrix", {})
        self.parallel_jobs = self.matrix_config.get("parallel_jobs", MATRIX_PARALLEL_JOBS)
        self.timeout_minutes = self.matrix_config.get("timeout_minutes", MATRIX_TIMEOUT_MINUTES)

    def generate_combinations(self) -> list[MatrixCombination]:
        """
        Generate all combinations for matrix testing.

        Returns:
            List of MatrixCombination objects to test
        """
        # Get version lists from matrix config
        matrix_versions = self.matrix_config.get("versions", {})

        # Build tool version lists
        tool_versions = {}
        for tool_name, base_version in self.base_tools.items():
            # Get additional versions to test for this tool
            extra_versions = matrix_versions.get(tool_name, [])

            # Combine base version with matrix versions
            all_versions = [base_version]
            if extra_versions:
                # Add matrix versions, avoiding duplicates
                for v in extra_versions:
                    if v not in all_versions:
                        all_versions.append(v)

            tool_versions[tool_name] = all_versions

        # Generate all combinations
        combinations = []

        if not tool_versions:
            return combinations

        tool_names = list(tool_versions.keys())
        version_lists = [tool_versions[tool] for tool in tool_names]

        for version_combo in itertools.product(*version_lists):
            combo_dict = dict(zip(tool_names, version_combo, strict=False))
            combinations.append(MatrixCombination(tools=combo_dict))

        return combinations

    async def run_stir_tests(
        self, stir_directory: pathlib.Path, test_filter: Callable[[MatrixCombination], bool] | None = None
    ) -> dict[str, Any]:
        """
        Run 'soup stir' tests across all matrix combinations.

        Args:
            stir_directory: Directory containing stir test cases
            test_filter: Optional function to filter which combinations to test

        Returns:
            Dictionary containing test results and statistics
        """
        combinations = self.generate_combinations()

        if test_filter:
            combinations = [c for c in combinations if test_filter(c)]

        if not combinations:
            return {
                "success_count": 0,
                "failure_count": 0,
                "results": [],
                "message": "No combinations to test",
            }

        console.print(f"\n[bold cyan]Running {len(combinations)} matrix combinations...[/bold cyan]")

        results = []
        semaphore = asyncio.Semaphore(self.parallel_jobs)

        async def test_combination(combo: MatrixCombination) -> MatrixResult:
            async with semaphore:
                return await self._test_single_combination(combo, stir_directory)

        # Run all combinations with progress tracking
        with Progress(
            SpinnerColumn(),
            TextColumn("[progress.description]{task.description}"),
            BarColumn(),
            TextColumn("[progress.percentage]{task.percentage:>3.0f}%"),
            TimeElapsedColumn(),
            console=console,
        ) as progress:
            task = progress.add_task("Testing combinations...", total=len(combinations))

            tasks = [test_combination(combo) for combo in combinations]

            for coro in asyncio.as_completed(tasks):
                result = await coro
                results.append(result)
                progress.advance(task)

                # Update progress description with latest result
                status = "✅" if result.success else "❌"
                progress.update(
                    task,
                    description=f"Testing combinations... {status} {result.combination}",
                )

        # Show results summary
        self._display_results_table(results)

        # Aggregate results
        success_count = sum(1 for r in results if r.success)
        failure_count = len(results) - success_count

        return {
            "success_count": success_count,
            "failure_count": failure_count,
            "results": [r.to_dict() for r in results],
            "total_combinations": len(combinations),
            "parallel_jobs": self.parallel_jobs,
        }

    async def _test_single_combination(
        self, combination: MatrixCombination, stir_directory: pathlib.Path
    ) -> MatrixResult:
        """Test a single tool version combination."""
        import time

        start_time = time.time()

        try:
            # Install all tools in this combination
            await self._install_combination_tools(combination)

            # Run soup stir with this combination
            result = await self._run_stir_test(combination, stir_directory)

            duration = time.time() - start_time

            return MatrixResult(
                combination=combination,
                success=result["success"],
                duration_seconds=duration,
                test_results=result,
            )

        except Exception as e:
            duration = time.time() - start_time

            return MatrixResult(
                combination=combination,
                success=False,
                duration_seconds=duration,
                error_message=str(e),
            )

    async def _install_combination_tools(self, combination: MatrixCombination) -> None:
        """Install all tools for a specific combination."""
        for tool_name, version in combination.tools.items():
            manager = get_tool_manager(tool_name, self.config)
            if not manager:
                raise Exception(f"No manager available for tool: {tool_name}")

            # Check if already installed
            current_version = manager.get_installed_version()
            if current_version == version:
                binary_path = manager.get_current_binary_path()
                if binary_path and binary_path.exists():
                    continue  # Already installed

            # Install the specific version
            console.print(f"Installing {tool_name} {version} for matrix testing...")
            await asyncio.get_event_loop().run_in_executor(
                None,
                manager.install_version,
                version,
                False,  # not dry_run
            )

    async def _run_stir_test(
        self, combination: MatrixCombination, stir_directory: pathlib.Path
    ) -> dict[str, Any]:
        """Run soup stir test for a specific combination."""
        import json

        # Build the soup stir command
        cmd = [
            "soup",
            "stir",
            str(stir_directory),
            "--json",  # Get JSON output for parsing
        ]

        # Set up environment with the tool versions
        env = dict(os.environ)
        for tool_name, version in combination.tools.items():
            # Ensure the right version is active
            manager = get_tool_manager(tool_name, self.config)
            if manager:
                binary_path = manager.get_binary_path(version)
                if binary_path.exists():
                    # Add to PATH
                    env["PATH"] = f"{binary_path.parent}:{env.get('PATH', '')}"

        # Run the stir command
        process = await asyncio.create_subprocess_exec(
            *cmd,
            env=env,
            stdout=asyncio.subprocess.PIPE,
            stderr=asyncio.subprocess.PIPE,
        )

        stdout, stderr = await asyncio.wait_for(process.communicate(), timeout=self.timeout_minutes * 60)

        if process.returncode == 0:
            # Parse JSON output if available
            try:
                result = json.loads(stdout.decode())
                result["success"] = True
            except (json.JSONDecodeError, ValueError):
                result = {
                    "success": True,
                    "stdout": stdout.decode(),
                    "stderr": stderr.decode(),
                }
        else:
            result = {
                "success": False,
                "stdout": stdout.decode(),
                "stderr": stderr.decode(),
                "returncode": process.returncode,
            }

        return result

    def _display_results_table(self, results: list[MatrixResult]) -> None:
        """Display results in a nice table."""
        table = Table(title="Matrix Test Results")

        # Add columns
        table.add_column("Combination", style="cyan")
        table.add_column("Status", style="bold")
        table.add_column("Duration", style="yellow")
        table.add_column("Error", style="red")

        # Add rows
        for result in results:
            duration = f"{result.duration_seconds:.1f}s"
            error = result.error_message or ""
            status = "[green]✅ PASS[/green]" if result.success else "[red]❌ FAIL[/red]"

            table.add_row(
                str(result.combination),
                status,
                duration,
                error,
            )

        console.print(table)

    def save_results(self, results: dict[str, Any], output_path: pathlib.Path) -> None:
        """Save matrix test results to a file."""
        with output_path.open("w") as f:
            json.dump(results, f, indent=2)

        console.print(f"[green]Matrix test results saved to: {output_path}[/green]")


# Convenience function for soup stir integration
async def run_matrix_stir_tests(
    stir_directory: pathlib.Path, tools: dict[str, str] | None = None, config: Any = None
) -> dict[str, Any]:
    """
    Run matrix testing for soup stir.

    This is the main entry point for the soup stir matrix testing feature.

    Args:
        stir_directory: Directory containing stir test cases
        tools: Optional base tools. If not provided, uses current config.
        config: Optional WorkenvConfig

    Returns:
        Test results dictionary

    Raises:
        ImportError: If wrknv is not installed.
    """
    if not WORKENV_AVAILABLE:
        raise ImportError(
            "Matrix testing requires the 'wrknv' package.\n"
            "Install with: pip install wrknv\n"
            "Or install from source: pip install -e /path/to/wrknv"
        )

    if config is None:
        config = create_workenv_config_with_soup()

    if tools is None:
        # Get tools from current configuration
        tools = config.get_all_tools()
        # Filter to just terraform/tofu
        tools = {k: v for k, v in tools.items() if k in ["terraform", "tofu"]}

    matrix = VersionMatrix(tools, config)
    return await matrix.run_stir_tests(stir_directory)


# 🥣🔬🔚

#
# SPDX-FileCopyrightText: Copyright (c) 2025 provide.io llc. All rights reserved.
# SPDX-License-Identifier: Apache-2.0
#

"""Profile-based matrix testing for TofuSoup.

Instead of generating combinations, uses pre-defined profiles from soup.toml
to test against specific tool configurations.

Note: Matrix testing requires the optional 'wrknv' dependency."""

import asyncio
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

from rich.console import Console
from rich.progress import BarColumn, Progress, SpinnerColumn, TextColumn, TimeElapsedColumn
from rich.table import Table

from tofusoup.config.defaults import MATRIX_PARALLEL_JOBS, MATRIX_TIMEOUT_MINUTES

# Optional wrknv imports - graceful degradation if not available
try:
    from wrknv import WorkenvConfig, get_tool_manager  # type: ignore[import-not-found]

    from ..workenv_integration import WORKENV_AVAILABLE, create_workenv_config_with_soup
except ImportError:
    WORKENV_AVAILABLE = False
    WorkenvConfig = None
    get_tool_manager = None
    create_workenv_config_with_soup = None  # type: ignore[assignment]

console = Console()


@dataclass
class ProfileTestResult:
    """Result from testing a specific profile."""

    profile_name: str
    success: bool
    duration_seconds: float = 0.0
    error_message: str | None = None
    test_results: dict[str, Any] = field(default_factory=dict)
    tools: dict[str, str] = field(default_factory=dict)

    def to_dict(self) -> dict[str, Any]:
        """Convert to dictionary for serialization."""
        return {
            "profile": self.profile_name,
            "success": self.success,
            "duration_seconds": self.duration_seconds,
            "error_message": self.error_message,
            "test_results": self.test_results,
            "tools": self.tools,
        }


class ProfileMatrix:
    """Manages profile-based matrix testing for TofuSoup."""

    def __init__(self, config: Any = None) -> None:
        """
        Initialize the profile matrix.

        Args:
            config: Optional WorkenvConfig. If not provided, creates one with soup compatibility.
        """
        self.config = config or create_workenv_config_with_soup()

        # Get matrix configuration
        self.matrix_config = self.config.get_setting("matrix", {})
        self.matrix_profiles = self.matrix_config.get("profiles", [])
        self.parallel_jobs = self.matrix_config.get("parallel_jobs", MATRIX_PARALLEL_JOBS)
        self.timeout_minutes = self.matrix_config.get("timeout_minutes", MATRIX_TIMEOUT_MINUTES)

    def get_test_profiles(self) -> list[str]:
        """
        Get list of profiles to test.

        Returns:
            List of profile names from matrix config
        """
        if self.matrix_profiles:
            result: list[str] = self.matrix_profiles
            return result

        # If no explicit matrix profiles, test all available profiles
        all_profiles = self.config.get_all_profiles()
        return list(all_profiles.keys())

    async def run_profile_tests(
        self, stir_directory: Path, profiles: list[str] | None = None
    ) -> dict[str, Any]:
        """
        Run 'soup stir' tests for each profile.

        Args:
            stir_directory: Directory containing stir test cases
            profiles: Optional list of specific profiles to test

        Returns:
            Dictionary containing test results and statistics
        """
        test_profiles = profiles or self.get_test_profiles()

        if not test_profiles:
            return {
                "success_count": 0,
                "failure_count": 0,
                "results": [],
                "message": "No profiles to test",
            }

        console.print(f"\n[bold cyan]Running tests for {len(test_profiles)} profiles...[/bold cyan]")

        results = []
        semaphore = asyncio.Semaphore(self.parallel_jobs)

        async def test_profile(profile_name: str) -> ProfileTestResult:
            async with semaphore:
                return await self._test_single_profile(profile_name, stir_directory)

        # Run all profiles with progress tracking
        with Progress(
            SpinnerColumn(),
            TextColumn("[progress.description]{task.description}"),
            BarColumn(),
            TextColumn("[progress.percentage]{task.percentage:>3.0f}%"),
            TimeElapsedColumn(),
            console=console,
        ) as progress:
            task = progress.add_task("Testing profiles...", total=len(test_profiles))

            tasks = [test_profile(profile) for profile in test_profiles]

            for coro in asyncio.as_completed(tasks):
                result = await coro
                results.append(result)
                progress.advance(task)

                # Update progress description with latest result
                status = "✅" if result.success else "❌"
                progress.update(
                    task,
                    description=f"Testing profiles... {status} {result.profile_name}",
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
            "total_profiles": len(test_profiles),
            "parallel_jobs": self.parallel_jobs,
        }

    async def _test_single_profile(self, profile_name: str, stir_directory: Path) -> ProfileTestResult:
        """Test a single profile configuration."""
        import os
        import time

        start_time = time.time()

        try:
            # Get profile configuration
            profile = self.config.get_profile(profile_name)
            if not profile:
                raise Exception(f"Profile '{profile_name}' not found")

            # Extract tools from profile
            tools = {}
            terraform_flavor = profile.get(
                "terraform_flavor", self.config.get_setting("terraform_flavor", "terraform")
            )

            # Get the appropriate tool based on flavor
            if terraform_flavor == "opentofu" and "tofu" in profile:
                tools["tofu"] = profile["tofu"]
            elif "terraform" in profile:
                tools["terraform"] = profile["terraform"]

            # Install tools for this profile
            await self._install_profile_tools(profile_name, profile)

            # Set up environment for this profile
            env = dict(os.environ)
            env["WORKENV_PROFILE"] = profile_name

            # Run soup stir with this profile
            result = await self._run_stir_test(profile_name, stir_directory, env)

            duration = time.time() - start_time

            return ProfileTestResult(
                profile_name=profile_name,
                success=result["success"],
                duration_seconds=duration,
                test_results=result,
                tools=tools,
            )

        except Exception as e:
            duration = time.time() - start_time

            return ProfileTestResult(
                profile_name=profile_name,
                success=False,
                duration_seconds=duration,
                error_message=str(e),
            )

    async def _install_profile_tools(self, profile_name: str, profile: dict[str, Any]) -> None:
        """Install all tools for a specific profile."""
        # Determine which tools to install based on terraform_flavor
        terraform_flavor = profile.get(
            "terraform_flavor", self.config.get_setting("terraform_flavor", "terraform")
        )

        tools_to_install = {}
        if terraform_flavor == "opentofu" and "tofu" in profile:
            tools_to_install["tofu"] = profile["tofu"]
        elif "terraform" in profile:
            tools_to_install["terraform"] = profile["terraform"]

        # Install each tool
        for tool_name, version in tools_to_install.items():
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
            console.print(f"Installing {tool_name} {version} for profile '{profile_name}'...")
            await asyncio.get_event_loop().run_in_executor(
                None,
                manager.install_version,
                version,
                False,  # not dry_run
            )

    async def _run_stir_test(
        self, profile_name: str, stir_directory: Path, env: dict[str, str]
    ) -> dict[str, Any]:
        """Run soup stir test for a specific profile."""
        import json

        # Build the soup stir command
        cmd = [
            "soup",
            "stir",
            str(stir_directory),
            "--json",  # Get JSON output for parsing
        ]

        # Run the stir command
        process = await asyncio.create_subprocess_exec(
            *cmd,
            env=env,
            stdout=asyncio.subprocess.PIPE,
            stderr=asyncio.subprocess.PIPE,
        )

        stdout, stderr = await asyncio.wait_for(process.communicate(), timeout=self.timeout_minutes * 60)

        result: dict[str, Any]
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

    def _display_results_table(self, results: list[ProfileTestResult]) -> None:
        """Display results in a nice table."""
        table = Table(title="Profile Test Results")

        # Add columns
        table.add_column("Profile", style="cyan")
        table.add_column("Tools", style="yellow")
        table.add_column("Status", style="bold")
        table.add_column("Duration", style="yellow")
        table.add_column("Error", style="red")

        # Add rows
        for result in results:
            duration = f"{result.duration_seconds:.1f}s"
            error = result.error_message or ""
            status = "[green]✅ PASS[/green]" if result.success else "[red]❌ FAIL[/red]"

            # Format tools display
            tools_str = ", ".join(f"{k}:{v}" for k, v in result.tools.items()) if result.tools else "N/A"

            table.add_row(
                result.profile_name,
                tools_str,
                status,
                duration,
                error,
            )

        console.print(table)

    def save_results(self, results: dict[str, Any], output_path: Path) -> None:
        """Save profile test results to a file."""
        import json

        with output_path.open("w") as f:
            json.dump(results, f, indent=2)

        console.print(f"[green]Profile test results saved to: {output_path}[/green]")


# Convenience function for soup stir integration
async def run_profile_matrix_tests(
    stir_directory: Path, profiles: list[str] | None = None, config: Any = None
) -> dict[str, Any]:
    """
    Run profile-based matrix testing for soup stir.

    Args:
        stir_directory: Directory containing stir test cases
        profiles: Optional list of specific profiles to test
        config: Optional WorkenvConfig

    Returns:
        Test results dictionary
    """
    matrix = ProfileMatrix(config)
    return await matrix.run_profile_tests(stir_directory, profiles)


# 🥣🔬🔚

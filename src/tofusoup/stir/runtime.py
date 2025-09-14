#
# tofusoup/stir/runtime.py
#

import asyncio
from pathlib import Path
import re
import tempfile
from typing import Any

from tofusoup.stir.display import console


class StirRuntime:
    """
    Runtime manager for Stir test execution.

    Handles provider management, environment setup, and ensures efficient
    parallel test execution by pre-warming providers before parallel execution.
    """

    def __init__(self, plugin_cache_dir: Path | None = None, force_upgrade: bool = False):
        """
        Initialize the Stir runtime.

        Args:
            plugin_cache_dir: Directory to use for plugin cache. If None, uses default.
            force_upgrade: Whether to force provider upgrades
        """
        self.force_upgrade = force_upgrade
        self.plugin_cache_dir = plugin_cache_dir or self._default_plugin_cache_dir()
        self.environment_vars: dict[str, str] = {}
        self._provider_cache_ready = False

    def _default_plugin_cache_dir(self) -> Path:
        """Get the default plugin cache directory."""
        return Path.home() / ".terraform.d" / "plugin-cache"

    async def prepare_providers(self, test_dirs: list[Path]) -> None:
        """
        Pre-download all required providers to avoid race conditions during parallel execution.

        Args:
            test_dirs: List of test directories to scan for provider requirements
        """
        console.print("[bold blue]🔧 Preparing providers...[/bold blue]")

        # Ensure plugin cache directory exists
        self.plugin_cache_dir.mkdir(parents=True, exist_ok=True)

        # Find all unique providers needed across all test directories
        required_providers = await self._scan_provider_requirements(test_dirs)

        if not required_providers:
            console.print("[yellow]⚠️  No provider requirements found in test directories[/yellow]")
            self._provider_cache_ready = True
            return

        # Create a temporary manifest to download all providers
        await self._download_providers(required_providers)

        self._provider_cache_ready = True
        console.print(f"[bold green]✅ Providers prepared[/bold green] ({len(required_providers)} unique providers)")

    async def _scan_provider_requirements(self, test_dirs: list[Path]) -> set[tuple[str, str]]:
        """
        Scan all test directories to identify required providers.

        Returns:
            Set of (source, version_constraint) tuples
        """
        providers = set()

        for test_dir in test_dirs:
            tf_files = list(test_dir.glob("*.tf"))
            for tf_file in tf_files:
                try:
                    content = tf_file.read_text(encoding="utf-8")
                    dir_providers = self._extract_providers_from_content(content)
                    providers.update(dir_providers)
                except Exception as e:
                    console.log(f"[{test_dir.name}] Warning: Could not read {tf_file.name}: {e}")

        return providers

    def _extract_providers_from_content(self, content: str) -> set[tuple[str, str]]:
        """
        Extract provider requirements from Terraform configuration content.

        Args:
            content: Terraform configuration file content

        Returns:
            Set of (source, version_constraint) tuples
        """
        providers = set()

        # Match terraform block with required_providers (handle both compact and expanded formats)
        terraform_block_pattern = r'terraform\s*\{.*?required_providers\s*\{(.*?)\}.*?\}'
        terraform_matches = re.findall(terraform_block_pattern, content, re.DOTALL | re.MULTILINE)

        for match in terraform_matches:
            # Extract provider declarations - handle compact format
            # First try to find source and version separately
            provider_entries = re.findall(r'(\w+)\s*=\s*\{([^}]+)\}', match)

            for provider_name, provider_config in provider_entries:
                # Extract source
                source_match = re.search(r'source\s*=\s*"([^"]+)"', provider_config)
                if source_match:
                    source = source_match.group(1)

                    # Extract version (optional)
                    version_match = re.search(r'version\s*=\s*"([^"]+)"', provider_config)
                    version = version_match.group(1) if version_match else ">= 0.0.0"

                    providers.add((source, version))

        # Also look for legacy provider syntax in provider blocks
        legacy_pattern = r'provider\s+"([^"]+)"\s*\{'
        legacy_matches = re.findall(legacy_pattern, content)
        for provider_name in legacy_matches:
            # For legacy syntax, assume hashicorp namespace if no explicit source
            if "/" not in provider_name:
                source = f"hashicorp/{provider_name}"
            else:
                source = provider_name
            providers.add((source, ">= 0.0.0"))

        # Debug: print what we found
        console.print(f"[blue]Found {len(providers)} providers: {providers}[/blue]")

        return providers

    async def _download_providers(self, providers: set[tuple[str, str]]) -> None:
        """
        Download all required providers using a temporary terraform configuration.

        Args:
            providers: Set of (source, version_constraint) tuples to download
        """
        if not providers:
            return

        # Create temporary directory for provider manifest
        with tempfile.TemporaryDirectory() as temp_dir:
            temp_path = Path(temp_dir)
            manifest_file = temp_path / "providers.tf"

            # Generate a minimal terraform configuration that requires all providers
            terraform_config = self._generate_provider_manifest(providers)
            manifest_file.write_text(terraform_config)

            console.print(f"[blue]Generated terraform config:[/blue]\n{terraform_config}")

            # Run terraform init to download providers
            from tofusoup.stir.terraform import run_terraform_command

            console.print(f"[blue]📥 Downloading {len(providers)} providers to cache...[/blue]")
            console.print(f"[blue]Cache directory: {self.plugin_cache_dir}[/blue]")

            init_args = ["init", "-no-color", "-input=false"]
            if self.force_upgrade:
                init_args.append("-upgrade")

            init_rc, _, stdout_log, stderr_log, _, _ = await run_terraform_command(
                temp_path,
                init_args,
                runtime=None,  # Don't use runtime for provider preparation
                override_cache_dir=self.plugin_cache_dir
            )

            if init_rc != 0:
                # Read logs to see what went wrong
                stdout_content = stdout_log.read_text() if stdout_log.exists() else "No stdout"
                stderr_content = stderr_log.read_text() if stderr_log.exists() else "No stderr"
                console.print(f"[red]Terraform init failed with code {init_rc}[/red]")
                console.print(f"[red]STDOUT:[/red] {stdout_content}")
                console.print(f"[red]STDERR:[/red] {stderr_content}")
                raise RuntimeError("Failed to download providers to cache")

    def _generate_provider_manifest(self, providers: set[tuple[str, str]]) -> str:
        """
        Generate a Terraform configuration that requires all specified providers.

        Args:
            providers: Set of (source, version_constraint) tuples

        Returns:
            Terraform configuration string
        """
        lines = [
            "terraform {",
            "  required_providers {"
        ]

        for i, (source, version) in enumerate(sorted(providers)):
            # Extract provider name from source (e.g., "hashicorp/aws" -> "aws")
            provider_name = source.split("/")[-1]
            # Ensure unique names in case of conflicts
            provider_key = f"{provider_name}_{i}" if i > 0 else provider_name

            lines.append(f'    {provider_key} = {{')
            lines.append(f'      source  = "{source}"')
            lines.append(f'      version = "{version}"')
            lines.append('    }')

        lines.extend([
            "  }",
            "}"
        ])

        return "\n".join(lines)

    def get_terraform_env(self, base_env: dict[str, str]) -> dict[str, str]:
        """
        Get the normalized Terraform environment for test execution.

        Args:
            base_env: Base environment to extend

        Returns:
            Environment variables dict for terraform execution
        """
        env = base_env.copy()

        # Always set plugin cache if directory exists
        if self.plugin_cache_dir.exists():
            env["TF_PLUGIN_CACHE_DIR"] = str(self.plugin_cache_dir)
            # Enable potentially faster caching at the expense of lock file completeness
            env["TF_PLUGIN_CACHE_MAY_BREAK_DEPENDENCY_LOCK_FILE"] = "1"

        return env

    @property
    def providers_ready(self) -> bool:
        """Check if providers have been prepared."""
        return self._provider_cache_ready

    def validate_ready(self) -> None:
        """Validate that the runtime is ready for test execution."""
        if not self._provider_cache_ready:
            raise RuntimeError("Runtime not ready: call prepare_providers() first")


__all__ = ["StirRuntime"]
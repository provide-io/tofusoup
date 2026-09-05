#
# SPDX-FileCopyrightText: Copyright (c) provide.io llc. All rights reserved.
# SPDX-License-Identifier: Apache-2.0
#


from pathlib import Path
import re
import tempfile

from tofusoup.stir.display import console


class StirRuntime:
    """
    Runtime manager for Stir test execution.

    Handles provider management, environment setup, and ensures efficient
    parallel test execution by pre-warming providers before parallel execution.
    """

    def __init__(self, plugin_cache_dir: Path | None = None, force_upgrade: bool = False) -> None:
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
        from tofusoup.stir.display import test_statuses

        # Add a special entry for provider preparation phase
        test_statuses["__PROVIDER_PREP__"] = {
            "text": "SCANNING",
            "style": "blue",
            "active": True,
            "success": False,
            "skipped": False,
            "start_time": None,
            "end_time": None,
            "last_log": "Scanning test directories for provider requirements...",
            "outputs": 0,
            "has_warnings": False,
            "providers": 0,
            "resources": 0,
            "data_sources": 0,
            "functions": 0,
            "ephemeral_functions": 0,
        }

        # Ensure plugin cache directory exists
        self.plugin_cache_dir.mkdir(parents=True, exist_ok=True)

        # Find all unique providers needed across all test directories
        test_statuses["__PROVIDER_PREP__"]["last_log"] = "Scanning test directories..."
        required_providers = await self._scan_provider_requirements(test_dirs)

        if not required_providers:
            test_statuses["__PROVIDER_PREP__"].update(
                text="SKIPPED",
                style="dim yellow",
                active=False,
                skipped=True,
                last_log="No provider requirements found",
            )
            self._provider_cache_ready = True
            return

        # Deduplicate providers by source, preferring higher versions
        deduplicated_providers = self._deduplicate_providers(required_providers)

        test_statuses["__PROVIDER_PREP__"]["providers"] = len(deduplicated_providers)
        test_statuses["__PROVIDER_PREP__"]["last_log"] = (
            f"Downloading {len(deduplicated_providers)} providers..."
        )

        # Create a temporary manifest to download all providers
        await self._download_providers(deduplicated_providers)

        self._provider_cache_ready = True
        test_statuses["__PROVIDER_PREP__"].update(
            text="COMPLETE",
            style="bold green",
            active=False,
            success=True,
            last_log=f"Downloaded {len(deduplicated_providers)} providers to cache",
        )

    async def _scan_provider_requirements(self, test_dirs: list[Path]) -> set[tuple[str, str]]:
        """
        Scan all test directories to identify required providers.

        Returns:
            Set of (source, version_constraint) tuples
        """
        providers = set()

        for test_dir in test_dirs:
            # Join the directory's files before extracting. Terraform merges every
            # .tf in a directory into one configuration, so a `required_providers`
            # block in provider.tf governs the sources named in its siblings. Reading
            # each file alone hid that and sent the legacy-syntax fallback below
            # looking for `hashicorp/<name>` for providers already declared local.
            chunks = []
            for tf_file in sorted(test_dir.glob("*.tf")):
                try:
                    chunks.append(tf_file.read_text(encoding="utf-8"))
                except Exception as e:
                    console.log(f"[{test_dir.name}] Warning: Could not read {tf_file.name}: {e}")
            if chunks:
                providers.update(self._extract_providers_from_content("\n".join(chunks)))

        return providers

    @staticmethod
    def _balanced_block(content: str, keyword: str) -> list[str]:
        """Return the body of each `<keyword> {...}` block, matching braces properly.

        A regex cannot do this: the previous pattern stopped at the first inner `}`,
        so a `required_providers` block declaring two providers yielded only the
        first, and the second was never pre-downloaded.
        """
        bodies: list[str] = []
        for m in re.finditer(rf"{keyword}\s*\{{", content):
            depth = 0
            for i in range(m.end() - 1, len(content)):
                if content[i] == "{":
                    depth += 1
                elif content[i] == "}":
                    depth -= 1
                    if depth == 0:
                        bodies.append(content[m.end() : i])
                        break
        return bodies

    def _extract_providers_from_content(self, content: str) -> set[tuple[str, str]]:
        """
        Extract provider requirements from Terraform configuration content.

        Args:
            content: Terraform configuration file content

        Returns:
            Set of (source, version_constraint) tuples
        """
        providers = set()

        for body in self._balanced_block(content, "required_providers"):
            # Every `name = { ... }` entry, not just the first.
            for entry in re.finditer(r"(\w+)\s*=\s*\{(.*?)\}", body, re.DOTALL):
                provider_content = entry.group(2)

                source_match = re.search(r'source\s*=\s*"([^"]+)"', provider_content)
                if not source_match:
                    continue
                source = source_match.group(1)

                # Skip local providers - they come from the filesystem mirror and
                # no registry has a matching name.
                if source.startswith("local/"):
                    continue

                version_match = re.search(r'version\s*=\s*"([^"]+)"', provider_content)
                providers.add((source, version_match.group(1) if version_match else ">= 0.0.0"))

        # Only look for legacy provider syntax if nothing in this directory declared
        # a source. Anchored to column 0 so only a top-level block matches -- a
        # `state_store` block nests `provider "name" {}` inside it, which is PSS
        # configuration and not a declaration of anything to download.
        if not providers and "required_providers" not in content:
            legacy_matches = re.findall(r'^provider\s+"([^"]+)"\s*\{', content, re.MULTILINE)
            for provider_name in legacy_matches:
                source = f"hashicorp/{provider_name}" if "/" not in provider_name else provider_name
                providers.add((source, ">= 0.0.0"))

        return providers

    def _deduplicate_providers(self, providers: set[tuple[str, str]]) -> set[tuple[str, str]]:
        """
        Deduplicate providers by source, keeping the one with the highest version.

        Args:
            providers: Set of (source, version_constraint) tuples

        Returns:
            Deduplicated set of providers
        """
        # Group by source
        by_source: dict[str, list[str]] = {}
        for source, version in providers:
            if source not in by_source:
                by_source[source] = []
            by_source[source].append(version)

        # For each source, pick the best version constraint
        result = set()
        for source, versions in by_source.items():
            # If we have ">= 0.0.0", prefer specific versions
            specific_versions = [v for v in versions if not v.startswith(">=")]
            # Use the first specific version found (they should all be the same for real projects)
            version = specific_versions[0] if specific_versions else versions[0]
            result.add((source, version))

        return result

    async def _download_providers(self, providers: set[tuple[str, str]]) -> None:
        """
        Download all required providers using a temporary terraform configuration.

        Args:
            providers: Set of (source, version_constraint) tuples to download

        Note:
            Uses tempfile.TemporaryDirectory which automatically cleans up after use.
            This is safe for parallel execution as each invocation gets a unique directory.
        """
        if not providers:
            return

        from tofusoup.stir.display import test_statuses

        # Create temporary directory for provider manifest (auto-cleaned on context exit)
        with tempfile.TemporaryDirectory() as temp_dir:
            temp_path = Path(temp_dir)
            manifest_file = temp_path / "providers.tf"

            # Generate a minimal terraform configuration that requires all providers
            terraform_config = self._generate_provider_manifest(providers)
            manifest_file.write_text(terraform_config)

            # Run terraform init to download providers
            from tofusoup.stir.terraform import run_terraform_command

            test_statuses["__PROVIDER_PREP__"]["text"] = "DOWNLOADING"
            test_statuses["__PROVIDER_PREP__"]["last_log"] = (
                f"Running terraform init to download {len(providers)} providers..."
            )

            init_args = ["init", "-no-color", "-input=false"]
            if self.force_upgrade:
                init_args.append("-upgrade")

            init_rc, _, stdout_log, stderr_log, _, _ = await run_terraform_command(
                temp_path,
                init_args,
                runtime=None,  # Don't use runtime for provider preparation
                override_cache_dir=self.plugin_cache_dir,
            )

            if init_rc != 0:
                # Read logs to see what went wrong
                stdout_content = stdout_log.read_text() if stdout_log.exists() else "No stdout"
                stderr_content = stderr_log.read_text() if stderr_log.exists() else "No stderr"

                test_statuses["__PROVIDER_PREP__"].update(
                    text="ERROR",
                    style="bold red",
                    active=False,
                    success=False,
                    last_log=f"Terraform init failed with code {init_rc}",
                )

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
        lines = ["terraform {", "  required_providers {"]

        for i, (source, version) in enumerate(sorted(providers)):
            # Extract provider name from source (e.g., "hashicorp/aws" -> "aws")
            provider_name = source.split("/")[-1]
            # Ensure unique names in case of conflicts - use dashes instead of underscores
            provider_key = f"{provider_name}-{i}" if i > 0 else provider_name

            lines.append(f"    {provider_key} = {{")
            lines.append(f'      source  = "{source}"')
            lines.append(f'      version = "{version}"')
            lines.append("    }")

        lines.extend(["  }", "}"])

        return "\n".join(lines)

    def get_terraform_env(self, base_env: dict[str, str], example_dir: Path | None = None) -> dict[str, str]:
        """
        Get the normalized Terraform environment for test execution.

        Args:
            base_env: Base environment to extend
            example_dir: The example being run. Each one gets its own plugin
                cache; omit only for the pre-download phase, which runs alone.

        Returns:
            Environment variables dict for terraform execution
        """
        env = base_env.copy()

        # One cache per example, not one for the suite.
        #
        # `MAX_CONCURRENT_TESTS` is os.cpu_count(), so several examples run
        # `terraform init` simultaneously and each installs the provider under
        # test. Sharing a cache directory means they all write the same path:
        # survivable on POSIX, fatal on Windows, where a file cannot be replaced
        # while another process holds it open. Three of four concurrent examples
        # died inside providercache.Dir.InstallPackage that way.
        #
        # prepare_providers does not cover this -- it skips `local/` sources, and
        # the provider under test is one.
        if example_dir is not None:
            cache_dir = example_dir / ".soup" / "plugin-cache"
            cache_dir.mkdir(parents=True, exist_ok=True)
        elif self.plugin_cache_dir.exists():
            cache_dir = self.plugin_cache_dir
        else:
            return env

        env["TF_PLUGIN_CACHE_DIR"] = str(cache_dir)
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

# 🥣🔬🔚

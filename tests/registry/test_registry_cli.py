#
# SPDX-FileCopyrightText: Copyright (c) 2025 provide.io llc. All rights reserved.
# SPDX-License-Identifier: Apache-2.0
#


from provide.testkit import isolated_cli_runner
from provide.testkit.mocking import AsyncMock, MagicMock, patch

from tofusoup.registry import cli as registry_cli
from tofusoup.registry.models.module import Module
from tofusoup.registry.models.provider import Provider
from tofusoup.registry.search.engine import SearchResult


class TestRegistrySearchCommand:
    def test_search_command_with_results(self) -> None:
        mock_results = [
            SearchResult(
                id="1",
                name="aws",
                namespace="hashicorp",
                type="provider",
                registry_source="terraform",
                provider_name=None,
                latest_version="6.8.0",
                total_versions=446,
                description="terraform-provider-aws",
            ),
            SearchResult(
                id="2",
                name="vpc",
                namespace="terraform-aws-modules",
                type="module",
                registry_source="terraform",
                provider_name="aws",
                latest_version="6.0.1",
                total_versions=231,
                description="Terraform module to create AWS VPC resources",
            ),
        ]

        with isolated_cli_runner() as runner, patch("asyncio.run", return_value=mock_results):
            result = runner.invoke(registry_cli.registry_cli, ["search", "aws"])
            assert result.exit_code == 0
            assert "Found 2 results for 'aws':" in result.output
            assert "hashicorp/aws" in result.output
            assert "terraform-aws-modules/vpc/aws" in result.output

    def test_search_command_no_results(self) -> None:
        with isolated_cli_runner() as runner, patch("asyncio.run", return_value=[]):
            result = runner.invoke(registry_cli.registry_cli, ["search", "nonexistent"])
            assert result.exit_code == 0
            assert "No results found for 'nonexistent'" in result.output

    def test_search_command_with_type_filter(self) -> None:
        mock_results = [
            SearchResult(
                id="1",
                name="aws",
                namespace="hashicorp",
                type="provider",
                registry_source="terraform",
                provider_name=None,
                latest_version="6.8.0",
                total_versions=446,
            )
        ]

        with isolated_cli_runner() as runner:
            with patch("asyncio.run", return_value=mock_results):
                result = runner.invoke(registry_cli.registry_cli, ["search", "aws", "-t", "provider"])
            assert result.exit_code == 0
            assert "hashicorp/aws" in result.output

    def test_search_command_no_term(self) -> None:
        with isolated_cli_runner() as runner:
            result = runner.invoke(registry_cli.registry_cli, ["search"])
        assert result.exit_code == 0  # Click doesn't exit with error for empty args
        assert "Please provide a search term" in result.output


class TestProviderCommands:
    @patch("tofusoup.registry.cli.IBMTerraformRegistry")
    @patch("tofusoup.registry.cli.OpenTofuRegistry")
    def test_provider_info_command(
        self, mock_tofu_reg: MagicMock, mock_tf_reg: MagicMock, sample_provider: Provider
    ) -> None:
        # Setup mocks
        mock_tf_instance = AsyncMock()
        mock_tf_instance.get_provider_details = AsyncMock(
            return_value={
                "namespace": sample_provider.namespace,
                "name": sample_provider.name,
                "description": sample_provider.description,
                "source": sample_provider.source_url,
                "download_count": 1000000,
            }
        )
        mock_tf_instance.__class__.__name__ = "IBMTerraformRegistry"
        mock_tf_reg.return_value = mock_tf_instance

        mock_tofu_instance = AsyncMock()
        mock_tofu_instance.get_provider_details = AsyncMock(side_effect=Exception("Not found"))
        mock_tofu_instance.__class__.__name__ = "OpenTofuRegistry"
        mock_tofu_reg.return_value = mock_tofu_instance

        with isolated_cli_runner() as runner:
            result = runner.invoke(registry_cli.registry_cli, ["provider", "info", "hashicorp/aws"])
        assert result.exit_code == 0
        assert "=== IBMTerraform Registry ===" in result.output
        assert "Provider: hashicorp/aws" in result.output
        assert "terraform-provider-aws" in result.output

    @patch("tofusoup.registry.cli.IBMTerraformRegistry")
    def test_provider_versions_command(
        self, mock_tf_reg: MagicMock, mock_provider_details: dict, mock_provider_versions: list
    ) -> None:
        mock_tf_instance = AsyncMock()
        mock_tf_instance.get_provider_details = AsyncMock(return_value=mock_provider_details)
        mock_tf_instance.list_provider_versions = AsyncMock(return_value=mock_provider_versions)
        mock_tf_instance.__class__.__name__ = "IBMTerraformRegistry"
        mock_tf_reg.return_value = mock_tf_instance

        with isolated_cli_runner() as runner:
            result = runner.invoke(
                registry_cli.registry_cli, ["provider", "versions", "hashicorp/aws", "-r", "terraform"]
            )
        assert result.exit_code == 0
        assert "Provider: hashicorp/aws" in result.output
        assert "6.8.0" in result.output
        assert "Versions (3 total):" in result.output

    @patch("tofusoup.registry.cli.IBMTerraformRegistry")
    def test_provider_versions_latest_flag(
        self, mock_tf_reg: MagicMock, mock_provider_details: dict, mock_provider_versions: list
    ) -> None:
        mock_tf_instance = AsyncMock()
        mock_tf_instance.get_provider_details = AsyncMock(return_value=mock_provider_details)
        mock_tf_instance.list_provider_versions = AsyncMock(return_value=mock_provider_versions)
        mock_tf_instance.__class__.__name__ = "IBMTerraformRegistry"
        mock_tf_reg.return_value = mock_tf_instance

        with isolated_cli_runner() as runner:
            result = runner.invoke(
                registry_cli.registry_cli,
                ["provider", "versions", "hashicorp/aws", "--latest", "-r", "terraform"],
            )
        assert result.exit_code == 0
        assert "Latest version: 6.8.0" in result.output
        assert "Versions (3 total):" not in result.output

    def test_provider_info_invalid_format(self) -> None:
        with isolated_cli_runner() as runner:
            result = runner.invoke(registry_cli.registry_cli, ["provider", "info", "invalid-format"])
        assert result.exit_code == 0  # Our CLI prints error but doesn't exit with error code
        assert "Provider must be in format 'namespace/name'" in result.output


class TestModuleCommands:
    @patch("tofusoup.registry.cli.IBMTerraformRegistry")
    def test_module_info_command(self, mock_tf_reg: MagicMock, sample_module: Module) -> None:
        mock_tf_instance = AsyncMock()
        mock_tf_instance.get_module_details = AsyncMock(
            return_value={
                "namespace": sample_module.namespace,
                "name": sample_module.name,
                "provider": sample_module.provider_name,
                "description": sample_module.description,
                "source": sample_module.source_url,
                "download_count": sample_module.downloads,
            }
        )
        mock_tf_instance.__class__.__name__ = "IBMTerraformRegistry"
        mock_tf_reg.return_value = mock_tf_instance

        with isolated_cli_runner() as runner:
            result = runner.invoke(
                registry_cli.registry_cli,
                ["module", "info", "terraform-aws-modules/vpc/aws", "-r", "terraform"],
            )
        assert result.exit_code == 0
        assert "Module: terraform-aws-modules/vpc/aws" in result.output

    @patch("tofusoup.registry.cli.IBMTerraformRegistry")
    def test_module_versions_command(
        self, mock_tf_reg: MagicMock, mock_module_details: dict, mock_module_versions: list
    ) -> None:
        mock_tf_instance = AsyncMock()
        mock_tf_instance.get_module_details = AsyncMock(return_value=mock_module_details)
        mock_tf_instance.list_module_versions = AsyncMock(return_value=mock_module_versions)
        mock_tf_instance.__class__.__name__ = "IBMTerraformRegistry"
        mock_tf_reg.return_value = mock_tf_instance

        with isolated_cli_runner() as runner:
            result = runner.invoke(
                registry_cli.registry_cli,
                ["module", "versions", "terraform-aws-modules/vpc/aws", "-r", "terraform"],
            )
        assert result.exit_code == 0
        assert "Module: terraform-aws-modules/vpc/aws" in result.output
        assert "6.0.1" in result.output

    def test_module_info_invalid_format(self) -> None:
        with isolated_cli_runner() as runner:
            result = runner.invoke(registry_cli.registry_cli, ["module", "info", "invalid/format"])
        assert result.exit_code == 0  # Our CLI prints error but doesn't exit with error code
        assert "Module must be in format 'namespace/name/provider'" in result.output


class TestCompareCommand:
    @patch("tofusoup.registry.cli.IBMTerraformRegistry")
    @patch("tofusoup.registry.cli.OpenTofuRegistry")
    def test_compare_provider_command(
        self,
        mock_tofu_reg: MagicMock,
        mock_tf_reg: MagicMock,
        mock_provider_details: dict,
        mock_provider_versions: list,
    ) -> None:
        # Setup Terraform registry mock
        mock_tf_instance = AsyncMock()
        mock_tf_instance.get_provider_details = AsyncMock(return_value=mock_provider_details)
        mock_tf_instance.list_provider_versions = AsyncMock(return_value=mock_provider_versions)
        mock_tf_instance.__class__.__name__ = "IBMTerraformRegistry"
        mock_tf_reg.return_value = mock_tf_instance

        # Setup OpenTofu registry mock
        mock_tofu_instance = AsyncMock()
        mock_tofu_instance.get_provider_details = AsyncMock(return_value=mock_provider_details)
        mock_tofu_instance.list_provider_versions = AsyncMock(
            return_value=mock_provider_versions[:2]
        )  # Fewer versions
        mock_tofu_instance.__class__.__name__ = "OpenTofuRegistry"
        mock_tofu_reg.return_value = mock_tofu_instance

        with isolated_cli_runner() as runner:
            result = runner.invoke(registry_cli.registry_cli, ["compare", "hashicorp/aws"])
        assert result.exit_code == 0
        assert "Comparing provider: hashicorp/aws" in result.output
        assert "Terraform Registry" in result.output
        assert "OpenTofu Registry" in result.output
        assert "Available" in result.output

    def test_compare_invalid_format(self) -> None:
        with isolated_cli_runner() as runner:
            result = runner.invoke(registry_cli.registry_cli, ["compare", "invalid"])
        assert result.exit_code == 0  # Our CLI prints error but doesn't exit with error code
        assert "Resource must be 'namespace/name' for providers" in result.output


# 🥣🔬🔚

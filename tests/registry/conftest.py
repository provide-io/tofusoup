#
# SPDX-FileCopyrightText: Copyright (c) 2025 provide.io llc. All rights reserved.
# SPDX-License-Identifier: Apache-2.0
#

"""TODO: Add module docstring."""

from provide.testkit.mocking import AsyncMock
import pytest

from tofusoup.registry.models.module import Module, ModuleVersion
from tofusoup.registry.models.provider import Provider, ProviderVersion
from tofusoup.registry.opentofu import OpenTofuRegistry
from tofusoup.registry.terraform import IBMTerraformRegistry


@pytest.fixture
def mock_terraform_registry() -> IBMTerraformRegistry:
    """Create a mock Terraform registry."""
    from tofusoup.registry.base import RegistryConfig
    from tofusoup.registry.terraform import IBMTerraformRegistry

    mock = AsyncMock(spec=IBMTerraformRegistry)
    mock.config = RegistryConfig(base_url="https://registry.terraform.io")
    return mock


@pytest.fixture
def mock_opentofu_registry() -> OpenTofuRegistry:
    """Create a mock OpenTofu registry."""
    from tofusoup.registry.opentofu import OpenTofuRegistry

    mock = AsyncMock(spec=OpenTofuRegistry)
    return mock


@pytest.fixture
def sample_provider() -> Provider:
    """Create a sample provider for testing."""
    return Provider(
        id="hashicorp/aws",
        namespace="hashicorp",
        name="aws",
        description="AWS Provider",
        source_url="https://github.com/hashicorp/terraform-provider-aws",
        tier="official",
    )


@pytest.fixture
def sample_provider_versions() -> list[ProviderVersion]:
    """Create sample provider versions for testing."""
    return [
        ProviderVersion(version="6.8.0", protocols=["6"], platforms=[]),
        ProviderVersion(version="6.7.0", protocols=["6"], platforms=[]),
        ProviderVersion(version="6.6.0", protocols=["6"], platforms=[]),
    ]


@pytest.fixture
def sample_module() -> Module:
    """Create a sample module for testing."""
    return Module(
        id="terraform-aws-modules/vpc/aws",
        namespace="terraform-aws-modules",
        name="vpc",
        provider_name="aws",
        description="Terraform module to create AWS VPC resources",
        downloads=500000,
        source_url="https://github.com/terraform-aws-modules/terraform-aws-vpc",
    )


@pytest.fixture
def sample_module_versions() -> list[ModuleVersion]:
    """Create sample module versions for testing."""
    return [
        ModuleVersion(version="6.0.1", published_at="2024-01-15"),
        ModuleVersion(version="6.0.0", published_at="2024-01-10"),
        ModuleVersion(version="5.9.0", published_at="2023-12-20"),
    ]


@pytest.fixture
def mock_provider_details(sample_provider: Provider) -> dict:
    """Create mock provider details dict for testing."""
    return {
        "namespace": sample_provider.namespace,
        "name": sample_provider.name,
        "description": sample_provider.description,
        "source": sample_provider.source_url,
        "download_count": 1000000,
    }


@pytest.fixture
def mock_module_details(sample_module: Module) -> dict:
    """Create mock module details dict for testing."""
    return {
        "namespace": sample_module.namespace,
        "name": sample_module.name,
        "provider": sample_module.provider_name,
        "description": sample_module.description,
        "source": sample_module.source_url,
        "download_count": 500000,
    }


@pytest.fixture
def mock_provider_versions(sample_provider_versions: list[ProviderVersion]) -> list[ProviderVersion]:
    """Alias for sample_provider_versions for backwards compatibility."""
    return sample_provider_versions


@pytest.fixture
def mock_module_versions(sample_module_versions: list[ModuleVersion]) -> list[ModuleVersion]:
    """Alias for sample_module_versions for backwards compatibility."""
    return sample_module_versions


# 🥣🔬🔚

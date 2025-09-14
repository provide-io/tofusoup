import pytest
from unittest.mock import AsyncMock, MagicMock

from tofusoup.registry.models.provider import Provider, ProviderVersion
from tofusoup.registry.models.module import Module, ModuleVersion


@pytest.fixture
def mock_terraform_registry():
    """Create a mock Terraform registry."""
    from tofusoup.registry.terraform import IBMTerraformRegistry
    from tofusoup.registry.base import RegistryConfig
    
    mock = AsyncMock(spec=IBMTerraformRegistry)
    mock.config = RegistryConfig(base_url="https://registry.terraform.io")
    return mock


@pytest.fixture
def mock_opentofu_registry():
    """Create a mock OpenTofu registry."""
    from tofusoup.registry.opentofu import OpenTofuRegistry
    
    mock = AsyncMock(spec=OpenTofuRegistry)
    return mock


@pytest.fixture
def sample_provider():
    """Create a sample provider for testing."""
    return Provider(
        id="hashicorp/aws",
        namespace="hashicorp",
        name="aws",
        alias="aws",
        tag="provider",
        description="AWS Provider",
        downloads=1000000,
        source="https://github.com/hashicorp/terraform-provider-aws"
    )


@pytest.fixture
def sample_provider_versions():
    """Create sample provider versions for testing."""
    return [
        ProviderVersion(version="6.8.0", protocols=["6"], platforms=[]),
        ProviderVersion(version="6.7.0", protocols=["6"], platforms=[]),
        ProviderVersion(version="6.6.0", protocols=["6"], platforms=[])
    ]


@pytest.fixture
def sample_module():
    """Create a sample module for testing."""
    return Module(
        id="terraform-aws-modules/vpc/aws",
        namespace="terraform-aws-modules",
        name="vpc",
        provider_name="aws",
        description="Terraform module to create AWS VPC resources",
        downloads=500000,
        source_url="https://github.com/terraform-aws-modules/terraform-aws-vpc"
    )


@pytest.fixture
def sample_module_versions():
    """Create sample module versions for testing."""
    return [
        ModuleVersion(version="6.0.1", published_at="2024-01-15"),
        ModuleVersion(version="6.0.0", published_at="2024-01-10"),
        ModuleVersion(version="5.9.0", published_at="2023-12-20")
    ]


# 🍲🥄🧪🪄

#
# SPDX-FileCopyrightText: Copyright (c) 2025 provide.io llc. All rights reserved.
# SPDX-License-Identifier: Apache-2.0
#

"""TODO: Add module docstring."""

import pytest

from tofusoup.registry.models.module import Module, ModuleVersion
from tofusoup.registry.models.provider import Provider, ProviderPlatform, ProviderVersion
from tofusoup.registry.models.version import VersionInfo


class TestProviderModels:
    def test_provider_creation(self) -> None:
        """Test creating a Provider instance."""
        provider = Provider(
            id="hashicorp/aws",
            namespace="hashicorp",
            name="aws",
            description="AWS Provider",
            source_url="https://github.com/hashicorp/terraform-provider-aws",
            tier="official",
        )

        assert provider.id == "hashicorp/aws"
        assert provider.namespace == "hashicorp"
        assert provider.name == "aws"
        assert provider.description == "AWS Provider"
        assert provider.source_url == "https://github.com/hashicorp/terraform-provider-aws"

    def test_provider_version_creation(self) -> None:
        """Test creating a ProviderVersion instance."""
        platform = ProviderPlatform(os="linux", arch="amd64")
        version = ProviderVersion(version="6.8.0", protocols=["6"], platforms=[platform])

        assert version.version == "6.8.0"
        assert "6" in version.protocols
        assert len(version.platforms) == 1
        assert version.platforms[0].os == "linux"

    def test_provider_optional_fields(self) -> None:
        """Test Provider with optional fields."""
        provider = Provider(id="test/provider", namespace="test", name="provider")

        assert provider.description is None
        assert provider.source_url is None
        assert provider.tier is None


class TestModuleModels:
    def test_module_creation(self) -> None:
        """Test creating a Module instance."""
        module = Module(
            id="terraform-aws-modules/vpc/aws",
            namespace="terraform-aws-modules",
            name="vpc",
            provider_name="aws",
            description="VPC Module",
            downloads=500000,
            source_url="https://github.com/terraform-aws-modules/terraform-aws-vpc",
        )

        assert module.id == "terraform-aws-modules/vpc/aws"
        assert module.namespace == "terraform-aws-modules"
        assert module.name == "vpc"
        assert module.provider_name == "aws"
        assert module.downloads == 500000

    def test_module_version_creation(self) -> None:
        """Test creating a ModuleVersion instance."""
        version = ModuleVersion(version="6.0.1", published_at="2024-01-15T10:00:00Z")

        assert version.version == "6.0.1"
        assert version.published_at == "2024-01-15T10:00:00Z"

    def test_module_provider_name_property(self) -> None:
        """Test the provider_name property of Module."""
        module = Module(
            id="terraform-aws-modules/vpc/aws",
            namespace="terraform-aws-modules",
            name="vpc",
            provider_name="aws",
        )

        assert module.provider_name == "aws"


class TestVersionModel:
    def test_version_creation(self) -> None:
        """Test creating a VersionInfo instance."""
        version = VersionInfo(raw_version="1.2.3")
        assert version.raw_version == "1.2.3"
        assert version.major == 1
        assert version.minor == 2
        assert version.patch == 3

    def test_version_with_prerelease(self) -> None:
        """Test version with prerelease info."""
        version = VersionInfo(raw_version="2.0.0-alpha.1")
        assert version.raw_version == "2.0.0-alpha.1"
        assert version.major == 2
        assert version.prerelease == "alpha.1"  # semver library returns prerelease as string

    def test_version_string_representation(self) -> None:
        """Test string representation of version."""
        v1 = VersionInfo(raw_version="1.0.0")
        v2 = VersionInfo(raw_version="2.0.0-beta")

        assert str(v1) == "1.0.0"
        assert str(v2) == "2.0.0-beta"

    def test_version_invalid_format(self) -> None:
        """Test that invalid version format raises error."""
        with pytest.raises(ValueError):
            VersionInfo(raw_version="not-a-version")


# 🥣🔬🔚

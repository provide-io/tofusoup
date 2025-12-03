#
# SPDX-FileCopyrightText: Copyright (c) 2025 provide.io llc. All rights reserved.
# SPDX-License-Identifier: Apache-2.0
#


import pytest
from pytest_httpx import HTTPXMock

from tofusoup.registry.base import RegistryConfig
from tofusoup.registry.terraform import IBMTerraformRegistry


@pytest.mark.asyncio
async def test_get_provider_details_success(httpx_mock: HTTPXMock) -> None:
    """Test successful provider details retrieval from Terraform Registry."""
    mock_response = {
        "id": "hashicorp/aws",
        "namespace": "hashicorp",
        "name": "aws",
        "description": "terraform-provider-aws",
        "source": "https://github.com/hashicorp/terraform-provider-aws",
    }

    httpx_mock.add_response(url="https://registry.terraform.io/v1/providers/hashicorp/aws", json=mock_response)

    registry = IBMTerraformRegistry(RegistryConfig(base_url="https://registry.terraform.io"))
    async with registry:
        details = await registry.get_provider_details("hashicorp", "aws")
        assert details["id"] == "hashicorp/aws"
        assert details["description"] == "terraform-provider-aws"


@pytest.mark.asyncio
async def test_get_provider_details_not_found(httpx_mock: HTTPXMock) -> None:
    """Test provider not found scenario."""
    httpx_mock.add_response(
        url="https://registry.terraform.io/v1/providers/nonexistent/provider",
        status_code=404,
        json={"errors": ["Not found"]},
    )

    registry = IBMTerraformRegistry(RegistryConfig(base_url="https://registry.terraform.io"))
    async with registry:
        result = await registry.get_provider_details("nonexistent", "provider")
        assert result == {}  # Terraform registry returns empty dict for 404


@pytest.mark.asyncio
async def test_get_module_details_success(httpx_mock: HTTPXMock) -> None:
    """Test successful module details retrieval."""
    mock_response = {
        "id": "terraform-aws-modules/vpc/aws",
        "namespace": "terraform-aws-modules",
        "name": "vpc",
        "provider": "aws",
        "description": "Terraform module to create AWS VPC resources",
    }

    httpx_mock.add_response(
        url="https://registry.terraform.io/v1/modules/terraform-aws-modules/vpc/aws/latest", json=mock_response
    )

    registry = IBMTerraformRegistry(RegistryConfig(base_url="https://registry.terraform.io"))
    async with registry:
        details = await registry.get_module_details("terraform-aws-modules", "vpc", "aws", "latest")
        assert details["name"] == "vpc"
        assert details["provider"] == "aws"


@pytest.mark.asyncio
async def test_get_module_details_not_found(httpx_mock: HTTPXMock) -> None:
    """Test module not found scenario."""
    httpx_mock.add_response(
        url="https://registry.terraform.io/v1/modules/nonexistent/module/provider/latest",
        status_code=404,
        json={"errors": ["Not found"]},
    )

    registry = IBMTerraformRegistry(RegistryConfig(base_url="https://registry.terraform.io"))
    async with registry:
        result = await registry.get_module_details("nonexistent", "module", "provider", "latest")
        assert result == {}  # Terraform registry returns empty dict for 404


@pytest.mark.asyncio
async def test_list_providers_with_search(httpx_mock: HTTPXMock) -> None:
    """Test listing providers with search query."""
    mock_response = {
        "providers": [
            {"id": "hashicorp/aws", "namespace": "hashicorp", "name": "aws", "alias": "aws", "tag": "provider"}
        ]
    }

    httpx_mock.add_response(
        url="https://registry.terraform.io/v1/providers?limit=50&q=aws", json=mock_response
    )

    registry = IBMTerraformRegistry(RegistryConfig(base_url="https://registry.terraform.io"))
    async with registry:
        providers = await registry.list_providers(query="aws")
        assert len(providers) == 1
        assert providers[0].name == "aws"


@pytest.mark.asyncio
async def test_list_provider_versions(httpx_mock: HTTPXMock) -> None:
    """Test listing provider versions."""
    mock_response = {
        "versions": [
            {"version": "6.8.0", "protocols": ["6"], "platforms": []},
            {"version": "6.7.0", "protocols": ["6"], "platforms": []},
            {"version": "6.6.0", "protocols": ["6"], "platforms": []},
        ]
    }

    httpx_mock.add_response(
        url="https://registry.terraform.io/v1/providers/hashicorp/aws/versions", json=mock_response
    )

    registry = IBMTerraformRegistry(RegistryConfig(base_url="https://registry.terraform.io"))
    async with registry:
        versions = await registry.list_provider_versions("hashicorp/aws")
        assert len(versions) == 3
        assert versions[0].version == "6.8.0"


# 🥣🔬🔚

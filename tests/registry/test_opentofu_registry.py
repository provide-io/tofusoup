#
# SPDX-FileCopyrightText: Copyright (c) provide.io llc. All rights reserved.
# SPDX-License-Identifier: Apache-2.0
#


import pytest
from pytest_httpx import HTTPXMock

from tofusoup.registry.opentofu import OpenTofuRegistry


@pytest.mark.asyncio
async def test_get_provider_details_success(httpx_mock: HTTPXMock) -> None:
    """Test successful provider details retrieval from OpenTofu Registry."""
    mock_response = {
        "id": "opentofu/aws",
        "namespace": "opentofu",
        "name": "aws",
        "description": "AWS Provider for OpenTofu",
        "source": "https://github.com/opentofu/terraform-provider-aws",
    }

    httpx_mock.add_response(url="https://registry.opentofu.org/v1/providers/opentofu/aws", json=mock_response)

    registry = OpenTofuRegistry()
    async with registry:
        details = await registry.get_provider_details("opentofu", "aws")
        assert details["id"] == "opentofu/aws"
        assert details["namespace"] == "opentofu"


@pytest.mark.asyncio
async def test_get_provider_details_not_found(httpx_mock: HTTPXMock) -> None:
    """Test provider not found scenario."""
    httpx_mock.add_response(
        url="https://registry.opentofu.org/v1/providers/nonexistent/provider",
        status_code=404,
        json={"errors": ["Not found"]},
    )

    registry = OpenTofuRegistry()
    async with registry:
        result = await registry.get_provider_details("nonexistent", "provider")
        assert result == {}  # OpenTofu registry returns empty dict for 404


@pytest.mark.asyncio
async def test_get_module_details_success(httpx_mock: HTTPXMock) -> None:
    """Test successful module details retrieval."""
    mock_response = {
        "id": "aws-ia/vpc/aws",
        "namespace": "aws-ia",
        "name": "vpc",
        "provider": "aws",
        "description": "AWS VPC Module",
    }

    httpx_mock.add_response(
        url="https://registry.opentofu.org/v1/modules/aws-ia/vpc/aws/latest", json=mock_response
    )

    registry = OpenTofuRegistry()
    async with registry:
        details = await registry.get_module_details("aws-ia", "vpc", "aws", "latest")
        assert details["name"] == "vpc"
        assert details["namespace"] == "aws-ia"


@pytest.mark.asyncio
async def test_list_modules_with_search(httpx_mock: HTTPXMock) -> None:
    """Test listing modules with search query."""

    # OpenTofu uses a different search API endpoint
    httpx_mock.add_response(
        url="https://api.opentofu.org/registry/docs/search?limit=20&q=vpc",
        json=[  # Note: returns a list directly, not wrapped in "modules"
            {
                "id": "modules/aws-ia/vpc/aws",  # OpenTofu expects id to start with "modules/"
                "namespace": "aws-ia",
                "name": "vpc",
                "provider": "aws",
                "description": "AWS VPC Module",
                "downloads": 1000,
            }
        ],
    )

    registry = OpenTofuRegistry()
    async with registry:
        modules = await registry.list_modules(query="vpc")
        assert len(modules) == 1
        assert modules[0].name == "vpc"
        assert modules[0].namespace == "aws-ia"


@pytest.mark.asyncio
async def test_list_module_versions(httpx_mock: HTTPXMock) -> None:
    """Test listing module versions."""
    mock_response = {
        "modules": [{"versions": [{"version": "4.5.0"}, {"version": "4.4.0"}, {"version": "4.3.0"}]}]
    }

    httpx_mock.add_response(
        url="https://registry.opentofu.org/v1/modules/aws-ia/vpc/aws/versions", json=mock_response
    )

    registry = OpenTofuRegistry()
    async with registry:
        versions = await registry.list_module_versions("aws-ia/vpc/aws")
        assert len(versions) == 3
        assert versions[0].version == "4.5.0"


# 🥣🔬🔚

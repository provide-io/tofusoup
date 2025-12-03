#
# SPDX-FileCopyrightText: Copyright (c) 2025 provide.io llc. All rights reserved.
# SPDX-License-Identifier: Apache-2.0
#


from provide.testkit.mocking import AsyncMock
import pytest

from tofusoup.registry.models.module import Module, ModuleVersion
from tofusoup.registry.models.provider import Provider, ProviderVersion
from tofusoup.registry.search.engine import SearchEngine, SearchQuery


class MockRegistry(AsyncMock):
    def __init__(self, name: str = "terraform") -> None:
        super().__init__()
        self._name = name

    async def __aenter__(self) -> "MockRegistry":
        return self

    async def __aexit__(
        self, exc_type: type[BaseException] | None, exc_val: BaseException | None, exc_tb: object | None
    ) -> None:
        pass

    @property
    def __class__(self) -> type:
        # Mock the class name for registry identification
        class FakeClass:
            def __init__(self, name: str) -> None:
                self.__name__ = f"{name}Registry"

        return FakeClass(self._name)


@pytest.mark.asyncio
async def test_search_engine_merges_results_and_versions() -> None:
    """Test that SearchEngine properly merges results from multiple registries."""
    # Create mock registries
    tf_registry = MockRegistry(name="Terraform")
    tofu_registry = MockRegistry(name="OpenTofu")

    # Mock provider data
    tf_provider = Provider(
        id="hashicorp/aws",
        namespace="hashicorp",
        name="aws",
        description="AWS Provider",
        source_url="https://github.com/hashicorp/terraform-provider-aws",
    )

    # Mock module data
    tf_module = Module(
        id="terraform-aws-modules/vpc/aws",
        namespace="terraform-aws-modules",
        name="vpc",
        provider_name="aws",
        description="VPC Module",
        downloads=500000,
        source_url="https://github.com/terraform-aws-modules/terraform-aws-vpc",
    )

    # Mock versions
    provider_versions = [
        ProviderVersion(version="6.8.0", protocols=["6"], platforms=[]),
        ProviderVersion(version="6.7.0", protocols=["6"], platforms=[]),
    ]

    module_versions = [ModuleVersion(version="6.0.1"), ModuleVersion(version="6.0.0")]

    # Setup mock returns
    tf_registry.list_providers = AsyncMock(return_value=[tf_provider])
    tf_registry.list_modules = AsyncMock(return_value=[tf_module])
    tf_registry.list_provider_versions = AsyncMock(return_value=provider_versions)
    tf_registry.list_module_versions = AsyncMock(return_value=module_versions)

    tofu_registry.list_providers = AsyncMock(return_value=[])
    tofu_registry.list_modules = AsyncMock(return_value=[])

    # Create search engine and execute search
    engine = SearchEngine([tf_registry, tofu_registry])
    query = SearchQuery(term="aws")

    results = []
    async for result in engine.search(query):
        results.append(result)

    # Verify results
    assert len(results) == 2

    # Check provider result
    provider_result = next((r for r in results if r.type == "provider"), None)
    assert provider_result is not None
    assert provider_result.name == "aws"
    assert provider_result.namespace == "hashicorp"
    assert provider_result.latest_version == "6.8.0"
    assert provider_result.total_versions == 2
    assert provider_result.registry_source == "terraform"

    # Check module result
    module_result = next((r for r in results if r.type == "module"), None)
    assert module_result is not None
    assert module_result.name == "vpc"
    assert module_result.namespace == "terraform-aws-modules"
    assert module_result.provider_name == "aws"
    assert module_result.latest_version == "6.0.1"
    assert module_result.total_versions == 2
    assert module_result.registry_source == "terraform"


@pytest.mark.asyncio
async def test_search_engine_handles_registry_errors() -> None:
    """Test that SearchEngine gracefully handles registry errors."""
    # Create mock registries
    good_registry = MockRegistry(name="Good")
    bad_registry = MockRegistry(name="Bad")

    # Good registry returns data
    good_registry.list_providers = AsyncMock(
        return_value=[Provider(id="hashicorp/aws", namespace="hashicorp", name="aws")]
    )
    good_registry.list_modules = AsyncMock(return_value=[])
    good_registry.list_provider_versions = AsyncMock(return_value=[])

    # Bad registry throws errors
    bad_registry.list_providers = AsyncMock(side_effect=Exception("Network error"))
    bad_registry.list_modules = AsyncMock(side_effect=Exception("Network error"))

    # Create search engine
    engine = SearchEngine([good_registry, bad_registry])
    query = SearchQuery(term="aws")

    # Execute search and collect results
    results = []
    async for result in engine.search(query):
        results.append(result)

    # Should still get results from good registry
    assert len(results) == 1
    assert results[0].name == "aws"


@pytest.mark.asyncio
async def test_search_engine_empty_query() -> None:
    """Test SearchEngine with empty query."""
    registry = MockRegistry(name="Test")
    registry.list_providers = AsyncMock(return_value=[])
    registry.list_modules = AsyncMock(return_value=[])

    engine = SearchEngine([registry])
    query = SearchQuery(term="")

    results = []
    async for result in engine.search(query):
        results.append(result)

    assert len(results) == 0

    # Verify the registry was called with None for empty query
    registry.list_providers.assert_called_once_with(query=None)
    registry.list_modules.assert_called_once_with(query=None)


# 🥣🔬🔚

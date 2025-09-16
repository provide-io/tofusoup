#
# tofusoup/registry/search/engine.py
#
import asyncio
from collections.abc import AsyncGenerator

from attrs import define, field
from provide.foundation import logger
import semver

from tofusoup.registry.base import BaseTfRegistry


@define
class SearchQuery:
    """Represents a search query."""

    term: str = ""


@define
class SearchResult:
    """Represents a single item in the search results."""

    id: str
    name: str
    namespace: str
    type: str
    registry_source: str
    provider_name: str | None = field(default=None)
    description: str | None = field(default=None)
    latest_version: str | None = field(default=None)
    total_versions: int | None = field(default=None)


class SearchEngine:
    def __init__(self, registries: list[BaseTfRegistry]) -> None:
        self.registries: list[BaseTfRegistry] = registries
        logger.debug(f"SearchEngine initialized with {len(self.registries)} registries.")

    async def search(self, query: SearchQuery) -> AsyncGenerator[SearchResult]:
        """
        FIX: Refactored to an async generator.
        Performs a search across all configured registries and yields results
        as they become available from each registry.
        """
        logger.info("SearchEngine.search started", query_term=query.term)

        search_tasks = [
            asyncio.create_task(self._search_single_registry(registry, query)) for registry in self.registries
        ]

        # Use asyncio.as_completed to process results as they finish
        for task in asyncio.as_completed(search_tasks):
            try:
                results_from_registry = await task
                logger.debug(f"Received {len(results_from_registry)} results from a registry.")
                for result in results_from_registry:
                    yield result
            except Exception as e:
                logger.error(f"Error processing a registry's search results: {e}", exc_info=True)

        logger.info("SearchEngine.search finished streaming results.")

    async def _search_single_registry(
        self, registry: BaseTfRegistry, query: SearchQuery
    ) -> list[SearchResult]:
        registry_identifier = registry.__class__.__name__.replace("Registry", "").lower()
        logger.info(
            f"Enter _search_single_registry for {registry_identifier}",
            query_term=query.term,
        )
        registry_results: list[SearchResult] = []
        try:
            async with registry:
                logger.debug(f"Registry context entered for {registry_identifier}.")
                effective_query_term = query.term if query.term else None

                modules = await registry.list_modules(query=effective_query_term)
                if modules is None:
                    modules = []
                logger.debug(f"{registry_identifier}.list_modules returned {len(modules)} modules.")
                for mod in modules:
                    versions = await registry.list_module_versions(
                        f"{mod.namespace}/{mod.name}/{mod.provider_name}"
                    )
                    if versions is None:
                        versions = []

                    latest_version = None
                    valid_versions = []
                    for v in versions:
                        try:
                            valid_versions.append(semver.Version.parse(v.version))
                        except ValueError:
                            logger.warning(
                                f"Skipping invalid semver version '{v.version}' for module {mod.id}"
                            )
                    if valid_versions:
                        latest_version = max(valid_versions)

                    registry_results.append(
                        SearchResult(
                            id=mod.id,
                            name=mod.name,
                            namespace=mod.namespace,
                            provider_name=mod.provider_name,
                            type="module",
                            registry_source=registry_identifier,
                            description=mod.description,
                            latest_version=str(latest_version) if latest_version else None,
                            total_versions=len(versions),
                        )
                    )

                providers = await registry.list_providers(query=effective_query_term)
                if providers is None:
                    providers = []
                logger.debug(f"{registry_identifier}.list_providers returned {len(providers)} providers.")
                for prov in providers:
                    versions = await registry.list_provider_versions(f"{prov.namespace}/{prov.name}")
                    if versions is None:
                        versions = []

                    latest_version = None
                    valid_versions = []
                    for v in versions:
                        try:
                            valid_versions.append(semver.Version.parse(v.version))
                        except ValueError:
                            logger.warning(
                                f"Skipping invalid semver version '{v.version}' for provider {prov.id}"
                            )
                    if valid_versions:
                        latest_version = max(valid_versions)

                    registry_results.append(
                        SearchResult(
                            id=prov.id,
                            name=prov.name,
                            namespace=prov.namespace,
                            type="provider",
                            registry_source=registry_identifier,
                            description=prov.description,
                            latest_version=str(latest_version) if latest_version else None,
                            total_versions=len(versions),
                        )
                    )
            logger.debug(f"Registry context exited for {registry_identifier}.")
            return registry_results
        except Exception as e:
            logger.error(f"Error searching registry {registry_identifier}: {e}", exc_info=True)
            raise

    async def close(self) -> None:
        logger.debug("SearchEngine.close called, no specific resources to clean up here.")
        pass


async def async_search_runner(search_term: str, registry_choice: str) -> list[SearchResult]:
    """Asynchronously performs the search operation against specified registries.

    This is a convenience function that sets up registries based on the choice,
    executes the search, and returns results.

    Args:
        search_term: The term to search for
        registry_choice: One of 'terraform', 'opentofu', or 'all'

    Returns:
        List of SearchResult objects
    """
    from ..base import RegistryConfig
    from ..opentofu import OpenTofuRegistry
    from ..terraform import IBMTerraformRegistry

    logger.debug(
        "async_search_runner started",
        search_term=search_term,
        registry_choice=registry_choice,
    )
    registries_to_search: list[BaseTfRegistry] = []

    if registry_choice in ["terraform", "all"]:
        tf_config = RegistryConfig(base_url="https://registry.terraform.io")
        registries_to_search.append(IBMTerraformRegistry(config=tf_config))
        logger.debug("TerraformRegistry added to search targets.")

    if registry_choice in ["opentofu", "all"]:
        registries_to_search.append(OpenTofuRegistry())
        logger.debug("OpenTofuRegistry added to search targets.")

    if not registries_to_search:
        logger.warning("No registries selected for search.")
        return []

    engine = SearchEngine(registries=registries_to_search)
    query = SearchQuery(term=search_term)

    results: list[SearchResult] = []
    try:
        logger.info(f"Executing search with SearchEngine for term: '{search_term}' on '{registry_choice}'")
        async for result in engine.search(query):
            results.append(result)
        logger.info(f"SearchEngine returned {len(results)} results.")
    except Exception as e:
        logger.error(f"Exception during search execution: {e}", exc_info=True)
        raise
    finally:
        await engine.close()
        logger.debug("SearchEngine closed.")

    return results


# 🍲🥄📄🪄

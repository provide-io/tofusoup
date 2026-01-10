#
# SPDX-FileCopyrightText: Copyright (c) provide.io llc. All rights reserved.
# SPDX-License-Identifier: Apache-2.0
#


from typing import Any

import httpx
from provide.foundation import logger

from tofusoup.registry.models.module import Module, ModuleVersion
from tofusoup.registry.models.provider import (
    Provider,
    ProviderPlatform,
    ProviderVersion,
)

from .base import BaseTfRegistry, RegistryConfig


class IBMTerraformRegistry(BaseTfRegistry):
    def __init__(self, config: RegistryConfig) -> None:
        super().__init__(config)

    async def list_providers(self, query: str | None = None) -> list[Provider]:
        if not self._client:
            return []
        params: dict[str, Any] = {"limit": 50}
        endpoint = "/v1/providers"
        if query:
            params["q"] = query
        try:
            response = await self._client.get(endpoint, params=params)
            response.raise_for_status()
            data = response.json()
            return [
                Provider(
                    id=p.get("id"),
                    namespace=p.get("namespace"),
                    name=p.get("name"),
                    description=p.get("description"),
                    tier=p.get("tier"),
                )
                for p in data.get("providers", [])
            ]
        except (httpx.HTTPStatusError, httpx.RequestError) as e:
            logger.error(
                "Error searching Terraform providers",
                request_url=e.request.url,
                exc_info=True,
            )
            return []

    async def list_modules(self, query: str | None = None) -> list[Module]:
        if not self._client:
            return []
        endpoint = "/v1/modules/search"
        params: dict[str, Any] = {"limit": 20}
        if query:
            params["q"] = query
        try:
            response = await self._client.get(endpoint, params=params)
            response.raise_for_status()
            data = response.json()
            return [
                Module(
                    id=m.get("id", ""),
                    namespace=m.get("namespace", ""),
                    name=m.get("name", ""),
                    provider_name=m.get("provider", ""),
                    description=m.get("description"),
                )
                for m in data.get("modules", [])
            ]
        except (httpx.HTTPStatusError, httpx.RequestError) as e:
            logger.error(
                "Error searching Terraform modules",
                request_url=e.request.url,
                exc_info=True,
            )
            return []

    async def get_provider_details(self, namespace: str, name: str) -> dict[str, Any]:
        if not self._client:
            return {}
        endpoint = f"/v1/providers/{namespace}/{name}"
        try:
            response = await self._client.get(endpoint)
            if response.status_code == 404:
                return {}
            response.raise_for_status()
            result: dict[str, Any] = response.json()
            return result
        except (httpx.HTTPStatusError, httpx.RequestError) as e:
            logger.error(
                f"Error fetching Terraform provider details for '{namespace}/{name}'",
                request_url=e.request.url,
                exc_info=True,
            )
            return {}

    async def list_provider_versions(self, provider_id: str) -> list[ProviderVersion]:
        if not self._client or "/" not in provider_id:
            return []
        namespace, name = provider_id.split("/", 1)
        endpoint = f"/v1/providers/{namespace}/{name}/versions"
        try:
            response = await self._client.get(endpoint)
            if response.status_code == 404:
                return []
            response.raise_for_status()
            data = response.json()
            return [
                ProviderVersion(
                    version=v.get("version", ""),
                    protocols=v.get("protocols", []),
                    platforms=[
                        ProviderPlatform(os=p.get("os", ""), arch=p.get("arch", ""))
                        for p in v.get("platforms", [])
                    ],
                )
                for v in data.get("versions", [])
            ]
        except (httpx.HTTPStatusError, httpx.RequestError) as e:
            logger.error(
                f"Error fetching Terraform provider versions for '{provider_id}'",
                request_url=e.request.url,
                exc_info=True,
            )
            return []

    async def get_module_details(
        self, namespace: str, name: str, provider: str, version: str
    ) -> dict[str, Any]:
        if not self._client:
            return {}
        endpoint = f"/v1/modules/{namespace}/{name}/{provider}/{version}"
        try:
            response = await self._client.get(endpoint)
            if response.status_code == 404:
                return {}
            response.raise_for_status()
            result: dict[str, Any] = response.json()
            return result
        except (httpx.HTTPStatusError, httpx.RequestError) as e:
            logger.error(
                f"Error fetching Terraform module details for '{namespace}/{name}/{provider}/{version}'",
                request_url=e.request.url,
                exc_info=True,
            )
            return {}

    async def list_module_versions(self, module_id: str) -> list[ModuleVersion]:
        if not self._client or module_id.count("/") != 2:
            return []
        namespace, name, provider = module_id.split("/")
        endpoint = f"/v1/modules/{namespace}/{name}/{provider}/versions"
        try:
            response = await self._client.get(endpoint)
            if response.status_code == 404:
                return []
            response.raise_for_status()
            data = response.json()
            versions_data = data.get("modules", [{}])[0].get("versions", [])
            return [ModuleVersion(version=v.get("version", "")) for v in versions_data if v.get("version")]
        except (httpx.HTTPStatusError, httpx.RequestError) as e:
            logger.error(
                f"Error fetching Terraform module versions for '{module_id}'",
                request_url=e.request.url,
                exc_info=True,
            )
            return []


# 🥣🔬🔚

#
# SPDX-FileCopyrightText: Copyright (c) 2025 provide.io llc. All rights reserved.
# SPDX-License-Identifier: Apache-2.0
#


from abc import ABC, abstractmethod
from typing import Any

from attrs import define
import httpx
from provide.foundation import logger

from tofusoup.registry.models.module import Module, ModuleVersion
from tofusoup.registry.models.provider import Provider, ProviderVersion


@define
class RegistryConfig:
    base_url: str


class BaseTfRegistry(ABC):
    def __init__(self, config: RegistryConfig) -> None:
        self.config = config
        self._client: httpx.AsyncClient | None = None
        logger.debug(f"BaseTfRegistry initialized for {config.base_url}")

    async def __aenter__(self) -> "BaseTfRegistry":
        if self._client is None:
            self._client = httpx.AsyncClient(base_url=self.config.base_url)
        return self

    async def __aexit__(
        self, exc_type: type[BaseException] | None, exc_val: BaseException | None, exc_tb: object | None
    ) -> None:
        if self._client:
            await self._client.aclose()
            self._client = None

    @abstractmethod
    async def list_providers(self, query: str | None = None) -> list[Provider]:
        pass

    @abstractmethod
    async def get_provider_details(self, namespace: str, name: str) -> dict[str, Any]:
        pass

    @abstractmethod
    async def list_provider_versions(self, provider_id: str) -> list[ProviderVersion]:
        pass

    @abstractmethod
    async def list_modules(self, query: str | None = None) -> list[Module]:
        pass

    @abstractmethod
    async def get_module_details(
        self, namespace: str, name: str, provider: str, version: str
    ) -> dict[str, Any]:
        pass

    @abstractmethod
    async def list_module_versions(self, module_id: str) -> list[ModuleVersion]:
        pass


# 🥣🔬🔚

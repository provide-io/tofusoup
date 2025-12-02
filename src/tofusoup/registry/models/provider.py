#
# SPDX-FileCopyrightText: Copyright (c) 2025 provide.io llc. All rights reserved.
# SPDX-License-Identifier: Apache-2.0
#


from datetime import datetime

from attrs import define, field


@define
class ProviderPlatform:
    """Represents a specific platform for a provider version."""

    os: str
    arch: str


@define
class ProviderVersion:
    """Represents a specific version of a provider."""

    version: str
    protocols: list[str] = field(factory=list)
    platforms: list[ProviderPlatform] = field(factory=list)
    published_at: datetime | None = field(default=None)


@define
class Provider:
    """Represents a provider in a registry."""

    id: str
    namespace: str
    name: str
    description: str | None = field(default=None)
    source_url: str | None = field(default=None)
    tier: str | None = field(default=None)
    versions: list[ProviderVersion] = field(factory=list)
    latest_version: ProviderVersion | None = field(default=None)
    registry_source: str | None = field(default=None)


# 🥣🔬🔚

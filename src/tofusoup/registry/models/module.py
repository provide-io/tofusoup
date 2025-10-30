#
# SPDX-FileCopyrightText: Copyright (c) 2025 provide.io llc. All rights reserved.
# SPDX-License-Identifier: Apache-2.0
#

"""TODO: Add module docstring."""

from datetime import datetime
from typing import Any

from attrs import define, field


@define
class ModuleInput:
    """Represents an input variable of a module."""

    name: str
    type: Any
    description: str | None = field(default=None)
    default: Any | None = field(default=None)
    required: bool = field(default=True)


@define
class ModuleOutput:
    """Represents an output value of a module."""

    name: str
    description: str | None = field(default=None)


@define
class ModuleResource:
    """Represents a resource managed by a module."""

    name: str
    type: str


@define
class ModuleVersion:
    """Represents a specific version of a module."""

    version: str
    published_at: datetime | None = field(default=None)
    readme_content: str | None = field(default=None)
    inputs: list[ModuleInput] = field(factory=list)
    outputs: list[ModuleOutput] = field(factory=list)
    resources: list[ModuleResource] = field(factory=list)


@define
class Module:
    """Represents a module in a registry."""

    id: str
    namespace: str
    name: str
    provider_name: str
    description: str | None = field(default=None)
    source_url: str | None = field(default=None)
    downloads: int = field(default=0)
    verified: bool = field(default=False)
    versions: list[ModuleVersion] = field(factory=list)
    latest_version: ModuleVersion | None = field(default=None)
    registry_source: str | None = field(default=None)


# 🥣🔬🔚

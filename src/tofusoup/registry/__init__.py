# 
# SPDX-FileCopyrightText: Copyright (c) 2025 provide.io llc. All rights reserved.
# SPDX-License-Identifier: Apache-2.0
#

"""Registry component for tfbrowser."""

from .base import BaseTfRegistry, RegistryConfig
from .opentofu import OpenTofuRegistry
from .terraform import IBMTerraformRegistry

__all__ = [
    "BaseTfRegistry",
    "IBMTerraformRegistry",
    "OpenTofuRegistry",
    "RegistryConfig",
]

# 🥣🔬🔚

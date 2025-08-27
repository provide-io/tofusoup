#
# tofusoup/registry/__init__.py
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

# 🐍⚙️


# 🍲🥄🚀🪄

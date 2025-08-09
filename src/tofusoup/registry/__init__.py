#
# tofusoup/registry/__init__.py
#
"""Registry component for tfbrowser."""

from .base import BaseRegistry, RegistryConfig
from .opentofu import OpenTofuRegistry
from .terraform import TerraformRegistry

__all__ = [
    "BaseRegistry",
    "OpenTofuRegistry",
    "RegistryConfig",
    "TerraformRegistry",
]

# 🐍⚙️


# 🍲🥄🚀🪄

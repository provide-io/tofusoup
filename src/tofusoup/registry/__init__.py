#
# tofusoup/registry/__init__.py
#
"""Registry component for tfbrowser."""

from .base import BaseTfRegistry, TfRegistryConfig
from .opentofu import OpenTofuRegistry
from .terraform import TerraformRegistry

__all__ = [
    "BaseTfRegistry",
    "OpenTofuRegistry",
    "TfRegistryConfig",
    "TerraformRegistry",
]

# 🐍⚙️


# 🍲🥄🚀🪄

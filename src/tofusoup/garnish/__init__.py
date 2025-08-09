#
# tofusoup/garnish/__init__.py
#
"""Documentation generation for Pyvider providers.

This package implements a comprehensive documentation generation system modeled after
HashiCorp's tfplugindocs tool. It extracts provider schemas, processes templates and
examples, and generates Terraform Registry-compliant documentation.
"""

from .cli import garnish_cli
from .generator import DocsGenerator
from .models import FunctionInfo, ProviderInfo, ResourceInfo

__all__ = [
    "DocsGenerator",
    "FunctionInfo",
    "ProviderInfo",
    "ResourceInfo",
    "garnish_cli",
]


# 🍲🥄🚀🪄

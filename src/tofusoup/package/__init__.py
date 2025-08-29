#
# tofusoup/package/__init__.py
#
"""
TofuSoup Package Module - PSPF Package Management

This module provides PSPF (Pyvider Secure Package Format) package management
functionality integrated into the TofuSoup CLI ecosystem.

Commands:
- soup package build    - Build PSPF packages
- soup package verify   - Verify package integrity
- soup package keygen   - Generate ECDSA signing keys
- soup package clean    - Clean build artifacts
- soup package init     - Initialize new provider projects
"""

# Re-export key components for clean API
# Note: flavor.models removed in newer flavor package
# from flavor.models import FlavorFooter as PspfFooter

from .exceptions import BuildError, PackageError, VerificationError

__all__ = [
    "BuildError",
    "PackageError",
    # "PspfFooter",  # Removed - no longer available in flavor
    "VerificationError",
]

# 📦🛠️✨


# 🍲🥄🚀🪄

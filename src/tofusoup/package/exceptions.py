#
# tofusoup/package/exceptions.py
#
"""Exceptions for the TofuSoup package command group."""

from tofusoup.common.exceptions import TofuSoupError


class PackageError(TofuSoupError):
    """Base exception for package-related errors."""

    pass


class BuildError(PackageError):
    """Exception raised when package building fails."""

    pass


class VerificationError(PackageError):
    """Exception raised when package verification fails."""

    pass


# 🍲🥄⚠️🪄

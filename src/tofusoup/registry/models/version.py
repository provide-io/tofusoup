#
# SPDX-FileCopyrightText: Copyright (c) provide.io llc. All rights reserved.
# SPDX-License-Identifier: Apache-2.0
#

"""Data models for versioning information."""

from datetime import datetime

from attrs import define, field
from provide.foundation import logger
import semver  # Using a library for robust semver parsing/comparison


@define
class VersionInfo:
    """Represents a semantic version, potentially with build metadata or other info."""

    raw_version: str = field()  # The original version string, e.g., "1.2.3-alpha+build.123"
    semantic_version: semver.Version = field(init=False)  # Parsed semver object
    published_at: datetime | None = field(default=None)
    # Add other generic version metadata if applicable

    def __attrs_post_init__(self) -> None:
        try:
            self.semantic_version = semver.Version.parse(self.raw_version)
        except ValueError as e:
            # Handle cases where raw_version might not be a strict semver string
            # Or raise a custom exception, or set a default/invalid state
            # For now, re-raise or log, depending on desired strictness
            # This example assumes strict parsing is desired.
            # Consider using semver.VersionInfo for the type if you don't need to re-parse often.
            logger.error("version_parse_error", raw_version=self.raw_version, error=str(e))
            # Fallback or error state for semantic_version if parsing fails
            # For simplicity in stub, we might let it raise or set to a known invalid state
            # For a robust app, you'd want a clear strategy here.
            # self.semantic_version = semver.Version(0,0,0,"invalid") # Example fallback
            raise  # Re-raising for now to indicate parsing failure

    @property
    def major(self) -> int:
        return self.semantic_version.major

    @property
    def minor(self) -> int:
        return self.semantic_version.minor

    @property
    def patch(self) -> int:
        return self.semantic_version.patch

    @property
    def prerelease(self) -> str | None:
        return self.semantic_version.prerelease

    @property
    def build(self) -> str | None:
        return self.semantic_version.build

    def __str__(self) -> str:
        return str(self.semantic_version)

    # Add comparison methods if needed, though semver.Version already provides them


# 🏷️🔢

# 🥣🔬🔚

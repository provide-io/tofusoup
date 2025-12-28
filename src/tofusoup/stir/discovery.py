#
# SPDX-FileCopyrightText: Copyright (c) 2025 provide.io llc. All rights reserved.
# SPDX-License-Identifier: Apache-2.0
#

"""Enhanced test discovery for hierarchical and flexible test detection."""

from __future__ import annotations

import fnmatch
from pathlib import Path
import re
import tomllib


class TestDiscovery:
    """Enhanced test discovery with hierarchical and pattern-based detection."""

    def __init__(
        self,
        patterns: list[str] | None = None,
        recursive: bool = False,
        max_depth: int | None = None,
        exclude_patterns: list[str] | None = None,
    ) -> None:
        """Initialize test discovery with configuration.

        Args:
            patterns: List of glob patterns to match test files
            recursive: Whether to search directories recursively
            max_depth: Maximum directory depth for recursive search
            exclude_patterns: Patterns to exclude from discovery
        """
        self.patterns = patterns or ["*.tf"]
        self.recursive = recursive
        self.max_depth = max_depth
        self.exclude_patterns = exclude_patterns or []

        # Common patterns that indicate test boundaries
        self.test_markers = [
            "main.tf",
            "test.tf",
            "example.tf",
            ".soup",
            "soup.toml",
            "terraform.tfvars",
        ]

        # Patterns to always exclude
        self.default_excludes = [
            ".terraform",
            ".terraform.lock.hcl",
            "terraform.tfstate*",
            ".git",
            "__pycache__",
            "*.pyc",
            ".pytest_cache",
            ".ruff_cache",
            "workenv",
            ".venv",
            "venv",
            "node_modules",
        ]

    def discover_tests(self, base_path: Path | str) -> list[Path]:
        """Discover test directories from the given base path.

        Args:
            base_path: Starting directory for test discovery

        Returns:
            List of discovered test directory paths
        """
        base_path = Path(base_path).resolve()

        # Handle non-existent paths or files
        if not base_path.exists() or not base_path.is_dir():
            return []

        discovered_tests = []

        if self.recursive:
            discovered_tests = self._discover_recursive(base_path)
        else:
            discovered_tests = self._discover_flat(base_path)

        # Apply filters and deduplication
        discovered_tests = self._filter_tests(discovered_tests)
        discovered_tests = self._deduplicate_tests(discovered_tests)

        return sorted(discovered_tests)

    def _discover_flat(self, base_path: Path) -> list[Path]:
        """Discover tests in a flat directory structure.

        Args:
            base_path: Directory to search

        Returns:
            List of test directories
        """
        tests = []

        # Check if base directory itself is a test
        if self._is_test_directory(base_path):
            tests.append(base_path)

        # Check immediate subdirectories
        for item in base_path.iterdir():
            if item.is_dir() and not self._should_exclude(item) and self._is_test_directory(item):
                tests.append(item)

        # Handle special directories like .plating-tests
        special_dirs = [".plating-tests", ".soup-tests", "examples", "tests"]
        for special in special_dirs:
            special_path = base_path / special
            if special_path.is_dir():
                for subdir in special_path.iterdir():
                    if subdir.is_dir() and self._is_test_directory(subdir):
                        tests.append(subdir)

        return tests

    def _discover_recursive(self, base_path: Path, depth: int = 0) -> list[Path]:
        """Recursively discover test directories.

        Args:
            base_path: Directory to search
            depth: Current recursion depth

        Returns:
            List of test directories
        """
        tests = []

        # Check depth limit
        if self.max_depth is not None and depth > self.max_depth:
            return tests

        # Check if current directory is a test
        if self._is_test_directory(base_path):
            tests.append(base_path)
            # Don't recurse into test directories by default
            return tests

        # Recurse into subdirectories
        for item in base_path.iterdir():
            if item.is_dir() and not self._should_exclude(item):
                tests.extend(self._discover_recursive(item, depth + 1))

        return tests

    def _is_test_directory(self, path: Path) -> bool:
        """Check if a directory contains tests.

        Args:
            path: Directory to check

        Returns:
            True if directory contains tests
        """
        # Check for test marker files
        for marker in self.test_markers:
            if (path / marker).exists():
                return True

        # Check for files matching patterns
        return any(list(path.glob(pattern)) for pattern in self.patterns)

    def _should_exclude(self, path: Path) -> bool:
        """Check if a path should be excluded from discovery.

        Args:
            path: Path to check

        Returns:
            True if path should be excluded
        """
        path_str = str(path)
        name = path.name

        # Check default excludes
        for exclude in self.default_excludes:
            if fnmatch.fnmatch(name, exclude) or exclude in path_str:
                return True

        # Check user-defined excludes
        for exclude in self.exclude_patterns:
            if fnmatch.fnmatch(name, exclude) or fnmatch.fnmatch(path_str, exclude):
                return True

        # Check for hidden directories (except special ones)
        return bool(name.startswith(".") and name not in [".plating-tests", ".soup-tests", ".soup"])

    def _filter_tests(self, tests: list[Path]) -> list[Path]:
        """Apply additional filtering to discovered tests.

        Args:
            tests: List of test directories

        Returns:
            Filtered list of test directories
        """
        filtered = []
        for test in tests:
            # Additional validation can be added here
            if test.exists() and test.is_dir():
                filtered.append(test)
        return filtered

    def _deduplicate_tests(self, tests: list[Path]) -> list[Path]:
        """Remove duplicate and nested test directories.

        Args:
            tests: List of test directories

        Returns:
            Deduplicated list of test directories
        """
        # Sort by path depth (shallow first)
        sorted_tests = sorted(tests, key=lambda p: len(p.parts))
        deduplicated = []

        for test in sorted_tests:
            # Check if this test is a child of any already added test
            is_child = False
            for existing in deduplicated:
                if test.is_relative_to(existing) and test != existing:
                    is_child = True
                    break

            if not is_child:
                deduplicated.append(test)

        return deduplicated


class TestFilter:
    """Filter discovered tests based on various criteria."""

    def __init__(
        self,
        path_filters: list[str] | None = None,
        tags: list[str] | None = None,
        types: list[str] | None = None,
        regex_pattern: str | None = None,
    ) -> None:
        """Initialize test filter.

        Args:
            path_filters: Path-based filters (e.g., "function/*")
            tags: Tag-based filters (e.g., ["basic", "example"])
            types: Component type filters (e.g., ["data_source", "resource"])
            regex_pattern: Regex pattern to match test paths
        """
        self.path_filters = path_filters or []
        self.tags = tags or []
        self.types = types or []
        self.regex_pattern = re.compile(regex_pattern) if regex_pattern else None

        # Map component types to path segments
        self.type_mappings = {
            "data_source": ["data_source", "data-source", "datasource"],
            "resource": ["resource", "resources"],
            "function": ["function", "functions", "func"],
            "provider": ["provider", "providers"],
        }

    def filter_tests(self, tests: list[Path]) -> list[Path]:
        """Filter tests based on configured criteria.

        Args:
            tests: List of test directories to filter

        Returns:
            Filtered list of test directories
        """
        if not any([self.path_filters, self.tags, self.types, self.regex_pattern]):
            return tests

        filtered = []
        for test in tests:
            if self._matches_filters(test):
                filtered.append(test)

        return filtered

    def _matches_filters(self, test: Path) -> bool:
        """Check if a test matches all configured filters.

        Args:
            test: Test directory to check

        Returns:
            True if test matches all filters
        """
        # Check path filters
        if self.path_filters and not self._matches_path_filter(test):
            return False

        # Check type filters
        if self.types and not self._matches_type_filter(test):
            return False

        # Check regex pattern
        if self.regex_pattern and not self._matches_regex(test):
            return False

        # Check tags (would need metadata extraction)
        return not (self.tags and not self._matches_tags(test))

    def _matches_path_filter(self, test: Path) -> bool:
        """Check if test matches any path filter.

        Args:
            test: Test directory to check

        Returns:
            True if test matches any path filter
        """
        test_str = str(test)
        for filter_pattern in self.path_filters:
            # Handle negation
            if filter_pattern.startswith("!"):
                if fnmatch.fnmatch(test_str, filter_pattern[1:]):
                    return False
            else:
                if fnmatch.fnmatch(test_str, f"*{filter_pattern}*"):
                    return True

        # If only negative filters, default to include
        return bool(all(f.startswith("!") for f in self.path_filters))

    def _matches_type_filter(self, test: Path) -> bool:
        """Check if test matches any type filter.

        Args:
            test: Test directory to check

        Returns:
            True if test matches any type filter
        """
        test_str = str(test).lower()
        for type_name in self.types:
            if type_name in self.type_mappings:
                for variant in self.type_mappings[type_name]:
                    if variant in test_str:
                        return True
            elif type_name in test_str:
                return True

        return False

    def _matches_regex(self, test: Path) -> bool:
        """Check if test matches regex pattern.

        Args:
            test: Test directory to check

        Returns:
            True if test matches regex pattern
        """
        if self.regex_pattern:
            return bool(self.regex_pattern.search(str(test)))
        return True

    def _extract_tags_from_directory_name(self, test: Path) -> list[str]:
        """Extract tags from directory name patterns."""
        name = test.name.lower()
        for pattern in ["test_", "_test", "example_", "_example"]:
            name = name.replace(pattern, " ")
        parts = [p for p in name.split("_") if p and len(p) > 1]
        skip_words = {"test", "tests", "example", "examples"}
        return [p for p in parts if p not in skip_words]

    def _extract_tags_from_soup_toml(self, test: Path) -> list[str]:
        """Extract tags from soup.toml metadata."""
        soup_toml = test / "soup.toml"
        if not soup_toml.exists():
            return []
        try:
            with soup_toml.open("rb") as f:
                data = tomllib.load(f)
            if "metadata" in data and "tags" in data["metadata"]:
                return list(data["metadata"]["tags"])
            if "test" in data and "tags" in data["test"]:
                return list(data["test"]["tags"])
        except Exception:
            pass
        return []

    def _extract_tags_from_main_tf(self, test: Path) -> list[str]:
        """Extract tags from # @tags: comments in main.tf."""
        main_tf = test / "main.tf"
        if not main_tf.exists():
            return []
        try:
            content = main_tf.read_text()
            for line in content.splitlines()[:20]:
                if line.strip().startswith("# @tags:"):
                    tag_str = line.split(":", 1)[1].strip()
                    return [t.strip() for t in tag_str.split(",") if t.strip()]
        except Exception:
            pass
        return []

    def _get_all_tags(self, test: Path) -> set[str]:
        """Get all tags from all sources."""
        tags: set[str] = set()
        tags.update(self._extract_tags_from_directory_name(test))
        tags.update(self._extract_tags_from_soup_toml(test))
        tags.update(self._extract_tags_from_main_tf(test))
        return tags

    def _matches_tags(self, test: Path) -> bool:
        """Check if test matches required tags.

        Args:
            test: Test directory to check

        Returns:
            True if test has required tags
        """
        all_tags = self._get_all_tags(test)
        for tag in self.tags:
            if tag.startswith("!"):
                if tag[1:] in all_tags:
                    return False
            elif tag in all_tags:
                return True
        return bool(all(t.startswith("!") for t in self.tags))


def discover_tests_with_patterns(
    base_path: Path | str,
    pattern: list[str] | None = None,
    recursive: bool = False,
    filters: TestFilter | None = None,
) -> list[Path]:
    """Convenience function for pattern-based test discovery.

    Args:
        base_path: Starting directory for test discovery
        pattern: List of glob patterns to match
        recursive: Whether to search recursively
        filters: Optional test filters to apply

    Returns:
        List of discovered and filtered test directories
    """
    discoverer = TestDiscovery(patterns=pattern, recursive=recursive)
    tests = discoverer.discover_tests(base_path)

    if filters:
        tests = filters.filter_tests(tests)

    return tests


# 🥣🔬🔚

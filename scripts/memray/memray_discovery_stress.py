#!/usr/bin/env python3
"""Memray stress test for test discovery hot paths.

Targets: TestDiscovery.discover_tests and TestFilter.filter_tests --
invoked on every `soup stir` run to find test directories.
"""

import os
import tempfile
from pathlib import Path

os.environ.setdefault("LOG_LEVEL", "ERROR")

from tofusoup.stir.discovery import TestDiscovery, TestFilter


def _build_test_tree(base: Path, num_dirs: int = 80) -> None:
    """Create a synthetic directory tree resembling a provider repo."""
    categories = ["resource", "data_source", "function", "provider"]
    for i in range(num_dirs):
        cat = categories[i % len(categories)]
        d = base / cat / f"test_{i:03d}"
        d.mkdir(parents=True, exist_ok=True)
        # Every test dir has a main.tf
        (d / "main.tf").write_text(f'resource "null_resource" "test_{i}" {{}}\n')
        # Some have soup.toml
        if i % 4 == 0:
            (d / "soup.toml").write_text(f'[metadata]\ntags = ["basic", "{cat}"]\n')
        # Some have extra .tf files
        if i % 3 == 0:
            (d / "variables.tf").write_text(f'variable "v_{i}" {{ type = string }}\n')

    # Add excluded dirs that should be skipped
    for excl in [".terraform", "__pycache__", ".git", ".venv"]:
        ed = base / excl
        ed.mkdir(parents=True, exist_ok=True)
        (ed / "main.tf").write_text("# should be excluded\n")

    # Add nested special dirs
    special = base / ".plating-tests"
    special.mkdir(parents=True, exist_ok=True)
    for j in range(10):
        sd = special / f"plating_{j}"
        sd.mkdir(parents=True, exist_ok=True)
        (sd / "main.tf").write_text(f'resource "null_resource" "plating_{j}" {{}}\n')


def main() -> None:
    tmpdir = Path(tempfile.mkdtemp())
    _build_test_tree(tmpdir, num_dirs=80)

    # Warmup
    disc = TestDiscovery(recursive=True, max_depth=5)
    for _ in range(5):
        disc.discover_tests(tmpdir)

    # Stress: flat + recursive discovery with filtering
    cycles = 200
    for i in range(cycles):
        # Alternate between flat and recursive
        if i % 2 == 0:
            d = TestDiscovery(recursive=False)
        else:
            d = TestDiscovery(recursive=True, max_depth=4)
        tests = d.discover_tests(tmpdir)

        # Apply filters on half the iterations
        if i % 3 == 0:
            tf = TestFilter(types=["resource"])
            tf.filter_tests(tests)
        elif i % 3 == 1:
            tf = TestFilter(path_filters=["*function*"])
            tf.filter_tests(tests)

    # Cleanup
    import shutil

    shutil.rmtree(tmpdir, ignore_errors=True)

    print(f"Discovery stress test complete: {cycles} discovery cycles")


if __name__ == "__main__":
    main()

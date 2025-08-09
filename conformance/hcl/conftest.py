# src/tofusoup/conformance/hcl/conftest.py
"""
Pytest fixtures specific to HCL conformance tests.
"""
import pytest
from pathlib import Path
import os

# Placeholder for a Go HCL harness fixture, if one is created/used.
# @pytest.fixture(scope="session")
# def go_hcl_parser_harness_executable(harnesses_bin_dir: Path, project_root: Path) -> Path:
#     from tofusoup.harness.logic import ensure_go_harness_build, TofuSoupError
#     try:
#         # Assuming a harness key "hcl-parser-go"
#         executable_path = ensure_go_harness_build("hcl-parser-go", project_root, output_base_dir=harness_bin_dir)
#         if not executable_path.exists() or not os.access(executable_path, os.X_OK):
#             pytest.fail(f"Go HCL harness executable missing or not executable: {executable_path}")
#         return executable_path
#     except TofuSoupError as e:
#         pytest.fail(f"Failed to ensure Go HCL harness was built: {e}")
#     except ImportError:
#         pytest.skip("Skipping Go HCL harness tests: tofusoup.harness.logic not available.")
#     return Path("dummy_go_hcl_harness_path")


# 🍲🥄🧪🪄

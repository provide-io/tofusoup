#
# tofusoup/harness/python/conftest.py
#
from pathlib import Path
import subprocess

import pytest


def build_harness(harness_name: str, source_path: Path) -> Path:
    """Helper to build a Go harness into the venv."""
    # Assume script is run from `tofusoup` directory, so .venv is at root
    venv_bin = Path(".venv/bin")
    venv_bin.mkdir(exist_ok=True)
    executable_path = venv_bin / harness_name

    # Simple check to avoid rebuilding on every test run
    if executable_path.exists():
        return executable_path

    cmd = ["go", "build", "-o", str(executable_path), str(source_path)]
    result = subprocess.run(cmd, capture_output=True, text=True, cwd=source_path.parent)
    if result.returncode != 0:
        pytest.fail(
            f"Failed to build Go harness '{harness_name}':\n{result.stderr}",
            pytrace=False,
        )
    return executable_path


@pytest.fixture(scope="session")
def go_cty_harness(request) -> Path:
    # Use request.config.rootpath to find the harness relative to the test root
    root_path = request.config.rootpath
    # Adjusted path to new Go harness location
    source_file = root_path / "harnesses/go/cty-generic/harness.go"
    if not source_file.exists():
        # Also check the cty-owf harness as it was similar
        source_file_owf = (
            root_path / "harnesses/go/cty-owf/main.go"
        )  # Assuming main.go is the entry
        if source_file_owf.exists():
            source_file = source_file_owf
            harness_name = "go-cty-owf-harness"
        else:
            pytest.skip(
                f"Go CTY harness source not found at {source_file} or {source_file_owf}."
            )
            return  # Should not be reached if skip works
    else:
        harness_name = "go-cty-generic-harness"  # Default name if primary found

    return build_harness(harness_name, source_file)


@pytest.fixture(scope="session")
def go_tfwire_harness(request) -> Path:
    root_path = request.config.rootpath
    # Adjusted path to new Go harness location
    source_file = root_path / "harnesses/go/tfwire/harness.go"
    if not source_file.exists():
        pytest.skip(f"Go TF-Wire harness source not found at {source_file}.")
    return build_harness("go-tfwire-harness", source_file)


@pytest.fixture(scope="session")
def go_kvstore_harness(request) -> Path:
    root_path = request.config.rootpath
    # Path should align with where `generate-harness kvstore-go` places it or its source.
    # Assuming `harnesses/go/rpc-kvstore/server/main.go` is the source for the server part.
    # The actual binary built by `ensure_go_harness_build` (called by test logic)
    # will be used by the tests. This fixture provides the *source* path convention if needed,
    # or could directly provide the *built* path if ensure_go_harness_build is called here.
    # For now, let's assume `ensure_go_harness_build("kvstore-go", root_path)` will be called
    # by the test execution logic (e.g. in `tofusoup.testing.logic.run_test_suite`)
    # and this fixture could provide a conventional name or path if tests needed to refer to it
    # beyond what the test logic already handles.

    # For tests that need to *start* the Go server with specific crypto,
    # this fixture might need to be more complex, or the test logic itself
    # would handle calling `ensure_go_harness_build` and then running the binary with args.

    # Let's have this fixture ensure the build and return the path to the executable.
    # This centralizes the build call for this specific harness.
    try:
        from tofusoup.harness.logic import (
            ensure_go_harness_build,
        )  # Local import to avoid top-level issues if problematic

        # The name "kvstore-go" should match a key in GO_HARNESS_CONFIG in harness.logic
        harness_bin_dir = ensure_go_harness_build(
            "kvstore-go", root_path
        )  # ensure_go_harness_build returns the bin dir

        # The actual executable name might vary. Common patterns: <harness_name> or main
        # Based on kvproto, it's likely 'kv-go-server' or compiled from 'plugin-go-server/main.go'
        # Let's assume ensure_go_harness_build places it predictably or returns the full path.
        # For now, assume the harness logic places it as "kvstore-go-server" in the returned dir.
        # This needs to align with the output of `generate-harness kvstore-go`.
        # The `plugin-go-server/main.go` from kvproto builds to `kv-go-server`.
        # The `go-harnesses/rpc/kvstore/` (used by soup generate-harness) also has a server.
        # Let's assume `generate-harness kvstore-go` produces `kvstore-server-go` in a general bin.

        # The ensure_go_harness_build should return the path to the directory containing the binary.
        # The actual name of the binary needs to be known.
        # `soup rpc kv server-start` assumes `kvstore-server-go` in `harness_path / "bin" / "kvstore-server-go"`
        # Let's assume `ensure_go_harness_build` returns the root of the harness build (e.g. .../tofusoup/harness/go/bin/go-rpc )
        # and the binary is at a known relative path like `bin/kvstore-server-go` or the name from GO_HARNESS_CONFIG.

        # For simplicity, this fixture will just return the directory provided by ensure_go_harness_build.
        # The test will then construct the full path to the executable.
        # A more robust fixture would return the full executable path.

        # Let's refine: assume `ensure_go_harness_build` returns the specific binary path directly.
        # This requires `harness.logic.ensure_go_harness_build` to be updated or to have a helper.
        # For now, let's assume it returns the directory, and we append the known name.
        # This needs to align with `soup rpc kv server-start` logic.
        # It uses: harness_path / "bin" / "kvstore-server-go"
        # where harness_path is from ensure_go_harness_build("kvstore-go", project_root)
        # So, ensure_go_harness_build must return the root of the specific harness deployment.

        # The `ensure_go_harness_build` in `tofusoup.harness.logic` is responsible for building
        # AND returning the path to the executable (or a directory from which it can be found).
        # The key "kvstore-go" must be defined in `GO_HARNESS_CONFIG` within `harness.logic.py`.

        # This fixture will ensure it's built and return the path to the executable.
        # The current `ensure_go_harness_build` in the plan returns the harness *root* dir.
        # Let's assume the build process places the binary at a known relative path from that root.
        # Or, `ensure_go_harness_build` should be enhanced to return the direct executable path.

        # For now, let this fixture just ensure it's built. The test logic will get the path.
        # This is consistent with how `run_test_suite` calls `ensure_go_harness_build`.
        # The test itself will then need to know the path to the executable.
        # This fixture is mainly for explicit invocation in tests if needed outside `run_test_suite`.

        # A simpler fixture: just provides the *name* of the harness key.
        # The test or test runner logic (`run_test_suite`) handles the building.
        # This avoids this conftest.py needing to know too much about build outputs.
        # return "kvstore-go" # The key for GO_HARNESS_CONFIG

        # Revised: Fixture should ensure build and provide path to the executable.
        # `ensure_go_harness_build` is expected to return the path to the directory
        # where binaries are placed, or directly to the binary.
        # Let's assume it returns the directory, and we know the executable name.
        harness_info = ensure_go_harness_build(
            "kvstore-go", root_path
        )  # This should give us enough info

        # harness_info could be a Path to the binary, or a dict with details.
        # Assuming harness_info is the Path to the built executable itself, as per
        # the ideal outcome of ensure_go_harness_build for a specific harness.
        # If ensure_go_harness_build returns a directory, this needs adjustment:
        # e.g., harness_executable = harness_info / "bin" / "kvstore-server-go" (or similar)
        # This depends on the contract of ensure_go_harness_build and GO_HARNESS_CONFIG in harness.logic.
        # For now, let's assume ensure_go_harness_build returns the direct path to the executable.
        if (
            not isinstance(harness_info, Path)
            or not harness_info.exists()
            or not os.access(harness_info, os.X_OK)
        ):
            # If harness_info is a directory, try to find the executable
            if isinstance(harness_info, Path) and harness_info.is_dir():
                # Attempt to find a known executable name, this must match build output
                potential_exe_name = (
                    "kvstore-server-go"  # This name is assumed by rpc.cli.py
                )
                exe_path = harness_info / "bin" / potential_exe_name
                if exe_path.exists() and os.access(exe_path, os.X_OK):
                    return exe_path
                # Fallback for older kvproto name if needed, or other conventions.
                potential_exe_name_alt = "kv-go-server"
                exe_path_alt = harness_info / "bin" / potential_exe_name_alt
                if exe_path_alt.exists() and os.access(exe_path_alt, os.X_OK):
                    return exe_path_alt
                pytest.fail(
                    f"Go KVStore server executable ('{potential_exe_name}' or '{potential_exe_name_alt}') not found in harness build dir: {harness_info}/bin"
                )
            else:
                pytest.fail(
                    f"ensure_go_harness_build for 'kvstore-go' did not return a valid executable path or directory. Got: {harness_info}"
                )
        return harness_info  # Assuming harness_info is the direct executable path

    except ImportError:
        pytest.skip(
            "TofuSoup harness logic (ensure_go_harness_build) not available, skipping Go KVStore harness dependent tests."
        )
    except Exception as e:
        pytest.fail(f"Failed to prepare Go KVStore harness fixture: {e}")


# 🍲🥄🧪🪄

# 🍲 TofuSoup Conformance Suite
=============================

TofuSoup is a comprehensive, cross-language conformance testing suite and utility toolkit for ensuring compatibility and correctness across various implementations of OpenTofu-related technologies, including CTY, HCL, RPC mechanisms, and the Terraform Wire Protocol (tfwire).

It provides:

-   **Python-driven test suites:** For validating Python implementations against canonical Go harnesses and other language implementations.
-   **Go test harnesses:** Reference implementations for CTY, tfwire, and example RPC services.
-   **A powerful Command-Line Interface (CLI):** For development, testing, data conversion, and interaction with test services.

## Core Philosophy
---------------

-   **Cross-Language Compatibility:** Ensure that data formats and protocol behaviors are consistent across Go, Python, Rust, and JavaScript in the OpenTofu ecosystem.
-   **Developer Experience (DX):** Provide intuitive tools and clear feedback to developers working on or with these core components. Uses the `rich` library for enhanced console output.
-   **Modularity & Extensibility:** Structure the suite and CLI in a way that's easy to understand, maintain, and extend with new tests or utilities.
-   **Test Harnesses:** Utilizes language-specific test harnesses (e.g., Go) managed via the `soup harness` commands.

## Installation and Setup
----------------------

1.  **Clone the Repository:**
    ```bash
    git clone https://github.com/opentofu/tofusoup.git # Assuming this is the future location
    cd tofusoup
    ```

2.  **Environment Setup:** This project uses `uv` for Python environment and package management.
    ```bash
    # Ensure uv is installed (see https://github.com/astral-sh/uv)
    # e.g., curl -LsSf https://astral.sh/uv/install.sh | sh

    # Source the environment script (activates venv, installs dependencies)
    # (From the root of the 'tofusoup' monorepo)
    source env.sh
    ```
    The `env.sh` script will:
    -   Create/activate a Python virtual environment (e.g., in `.venv/`).
    -   Install `tofusoup` in editable mode along with its dependencies using `uv pip install -e .[dev]`.
    -   Install any sibling `pyvider-*` packages found in the parent directory in editable mode.

3.  **Verify Installation:** The `env.sh` script will output version information upon successful setup. You can also manually check:
    ```bash
    uv --version
    python3 --version
    soup --version
    ```

**Note on Go Harnesses:** The Go test harnesses (`go-cty`, `go-wire`, `go-rpc`, `go-hcl`) are standardized to use `cobra` for their CLI structure and `go-hclog` for logging. This provides a consistent interface and configurable logging (via a `--log-level` flag) across these tools.

**Note on Test Artifacts:** Output from CLI verification tests (stdout, stderr of harness executions) is saved to `tofusoup/soup/output/cli_verification/<harness_name>/<test_id>/` for inspection. Other build or test artifacts may also be placed under `tofusoup/soup/output/`.

## `tofusoup` Command-Line Interface (CLI)
---------------------------------------

The `tofusoup` CLI is your primary interface for interacting with the suite. It's organized into subcommands based on the component you're working with. All commands provide enhanced terminal output using the `rich` library.

**General Options (available for `tofusoup` and all subcommands):**
-   `--help`: Show help for the current command or subcommand.
-   `--verbose`: Enable verbose output (shortcut for --log-level DEBUG).
-   `--log-level <LEVEL>`: Set the logging level (e.g., DEBUG, INFO). Overrides `TOFUSOUP_LOG_LEVEL` env var and `soup.toml` settings. See `docs/CONFIG_TOML.md`.
-   `--config-file <PATH>`: Path to the TofuSoup configuration file (TOML format, default: `soup.toml`). Searched in order: explicit path, `./soup.toml`, `<project_root>/soup/soup.toml`. See `docs/CONFIG_TOML.md`.
-   `--version` (only for top-level `tofusoup`): Show TofuSoup version.

* * * * *

### 🧱 `soup cty` - CTY Utilities & Tests

Commands for working with the Configuration Type System (CTY).

-   **`soup cty view <filepath> [--format <json|msgpack|hcl>]`**
    -   Displays the CTY structure of a given JSON, Msgpack, or HCL data file. The format is inferred from the extension if not specified. For HCL, this command attempts to parse it as generic CTY-compatible HCL; for more direct HCL parsing and representation, use `soup hcl view`.
    -   Output is a rich tree view.
    -   Example: `soup cty view data.json`
    -   Example: `soup cty view data.mpk --format msgpack`
    -   Example: `soup cty view config.tfvars --format hcl` (with warning)

-   **`soup cty convert <input_file> <output_file> [--input-format <json|msgpack|hcl>] [--output-format <json|msgpack>]`**
    -   Converts files between CTY-compatible JSON, Msgpack, and HCL (input only for HCL).
    -   Formats are inferred from file extensions if options are not provided.
    -   Example: `soup cty convert input.json output.msgpack`
    -   Example: `soup cty convert config.tf output.json --input-format hcl`

-   **`soup cty test [compat|all]`**
    -   (Deprecated in favor of `soup test cty`). Runs older CTY test suites.
    -   `compat`: Executes Python vs. Go CTY compatibility tests. Requires `go-cty` harness.

-   **`soup cty benchmark [--iterations N] [--testcase <name>] [--data-file <path>] [--output-dir <path>]`**
    -   Runs CTY encoding/decoding benchmarks. Options can be defaulted in `soup.toml`.
    -   Requires `go-cty` harness. See `docs/CONFIG_TOML.md`.

-   **`soup cty validate-value <value_json_string> --type-string <cty_type_string> [--harness-path <path>]`**
    -   Validates a CTY value (JSON string) against a CTY type string using the `go-cty` harness.
    -   Type string example: "object({name=string,age=number})".
    -   The value must be a valid JSON representation of the data to be validated.
    -   Example: `soup cty validate-value '"hello"' --type-string string`
    -   Example: `soup cty validate-value '[1, 2, 3]' --type-string "list(number)"`
    -   Example: `soup cty validate-value '{"name":"opustofu","age":1}' --type-string "object({name=string,age=number})"`

* * * * *

### 📄 `soup hcl` - HCL Utilities

Commands specifically for HCL file processing (often in conjunction with CTY).

-   **`soup hcl view <filepath>`**
    -   Parses an HCL file and displays its structure as a CTY representation using a rich tree view.
    -   Example: `soup hcl view main.tf`

-   **`soup hcl convert <input_file> <output_file> [--output-format <json|msgpack>]`**
    -   Converts an HCL file to JSON or Msgpack. This implicitly uses CTY as the intermediate representation.
    -   Output format inferred if not specified.
    -   Example: `soup hcl convert network.hcl network.json`
    -   Default output format can be configured in `soup.toml`. See `docs/CONFIG_TOML.md`.

* * * * *

### 🔌 `soup rpc` - RPC Utilities & Tests

Commands for interacting with and testing RPC components, exemplified by a Key-Value store. Uses `pyvider-rpcplugin` for Python client logic.

-   **`soup rpc kv server-start [--py | --go-server-bin <path>] [<go_server_options>]`**
    -   Starts an RPC Key-Value store server.
    -   `--py`: Starts the Python server.
    -   `--go-server-bin <path>`: Path to Go server binary (default: built `go-rpc` harness).
    -   Go server options (e.g., `--cert-algo`, `--no-mtls`) can be defaulted in `soup.toml`. See `docs/CONFIG_TOML.md`.

-   **`soup rpc kv get <key> [--server-bin <path>]`**
    -   Gets a value from an RPC KV server using the Python client.
    -   `--server-bin`: Path to server (e.g., `tofusoup/src/tofusoup/harness/go/bin/go-rpc`). Default from `PLUGIN_SERVER_PATH` env var or `soup.toml`. See `docs/CONFIG_TOML.md`.
    -   Example: `soup rpc kv get mykey --server-bin tofusoup/src/tofusoup/harness/go/bin/go-rpc`

-   **`soup rpc kv put <key> <value> [--server-bin <path>]`**
    -   Puts a key-value pair into an RPC KV server using the Python client.
    -   `--server-bin`: Path to server. Default from `PLUGIN_SERVER_PATH` env var or `soup.toml`.
    -   Example: `soup rpc kv put mykey "hello" --server-bin tofusoup/src/tofusoup/harness/go/bin/go-rpc`

-   **`soup rpc test [compat|all]`**
    -   (Deprecated in favor of `soup test rpc`). Runs older RPC test suites.
    -   Requires `go-rpc` harness.

* * * * *

### 🔗 `soup wire` - Terraform Wire Protocol Utilities & Tests

Commands for working with the Terraform Wire Protocol (tfwire) objects. These commands act as a CLI and testing interface for the canonical `pyvider.wire` Python library.

-   **`soup wire encode <input_json_file> <output_tfw_b64_file>`**
    -   Encodes a JSON representation of a Terraform object (which must include 'type' and 'value' keys) into the tfwire format (MessagePack, then Base64 encoded), utilizing `pyvider.wire`.
    -   Use `-` for stdin/stdout.
    -   Example: `soup wire encode value_with_type.json value.tfw.b64`

-   **`soup wire decode <input_tfw_b64_file> <output_json_file>`**
    -   Decodes a tfwire (Base64 encoded MessagePack) object into its JSON representation (which will include 'type' and 'value' keys).
    -   Use `-` for stdin/stdout.
    -   Example: `soup wire decode value.tfw.b64 value.json`

-   **`soup wire test [compat|all]`**
    -   (Deprecated in favor of `soup test wire`). Runs older tfwire compatibility tests.
    -   Requires `go-wire` harness.

* * * * *

### 🛠️ `soup harness` - Manage Test Harnesses

Commands to list, build/setup, verify, and clean test harnesses (e.g., Go executables). Compiled binaries are typically placed in `tofusoup/src/tofusoup/harness/go/bin/`. See `docs/CONFIG_TOML.md`.

-   **`soup harness list`**
    -   Lists available harnesses and their build/setup status.

-   **`soup harness build [<harness_names...>] [--language <lang>] [--all] [--force-rebuild|--force-setup]`**
    -   Builds/sets up harnesses. If no specific targets are given, uses `default_targets` from `soup.toml` for this command, or all known harnesses.
    -   Examples:
        -   `soup harness build go-cty rb-rpc`
        -   `soup harness build --language go --force-rebuild`

-   **`soup harness verify-cli [<harness_names...>] [--language <lang>] [--all]`**
    -   Verifies basic CLI functionality of primarily Go harnesses using `scripts/verify_harness_cli.py`. Default targets from `soup.toml` or all applicable.

-   **`soup harness clean [<harness_names...>] [--language <lang>] [--all]`**
    -   Removes built harness artifacts. Default targets from `soup.toml` or all.

* * * * *

### ✅ `soup test` - Run Conformance Tests

Runs Pytest-based conformance test suites located in `tofusoup/conformance/`. Test behavior (env vars, skips, args) can be configured in `soup.toml`. See `docs/CONFIG_TOML.md`.

-   **`soup test <suite_name> [pytest_args...]`**
    -   Runs a specific test suite (e.g., `cty`, `rpc`, `wire`, `cli-cty`, `cli-hcl`, `cli-wire`).
    -   Any additional arguments are passed directly to `pytest`.
    -   Example: `soup test cty -k "some_test_name" -m "not slow"`

-   **`soup test all`**
    -   Runs all defined test suites.

* * * * *

## Project Structure Highlights
----------------------------

-   **`tofusoup/` (Monorepo Root)**
    -   **`env.sh`**: Main environment setup script.
    -   **`pyproject.toml`**: Defines the `tofusoup` Python package and dependencies.
    -   **`src/tofusoup/`**: The main Python source code for the `tofusoup` CLI and its submodules.
        -   `cli.py`: Main CLI entry point.
        -   `common/`: Shared utilities (exceptions, config, Rich helpers, etc.).
        -   `cty/`, `hcl/`, `rpc/`, `wire/`: Component-specific logic and CLI subcommands.
        -   `protos/`: Source `.proto` files are now co-located with their respective harness sources. Generated Python stubs are placed within `src/tofusoup/protos/` by build scripts.
        -   `harness/`: Logic and CLI for building/managing external test harnesses.
        -   `testing/`: Logic and CLI for running test suites.
    -   **`tofusoup/src/tofusoup/harness/go/`**: Source code for Go test harnesses (e.g., `go-cty/`, `go-hcl/`, `go-rpc/kv/plugin-go-server/`, `go-wire/`).
    -   **`tofusoup/conformance/`**: Pytest test suites for cross-language conformance.
        -   `cty/`, `hcl/`, `rpc/`, `wire/`: Component-specific conformance tests.
        -   `cli_verification/`: Tests for harness CLIs.
        -   `utils/`: Shared utilities for conformance tests.
    -   **`tofusoup/soup/soup.toml`**: Default and recommended location for the TOML configuration file for TofuSoup. An example file is provided here. The CLI also checks `<pwd>/soup.toml`.
    -   **`tofusoup/soup/`**: Runtime data, output artifacts.
        -   `output/`: Default directory for test artifacts, logs.
    -   **`docs/`**: Documentation files.
        -   `CONFIG_TOML.md` (Future): Will contain detailed information about the `soup.toml` configuration file. Refer to the example at `tofusoup/soup/soup.toml` for now.
    -   **`tofusoup/tests/`**: General Python unit/integration tests for TofuSoup's own CLI and core Python functionalities (distinct from cross-language conformance tests).
    -   *(Note: Legacy directories like `ctytool/`, `go-harnesses/`, `kvproto/` have been removed or integrated into the new structure).*

## Contributing
------------

Contributions are welcome! Please look for a `CONTRIBUTING.md` file (or create one if it doesn't exist) for guidelines. Key areas for contribution:

-   Implementing the placeholder commands and test logic in the new CLI structure.
-   Adding more test cases for CTY, HCL, RPC, and Wire.
-   Developing or improving Rust and JavaScript test harnesses and drivers.
-   Enhancing the CLI with new features or improved usability.
-   Improving documentation and adding examples.

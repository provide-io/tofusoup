# 🥣🔬 TofuSoup

[![License](https://img.shields.io/badge/License-Apache_2.0-blue.svg)](https://opensource.org/licenses/Apache-2.0)
[![Python 3.11+](https://img.shields.io/badge/python-3.11+-blue.svg)](https://www.python.org/downloads/)
[![uv](https://img.shields.io/badge/uv-package_manager-FF6B35.svg)](https://github.com/astral-sh/uv)
[![Ruff](https://img.shields.io/endpoint?url=https://raw.githubusercontent.com/astral-sh/ruff/main/assets/badge/v2.json)](https://github.com/astral-sh/ruff)
[![CI](https://github.com/provide-io/tofusoup/actions/workflows/ci.yml/badge.svg)](https://github.com/provide-io/tofusoup/actions)

=============================

TofuSoup is a comprehensive, cross-language conformance testing suite and utility toolkit for ensuring compatibility and correctness across various implementations of OpenTofu-related technologies, including CTY, HCL, RPC mechanisms, and the Terraform Wire Protocol (tfwire).

It provides:

-   **Python-driven test suites:** For validating Python implementations against canonical Go harnesses and other language implementations.
-   **Go test harnesses:** Reference implementations for CTY, tfwire, and example RPC services.
-   **A powerful Command-Line Interface (CLI):** For development, testing, data conversion, and interaction with test services.

## ✨ Key Features

- 🧪 **Conformance Testing** - Test suite for Terraform and OpenTofu tooling
- 🔄 **Matrix Testing** - CLI workflows for multi-version testing and state inspection
- 🔗 **Cross-Language Compatibility** - Harnesses and fixtures for Python/Go interoperability

## Quick Start

> **Note**: tofusoup is in pre-release (v0.x.x). APIs and features may change before 1.0 release.

1. Install: `uv tool install tofusoup`
2. Read the [Quick Start guide](https://github.com/provide-io/tofusoup/blob/main/docs/getting-started/quick-start.md).
3. Run sample tests from [docs/examples/README.md](https://github.com/provide-io/tofusoup/blob/main/docs/examples/README.md).

## Documentation
- [Documentation index](https://github.com/provide-io/tofusoup/blob/main/docs/index.md)
- [Getting started](https://github.com/provide-io/tofusoup/blob/main/docs/getting-started/quick-start.md)
- [CLI reference](https://github.com/provide-io/tofusoup/blob/main/docs/reference/cli.md)

## Development
--------------

### Quick Start

```bash
# Set up environment
uv sync

# Run common tasks
we run test       # Run tests
we run lint       # Check code
we run format     # Format code
we tasks          # See all available commands
```

### Available Commands

This project uses `wrknv` for task automation. Run `we tasks` to see all available commands.

**Common tasks:**
- `we run test` - Run all tests
- `we run test.coverage` - Run tests with coverage
- `we run test.parallel` - Run tests in parallel
- `we run lint` - Check code quality
- `we run lint.fix` - Auto-fix linting issues
- `we run format` - Format code
- `we typecheck` - Run type checker

See [CLAUDE.md](https://github.com/provide-io/tofusoup/blob/main/CLAUDE.md) for detailed development instructions and architecture information.

## Contributing
------------

Contributions are welcome! Please look for a `CONTRIBUTING.md` file (or create one if it doesn't exist) for guidelines. Key areas for contribution:

-   Implementing the placeholder commands and test logic in the new CLI structure.
-   Adding more test cases for CTY, HCL, RPC, and Wire.
-   Developing or improving Rust and JavaScript test harnesses and drivers.
-   Enhancing the CLI with new features or improved usability.
-   Improving documentation and adding examples.

## License
See [LICENSE](https://github.com/provide-io/tofusoup/blob/main/LICENSE) for license details.

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
    git clone https://github.com/provide-io/tofusoup.git
    cd tofusoup
    ```

2.  **Environment Setup:** This project uses `uv` for Python environment and package management.
    ```bash
    # Ensure uv is installed (see https://github.com/astral-sh/uv)
    # e.g., curl -LsSf https://astral.sh/uv/install.sh | sh

    # Set up development environment
    uv sync
    ```

3.  **Verify Installation:**
    ```bash
    uv --version
    python3 --version
    soup --version
    ```

**Note on Go Harnesses:** The Go test harness `soup-go` is a unified polyglot CLI that provides CTY, HCL, Wire Protocol, and RPC functionality. It uses `cobra` for its CLI structure and `go-hclog` for logging, providing a consistent interface and configurable logging (via a `--log-level` flag) across all subcommands.

**Note on Build Artifacts:** Built harness binaries are placed in `harnesses/bin/` (created during first build). This directory is not included in version control. Run `soup harness build --all` to generate these binaries.

**Note on Test Artifacts:** Output from CLI verification tests (stdout, stderr of harness executions) is saved to `soup/output/cli_verification/<harness_name>/<test_id>/` for inspection. Other build or test artifacts may also be placed under `soup/output/`.

## `soup` Command-Line Interface (CLI)
---------------------------------------

The `soup` CLI is your primary interface for interacting with the suite. It's organized into subcommands based on the component you're working with. All commands provide enhanced terminal output using the `rich` library.

**General Options (available for `soup` and all subcommands):**
-   `--help`: Show help for the current command or subcommand.
-   `--verbose`: Enable verbose output (shortcut for --log-level DEBUG).
-   `--log-level <LEVEL>`: Set the logging level (e.g., DEBUG, INFO). Overrides `TOFUSOUP_LOG_LEVEL` env var and `soup.toml` settings. See `docs/CONFIGURATION.md`.
-   `--config-file <PATH>`: Path to the TofuSoup configuration file (TOML format, default: `soup.toml`). Searched in order: explicit path, `./soup.toml`. See `docs/CONFIGURATION.md`.
-   `--version` (only for top-level `soup`): Show TofuSoup version.

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

-   **`soup cty benchmark [--iterations N] [--testcase <name>] [--data-file <path>] [--output-dir <path>]`**
    -   Runs CTY encoding/decoding benchmarks. Options can be defaulted in `soup.toml`.
    -   Requires `soup-go` harness. See `docs/reference/configuration.md`.

-   **`soup cty validate-value <value_json_string> --type-string <cty_type_string> [--harness-path <path>]`**
    -   Validates a CTY value (JSON string) against a CTY type string using the `soup-go` harness.
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
    -   Default output format can be configured in `soup.toml`. See `docs/reference/configuration.md`.

* * * * *

### 🔌 `soup rpc` - RPC Utilities & Tests

Commands for interacting with and testing RPC components, exemplified by a Key-Value store. Uses `pyvider-rpcplugin` for Python client logic.

-   **`soup rpc kv server-start [--py | --go-server-bin <path>] [<go_server_options>]`**
    -   Starts an RPC Key-Value store server.
    -   `--py`: Starts the Python server.
    -   `--go-server-bin <path>`: Path to Go server binary (default: built `soup-go` harness).
    -   Go server options (e.g., `--cert-algo`, `--no-mtls`) can be defaulted in `soup.toml`. See `docs/reference/configuration.md`.

-   **`soup rpc kv get <key> [--server-bin <path>]`**
    -   Gets a value from an RPC KV server using the Python client.
    -   `--server-bin`: Path to server (e.g., `harnesses/bin/soup-go`). Default from `PLUGIN_SERVER_PATH` env var or `soup.toml`. See `docs/reference/configuration.md`.
    -   Example: `soup rpc kv get mykey --server-bin harnesses/bin/soup-go`

-   **`soup rpc kv put <key> <value> [--server-bin <path>]`**
    -   Puts a key-value pair into an RPC KV server using the Python client.
    -   `--server-bin`: Path to server. Default from `PLUGIN_SERVER_PATH` env var or `soup.toml`.
    -   Example: `soup rpc kv put mykey "hello" --server-bin harnesses/bin/soup-go`

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

* * * * *

### 🛠️ `soup harness` - Manage Test Harnesses

Commands to list, build/setup, verify, and clean test harnesses (e.g., Go executables). Compiled binaries are typically placed in `harnesses/bin/`. See `docs/reference/configuration.md`.

-   **`soup harness list`**
    -   Lists available harnesses and their build/setup status.

-   **`soup harness build [<harness_names...>] [--language <lang>] [--all] [--force-rebuild|--force-setup]`**
    -   Builds/sets up harnesses. If no specific targets are given, uses `default_targets` from `soup.toml` for this command, or all known harnesses.
    -   Examples:
        -   `soup harness build soup-go`
        -   `soup harness build --language go --force-rebuild`

-   **`soup harness verify-cli [<harness_names...>] [--language <lang>] [--all]`**
    -   Verifies basic CLI functionality of primarily Go harnesses via pytest suites under `conformance/cli_verification/`. Default targets from `soup.toml` or all applicable.

-   **`soup harness clean [<harness_names...>] [--language <lang>] [--all]`**
    -   Removes built harness artifacts. Default targets from `soup.toml` or all.

* * * * *

### ✅ `soup test` - Run Conformance Tests

Runs Pytest-based conformance test suites located in `conformance/`. Test behavior (env vars, skips, args) can be configured in `soup.toml`. See `docs/reference/configuration.md`.

-   **`soup test <suite_name> [pytest_args...]`**
    -   Runs a specific test suite (e.g., `cty`, `rpc`, `wire`, `cli-cty`, `cli-hcl`, `cli-wire`).
    -   Any additional arguments are passed directly to `pytest`.
    -   Example: `soup test cty -k "some_test_name" -m "not slow"`

-   **`soup test all`**
    -   Runs all defined test suites.

* * * * *

## Project Structure Highlights
----------------------------

-   **Project Root**
    -   **`pyproject.toml`**: Defines the `tofusoup` Python package and dependencies.
    -   **`src/tofusoup/`**: The main Python source code for the `tofusoup` CLI and its submodules.
        -   `cli.py`: Main CLI entry point.
        -   `common/`: Shared utilities (exceptions, config, Rich helpers, etc.).
        -   `cty/`, `hcl/`, `rpc/`, `wire/`: Component-specific logic and CLI subcommands.
        -   `protos/`: Source `.proto` files are now co-located with their respective harness sources. Generated Python stubs are placed within `src/tofusoup/protos/` by build scripts.
        -   `harness/`: Logic and CLI for building/managing external test harnesses.
        -   `testing/`: Logic and CLI for running test suites.
    -   **`src/tofusoup/harness/go/`**: Source code for the unified `soup-go` test harness.
        -   `soup-go/`: Unified polyglot harness providing CTY, HCL, Wire, and RPC functionality.
    -   **`harnesses/bin/`**: Built harness binaries (e.g., `soup-go`).
    -   **`conformance/`**: Pytest test suites for cross-language conformance.
        -   `cty/`, `hcl/`, `rpc/`, `wire/`: Component-specific conformance tests.
        -   `cli_verification/`: Tests for harness CLIs.
        -   `utils/`: Shared utilities for conformance tests.
    -   **`soup.toml`**: Configuration file for TofuSoup (in project root or current directory). See `docs/reference/configuration.md` for detailed documentation.
    -   **`soup/`**: Runtime data, output artifacts (optional, created as needed).
        -   `output/`: Default directory for test artifacts, logs.
    -   **`docs/`**: Documentation files.
        -   `reference/configuration.md`: Complete documentation for the `soup.toml` configuration file.
        -   `architecture/`: Architecture and design documents.
        -   `guides/`: Step-by-step usage guides.
    -   **`tests/`**: General Python unit/integration tests for TofuSoup's own CLI and core Python functionalities (distinct from cross-language conformance tests).

Copyright (c) provide.io LLC.

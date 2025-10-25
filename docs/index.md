# TofuSoup Documentation

Welcome to TofuSoup - A comprehensive toolkit and conformance testing suite for the OpenTofu/Terraform ecosystem.

## What is TofuSoup?

TofuSoup provides CLI tools and testing frameworks for working with Terraform-related technologies:

- **CTY Operations**: Work with Terraform's Configuration Type System
- **HCL Processing**: Parse and convert HashiCorp Configuration Language
- **Wire Protocol**: Encode/decode Terraform wire protocol messages
- **RPC Testing**: Cross-language RPC compatibility testing (Python ↔ Go)
- **Registry Access**: Query and search Terraform/OpenTofu registries
- **Matrix Testing**: Test providers across multiple Terraform/OpenTofu versions
- **Provider Tools**: Development utilities for provider authors

## Installation

Install from PyPI:

```console
$ pip install tofusoup
```

Or for development:

```console
$ git clone https://github.com/provide-io/tofusoup.git
$ cd tofusoup
$ uv sync
```

Verify installation:

```console
$ soup --version
tofusoup, version 0.1.0
```

## Quick Start

### Working with CTY Values

View and convert CTY data between formats:

```console
$ soup cty view data.json
# Displays CTY structure as a tree

$ soup cty convert input.json output.msgpack
# Convert between JSON, MessagePack, and HCL formats
```

### Working with HCL

Parse and convert HCL files:

```console
$ soup hcl view main.tf
# Parse and display HCL structure

$ soup hcl convert config.hcl config.json
# Convert HCL to JSON or MessagePack
```

### Working with Wire Protocol

Encode and decode Terraform wire protocol messages:

```console
$ soup wire encode value.json value.tfw.b64
# Encode JSON to wire format

$ soup wire decode value.tfw.b64 value.json
# Decode wire format back to JSON
```

### RPC Testing

Test cross-language RPC compatibility:

```console
$ soup rpc kv put mykey "hello world"
# Store a value via RPC

$ soup rpc kv get mykey
# Retrieve a value via RPC
```

### Running Conformance Tests

Run cross-language compatibility tests:

```console
$ soup test all
# Run all conformance test suites

$ soup test cty
# Run only CTY conformance tests

$ soup test rpc -v
# Run RPC tests with verbose output
```

### Matrix Testing with Stir

Test providers across multiple Terraform/OpenTofu versions:

```console
$ soup stir tests/stir_cases
# Run integration tests

$ soup stir tests/stir_cases --matrix
# Run tests across all configured tool versions
```

### Registry Operations

Query Terraform and OpenTofu registries:

```console
$ soup registry search provider aws
# Search for AWS provider

$ soup registry info hashicorp/aws
# Get detailed provider information

$ soup sui
# Launch interactive TUI browser
```

### Managing Test Harnesses

Build and manage Go test harnesses:

```console
$ soup harness list
# List available harnesses

$ soup harness build --all
# Build all Go harnesses

$ soup harness verify-cli go-cty
# Verify harness CLI functionality
```

## Documentation Structure

- **[Architecture](architecture/01-overview.md)**: System design and architecture
- **[Guides](guides/01-running-conformance-tests.md)**: Step-by-step tutorials
- **[Configuration](CONFIGURATION.md)**: soup.toml configuration reference
- **[Testing](testing/conformance-test-status.md)**: Testing documentation

## Core Capabilities

### CTY (Configuration Type System)

Tools for working with Terraform's type system:

- View CTY structures with rich tree visualization
- Convert between JSON, MessagePack, and HCL formats
- Validate values against CTY type specifications
- Benchmark encoding/decoding performance

**See:** `soup cty --help`

### HCL (HashiCorp Configuration Language)

Tools for HCL file processing:

- Parse HCL files and display structure
- Convert HCL to JSON or MessagePack
- Work with CTY representations of HCL

**See:** `soup hcl --help`

### Wire Protocol

Terraform wire protocol utilities:

- Encode JSON to wire format (MessagePack + Base64)
- Decode wire format back to JSON
- Cross-language wire protocol compatibility testing

**See:** `soup wire --help`

### RPC and Plugin System

Cross-language RPC testing infrastructure:

- Python and Go RPC server implementations
- mTLS and certificate management
- Cross-language compatibility testing (Python ↔ Go)
- go-plugin compatible plugin server

**See:** `soup rpc --help`

### Conformance Testing

Pytest-based conformance test suites:

- CTY cross-language compatibility
- HCL parsing consistency
- Wire protocol encoding/decoding
- RPC communication validation

**See:** `soup test --help` and [Running Conformance Tests](guides/01-running-conformance-tests.md)

### Matrix Testing (Stir)

Test providers across multiple tool versions:

- Parallel test execution
- Support for Terraform and OpenTofu
- Version matrix configuration
- Automated test reporting

**See:** `soup stir --help` and [Matrix Testing Guide](guides/05-matrix-testing-with-stir.md)

### Registry Operations

Query and browse Terraform/OpenTofu registries:

- Provider and module search
- Version information
- Documentation access
- Interactive TUI browser (sui command)

**See:** `soup registry --help` and `soup sui --help`

## Configuration

TofuSoup uses `soup.toml` for configuration:

```toml
[global_settings]
default_python_log_level = "INFO"

[harness_defaults.go]
build_flags = ["-v"]
timeout_seconds = 300

[test_suite.rpc]
env_vars = { KV_STORAGE_DIR = "/tmp" }

[workenv.matrix]
parallel_jobs = 4
timeout_minutes = 30
```

**See:** [Configuration Documentation](CONFIGURATION.md)

## Development

For development setup and contribution guidelines:

```console
$ git clone https://github.com/provide-io/tofusoup.git
$ cd tofusoup
$ uv sync
$ uv run pytest
```

**See:** [CONTRIBUTING.md](../CONTRIBUTING.md) and [CLAUDE.md](../CLAUDE.md)
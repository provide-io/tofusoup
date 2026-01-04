# TofuSoup Documentation

!!! warning "Pre-release"
    This documentation covers a pre-release. APIs and features may change, and some documented or roadmap items are exploratory and may change or be removed.


Welcome to TofuSoup - A comprehensive toolkit and conformance testing suite for the OpenTofu/Terraform ecosystem.

## What is TofuSoup?

TofuSoup provides CLI tools and testing frameworks for working with Terraform-related technologies:

- **CTY Operations**: Work with Terraform's Configuration Type System
- **HCL Processing**: Parse and convert HashiCorp Configuration Language
- **Wire Protocol**: Encode/decode Terraform wire protocol messages
- **RPC Testing**: Cross-language RPC compatibility testing (Python ↔ Go)
- **Registry Access**: Query and search Terraform/OpenTofu registries
- **Matrix Testing**: Test providers across multiple Terraform/OpenTofu versions

## Installation

Install from PyPI:

```console
$ uv tool install tofusoup
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

```console
# View CTY data
$ soup cty view data.json

# Parse HCL files
$ soup hcl view main.tf

# Test RPC functionality
$ soup rpc kv put mykey "value"
$ soup rpc kv get mykey

# Run conformance tests
$ soup test all

# Search registries
$ soup registry search provider aws

# Build test harnesses
$ soup harness build --all
```

For complete CLI documentation, see the [CLI Reference](reference/cli/).

## Part of the provide.io Ecosystem

This project is part of a larger ecosystem of tools for Python and Terraform development.

**[View Ecosystem Overview →](https://foundry.provide.io/provide-foundation/ecosystem/)**

Understand how provide-foundation, pyvider, flavorpack, and other projects work together.

## Documentation

- **[Architecture](architecture/01-overview/)**: System design and architecture
- **[Guides](guides/testing/01-running-conformance-tests/)**: Step-by-step tutorials
- **[CLI Reference](reference/cli/)**: Complete command reference
- **[Configuration](reference/configuration/)**: soup.toml configuration reference
- **[Testing](testing/conformance-test-status/)**: Testing documentation

## Core Capabilities

### CTY (Configuration Type System)
Work with Terraform's type system: view structures, convert formats, validate values.

**Commands**: `soup cty view`, `soup cty convert`, `soup cty benchmark`

### HCL (HashiCorp Configuration Language)
Parse and process HCL files: display structure, convert to JSON/MessagePack.

**Commands**: `soup hcl view`, `soup hcl convert`

### Wire Protocol
Terraform wire protocol utilities: encode/decode MessagePack and Base64.

**Commands**: `soup wire encode`, `soup wire decode`

### RPC and Plugin System
Cross-language RPC testing with Python and Go implementations, mTLS support.

**Commands**: `soup rpc kv server`, `soup rpc kv client`, `soup rpc kv test`

### Conformance Testing
Pytest-based test suites for CTY, HCL, wire protocol, and RPC compatibility.

**Commands**: `soup test all`, `soup test cty`, `soup test hcl`, `soup test wire`, `soup test rpc`

### Matrix Testing (Stir)
Test providers across multiple Terraform/OpenTofu versions with parallel execution.

**Commands**: `soup stir <path>`, `soup stir <path> --matrix`

**Note**: Requires optional `wrknv` package: `uv pip install -e /path/to/wrknv`

### Registry Operations
Query and browse Terraform/OpenTofu registries with CLI or interactive TUI.

**Commands**: `soup registry search`, `soup registry info`, `soup sui`

### Test Harnesses
Build and manage Go test harnesses for cross-language compatibility testing.

**Commands**: `soup harness list`, `soup harness build`, `soup harness verify-cli`

## Configuration

TofuSoup uses `soup.toml` for configuration. Example:

```toml
[global_settings]
default_python_log_level = "INFO"

[harness_defaults.go]
build_flags = ["-v"]

[test_suite.rpc]
env_vars = { KV_STORAGE_DIR = "/tmp" }
```

See the [Configuration Reference](reference/configuration/) for complete details.

---

**Ready to get started?** Check out the [Architecture Overview](architecture/01-overview/) or dive into the [CLI Reference](reference/cli/).

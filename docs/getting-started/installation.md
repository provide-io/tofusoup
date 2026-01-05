# Installation

Get started with TofuSoup, a cross-language conformance testing suite and tooling framework for OpenTofu/Terraform ecosystems.

## Prerequisites

--8<-- ".provide/foundry/docs/_partials/python-requirements.md"

--8<-- ".provide/foundry/docs/_partials/go-requirements.md"

!!! info "Go Required for Test Harnesses"
    Go 1.24+ is required to build test harnesses for cross-language compatibility testing. If you only need the Python CLI tools without harness building, Go is optional.

--8<-- ".provide/foundry/docs/_partials/uv-installation.md"

--8<-- ".provide/foundry/docs/_partials/python-version-setup.md"

## Installation Methods

### As a Command-Line Tool

If you want to use the `soup` CLI for CTY, HCL, wire protocol, and RPC operations:

**Using uv (Recommended):**
```bash
# Install tofusoup globally with uv
uvx soup --help

# Or install in a dedicated virtual environment
uv tool install tofusoup

# With all optional dependencies
uv tool install "tofusoup[all]"
```

### As a Library Dependency

If you're integrating TofuSoup into your project:

**Using uv:**
```bash
uv add tofusoup

# Or with specific extras
uv add "tofusoup[cty,hcl,rpc]"
```

**In your `pyproject.toml`:**
```toml
[project]
dependencies = [
    "tofusoup[all]>=0.1.0",
]
```

### For Development

Clone the repository and set up the development environment:

```bash
# Clone the repository
git clone https://github.com/provide-io/tofusoup.git
cd tofusoup

# Set up development environment
uv sync

# Or install with all development dependencies
uv sync --all-groups

# Verify installation
soup --version
```

This creates a `.venv/` virtual environment with all dependencies installed.

--8<-- ".provide/foundry/docs/_partials/virtual-env-setup.md"

--8<-- ".provide/foundry/docs/_partials/platform-specific-macos.md"

## Optional Dependencies

TofuSoup has several optional dependency groups for specific features:

### CTY Support

```bash
uv tool install tofusoup[cty]
```

**Includes:**
- `pyvider-cty` - Python implementation of go-cty type system
- CTY value operations and conversions
- Type-safe value creation and manipulation

**CLI Commands:**
```bash
soup cty view data.json
soup cty convert input.json output.msgpack
```

### HCL Support

```bash
uv tool install tofusoup[hcl]
```

**Includes:**
- `pyvider-hcl` - Python HCL parser
- HCL to JSON/CTY conversion
- Configuration parsing

**CLI Commands:**
```bash
soup hcl parse config.hcl
soup hcl to-json config.hcl output.json
```

### RPC Support

```bash
uv tool install tofusoup[rpc]
```

**Includes:**
- `pyvider-rpcplugin` - RPC plugin infrastructure
- gRPC server and client implementations
- Plugin protocol support

**CLI Commands:**
```bash
soup rpc kv server-start
soup rpc kv put key value
soup rpc kv get key
```

### Browser/TUI Support

The interactive Terminal UI (sui command) requires additional dependencies:

```bash
uv tool install tofusoup[browser]
```

**Features:**
- Interactive registry browser
- Provider and module exploration
- Rich terminal interface

**CLI Commands:**
```bash
sui  # Launch interactive browser
```

### Matrix Testing

Matrix testing across multiple Terraform/OpenTofu versions requires `wrknv`:

```bash
# Install from local source
uv add --editable /path/to/wrknv
```

**Features:**
- Multi-version testing
- Parallel test execution
- Version management integration

### All Features

Install all optional dependencies at once:

```bash
uv tool install tofusoup[all]
```

Includes: cty, hcl, rpc, and browser support.

**Note**: Matrix testing (`wrknv`) requires separate installation.

## Building Test Harnesses

TofuSoup uses Go test harnesses for cross-language compatibility testing:

### Unified Go Harness (soup-go)

The recommended harness for all cross-language testing:

```bash
# List available harnesses
soup harness list

# Build soup-go harness
soup harness build soup-go

# Verify harness CLI
soup harness verify-cli soup-go
```

**Build Artifacts:**
- Harness binaries: `harnesses/bin/`
- Not included in version control
- Must be built locally

### Using Harnesses

Once built, harnesses can be used directly:

```bash
# Run harness commands
./harnesses/bin/soup-go cty view data.json
./harnesses/bin/soup-go wire encode value.json output.tfw.b64
./harnesses/bin/soup-go hcl parse config.hcl
```

**Harness Features:**
- Reference implementations in Go
- Cross-language compatibility testing
- MessagePack and wire protocol support
- CTY and HCL operations

### Build Requirements

Harness building requires:

```bash
# Verify Go installation
go version  # Should show 1.21+

# Check GOPATH
go env GOPATH

# Build all harnesses
soup harness build --all

# Clean harness artifacts
soup harness clean
```

## Verifying Installation

### Basic Verification

**1. Check Python and Package:**
```bash
# Check Python version
python --version  # Should show 3.11+

# Verify package installation
python -c "import tofusoup; print('✅ TofuSoup installed')"

# Check version
soup --version
```

**2. Verify CLI Commands:**
```bash
# Display main help
soup --help

# List available commands
soup cty --help
soup hcl --help
soup wire --help
soup rpc --help
```

**3. Test Core Functionality:**
```bash
# Test CTY operations (if cty extra installed)
echo '{"type":"string","value":"hello"}' > test.json
soup cty view test.json
rm test.json

# Test harness operations (if Go harness built)
soup harness list
```

### TofuSoup-Specific Verification

**1. Test Ecosystem Imports:**
```python
# Verify pyvider ecosystem integration
from pyvider.cty import CtyString, CtyNumber
from pyvider.hcl import parse_hcl
from pyvider.rpcplugin import plugin_server

# Test TofuSoup modules
from tofusoup.cty import logic as cty_logic
from tofusoup.hcl import operations as hcl_ops
from tofusoup.rpc import services
from tofusoup.testing import runner

print("✅ All imports successful")
```

**2. Run Conformance Tests:**
```bash
# Run CTY conformance tests
soup test cty

# Run HCL conformance tests
soup test hcl

# Run wire protocol tests
soup test wire

# Run RPC cross-language tests
soup test rpc
```

**3. Test Harness Integration:**
```bash
# Verify harness is functional
soup harness verify-cli soup-go

# Run harness-based tests
uv run pytest conformance/cty/ -v
```

## Development Workflow

--8<-- ".provide/foundry/docs/_partials/testing-setup.md"

**Additional Testing Options:**

```bash
# Run conformance tests
uv run pytest conformance/

# Run with specific markers
uv run pytest -m cty
uv run pytest -m hcl
uv run pytest -m wire

# Run tests in parallel
uv run pytest -n auto

# Run specific test suite via CLI
soup test cty
soup test rpc
```

--8<-- ".provide/foundry/docs/_partials/code-quality-setup.md"

### Pre-commit Hooks

```bash
# Install pre-commit hooks
pre-commit install

# Run all hooks manually
pre-commit run --all-files
```

### Building the Package

```bash
# Build distribution packages
uv build

# The wheel will be in dist/
ls dist/
```

## Configuration

TofuSoup can be configured via `soup.toml` in your project directory:

```toml
[global_settings]
default_python_log_level = "INFO"

[harness_defaults.go]
build_flags = ["-v"]
timeout_seconds = 300

[test_suites.cty]
test_dir = "conformance/cty"
markers = ["cty"]

[test_suites.rpc]
test_dir = "conformance/rpc"
markers = ["rpc", "cross_language"]
```

See [Configuration Reference](../reference/configuration.md) for complete details.

## Troubleshooting

--8<-- ".provide/foundry/docs/_partials/troubleshooting-common.md"

### TofuSoup-Specific Issues

#### Command not found: soup

Ensure the package is installed and your PATH includes Python's bin directory:

```bash
# Check installation
uv pip list | grep tofusoup

# Find soup executable
which soup

# Add to PATH if needed
export PATH="$HOME/.local/bin:$PATH"

# For virtual environment
source .venv/bin/activate
```

#### Go harness build failures

Verify Go installation and configuration:

```bash
# Check Go installation
go version

# Check GOPATH
go env GOPATH

# Verify Go module support
go env GO111MODULE  # Should show 'on' or ''

# Clean and rebuild
soup harness clean
soup harness build soup-go
```

#### Module import errors for pyvider packages

Install required optional dependencies:

```bash
# Install all extras
uv tool install tofusoup[all]

# Or specific extras
uv tool install tofusoup[cty,hcl,rpc]

# Verify pyvider packages
uv pip list | grep pyvider
```

#### Conformance test failures

Ensure harnesses are built and functional:

```bash
# Build harness
soup harness build soup-go

# Verify harness CLI
soup harness verify-cli soup-go

# Run with verbose output
uv run pytest conformance/ -vv

# Check for missing test fixtures
ls conformance/fixtures/
```

#### RPC plugin connection timeouts

Check certificate generation and mTLS setup:

```bash
# Verify RPC components
python -c "from pyvider.rpcplugin import plugin_server; print('✅ RPC available')"

# Test basic RPC server
soup rpc kv server-start

# Check logs for certificate errors
export FOUNDATION_LOG_LEVEL=DEBUG
soup rpc kv server-start
```

### Getting Help

If you encounter issues:

1. **Check logs** - Run with `FOUNDATION_LOG_LEVEL=DEBUG` for detailed output
2. **Verify Python version** - Ensure you're using Python 3.11+
3. **Check optional dependencies** - Install required extras for your use case
4. **Verify harnesses** - Ensure Go harnesses build successfully
5. **Review configuration** - Check `soup.toml` syntax
6. **Report issues** - [GitHub Issues](https://github.com/provide-io/tofusoup/issues)

## Next Steps

### Quick Start

1. **[Quick Start Guide](quick-start.md)** - Run your first TofuSoup commands
2. **[What is TofuSoup?](what-is-tofusoup.md)** - Learn about capabilities and use cases
3. **[Configuration Reference](../reference/configuration.md)** - Complete configuration guide

### Core Features

- **[CTY Operations](../guides/cli-usage/03-using-cty-and-hcl-tools.md)** - Working with Terraform's type system
- **[Wire Protocol](../guides/cli-usage/wire-protocol.md)** - Encoding and decoding wire protocol messages
- **[Matrix Testing](../guides/cli-usage/matrix-testing.md)** - Testing across Terraform/OpenTofu versions
- **[RPC Testing](../guides/testing/01-running-conformance-tests.md)** - Cross-language RPC compatibility

### Advanced Topics

- **[Harness Development](../guides/testing/test-harness-development.md)** - Creating custom test harnesses
- **[Conformance Testing](../core-concepts/conformance-testing.md)** - Testing strategy and patterns
- **[Architecture](../architecture/01-overview.md)** - System architecture and design

Ready to start testing? Check out the [Quick Start Guide](quick-start.md)!

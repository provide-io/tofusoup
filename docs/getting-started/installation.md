# Installation

This guide covers installing TofuSoup and its dependencies.

## Requirements

- **Python**: 3.11 or higher
- **Go**: 1.21+ (for building test harnesses)
- **uv**: Package manager (recommended) or pip

## Install via PyPI

```bash
pip install tofusoup
```

For all optional dependencies:

```bash
pip install tofusoup[all]
```

## Install for Development

Clone the repository and set up the development environment:

```bash
# Clone repository
git clone https://github.com/provide-io/tofusoup.git
cd tofusoup

# Set up development environment with uv
uv sync

# Verify installation
soup --version
```

## Optional Dependencies

TofuSoup has several optional dependency groups:

### CTY Support
```bash
pip install tofusoup[cty]
```
Includes: `pyvider-cty` for Python CTY operations

### HCL Support
```bash
pip install tofusoup[hcl]
```
Includes: `pyvider-hcl` for HCL parsing

### RPC Support
```bash
pip install tofusoup[rpc]
```
Includes: `pyvider-rpcplugin` for RPC plugin infrastructure

### Matrix Testing

Matrix testing requires the `wrknv` package (not yet on PyPI):

```bash
# Install from local source
pip install -e /path/to/wrknv
```

### All Features
```bash
pip install tofusoup[all]
```
Includes all optional dependencies (cty, hcl, rpc)

**Note**: Matrix testing requires separate `wrknv` installation

## Build Test Harnesses

TofuSoup uses Go test harnesses for cross-language compatibility testing:

```bash
# List available harnesses
soup harness list

# Build all harnesses
soup harness build --all

# Build specific harness
soup harness build soup-go
```

**Note**: Requires Go 1.21+ to be installed and available in your PATH.

**Build Artifacts**: Harness binaries are created in `harnesses/bin/` during the build process. This directory is not included in version control and must be created by building the harnesses locally.

## Verify Installation

Test that everything is working:

```bash
# Check CLI
soup --version

# List available commands
soup --help

# Run a simple test
soup test cty
```

## Configuration

TofuSoup can be configured via `soup.toml` in your project directory:

```toml
[global_settings]
default_python_log_level = "INFO"

[harness_defaults.go]
build_flags = ["-v"]
timeout_seconds = 300
```

See [Configuration Reference](../reference/configuration.md) for details.

## Troubleshooting

### Command not found: soup

Ensure the package is installed and your PATH includes Python's bin directory:

```bash
# Check installation
pip list | grep tofusoup

# Find soup executable
which soup

# Add to PATH if needed (example for macOS/Linux)
export PATH="$HOME/.local/bin:$PATH"
```

### Go harness build failures

Ensure Go is installed and configured:

```bash
# Check Go installation
go version

# Check GOPATH
go env GOPATH
```

### Module import errors

Run `uv sync` to ensure all dependencies are installed:

```bash
cd /path/to/tofusoup
uv sync
```

## Next Steps

- **[Quick Start](quick-start.md)**: Run your first commands
- **[What is TofuSoup?](what-is-tofusoup.md)**: Learn about TofuSoup's capabilities
- **[Configuration](../reference/configuration.md)**: Configure TofuSoup for your project

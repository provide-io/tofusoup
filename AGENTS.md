# AGENTS.md

This file provides guidance for AI assistants when working with code in this repository.

## Project Overview

`tofusoup` is a cross-language conformance testing suite and tooling framework for OpenTofu/Terraform ecosystems. It provides CLI tools and testing frameworks for:

- **CTY (Configuration Type System)** - Working with Terraform's type system
- **HCL (HashiCorp Configuration Language)** - Parsing and converting HCL
- **Wire Protocol** - Terraform wire protocol encoding/decoding
- **RPC/gRPC** - Cross-language RPC testing and plugin systems
- **Registry Operations** - Querying Terraform/OpenTofu registries
- **Matrix Testing (Stir)** - Testing providers across multiple Terraform/Tofu versions
- **Provider Development** - Tools for provider project management

The project focuses on ensuring compatibility between Go, Python, and other language implementations of Terraform-adjacent technologies.

## Development Environment Setup

**IMPORTANT**: Use `uv sync` to set up the development environment. This creates a virtual environment at `.venv/`.

> **Note on "workenv"**: The project uses `.venv/` for the Python virtual environment. The `[workenv]` sections in `soup.toml` configure the `wrknv` tool for matrix testing across Terraform/OpenTofu versions - this is unrelated to the virtual environment directory.

```bash
# Install uv if needed: https://github.com/astral-sh/uv
uv sync
```

## Task Runner

This project uses `wrknv` for task automation. Commands are defined in `wrknv.toml`.

### Quick Reference
```bash
we tasks             # List all available tasks
we run test          # Run tests
we run lint          # Check code quality
we run format        # Format code
we run typecheck     # Type checking
we run build         # Build package
```

All tasks can be run with `we run <task>`. Nested tasks use dotted names (e.g., `we run test.coverage`).

### Task Discovery

Run `we tasks` to see the complete task tree for this project. Common task hierarchies:

```bash
we run test                # Run all tests
we run test.unit           # Run only unit tests (if configured)
we run test.coverage       # Run tests with coverage
we run test.parallel       # Run tests in parallel
```

## Common Development Commands

```bash
# Environment setup
uv sync                                 # Set up development environment

# Primary workflow (using we)
we run test                             # Run all tests
we run test.coverage                    # Run with coverage report
we run test.parallel                    # Run tests in parallel
we run lint                             # Check code quality
we run lint.fix                         # Auto-fix linting issues
we run format                           # Format code
we run format.check                     # Check formatting without changes
we run typecheck                        # Run type checker
we run build                            # Build distribution

# Alternative (direct uv commands)
uv run pytest                           # Direct test execution
uv run pytest conformance/              # Run conformance tests
uv run pytest tests/                    # Run unit tests
uv run pytest -n auto                   # Run tests in parallel
uv run pytest -k "test_name"            # Run tests matching pattern
uv run ruff check .                     # Direct linting
uv run ruff format .                    # Direct formatting
uv run mypy src/                        # Direct type checking

# CLI operations (command is 'soup', not 'tofusoup')
soup --help                            # Main CLI help
soup cty --help                        # CTY utilities
soup hcl --help                        # HCL utilities
soup wire --help                       # Wire protocol utilities
soup rpc --help                        # RPC utilities
soup test --help                       # Conformance testing
soup stir --help                       # Matrix testing
soup registry --help                   # Registry operations
soup harness --help                    # Test harness management

# Harness operations
soup harness list                      # List available harnesses
soup harness build soup-go             # Build unified Go harness
soup harness verify-cli soup-go        # Verify harness functionality

# Build and distribution
uv build                               # Build package
uv publish                             # Publish to PyPI
```

For complete task documentation, see [wrknv.toml](wrknv.toml) or run `we tasks`.

## Architecture & Code Structure

### Core Components

The codebase is organized into functional modules under `src/tofusoup/`:

1. **`cty/`** - CTY value operations
   - CLI commands for viewing, converting CTY data
   - Integration with `pyvider-cty` for Python implementation
   - Cross-language compatibility testing against Go harnesses

2. **`hcl/`** - HCL operations
   - HCL parsing and conversion
   - Integration with `pyvider-hcl`
   - CTY representation of HCL structures

3. **`wire/`** - Terraform wire protocol
   - Encoding/decoding wire protocol messages
   - MessagePack and Base64 handling
   - Integration with `pyvider.wire` library

4. **`rpc/`** - RPC and plugin system
   - gRPC service implementations (KV store example)
   - Plugin server capabilities (go-plugin compatible)
   - Cross-language RPC testing (Python ↔ Go)
   - Certificate and mTLS management

5. **`harness/`** - Test harness management
   - Building and managing Go test harnesses
   - CLI for harness lifecycle (build, verify, clean)
   - Proto definitions and generated code

6. **`testing/`** - Conformance test execution
   - Unified CLI for running pytest-based conformance suites
   - Test discovery and execution orchestration
   - Configuration via `soup.toml`

7. **`stir/`** - Matrix testing framework
   - Multi-version Terraform/OpenTofu testing
   - Parallel test execution across tool versions
   - Integration with workenv for version management

8. **`registry/`** - Registry operations
   - Querying Terraform and OpenTofu registries
   - Provider and module search
   - Caching and API clients

9. **`browser/` (sui)** - Terminal UI
   - Textual-based TUI for browsing registries
   - Interactive provider/module exploration

10. **`provider/`** - Provider development tools
    - Provider project scaffolding
    - Development utilities

11. **`state/`** - State inspection
    - Terraform state file analysis
    - Private state attributes access

12. **`common/`** - Shared utilities
    - Configuration loading (`config.py`)
    - Rich terminal output helpers
    - Exception classes
    - Lazy loading for CLI performance

13. **`scaffolding/`** - Project scaffolding
    - Generate new project structures
    - Template-based code generation

### Key Design Patterns

1. **Lazy Loading CLI**: Uses `LazyGroup` for fast CLI startup - subcommands load only when invoked
2. **Foundation Integration**: Uses `provide-foundation` for structured logging and telemetry
3. **Rich Terminal Output**: Extensive use of `rich` library for beautiful CLI output
4. **Plugin Compatibility**: RPC server can run as go-plugin compatible plugin
5. **Configuration-Driven**: `soup.toml` for configuring harnesses, tests, and commands
6. **Cross-Language Testing**: Conformance tests validate Python ↔ Go compatibility

### Directory Structure

```
tofusoup/
├── src/tofusoup/           # Main source code
│   ├── cli.py              # Main CLI entry point
│   ├── browser/            # TUI (sui command)
│   ├── common/             # Shared utilities
│   ├── config/             # Configuration defaults
│   ├── cty/                # CTY operations
│   ├── hcl/                # HCL operations
│   ├── wire/               # Wire protocol
│   ├── rpc/                # RPC and plugin system
│   ├── harness/            # Harness management + Go source
│   ├── testing/            # Test execution
│   ├── stir/               # Matrix testing
│   ├── registry/           # Registry operations
│   ├── provider/           # Provider tools
│   ├── state/              # State inspection
│   └── scaffolding/        # Project scaffolding
├── conformance/            # Conformance test suites
│   ├── cty/                # CTY conformance tests
│   ├── hcl/                # HCL conformance tests
│   ├── wire/               # Wire protocol tests
│   └── rpc/                # RPC cross-language tests
├── tests/                  # Unit/integration tests
├── docs/                   # Documentation
├── pyproject.toml          # Package configuration
├── soup.toml               # TofuSoup configuration
└── README.md               # User documentation
```

## Testing Strategy

### Core Testing Requirements

**CRITICAL**: `provide-testkit` MUST be available for testing utilities.

- **provide-testkit dependency**: Required in dev dependencies
- **Foundation integration**: Uses `provide-foundation` for structured logging
- **Async testing**: Comprehensive async test support via `pytest-asyncio`
- **HTTP testing**: Mock HTTP services with `pytest-httpx` and `respx`
- **Conformance tests**: Located in `conformance/` directory
- **Unit tests**: Located in `tests/` directory

### Standard Testing Pattern

```python
import pytest
from pathlib import Path

def test_cty_conversion():
    """Test CTY value conversion."""
    from tofusoup.cty.logic import convert_cty_file

    result = convert_cty_file(
        input_path=Path("test.json"),
        output_path=Path("test.msgpack"),
        input_format="json",
        output_format="msgpack"
    )
    assert result is not None
```

### Running Tests

```bash
# Run all tests
uv run pytest

# Run specific test suite via CLI
soup test cty                    # CTY conformance tests
soup test rpc                    # RPC conformance tests
soup test wire                   # Wire protocol tests

# Run with pytest directly
uv run pytest conformance/cty/ -v
uv run pytest tests/ -k test_name
```

### Testing Infrastructure

- Pytest-based with comprehensive markers (see `pyproject.toml`)
- Conformance tests validate cross-language compatibility
- Go harnesses provide reference implementations
- Python implementations tested against Go harnesses
- Matrix testing validates multiple Terraform/Tofu versions

## Common Issues & Solutions

1. **ModuleNotFoundError for dependencies**: Run `uv sync` to ensure proper environment setup
2. **Harness build failures**: Ensure Go is installed and `GOPATH` is configured
3. **Plugin connection timeouts**: Check certificate generation and mTLS configuration
4. **Test execution timeouts**: Increase timeout settings in pytest configuration
5. **Import errors**: Ensure PYTHONPATH includes `src/` (configured in `pyproject.toml`)

## Development Guidelines

- Always use modern Python 3.11+ type hints (e.g., `list[str]` not `List[str]`)
- Use `attrs` for data classes consistently
- Follow async patterns for I/O operations
- Use structured logging via `provide.foundation.logger`
- Only use absolute imports, never relative imports
- Use async in tests where appropriate
- No hardcoded defaults - use configuration constants from `config/defaults.py`

## Integration with Ecosystem

### Pyvider Integration

TofuSoup integrates with the Pyvider ecosystem:

```python
# CTY operations use pyvider-cty
from pyvider.cty import Value, Type

# HCL operations use pyvider-hcl
from pyvider.hcl import parse_hcl

# RPC uses pyvider-rpcplugin
from pyvider.rpcplugin.server import RPCPluginServer
```

### Plating Integration

Documentation generation has been moved to the separate `plating` package. TofuSoup can work with plating bundles but doesn't generate them directly.

### Go Harness Integration

TofuSoup includes a unified Go test harness (`soup-go`) for reference implementations:

```bash
# Build Go harness
soup harness build soup-go

# Verify harness CLI
soup harness verify-cli soup-go

# List available harnesses
soup harness list

# Run harness directly
./harnesses/bin/soup-go cty view data.json
./harnesses/bin/soup-go wire encode value.json output.tfw.b64
```

## Output Guidelines for CLI and Logging

**IMPORTANT**: Use the correct output method for the context:

- **CLI User-Facing Output**: Use `rich` for formatted terminal output
- **Application Logging**: Use `provide.foundation.logger` for structured logging
- **Plugin Mode**: All logging goes to stderr (stdout reserved for plugin handshake)
- **Test Results**: Use pytest's output mechanisms

Example:
```python
from provide.foundation import logger
from rich import print as rich_print

# For logging (debugging, internal state)
logger.info("Processing CTY value", value_type="string")

# For CLI output (user-facing information)
rich_print("[green]✓[/green] Conversion successful")
```

## Third-Party Dependencies

Key integrations:

- **pyvider-cty**: Python CTY implementation
- **pyvider-hcl**: Python HCL parser
- **pyvider-rpcplugin**: RPC plugin infrastructure
- **provide-foundation**: Logging and telemetry
- **provide-testkit**: Testing utilities
- **click**: CLI framework
- **rich**: Terminal formatting
- **textual**: Terminal UI (for sui command)
- **msgpack**: Binary serialization
- **httpx/respx**: HTTP client and mocking

## Configuration Files

- **`soup.toml`**: Main configuration file for TofuSoup
  - Harness build settings
  - Test suite configuration
  - Default command options
  - Workenv/matrix testing settings
- **`pyproject.toml`**: Python package configuration
  - Dependencies
  - Pytest configuration
  - Ruff/mypy settings
- **`conformance/`**: Directory containing conformance test specifications
- **See `docs/CONFIGURATION.md` for complete `soup.toml` documentation**

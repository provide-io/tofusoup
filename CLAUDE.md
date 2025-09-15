# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project Overview

`tofusoup` is a cross-language conformance test suite for OpenTofu/Terraform tooling. It provides automated testing frameworks for verifying compatibility and correctness across different implementations of Terraform-compatible tools, particularly focusing on the Pyvider ecosystem.

## Development Environment Setup

**IMPORTANT**: Use `source env.sh` to set up the development environment. This script provisions a virtual environment in `workenv/` (NOT `.venv`). The environment setup handles:
- Python 3.11+ requirement
- UV package manager for dependency management
- Platform-specific virtual environments (e.g., `workenv/tofusoup_darwin_arm64`)

## Common Development Commands

```bash
# Environment setup (always use this instead of manual venv creation)
source env.sh

# Run tests
pytest                           # Run all tests
pytest conformance/             # Run conformance tests
pytest tests/                   # Run unit tests
pytest -n auto                  # Run tests in parallel
pytest -n auto -vvv             # Verbose parallel test run
pytest -k "test_name"           # Run tests matching pattern

# Code quality checks
ruff check .                    # Run linter
ruff format .                   # Format code
mypy src/                       # Type checking

# CLI operations
soup --help                     # Main CLI help
soup generate                   # Generate test configurations
soup validate                   # Validate configurations
soup test                       # Run test suites
soup report                     # Generate test reports

# Build and distribution
uv build                        # Build package
uv publish                      # Publish to PyPI
```

## Architecture & Code Structure

### Core Components

1. **Test Generation Engine** (`src/tofusoup/generators/`)
   - Configuration generators for different test scenarios
   - Template-based test case creation
   - Cross-language compatibility test generation

2. **Validation Framework** (`src/tofusoup/validators/`)
   - Schema validation for Terraform configurations
   - Semantic validation for provider behaviors
   - Cross-platform compatibility validation

3. **Execution Engine** (`src/tofusoup/executors/`)
   - Test execution orchestration
   - Parallel test runner with result aggregation
   - Integration with external tools (terraform, tofu, etc.)

4. **Reporting System** (`src/tofusoup/reporters/`)
   - Test result aggregation and analysis
   - HTML/JSON/XML report generation
   - Performance benchmarking reports

5. **Configuration Management** (`src/tofusoup/config/`)
   - Test suite configuration loading
   - Environment-specific settings
   - Provider configuration management

### Key Design Patterns

1. **Plugin Architecture**: Extensible system for adding new test types and validators
2. **Template-Driven**: Jinja2-based template system for generating test configurations
3. **Async-First**: Built on asyncio for concurrent test execution
4. **Cross-Language**: Supports testing multiple language implementations
5. **Schema-Driven**: Uses JSON schemas for test configuration validation

### Important Implementation Notes

1. **Integration with Plating**: Uses `plating` for documentation generation and Terraform configuration templating
2. **Pyvider Ecosystem**: Integrates with `pyvider-cty`, `pyvider-hcl`, and `pyvider-rpcplugin` for testing
3. **Conformance Testing**: Provides standardized test suites for Terraform provider compliance
4. **Multi-Format Output**: Supports multiple output formats for CI/CD integration

## Testing Strategy

### Core Testing Requirements

**CRITICAL**: When testing tofusoup, `provide-testkit` MUST be available and used for all testing utilities.

- **provide-testkit dependency**: Required in dev dependencies (configured)
- **Foundation integration**: Uses `provide-foundation` for structured logging
- **Async testing**: Comprehensive async test support via `pytest-asyncio`
- **HTTP testing**: Mock HTTP services for testing provider interactions

### Standard Testing Pattern

```python
import pytest
from provide.testkit import temp_directory, test_files_structure
from tofusoup.generators import ConfigGenerator
from tofusoup.validators import SchemaValidator

def test_config_generation(temp_directory):
    """Test configuration generation."""
    generator = ConfigGenerator()
    config = generator.generate_test_config(
        provider="example",
        resources=["test_resource"]
    )

    config_file = temp_directory / "test.tf"
    config_file.write_text(config)

    validator = SchemaValidator()
    assert validator.validate(config_file)
```

### Testing Infrastructure

- Comprehensive test coverage including unit, integration, and conformance tests
- Tests use `pytest` with async support via `pytest-asyncio`
- HTTP mocking with `pytest-httpx` and `respx`
- Database testing with `aiosqlite` for test result storage
- Performance testing with `pytest-benchmark`

## Common Issues & Solutions

1. **ModuleNotFoundError for dependencies**: Run `source env.sh` to ensure proper environment setup
2. **Test execution timeouts**: Increase timeout settings in pytest configuration
3. **Provider compatibility issues**: Check provider version requirements and compatibility matrix
4. **Import errors**: Ensure PYTHONPATH includes both `src/` and project root

## Development Guidelines

- Always use modern Python 3.11+ type hints (e.g., `list[str]` not `List[str]`)
- Use `attrs` for data classes consistently
- Follow async patterns for I/O operations
- Use structured logging via `provide.foundation`
- No migration, backward compatibility, or legacy implementation logic
- Only use absolute imports, never relative imports
- Use async in tests where appropriate
- No hardcoded defaults - use configuration constants

## Integration with Ecosystem

### Pyvider Integration

```python
from tofusoup.integrations.pyvider import PyviderTestSuite
from pyvider.hub import discover_components

# Test Pyvider provider components
test_suite = PyviderTestSuite()
components = discover_components()
results = await test_suite.test_components(components)
```

### Plating Integration

```python
from tofusoup.integrations.plating import PlatingGenerator
from plating import PlatingBundle

# Generate documentation tests
generator = PlatingGenerator()
bundles = PlatingBundle.discover()
test_configs = generator.generate_from_bundles(bundles)
```

### OpenTofu/Terraform Integration

```python
from tofusoup.executors import TerraformExecutor, OpenTofuExecutor

# Test against multiple tools
terraform = TerraformExecutor()
tofu = OpenTofuExecutor()

results = await asyncio.gather(
    terraform.execute_test_suite(test_configs),
    tofu.execute_test_suite(test_configs)
)
```

## Output Guidelines for CLI and Logging

**IMPORTANT**: Use the correct output method for the context:

- **CLI User-Facing Output**: Use Foundation's output utilities for user messages
- **Application Logging**: Use Foundation logger for internal logging/debugging
- **Test Results**: Use structured JSON output for programmatic consumption
- **Reports**: Use Rich for terminal UI and HTML for web reports

## Third-Party Dependencies

The package integrates with multiple external tools:

- **OpenTofu/Terraform**: Primary test targets
- **Jinja2**: Template engine for configuration generation
- **aiosqlite**: Test result storage and analysis
- **httpx/respx**: HTTP client testing and mocking
- **textual**: Terminal UI for interactive test execution
- **msgpack**: Efficient serialization for test data

## Performance Considerations

- **Parallel Execution**: Tests run in parallel by default using asyncio
- **Caching**: Test results are cached to avoid redundant execution
- **Streaming**: Large test suites use streaming to manage memory usage
- **Benchmarking**: Built-in performance benchmarking for regression testing

## Security Considerations

- **Sandbox Execution**: Test execution is sandboxed to prevent system interference
- **Input Validation**: All test configurations are validated before execution
- **Credential Management**: Test credentials are managed securely
- **Network Isolation**: Tests can run in network-isolated environments

## Configuration Files

- **`tofusoup.toml`**: Main configuration file for test suites
- **`conformance/`**: Directory containing conformance test specifications
- **`templates/`**: Jinja2 templates for test generation
- **`schemas/`**: JSON schemas for validation
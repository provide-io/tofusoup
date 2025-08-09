# AI Agents Guide for TofuSoup

This document provides guidance for AI agents (like Claude, GitHub Copilot, etc.) working with the TofuSoup codebase.

## Overview

TofuSoup is a cross-language conformance testing suite for Terraform providers. It validates that providers correctly implement the Terraform Plugin Protocol v6 across different programming languages (Go, Python, .NET).

## Key Concepts

### 1. **Conformance Testing**
- Tests verify protocol compliance, not business logic
- Each test case has expected wire protocol inputs/outputs
- Tests run against multiple provider implementations

### 2. **Test Harness Generation**
- Harnesses are generated in Go, Python, and .NET
- Each harness implements the same test logic
- Harnesses communicate with providers via gRPC

### 3. **Wire Protocol**
- CTY (Terraform's type system) values encoded in MessagePack
- Base64 encoding for transport
- Strict protocol buffer definitions

## Development Guidelines

### When Adding New Tests

1. **Define the test case** in the appropriate test file
2. **Generate expected wire data** using the wire encoding tools
3. **Update harness templates** if new test patterns are needed
4. **Run against all language implementations** to ensure consistency

### When Modifying Core Components

1. **CTY Wire Encoding** (`src/tofusoup/cty_wire/`)
   - Changes here affect all tests
   - Must maintain backward compatibility
   - Update encoding/decoding tests

2. **Harness Generation** (`src/tofusoup/harness/`)
   - Templates use Jinja2 for all languages
   - Keep generated code idiomatic for each language
   - Test generated harnesses compile and run

3. **Test Infrastructure** (`src/tofusoup/`)
   - Core test runner and utilities
   - Should support parallel execution
   - Must handle provider lifecycle correctly

## Common Tasks

### Running Tests
```bash
# Run all conformance tests
soup test all

# Run specific test suite
soup test functions

# Run against specific provider
soup test --provider ./path/to/provider
```

### Generating Harnesses
```bash
# Generate harnesses for all tests
soup harness build

# Generate for specific language
soup harness build --language go
```

### Working with Wire Data
```bash
# Encode CTY value to wire format
soup wire encode input.json output.b64

# Decode wire format to CTY
soup wire decode input.b64 output.json

# Compare two wire encodings
soup wire compare expected.b64 actual.b64
```

## Architecture Notes

### Directory Structure
```
src/tofusoup/
├── cty_wire/        # CTY wire protocol encoding/decoding
├── harness/         # Test harness generation
├── templates/       # Jinja2 templates for each language
├── tests/           # Test definitions and data
└── cli/             # Command-line interface
```

### Key Classes
- `CtyWireEncoder`: Handles CTY to MessagePack encoding
- `HarnessGenerator`: Generates test harnesses from templates
- `ConformanceTest`: Base class for all conformance tests
- `ProviderRunner`: Manages provider process lifecycle

### Testing Philosophy
- **Property-based testing**: Use Hypothesis for wire encoding
- **Snapshot testing**: Compare against known-good outputs
- **Cross-language validation**: Same test must pass in all languages

## Performance Considerations

1. **Parallel Execution**: Tests should run in parallel when possible
2. **Provider Reuse**: Reuse provider processes across tests
3. **Caching**: Cache generated harnesses and compiled binaries
4. **Memory Usage**: Stream large wire data instead of loading fully

## Security Notes

- Never commit provider credentials or sensitive data
- Test harnesses should not execute arbitrary code
- Validate all wire data before decoding
- Use subprocess with appropriate sandboxing

## Debugging Tips

1. **Enable debug logging**: `SOUP_LOG_LEVEL=DEBUG soup test`
2. **Inspect wire data**: Use `soup wire decode` to examine protocol data
3. **Check generated harnesses**: Look in `.soup/harnesses/` directory
4. **Provider logs**: Check `.soup/logs/` for provider output

## Common Pitfalls

1. **Type Mismatches**: CTY types must exactly match protocol expectations
2. **Encoding Issues**: MessagePack encoding is order-sensitive
3. **Provider State**: Ensure clean state between tests
4. **Platform Differences**: Test on all target platforms

## Contributing

When contributing to TofuSoup:

1. Write tests for new functionality
2. Ensure all languages are supported
3. Update documentation and examples
4. Run the full test suite before submitting
5. Follow the existing code style

## Resources

- [Terraform Plugin Protocol v6 Specification](https://github.com/hashicorp/terraform-plugin-protocol)
- [CTY Type System Documentation](https://github.com/zclconf/go-cty)
- [MessagePack Specification](https://msgpack.org/)

## AI-Specific Notes

When working with this codebase:

1. **Respect the cross-language nature**: Changes must work in Go, Python, and .NET
2. **Maintain protocol compatibility**: Don't break existing wire formats
3. **Test thoroughly**: Use property-based testing for encoders/decoders
4. **Document wire formats**: Include examples of encoded data
5. **Keep harnesses idiomatic**: Generated code should look native to each language

Remember: TofuSoup ensures Terraform providers work correctly across languages. Your changes should enhance this goal without breaking existing functionality.
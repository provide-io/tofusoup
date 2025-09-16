# TofuSoup Documentation

Welcome to TofuSoup - Cross-language conformance testing framework for ensuring compatibility and consistency across polyglot systems.

## Features

TofuSoup provides:

- **Cross-Language Testing**: Test compatibility between Python, Go, TypeScript, and more
- **Conformance Validation**: Ensure implementations meet specifications
- **Protocol Testing**: Validate communication protocols and data formats
- **Schema Validation**: Cross-language schema and type validation
- **Integration Testing**: End-to-end testing across language boundaries
- **Performance Benchmarking**: Cross-language performance comparison

## Quick Start

```python
from tofusoup import ConformanceTest, Protocol

# Define a cross-language test
test = ConformanceTest("user-api")
test.add_implementation("python", "api.py")
test.add_implementation("go", "api.go")

# Run conformance validation
results = test.validate()
```

## API Reference

For complete API documentation, see the [API Reference](api/index.md).

## Testing Framework

- **Conformance**: Cross-language conformance validation
- **Protocol**: Communication protocol testing
- **Schema**: Data schema and type validation
- **Benchmarks**: Performance testing and comparison
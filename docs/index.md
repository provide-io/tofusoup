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

### Installation

<div class="termy">

```console
$ pip install tofusoup
// Installing tofusoup...
Successfully installed tofusoup

$ soup --version
tofusoup, version 0.1.0
```

</div>

### Generate Test Configuration

<div class="termy">

```console
$ soup generate --type conformance --name user-api
// Creating conformance test suite...
✓ Generated conformance/user-api/
✓ Created test specifications
✓ Created fixtures

Test configuration created successfully!
```

</div>

### Run Conformance Tests

<div class="termy">

```console
$ soup test --all
// Running conformance test suite...
// Loading test configurations...
Found 12 test cases

Testing Python implementation...
---> 100%
✓ 12/12 passed

Testing Go implementation...
---> 100%
✓ 12/12 passed

Cross-language validation...
---> 100%
✓ All implementations conform to specification

All tests passed! ✨
```

</div>

### Validate Specific Components

<div class="termy">

```console
$ soup validate --component user-api
// Validating user-api component...

Schema validation: ✓ passed
Protocol validation: ✓ passed
Type compatibility: ✓ passed
Performance benchmarks: ✓ within limits

Component validation successful!
```

</div>

### Generate Test Report

<div class="termy">

```console
$ soup report --format html --output report.html
// Generating test report...
// Analyzing test results...
// Creating visualizations...
---> 100%

✓ Report generated: report.html
  - 48 test cases
  - 100% pass rate
  - Cross-language compatibility: ✓
```

</div>

### Python API Usage

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
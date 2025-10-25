# Conformance Testing Strategy

This document outlines the architecture for the TofuSoup conformance testing suite.

## Testing Philosophy: `souptest` vs. `pytest`

A core distinction in this project is the separation of concerns in testing:
-   **Conformance Tests (`souptest_*.py`)**: These tests, located in `tofusoup/conformance/`, are for verifying **cross-language compatibility**. They compare the behavior of Python implementations against the canonical Go harnesses. They are run via the `soup test` command.
-   **Internal Tests (`test_*.py`)**: These are standard unit and integration tests for the `tofusoup` tool **itself**. They are located in `tofusoup/tests/` and are run using `pytest` directly.

## Directory Structure

The conformance test suite is organized by component and test type:

```
conformance/
├── conftest.py                         # Global fixtures and configurations
├── utils/                              # Shared test utilities
│
├── cty/                                # CTY conformance tests
│   ├── souptest_cty_python_vs_go.py   # Cross-language CTY compatibility
│   └── conftest.py                     # CTY-specific fixtures
│
├── hcl/                                # HCL conformance tests
│   ├── souptest_hcl_python_vs_go.py   # Cross-language HCL compatibility
│   ├── testdata/                       # HCL test fixtures
│   └── conftest.py                     # HCL-specific fixtures
│
├── wire/                               # Wire protocol conformance tests
│   ├── souptest_wire_python_vs_go.py  # Wire protocol compatibility
│   └── conftest.py                     # Wire-specific fixtures
│
├── rpc/                                # RPC conformance tests
│   ├── souptest_rpc_matrix.py         # Cross-language RPC matrix testing
│   ├── souptest_rpc_kv.py             # KV service tests
│   ├── certs/                          # Test certificates
│   └── conftest.py                     # RPC-specific fixtures
│
├── cli_verification/                   # CLI harness verification tests
│   ├── souptest_cty_cli.py            # CTY CLI tests
│   ├── souptest_hcl_cli.py            # HCL CLI tests
│   └── souptest_wire_cli.py           # Wire CLI tests
│
├── equivalence/                        # Terraform equivalence testing
│   ├── tests/                          # Equivalence test cases
│   └── tfcoremock/                     # Terraform mock infrastructure
│
└── tf/                                 # Terraform integration tests
    ├── http_api/                       # HTTP backend tests
    └── nested/                         # Nested module tests
```

## Test Organization

### Component Tests

Each component has dedicated conformance tests that validate cross-language compatibility:

- **CTY Tests**: Verify that Python CTY encoding/decoding produces identical results to Go
- **HCL Tests**: Ensure HCL parsing produces identical AST representations
- **Wire Tests**: Validate binary-level equivalence in wire protocol encoding
- **RPC Tests**: Test cross-language RPC communication (Python ↔ Go)

### CLI Verification Tests

CLI verification tests validate that harness command-line interfaces work correctly:
- Execute harness binaries with various inputs
- Verify exit codes and output formats
- Ensure consistent behavior across language implementations

### Integration Tests

Integration tests in `equivalence/` and `tf/` directories validate:
- Full Terraform workflows
- Provider lifecycle operations
- State management
- Backend operations

## Running Tests

### Run All Conformance Tests

```bash
soup test all
```

### Run Component-Specific Tests

```bash
soup test cty     # CTY conformance tests
soup test hcl     # HCL conformance tests
soup test wire    # Wire protocol tests
soup test rpc     # RPC tests
```

### Run with Pytest Directly

```bash
# All conformance tests
pytest conformance/

# Specific component
pytest conformance/cty/ -v

# With markers
pytest conformance/ -m "not slow"
```

## Test Design Principles

1. **Cross-Language Validation**: Every test compares Python and Go implementations
2. **Binary-Level Equivalence**: Wire protocol tests verify byte-for-byte output matching
3. **Shared Fixtures**: Common test data defined in `conftest.py` files
4. **Clear Test Naming**: `souptest_*` prefix identifies conformance tests
5. **Harness Integration**: Tests use actual harness binaries, not mocked implementations

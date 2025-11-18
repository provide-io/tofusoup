# RPC K/V Matrix Testing

This directory contains the complete RPC K/V matrix testing implementation for TofuSoup. The tests verify that Pyvider's RPC implementation is fully conformant with the Go implementation across all supported cryptographic configurations.

## Test Matrix Overview

**Total Test Combinations: 20**
- **Client Languages**: `go`, `pyvider`
- **Server Languages**: `go`, `pyvider`  
- **Crypto Configurations**: 
  - `auto_mtls + rsa_2048` (RSA 2048-bit keys)
  - `auto_mtls + rsa_4096` (RSA 4096-bit keys) 
  - `auto_mtls + ec_256` (P-256 elliptic curve)
  - `auto_mtls + ec_384` (P-384 elliptic curve)
  - `auto_mtls + ec_521` (P-521 elliptic curve)

## Test Coverage

Each combination tests:
1. **Basic Operations**: PUT/GET key-value pairs with verification
2. **Multiple Keys**: Independent key storage and retrieval  
3. **Key Overwriting**: Value replacement behavior
4. **Edge Cases**: Empty values, long keys/values, special characters
5. **Crypto Validation**: Certificate generation and mTLS functionality

## Files Overview

### Core Implementation
- **`matrix_config.py`** - Matrix parameter definitions and crypto configurations
- **`cert_manager.py`** - Certificate generation using pyvider-rpcplugin crypto system
- **`harness_factory.py`** - Dynamic client/server creation for Go and Python
- **`test_rpc_kv_matrix.py`** - Main test suite with all matrix combinations

### Test Infrastructure  
- **`conftest.py`** - Pytest configuration, fixtures, and test session management
- **`run_matrix_tests.py`** - Convenience test runner script

## Usage

### Quick Start
```bash
cd tofusoup
source env.sh

# Run a quick subset of tests (recommended for development)
python conformance/rpc/run_matrix_tests.py quick

# Run crypto validation only
python conformance/rpc/run_matrix_tests.py crypto

# Run specific language pair
python conformance/rpc/run_matrix_tests.py go-pyvider
```

### Full Test Suite
```bash
# Run all 20 combinations (takes ~10-15 minutes)
python conformance/rpc/run_matrix_tests.py full

# Or use pytest directly
pytest conformance/rpc/test_rpc_kv_matrix.py -v
```

### Targeted Testing
```bash
# Test specific crypto configuration
pytest conformance/rpc/test_rpc_kv_matrix.py -k "rsa_2048" -v

# Test basic operations only
pytest conformance/rpc/test_rpc_kv_matrix.py -k "test_rpc_kv_basic_operations" -v

# Test edge cases
pytest conformance/rpc/test_rpc_kv_matrix.py -k "edge_cases" -v
```

## Test Configuration Options

The test runner supports several configurations:

- **`quick`** - 5 combinations + crypto validation (~2-3 minutes)
- **`crypto`** - Crypto validation only (~1 minute)  
- **`go-go`** - Go client → Go server combinations
- **`pyvider-pyvider`** - Python client → Python server combinations
- **`go-pyvider`** - Go client → Python server combinations  
- **`pyvider-go`** - Python client → Go server combinations
- **`full`** - All 20 combinations (~10-15 minutes)
- **`basic`** - Basic operations only

## Matrix Test Details

### Test Functions

1. **`test_rpc_kv_basic_operations`** (20 tests)
   - Tests fundamental PUT/GET operations
   - Verifies correct value retrieval
   - Tests non-existent key handling

2. **`test_rpc_kv_multiple_keys`** (20 tests) 
   - Tests multiple independent keys
   - Verifies key isolation
   - Tests similar key names

3. **`test_rpc_kv_overwrite_key`** (20 tests)
   - Tests key value replacement
   - Verifies complete overwriting
   - Tests old value cleanup

4. **`test_rpc_kv_crypto_validation`** (5 tests)
   - Tests certificate generation for each crypto config
   - Verifies mTLS handshake success
   - Tests encrypted communication

5. **`test_rpc_kv_edge_cases`** (4 tests)
   - Tests empty values, long keys/values
   - Tests special characters and Unicode
   - Uses subset of matrix for efficiency

**Total Test Executions: 69**

### Certificate Management

The system automatically generates certificates for each crypto configuration using the pyvider-rpcplugin certificate system:

- **CA Certificate**: Self-signed certificate authority
- **Server Certificate**: Signed by CA, includes localhost SAN
- **Client Certificate**: Signed by CA for mutual authentication

Certificates are cached per configuration to avoid regeneration overhead.

## Example Test Output

```
🍲 TofuSoup RPC K/V Matrix Test Suite
================================================================================
Total test combinations: 20
Client languages: go, pyvider
Server languages: go, pyvider  
Crypto configurations: rsa_2048, rsa_4096, ec_256, ec_384, ec_521
================================================================================

conformance/rpc/test_rpc_kv_matrix.py::test_rpc_kv_basic_operations[go_go_rsa_2048] PASSED
conformance/rpc/test_rpc_kv_matrix.py::test_rpc_kv_basic_operations[go_go_rsa_4096] PASSED
conformance/rpc/test_rpc_kv_matrix.py::test_rpc_kv_basic_operations[go_go_ec_256] PASSED
...
```

## Architecture Benefits

### Matrix-Based Testing
- **Comprehensive Coverage**: All language/crypto combinations tested systematically
- **Single Test Functions**: No duplication across parameter variations  
- **Automatic Scaling**: Adding parameters automatically scales test coverage
- **Clear Reporting**: Matrix results clearly identify which combinations pass/fail

### Certificate Management
- **Leverages Existing System**: Uses proven pyvider-rpcplugin certificate generation
- **Automatic Generation**: Certificates created on-demand for each configuration
- **Proper mTLS**: Full mutual authentication with proper certificate chains
- **Caching**: Certificates reused across test runs for efficiency

### Process Management
- **Isolated Environments**: Each test gets its own work directory and processes
- **Robust Cleanup**: Proper server shutdown and resource cleanup
- **Error Handling**: Graceful handling of process startup/shutdown failures
- **Logging**: Comprehensive logging for debugging test failures

## Troubleshooting

### Common Issues

1. **Certificate Generation Failures**
   - Ensure pyvider-rpcplugin is properly installed
   - Check that the work directory is writable
   - Verify crypto configuration is valid

2. **Server Startup Failures**  
   - Check that Go harnesses are built (`soup harness build`)
   - Verify port availability
   - Check server logs in test output

3. **Client Connection Failures**
   - Verify server is running and address is correct
   - Check certificate paths and permissions
   - Validate mTLS configuration matches between client/server

### Debug Mode
```bash
# Run with detailed logging
pytest conformance/rpc/test_rpc_kv_matrix.py -v -s --log-cli-level=DEBUG

# Run single test combination
pytest conformance/rpc/test_rpc_kv_matrix.py::test_rpc_kv_basic_operations[go_pyvider_rsa_2048] -v -s
```

## Contributing

When adding new crypto configurations:

1. Update `matrix_config.py` with new `CryptoConfig` entries
2. Ensure pyvider-rpcplugin supports the new configuration  
3. Update certificate manager if needed
4. Add any new CLI arguments to harness factory
5. Update this README with new configuration details

## Performance Notes

- Full matrix (20 combinations × 3 test types) takes ~10-15 minutes
- Certificate generation adds ~2-3 seconds per crypto config
- Go harness builds add ~10-30 seconds (cached after first run)  
- Parallel execution can reduce total time (~5 minutes with `-n auto`)

The test suite is designed for comprehensive validation rather than speed, prioritizing thoroughness over execution time.
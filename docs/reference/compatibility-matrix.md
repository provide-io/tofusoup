# RPC Cross-Language Compatibility Matrix

This document details the compatibility matrix for cross-language RPC connections in tofusoup, including client-server language pairs and cryptographic curve support.

## Language Pair Compatibility

| Client → Server | Status | Notes |
|----------------|--------|-------|
| Python → Python | ✅ Supported | Full support with all features |
| Go → Python | ✅ Supported | Recommended for cross-language scenarios |
| Go → Go | ✅ Supported | Full support with all features |
| **Python → Go** | ❌ **Not Supported** | **Known bug in pyvider-rpcplugin** |

### Known Issues

#### Python → Go Connection Failure

**Problem**: Python clients cannot connect to Go servers due to a TLS handshake incompatibility in pyvider-rpcplugin.

**Symptoms**:
- Connection timeout after 10-30 seconds
- TLS handshake failure errors
- Server process starts but client cannot establish channel

**Workarounds**:
1. **Use Go client → Python server** (recommended for cross-language scenarios)
2. Use Python client → Python server (pure Python)
3. Use Go client → Go server (pure Go)

**Related Issues**:
- pyvider-rpcplugin: Incompatibility with go-plugin server TLS handshake
- Expected to be resolved in future pyvider releases

## Elliptic Curve Support

### Python Runtime (grpcio)

| Curve | Status | Notes |
|-------|--------|-------|
| secp256r1 (P-256) | ✅ Supported | Recommended, widely compatible |
| secp384r1 (P-384) | ✅ Supported | Higher security margin |
| secp521r1 (P-521) | ❌ **Not Supported** | **grpcio limitation** |

### Go Runtime (crypto/tls)

| Curve | Status | Notes |
|-------|--------|-------|
| secp256r1 (P-256) | ✅ Supported | Recommended, widely compatible |
| secp384r1 (P-384) | ✅ Supported | Higher security margin |
| secp521r1 (P-521) | ✅ Supported | Highest security, Go only |

### Curve Compatibility Notes

- **Python servers**: Only accept connections with `secp256r1` or `secp384r1`
- **Go servers**: Accept connections with any standard NIST curve
- **Cross-language**: When connecting Go → Python, use `secp256r1` or `secp384r1`
- **Auto mode**: Set `tls_curve="auto"` to let the runtime choose (uses secp256r1)

## TLS Mode Compatibility

### Supported TLS Modes

| Mode | Description | Compatibility |
|------|-------------|---------------|
| `disabled` | No encryption | Both Python and Go |
| `auto` | Automatic mTLS with generated certs | Both Python and Go |
| `manual` | User-provided certificates | Both Python and Go |

### TLS Mode Requirements

**Auto Mode**:
- Server and client must both use `auto` mode
- Specify `tls_key_type` (default: `"ec"`)
- Specify `tls_curve` for EC keys (default: `"secp256r1"`)
- Certificates generated automatically

**Manual Mode**:
- Provide `cert_file` and `key_file` parameters
- Certificates must be compatible (matching key types and curves)
- Both client and server need matching CA certificates

## Testing Compatibility

### Automated Test Coverage

The test suite validates all supported combinations:

```bash
# Run all compatibility tests
pytest tests/integration/

# Run specific test suites
pytest tests/integration/test_cross_language_matrix.py    # Language pairs
pytest tests/integration/test_curve_support.py            # Curve validation
pytest tests/integration/test_error_scenarios.py          # Error handling
```

### Test Matrix

The following combinations are tested automatically:

| Test Scenario | Client | Server | Curve | Expected Result |
|---------------|--------|--------|-------|-----------------|
| Python basic | Python | Python | secp256r1 | ✅ Pass |
| Python P-384 | Python | Python | secp384r1 | ✅ Pass |
| Go → Python | Go | Python | auto | ✅ Pass |
| Go → Go | Go | Go | secp384r1 | ✅ Pass |
| Python P-521 | Python | Python | secp521r1 | ❌ Expected Fail |
| Python → Go | Python | Go | any | ⏭️ Skipped (known bug) |

## CLI Validation

Use the validation command to check compatibility before connecting:

```bash
# Check if a connection will work
soup rpc validate-connection --client python --server harnesses/bin/soup-go

# Output:
# ⚠️  Python → Go connections not supported
# ✓  Supported alternatives:
#    - Go → Python (recommended)
#    - Python → Python
#    - Go → Go
```

## Recommendations

### For Production Use

1. **Use Go → Python** for cross-language scenarios (most reliable)
2. **Use secp256r1 or secp384r1** for Python servers
3. **Use auto TLS mode** unless you have specific cert requirements
4. **Test your configuration** with `soup rpc validate-connection` before deployment

### For Development

1. **Use Python → Python** for quick iteration on Python code
2. **Use Go → Go** for quick iteration on Go code
3. **Avoid Python → Go** until the bug is fixed
4. **Run integration tests** to verify your setup: `pytest tests/integration/`

## Error Messages

When encountering compatibility issues, the client provides helpful error messages:

### Python → Go Timeout

```
Connection timeout after 15.234s - Python client → Go server is not supported.

This is a known issue in pyvider-rpcplugin.

Supported alternatives:
  ✓ Go client → Python server (use soup-go binary as client)
  ✓ Python client → Python server
  ✓ Go client → Go server

Server path: harnesses/bin/soup-go
```

### Unsupported Curve

```
Curve 'secp521r1' is not supported by Python's grpcio library.
Supported curves for Python: secp256r1, secp384r1

Original error: TimeoutError: Connection timeout
```

## Future Improvements

Planned enhancements to the compatibility matrix:

1. **Fix Python → Go connection** (pyvider-rpcplugin update needed)
2. **Add Rust client/server support** (future runtime)
3. **Add secp521r1 support for Python** (requires grpcio update or alternative)
4. **Enhanced curve negotiation** (automatic downgrade for compatibility)

## Related Documentation

- [RPC Matrix Specification](../architecture/03-rpc-matrix-specification/)
- [Running Conformance Tests](../guides/testing/01-running-conformance-tests/)
- [Cross-Language Compatibility](../testing/cross-language-compatibility/)
- [pyvider-rpcplugin Documentation](https://github.com/provide-io/pyvider)

---

Last Updated: 2025-10-11

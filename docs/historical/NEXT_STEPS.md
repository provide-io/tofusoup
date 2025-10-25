# Python → Go RPC Connection - Next Steps

## Current Status: Bug Fixed, Testing Pending

### Summary
We identified and fixed a critical bug preventing Python client → Go server RPC connections. The issue was in `pyvider-rpcplugin`, not in the core protocol or grpcio.

---

## Bug Fix Details

### Root Cause
**File**: `/Users/tim/code/gh/provide-io/pyvider-rpcplugin/src/pyvider/rpcplugin/client/handshake.py`
**Lines**: 195-196, 207-208

The code was accessing non-existent attributes on the `Certificate` class:
```python
# BROKEN (old code):
cert_obj = Certificate.create_self_signed_client_cert(...)
self.client_cert = cert_obj.cert      # ❌ AttributeError: no attribute 'cert'
self.client_key_pem = cert_obj.key    # ❌ AttributeError: no attribute 'key'
```

### Fix Applied
Changed to use the correct attribute names:
```python
# FIXED (new code):
cert_obj = Certificate.create_self_signed_client_cert(...)
self.client_cert = cert_obj.cert_pem  # ✅ Correct attribute
self.client_key_pem = cert_obj.key_pem  # ✅ Correct attribute
```

**Two locations fixed**:
1. Line 195-196: Loading existing certificates
2. Line 207-208: Auto-generating mTLS certificates

---

## Environment Setup

### Current Installation
- **pyvider-rpcplugin**: Editable install from `/Users/tim/code/gh/provide-io/pyvider-rpcplugin`
- **grpcio**: Version 1.77.0.dev0 (custom build)
- **Working directory**: `/Users/tim/code/gh/provide-io/tofusoup`

### Test Files Available
- `test_curve.py` - Tests Python → Go with specific curves (currently shows warnings about unsupported)
- `test_py_to_py.py` - Tests Python → Python (working, uses foundation pout/perr)
- `tests/integration/test_cross_language_matrix.py` - Full compatibility matrix tests
- `tests/integration/test_curve_support.py` - Curve validation tests
- `tests/integration/test_error_scenarios.py` - Error handling tests

---

## Immediate Next Steps

### 1. Test the Fix

**Run the Python → Go test**:
```bash
cd /Users/tim/code/gh/provide-io/tofusoup
python3 test_curve.py secp384r1
```

**Expected outcome**:
- ✅ Certificate generation succeeds (no more AttributeError)
- ✅ Python client connects to Go server
- ✅ Put/Get operations work
- ✅ Test completes successfully

**If it fails**:
- Check logs for the new error type
- The certificate generation should now work, so any new errors are different issues

### 2. Update Test Documentation

Once working, update these files to reflect that Python → Go IS supported:

**Files to update**:
1. `test_curve.py` - Remove warnings about "NOT SUPPORTED"
2. `test_py_to_py.py` - Update note about Python → Go
3. `docs/rpc-compatibility-matrix.md` - Update compatibility table
4. `src/tofusoup/rpc/validation.py` - Update `get_compatibility_matrix()` to mark Python → Go as True
5. `src/tofusoup/rpc/client.py` - Remove the Python → Go error handling (lines 172-183, 198-207)

### 3. Run Full Test Suite

```bash
# Run all integration tests
pytest tests/integration/ -v

# Run specific test suites
pytest tests/integration/test_cross_language_matrix.py
pytest tests/integration/test_curve_support.py
pytest tests/integration/test_error_scenarios.py
```

### 4. Test All Curve Combinations

```bash
# Test each curve
python3 test_curve.py secp256r1
python3 test_curve.py secp384r1
python3 test_curve.py secp521r1  # This should fail on Python (grpcio limitation)
```

---

## Developer Experience Improvements (Already Completed)

### ✅ Phase 2: Test Coverage
- Created `tests/integration/test_cross_language_matrix.py`
- Created `tests/integration/test_curve_support.py`
- Created `tests/integration/test_error_scenarios.py`

### ✅ Phase 3: Better UX
- Enhanced error messages in `src/tofusoup/rpc/client.py`
- Created `docs/rpc-compatibility-matrix.md`
- Added `soup rpc validate-connection` CLI command
- Updated test scripts to use Foundation's `pout`/`perr` utilities
- Created `src/tofusoup/rpc/validation.py` with validation functions

---

## Known Limitations (Still True)

### Curve Support Differences
**Python (grpcio)**:
- ✅ secp256r1 (P-256)
- ✅ secp384r1 (P-384)
- ❌ secp521r1 (P-521) - Not supported by grpcio

**Go (crypto/tls)**:
- ✅ secp256r1 (P-256)
- ✅ secp384r1 (P-384)
- ✅ secp521r1 (P-521)

**Implication**: When connecting Python ↔ anything, use secp256r1 or secp384r1 only.

---

## Files Modified in This Session

### pyvider-rpcplugin
1. `/Users/tim/code/gh/provide-io/pyvider-rpcplugin/src/pyvider/rpcplugin/client/handshake.py`
   - Fixed line 195: `cert_obj.cert` → `cert_obj.cert_pem`
   - Fixed line 196: `cert_obj.key` → `cert_obj.key_pem`
   - Fixed line 207: `cert_obj.cert` → `cert_obj.cert_pem`
   - Fixed line 208: `cert_obj.key` → `cert_obj.key_pem`

### tofusoup (DX improvements - already completed)
1. `src/tofusoup/rpc/client.py` - Enhanced error messages
2. `src/tofusoup/rpc/cli.py` - Added validate-connection command
3. `src/tofusoup/rpc/validation.py` - Validation utilities (already existed)
4. `test_py_to_py.py` - Updated to use pout/perr
5. `test_curve.py` - Updated to use pout/perr
6. `docs/rpc-compatibility-matrix.md` - Created comprehensive compatibility docs
7. `tests/integration/test_cross_language_matrix.py` - Created (already existed)
8. `tests/integration/test_curve_support.py` - Created (already existed)
9. `tests/integration/test_error_scenarios.py` - Created (already existed)

---

## CLI Commands Reference

### Validate Connection Compatibility
```bash
# Check if a language pair will work
soup rpc validate-connection --client python --server /path/to/soup-go
soup rpc validate-connection --client go --server python --curve secp384r1
```

### Test RPC Connections
```bash
# Python → Python (working)
python3 test_py_to_py.py

# Python → Go (should now work!)
python3 test_curve.py secp384r1

# Go → Python (working - tested via Go harness)
# Go → Go (working - tested via Go harness)
```

---

## Success Criteria Checklist

- [ ] Python client successfully generates certificates (no AttributeError)
- [ ] Python → Go connection completes handshake
- [ ] Python → Go Put/Get operations work
- [ ] `python3 test_curve.py secp384r1` passes
- [ ] Integration tests pass: `pytest tests/integration/`
- [ ] Documentation updated to reflect Python → Go support
- [ ] Validation rules updated to mark Python → Go as supported
- [ ] Error messages removed from client.py for Python → Go

---

## If Issues Persist

### Debugging Steps
1. **Check certificate generation**: Look for logs showing certificate was created
2. **Check handshake**: Look for handshake success message with server cert present
3. **Check channel creation**: Verify secure channel is created (not insecure)
4. **Enable debug logging**: `LOG_LEVEL=DEBUG python3 test_curve.py secp384r1`

### Potential Remaining Issues
If the fix doesn't work, the next likely culprits are:
1. **Go server not outputting certificate in handshake** - Check if `_server_cert` is populated
2. **Certificate format mismatch** - Check `_rebuild_x509_pem()` method
3. **gRPC channel credentials setup** - Check if `ssl_channel_credentials` is called correctly
4. **Different bug in connection/channel code** - May need to investigate gRPC channel creation

---

## Historical Context

### Previous Belief (INCORRECT)
We initially thought Python → Go was fundamentally incompatible due to:
- Protocol mismatch between go-plugin and pyvider-rpcplugin
- TLS handshake issues
- grpcio version problems

### Actual Problem (CORRECT)
- Simple API mismatch after Certificate class was refactored in provide-foundation
- The `.cert` and `.key` attributes were renamed to `.cert_pem` and `.key_pem`
- This broke certificate generation, causing the connection to fail early
- The error message was misleading (AttributeError vs connection timeout)

### Evidence
```
[SecurityError] Failed to auto-generate client certificate:
'Certificate' object has no attribute 'cert'
```

This error appeared in the test output when using the editable install of pyvider-rpcplugin.

---

## Contact & References

**Working directories**:
- tofusoup: `/Users/tim/code/gh/provide-io/tofusoup`
- pyvider-rpcplugin: `/Users/tim/code/gh/provide-io/pyvider-rpcplugin`
- Virtual env: `/Users/tim/code/gh/provide-io/pyvider/.venv`

**Documentation**:
- Compatibility matrix: `docs/rpc-compatibility-matrix.md`
- Validation module: `src/tofusoup/rpc/validation.py`
- Test matrix: `tests/integration/test_cross_language_matrix.py`

**Key insight**: You had this working before with the same rpcplugin code - the Certificate API must have changed in provide-foundation, breaking the integration.

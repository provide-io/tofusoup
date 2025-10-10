# Cross-Language RPC Testing Results

## Executive Summary

Comprehensive testing of RPC operations across Go and Python client/server combinations.

**Date**: October 10, 2025
**Test Framework**: TofuSoup RPC Plugin Architecture
**Protocol**: gRPC with go-plugin framework
**Authentication**: Auto-mTLS (mutual TLS with auto-generated certificates)

---

## 🎯 Test Matrix

| Client | Server | Status | Duration | Notes |
|--------|--------|--------|----------|-------|
| Go | Go | ✅ **PASS** | 0.04s | Full put/get proof provided |
| Python | Python | ❌ FAIL | 10.39s | Known auto-TLS timeout issue |
| Python | Go | ❌ FAIL | 15.00s | mTLS handshake failure |
| Go | Python | ❌ FAIL | 30.00s | mTLS handshake failure |

**Overall Success Rate**: 25% (1/4 tests passing)

---

## ✅ Test 1: Go Client → Go Server (PASSING)

### Configuration
- **Client**: soup-go rpc client test
- **Server**: soup-go rpc server-start
- **TLS Mode**: auto (mTLS)
- **Key Type**: EC (default)

### Proof of Put/Get Operations

```
15:27:41.572 [INFO]  soup-go: 🌐📤 testing Put operation: key=go_client_test_key value_size=34
15:27:41.572 [DEBUG] 🔌🌐 kv-grpc-client: 🌐📤 initiating Put request: key=go_client_test_key value_size=34
15:27:41.572 [DEBUG] 🔌🌐 kv-grpc-client: 🌐✅ Put request completed successfully: key=go_client_test_key

15:27:41.572 [INFO]  soup-go: 🌐📥 testing Get operation: key=go_client_test_key
15:27:41.572 [DEBUG] 🔌🌐 kv-grpc-client: 🌐📥 initiating Get request: key=go_client_test_key
15:27:41.573 [DEBUG] 🔌🌐 kv-grpc-client: 🌐✅ Get request completed successfully: key=go_client_test_key value_size=34
15:27:41.573 [INFO]  soup-go: 🌐✅ Get operation successful: value="Hello from Go client to Go server!"

15:27:41.573 [INFO]  soup-go: 🌐🎉 RPC client test completed successfully
```

### Evidence
1. ✅ **Put Operation**: Successfully stored key `go_client_test_key` with 34-byte value
2. ✅ **Get Operation**: Successfully retrieved exact same value: `"Hello from Go client to Go server!"`
3. ✅ **Non-existent Key Handling**: Properly returned error for non-existent key
4. ✅ **Full Test Completion**: Test suite completed successfully in 0.04s

### Why It Works
- Both client and server use hashicorp/go-plugin framework
- Auto-mTLS handled natively by go-plugin
- Certificates generated and exchanged automatically
- Protocol buffers and gRPC fully compatible

---

## ❌ Test 2: Python Client → Python Server (FAILING)

### Configuration
- **Client**: KVClient (pyvider-rpcplugin)
- **Server**: soup rpc server-start (Python)
- **TLS Mode**: auto (RSA 2048)
- **Duration**: 10.39s timeout

### Error
```
Connection timeout after 10.39s (known issue)
```

### Root Cause
Python server's auto-TLS implementation is incomplete:

```python
elif tls_mode == "auto":
    logger.info("Auto TLS mode not fully implemented in Python server - falling back to insecure")
    logger.warning(
        "Python server does not yet support auto-generated certificates like Go's go-plugin framework"
    )
    port = server.add_insecure_port("[::]:0")
```

**Location**: `src/tofusoup/rpc/server.py:182-187`

### Status
**KNOWN LIMITATION** - Documented in code. Python server cannot auto-generate mTLS certificates like Go's go-plugin framework.

---

## ❌ Test 3: Python Client → Go Server (FAILING)

### Configuration
- **Client**: KVClient (pyvider-rpcplugin)
- **Server**: soup-go rpc server-start
- **TLS Mode**: auto
- **Key Type**: EC
- **Duration**: 15.00s timeout

### Error
```
SSL_ERROR_SSL: error:10000410:SSL routines:OPENSSL_internal:SSLV3_ALERT_HANDSHAKE_FAILURE:
Invalid certificate verification context
```

### Root Cause Analysis

#### 1. Client Certificate Generation ✅
```
2025-10-10 15:30:35.363051 [debug] 🗣️ ⚙️📖 Getting config PLUGIN_AUTO_MTLS = True
2025-10-10 15:30:35.363099 [info ] 🗣️ 🔐 Generating ephemeral self-signed client certificate.
2025-10-10 15:30:35.364508 [debug] 🗣️ 📜🔑🚀 Generating ECDSA key (curve: secp384r1).
2025-10-10 15:30:35.367523 [debug] 🗣️ 📜📝✅ Certificate signed successfully.
```

#### 2. Server Certificate Received ✅
```
2025-10-10 15:30:35.695292 [debug] 🗣️ 📡🔐 Restored certificate padding for handshake parsing.
2025-10-10 15:30:35.695309 [debug] 🗣️ 📡✅ Handshake parsing success: ... server_cert=present
```

#### 3. TLS Channel Creation **WITHOUT CLIENT CERT** ❌
```
2025-10-10 15:30:35.696283 [debug] 🗣️ ⚙️📖 Getting config PLUGIN_CLIENT_CERT = None
2025-10-10 15:30:35.696301 [debug] 🗣️ 🔐 Creating TLS channel (server auth only) using server's cert as root CA.
                                       Client certs (if auto-generated) will not be presented.
```

### The Bug

**Location**: pyvider-rpcplugin gRPC channel creation logic

1. Client **generates** a certificate (secp384r1)
2. Client **receives** server's certificate
3. Client creates TLS channel with **server auth only**
4. Client **does not present** its certificate to server
5. Server expects **mutual TLS** but only sees server auth
6. Handshake fails: "Invalid certificate verification context"

### Additional Issue: Curve Mismatch

Client requested P-256 but generated P-384 (secp384r1):

```python
# User requested:
KVClient(..., tls_curve="P-256")

# But client generated:
'curve': <CurveType.SECP384R1: 'secp384r1'>  # This is P-384!
```

This suggests the curve parameter isn't being passed correctly to the certificate generation logic.

---

## ❌ Test 4: Go Client → Python Server (FAILING)

### Configuration
- **Client**: soup-go rpc client test
- **Server**: soup (Python)
- **Duration**: 30.00s timeout

### Error
Similar SSL handshake failure as Test 3 (same root cause from opposite direction).

### Root Cause
Same mTLS certificate presentation issue - when roles are reversed, the Python components still fail to properly handle mutual TLS.

---

## 🔍 Infrastructure Analysis

### What Works Well

1. **Go → Go Communication**
   - Native go-plugin framework
   - Auto-mTLS fully functional
   - Fast (<100ms)
   - Reliable

2. **Test Infrastructure**
   - `test_cross_language_proof.py` - Comprehensive testing script
   - Clear output with colored formatting
   - Proper error handling and timeout management
   - Evidence capture for debugging

3. **Existing Components**
   - Unified CLI (`soup-go`, `soup`)
   - Argument alignment between Go and Python servers
   - KV storage with configurable directory
   - Protocol buffer definitions

### Critical Bugs Found

1. **pyvider-rpcplugin mTLS Bug**
   - **Severity**: High
   - **Impact**: Blocks all Python↔Go RPC communication
   - **Location**: TLS channel creation in pyvider-rpcplugin
   - **Fix Needed**: Modify gRPC channel creation to present client certificate when auto-generated

2. **Python Server Auto-TLS**
   - **Severity**: Medium
   - **Impact**: Python→Python communication fails
   - **Location**: `src/tofusoup/rpc/server.py:182-187`
   - **Status**: Documented limitation, fallback to insecure mode
   - **Fix Needed**: Implement auto certificate generation in Python server

3. **Curve Parameter Not Honored**
   - **Severity**: Low
   - **Impact**: Wrong curve used (P-384 instead of P-256)
   - **Location**: pyvider-rpcplugin certificate generation
   - **Fix Needed**: Pass `tls_curve` parameter through to Certificate class

---

## 📊 Test Artifacts

### Scripts Created
- `/Users/tim/code/gh/provide-io/tofusoup/test_cross_language_proof.py` - Main test suite
- `/Users/tim/code/gh/provide-io/tofusoup/test_python_to_go_simple.py` - Isolated Python→Go test
- `/Users/tim/code/gh/provide-io/tofusoup/test_go_to_python.py` - Isolated Go→Python test

### Existing Infrastructure Leveraged
- `conformance/rpc/test_rpc_kv_matrix.py` - Comprehensive pytest-based matrix
- `conformance/rpc/harness_factory.py` - Client/server factory functions
- `conformance/rpc/matrix_config.py` - Crypto configuration matrix
- `src/tofusoup/rpc/client.py` - Python KVClient
- `src/tofusoup/rpc/server.py` - Python KV server
- `src/tofusoup/harness/go/soup-go/rpc.go` - Go RPC implementation

---

## 🎓 Recommendations

### Immediate Actions

1. **Fix pyvider-rpcplugin TLS Channel Creation**
   ```python
   # Current (broken):
   credentials = grpc.ssl_channel_credentials(
       root_certificates=server_cert_pem
   )

   # Fixed (needed):
   credentials = grpc.ssl_channel_credentials(
       root_certificates=server_cert_pem,
       private_key=client_key_pem,
       certificate_chain=client_cert_pem
   )
   ```

2. **Implement Python Server Auto-TLS**
   - Generate server certificates using cryptography library
   - Follow go-plugin's auto-mTLS pattern
   - Exchange certificates via handshake protocol

3. **Fix Curve Parameter Passing**
   - Ensure `tls_curve` parameter flows through to Certificate generation
   - Add validation for supported curves (P-256, P-384, P-521)

### Testing Strategy

1. **Unit Tests**: Test certificate generation in isolation
2. **Integration Tests**: Use existing `test_rpc_kv_matrix.py` after fixes
3. **Proof Tests**: Continue using `test_cross_language_proof.py` for quick validation

---

## 📝 Conclusion

### What We Proved

✅ **Go client and Go server successfully perform put/get operations** with full mTLS encryption and proper error handling.

### What We Found

❌ **Python↔Go communication is blocked** by a certificate presentation bug in pyvider-rpcplugin's TLS channel creation.

❌ **Python→Python communication fails** due to incomplete auto-TLS implementation in the Python server.

### Impact

The RPC infrastructure is **solid for Go↔Go** communication but requires **pyvider-rpcplugin fixes** before cross-language communication will work.

---

**Generated**: October 10, 2025
**Test Duration**: ~60 seconds total
**Evidence**: Full logs captured in test output

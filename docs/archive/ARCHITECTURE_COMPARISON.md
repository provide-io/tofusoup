# Architecture Comparison: Manual vs. Abstracted Server Implementation

## Quick Reference

| Aspect | Manual (server.py) | Abstracted (plugin_server.py) | Winner |
|--------|-------------------|-------------------------------|--------|
| **Lines of Code** | 414 | 87 | Abstracted (5x smaller) |
| **TLS Configuration** | 4 functions | Config-driven | Abstracted |
| **Handshake** | Manual string construction | `build_handshake_response()` | Abstracted |
| **Transport Negotiation** | Hardcoded TCP | Negotiated | Abstracted |
| **Rate Limiting** | Not supported | Built-in | Abstracted |
| **Health Checks** | Not supported | Built-in | Abstracted |
| **Async/await** | Yes, but manual | Native pyvider pattern | Abstracted |
| **Signal Handling** | Manual | pyvider built-in | Abstracted |
| **Config System** | Partial (env vars) | Full rpcplugin_config | Abstracted |
| **Currently Spawned** | Yes | No | Manual |

---

## File Comparison

### Current Manual Implementation

**File**: `src/tofusoup/rpc/server.py` (414 lines)

```python
# Lines 301-327: MANUAL HANDSHAKE CONSTRUCTION
def _start_server_and_handshake(
    server: grpc.Server, port: int, server_cert_pem: str | None, output_handshake: bool
) -> None:
    server.start()
    
    if output_handshake:
        core_version = "1"
        protocol_version = "1"
        network = "tcp"
        address = f"127.0.0.1:{port}"
        protocol = "grpc"
        cert_b64 = ""
        if server_cert_pem:
            # Remove PEM headers and ALL whitespace
            cert_clean = server_cert_pem.replace("-----BEGIN CERTIFICATE-----", "")
            cert_clean = cert_clean.replace("-----END CERTIFICATE-----", "")
            cert_b64 = re.sub(r'\s+', '', cert_clean)
        
        # THIS IS THE PROBLEM: Manual string construction
        handshake_line = f"{core_version}|{protocol_version}|{network}|{address}|{protocol}|{cert_b64}"
        print(handshake_line, flush=True)
        sys.stdout.flush()

# Lines 248-276: MANUAL TLS CONFIGURATION
def _configure_tls_auto(server: grpc.Server, tls_key_type: str, tls_curve: str) -> tuple[int, str | None]:
    logger.info("Auto TLS enabled - generating server certificate", ...)
    from provide.foundation.crypto import Certificate
    
    try:
        cert_obj = Certificate.create_self_signed_server_cert(
            common_name="tofusoup.rpc.server",
            organization_name="TofuSoup",
            validity_days=365,
            alt_names=["localhost", "127.0.0.1"],
            key_type="ecdsa" if tls_key_type == "ec" else tls_key_type,
            ecdsa_curve=tls_curve,
        )
        server_cert_pem = cert_obj.cert_pem
        server_key_pem = cert_obj.key_pem
        
        server_credentials = grpc.ssl_server_credentials(
            [(server_key_pem.encode("utf-8"), server_cert_pem.encode("utf-8"))],
            root_certificates=None,
            require_client_auth=False,
        )
        port = server.add_secure_port("[::]:0", server_credentials)
        # ... more manual handling
```

**Problems**:
- 4 separate TLS configuration functions (lines 241-298)
- Manual certificate encoding/decoding
- Hardcoded TCP transport
- Manual handshake string construction
- Doesn't integrate with pyvider-rpcplugin config system
- No rate limiting, health checks, etc.

---

### Correct Abstracted Implementation

**File**: `src/tofusoup/rpc/plugin_server.py` (87 lines)

```python
from pyvider.rpcplugin.factories import plugin_server
from pyvider.rpcplugin.protocol.base import RPCPluginProtocol
from tofusoup.rpc.server import KV


class KVProtocol(RPCPluginProtocol):
    """Protocol implementation for the KV service"""
    
    async def get_grpc_descriptors(self) -> tuple[Any, str]:
        """Return the gRPC descriptor and service name"""
        return kv_pb2_grpc, "kv.KVService"
    
    async def add_to_server(self, server: Any, handler: Any) -> None:
        """Add the KV service to the gRPC server"""
        kv_pb2_grpc.add_KVServicer_to_server(handler, server)
        logger.info("KV service registered with gRPC server")


async def start_kv_server() -> None:
    """Start the KV plugin server - this is the expected entry point"""
    logger.info("Starting KV plugin server...")
    
    # Create the KV handler
    handler = KV()
    
    # Create the protocol wrapper
    protocol = KVProtocol()
    
    # Create the plugin server using the factory function
    server = plugin_server(protocol=protocol, handler=handler)
    
    try:
        # THIS SINGLE CALL HANDLES EVERYTHING:
        # - Magic cookie validation
        # - Protocol/transport negotiation
        # - TLS setup
        # - Handshake generation
        # - Server management
        # - Signal handling
        await server.serve()
    except KeyboardInterrupt:
        logger.info("Received shutdown signal")
    except Exception as e:
        logger.error(f"Plugin server error: {e}")
        sys.exit(1)
    finally:
        logger.info("Plugin server shut down")


async def main() -> None:
    """Main entry point for the plugin server executable"""
    # Check for magic cookie
    magic_cookie_key = os.getenv("PLUGIN_MAGIC_COOKIE_KEY", "BASIC_PLUGIN")
    magic_cookie_value = os.getenv(magic_cookie_key)
    expected_magic_value = os.getenv("PLUGIN_MAGIC_COOKIE_VALUE", "hello")
    
    if magic_cookie_value != expected_magic_value:
        logger.error("Magic cookie mismatch. This binary is a plugin...")
        sys.exit(1)
    
    await start_kv_server()


if __name__ == "__main__":
    asyncio.run(main())
```

**Benefits**:
- Uses pyvider-rpcplugin abstractions throughout
- All TLS handled by RPCPluginServer
- All handshake handling by RPCPluginServer
- Integrates with pyvider-rpcplugin config system
- Automatically gets rate limiting, health checks, etc.
- Cleaner, more maintainable code

---

## pyvider-rpcplugin Server Abstraction Details

### What RPCPluginServer.serve() Does

From `/Users/tim/.local/share/uv/tools/pyvider-builder/lib/python3.13/site-packages/pyvider/rpcplugin/server.py` (lines 577-610):

```python
async def serve(self) -> None:
    try:
        # 1. Register signal handlers for graceful shutdown
        self._register_signal_handlers()
        
        # 2. Negotiate handshake - validates magic cookie, protocol version, transport
        await self._negotiate_handshake()
        
        # 3. Setup gRPC server with proper credentials
        # - Handles auto-mTLS certificate generation
        # - Integrates health servicer
        # - Sets up rate limiting if enabled
        await self._setup_server(client_cert_str=None)
        
        # 4. Watch for shutdown signals (file-based shutdown)
        if self._shutdown_file_path:
            self._shutdown_watcher_task = asyncio.create_task(
                self._watch_shutdown_file()
            )
        
        # 5. BUILD PROPER HANDSHAKE RESPONSE
        # - NOT manual string construction!
        # - Uses transport abstraction
        # - Handles certificate encoding internally
        concrete_transport = cast(RPCPluginTransportType, self._transport)
        response = await build_handshake_response(
            plugin_version=self._protocol_version,
            transport_name=self._transport_name,
            transport=concrete_transport,
            server_cert=self._server_cert_obj,  # Already handled!
            port=self._port,
        )
        
        # 6. OUTPUT TO STDOUT
        # - This is where go-plugin client reads the handshake
        sys.stdout.buffer.write(f"{response}\n".encode())
        sys.stdout.buffer.flush()
        
        # 7. Wait for shutdown signal
        self._serving_event.set()
        await self._serving_future
    finally:
        await self.stop()
```

### Key Abstractions Provided

1. **Handshake Negotiation** (`_negotiate_handshake`)
   - Validates magic cookie automatically
   - Negotiates protocol version
   - Negotiates transport type (TCP/Unix)

2. **Server Setup** (`_setup_server`)
   - Creates async gRPC server
   - Registers user's protocol service
   - Registers health servicer
   - Sets up rate limiting if configured
   - Handles TLS credentials

3. **Transport Negotiation** (`negotiate_transport`)
   - TCP Socket Transport
   - Unix Socket Transport
   - Automatic selection

4. **Credential Generation** (`_generate_server_credentials`)
   - Auto-mTLS with self-signed certs
   - Manual cert support
   - Client auth validation

5. **Handshake Response** (`build_handshake_response`)
   - Proper protocol compliance
   - Certificate encoding handled internally
   - Not manual string construction

---

## Current Spawning Flow

### Manual Implementation (Current)

```
KVClient (python/client.py)
    │
    ├─ Check server_path is executable
    ├─ Build command: ["python", "src/tofusoup/rpc/server.py"]
    ├─ Set environment variables (magic cookies, TLS config)
    └─ Spawn subprocess with env
         │
         ├─ server.py __main__ checks env vars
         │  (lines 394-408)
         │
         ├─ Calls start_kv_server(
         │     tls_mode=...,
         │     tls_key_type=...,
         │     tls_curve=...,
         │     storage_dir=...,
         │     output_handshake=True
         │  )
         │
         ├─ Creates grpc.Server manually
         │  (line 373)
         │
         ├─ Configures TLS manually
         │  _configure_tls_disabled() OR
         │  _configure_tls_auto() OR
         │  _configure_tls_manual()
         │
         ├─ Calls _start_server_and_handshake(
         │     server, port, cert_pem, True
         │  )
         │
         ├─ MANUALLY CONSTRUCTS HANDSHAKE STRING
         │  (lines 321-324)
         │  "1|1|tcp|127.0.0.1:PORT|grpc|CERT_B64"
         │
         └─ Prints to stdout
             │
             KVClient reads from stdout
             KVClient parses handshake
             KVClient connects to gRPC server
```

**Total Handshake Code**: ~170 lines of manual implementation

---

### Abstracted Implementation (Better)

```
KVClient (python/client.py)
    │
    ├─ Check server_path is executable
    ├─ Build command: ["python", "src/tofusoup/rpc/plugin_server.py"]
    ├─ Set environment variables (magic cookies, TLS config)
    └─ Spawn subprocess with env
         │
         ├─ plugin_server.py __main__ calls asyncio.run(main())
         │  (line 84)
         │
         ├─ main() validates magic cookie
         │
         ├─ Creates KVProtocol() instance
         │
         ├─ Creates KV() handler instance
         │
         ├─ Calls plugin_server(
         │     protocol=...,
         │     handler=...,
         │  )
         │  Returns RPCPluginServer instance
         │
         ├─ Calls await server.serve()
         │  (pyvider-rpcplugin handles EVERYTHING)
         │
         │  Inside serve():
         │  ├─ Registers signal handlers
         │  ├─ Negotiates handshake
         │  ├─ Sets up gRPC server with TLS
         │  ├─ Builds proper handshake response
         │  └─ Outputs to stdout
         │
         └─ Waits for shutdown signal
             │
             KVClient reads from stdout
             KVClient parses handshake
             KVClient connects to gRPC server
```

**Total Handshake Code**: 0 lines (all in pyvider-rpcplugin)

---

## Feature Matrix

### Features Comparison

| Feature | Manual (server.py) | Abstracted (plugin_server.py) |
|---------|-------------------|-------------------------------|
| **Magic Cookie Validation** | Manual (env check) | Automatic (pyvider) |
| **Protocol Version Negotiation** | Hardcoded | Automatic (pyvider) |
| **Transport Negotiation** | Hardcoded TCP | TCP/Unix automatic (pyvider) |
| **TLS/mTLS** | 4 manual functions | Automatic (pyvider) |
| **Certificate Generation** | Manual provide.foundation | Automatic (pyvider) |
| **Handshake Response** | Manual string | Automatic (pyvider) |
| **Rate Limiting** | Not supported | Built-in (pyvider) |
| **Health Checks** | Not supported | Built-in (pyvider) |
| **Shutdown File Watching** | Not supported | Built-in (pyvider) |
| **Signal Handling** | Manual while True | Automatic (pyvider) |
| **Config Integration** | Partial | Full rpcplugin_config (pyvider) |
| **Graceful Shutdown** | Manual | Automatic (pyvider) |
| **Logging Integration** | Foundation + manual | Foundation + pyvider (pyvider) |

---

## Code Quality Metrics

### Cyclomatic Complexity

**Manual Implementation (server.py)**:
- `start_kv_server()`: 4 branches (tls_mode if/elif/elif/else)
- `_configure_tls_auto()`: 3 try/except blocks
- `_start_server_and_handshake()`: 2 branches (output_handshake if)
- Total manual complexity: Medium-High

**Abstracted Implementation (plugin_server.py)**:
- `start_kv_server()`: 1 try/except block
- `main()`: 1 if/else validation
- Total complexity: Low

### Test Coverage

**Manual Implementation**:
- Requires mocking grpc.Server
- Requires mocking ssl_server_credentials
- Requires mocking stdout for handshake verification
- Complex integration testing

**Abstracted Implementation**:
- pyvider-rpcplugin handles most logic
- Only needs to test KVProtocol interface
- Simpler unit tests

---

## Migration Path

### Option 1: Full Migration (Recommended)

1. Update `KVClient` to spawn `plugin_server.py` instead of `server.py`
2. Remove manual TLS/handshake code from `server.py`
3. Keep `server.py` for standalone/insecure testing mode
4. Leverage pyvider-rpcplugin config system

### Option 2: Gradual Migration

1. Create new `plugin_server.py` for go-plugin mode (already exists)
2. Keep `server.py` as fallback
3. Update tests to use `plugin_server.py`
4. Deprecate `server.py` over time

### Option 3: Wrapper Approach

1. Create wrapper that uses pyvider-rpcplugin internally
2. Maintain backwards compatibility with server.py CLI
3. Minimal code changes

---

## Summary

**pyvider-rpcplugin provides full server-side abstraction** that eliminates the need for manual handshake/TLS/protocol handling.

**Current State**:
- Client uses abstractions (RPCPluginClient) ✓
- Server uses manual implementation ✗
- Architectural asymmetry

**Better State**:
- Client uses abstractions (RPCPluginClient) ✓
- Server uses abstractions (RPCPluginServer) ✓
- Consistent architecture

**Benefits of Migration**:
- 5x less code
- No manual protocol handling
- Access to rate limiting, health checks
- Easier maintenance
- Better integration with ecosystem

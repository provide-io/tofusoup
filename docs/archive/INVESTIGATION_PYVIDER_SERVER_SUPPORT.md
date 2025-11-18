# pyvider-rpcplugin Architecture Investigation Report

## Executive Summary

**CRITICAL FINDING**: pyvider-rpcplugin **DOES have comprehensive server-side support** via `RPCPluginServer` class, but TofuSoup is NOT using it. Instead, TofuSoup manually reimplements handshake/protocol details in `/Users/tim/code/gh/provide-io/tofusoup/src/tofusoup/rpc/server.py`, creating unnecessary code duplication and maintenance burden.

**There is a fundamental architectural asymmetry:**
- **Client-side**: Uses `pyvider.rpcplugin.client.RPCPluginClient` (full abstraction of handshake, certificates, protocol negotiation)
- **Server-side**: TofuSoup manually implements what should be abstracted

---

## 1. Does pyvider-rpcplugin Have Server-Side Support?

### YES - Complete server-side framework exists

**Location**: `/Users/tim/.local/share/uv/tools/pyvider-builder/lib/python3.13/site-packages/pyvider/rpcplugin/`

**Core Server Components**:

1. **`RPCPluginServer` class** (server.py, line 81-630)
   - Full go-plugin protocol implementation
   - Handshake negotiation
   - Transport negotiation (TCP/Unix sockets)
   - Auto-mTLS with certificate generation
   - Signal handling and graceful shutdown
   - Rate limiting
   - Health checking

2. **`plugin_server()` factory** (factories.py, line 128-157)
   - Convenient factory for creating servers
   - Auto-configures transport
   - Handles protocol setup

3. **`RPCPluginProtocol` base class** (protocol/base.py)
   - Protocol abstraction for service registration
   - Requires implementing:
     - `get_grpc_descriptors()`
     - `add_to_server()`

4. **Protocol support services**:
   - Transport negotiation (TCP, Unix sockets)
   - Certificate generation and management
   - Handshake response building
   - Health servicer integration

---

## 2. Correct Server-Side Architecture (Already in TofuSoup!)

### A. The CORRECT Implementation Already Exists in TofuSoup

**File**: `/Users/tim/code/gh/provide-io/tofusoup/src/tofusoup/rpc/plugin_server.py`

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

async def start_kv_server() -> None:
    """Start the KV plugin server - this is the expected entry point"""
    handler = KV()
    protocol = KVProtocol()
    server = plugin_server(protocol=protocol, handler=handler)
    
    try:
        # This handles ALL the go-plugin handshake and serving!
        await server.serve()
    except KeyboardInterrupt:
        logger.info("Received shutdown signal")
```

**Status**: THIS IS THE RIGHT APPROACH!
- Uses pyvider-rpcplugin abstractions
- No manual handshake construction
- No manual certificate handling
- No manual protocol negotiation

---

## 3. The PROBLEMATIC Implementation That Exists

### B. The WRONG Implementation Also Exists (server.py)

**File**: `/Users/tim/code/gh/provide-io/tofusoup/src/tofusoup/rpc/server.py`

**Lines 301-327: Manual Handshake Construction**
```python
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
            # Remove PEM headers and ALL whitespace for clean base64 encoding
            cert_clean = server_cert_pem.replace("-----BEGIN CERTIFICATE-----", "")
            cert_clean = cert_clean.replace("-----END CERTIFICATE-----", "")
            cert_b64 = re.sub(r'\s+', '', cert_clean)
        
        # THIS IS MANUAL HANDSHAKE REIMPLEMENTATION!
        handshake_line = f"{core_version}|{protocol_version}|{network}|{address}|{protocol}|{cert_b64}"
        print(handshake_line, flush=True)
        sys.stdout.flush()
```

**Problems**:
1. Reimplements what `RPCPluginServer.serve()` already does
2. Doesn't use transport negotiation abstraction
3. Doesn't integrate with config system
4. Manual certificate encoding/decoding
5. No integration with rate limiting, health checks, etc.

---

## 4. Current Asymmetric Usage Pattern

### What KVClient Does (Client-Side - CORRECT)

**File**: `/Users/tim/code/gh/provide-io/tofusoup/src/tofusoup/rpc/client.py`

```python
from pyvider.rpcplugin.client import RPCPluginClient

# Abstraction-based initialization
self._client = RPCPluginClient(
    command=server_command,
    config=client_config,  # Handles all config, certs, etc.
)

# Simple async connection
await asyncio.wait_for(self._client.start(), timeout=self.connection_timeout)

# gRPC channel is automatically negotiated
self._stub = kv_pb2_grpc.KVStub(self._client.grpc_channel)
```

**What KVClient spawns for Python servers** (from logic.py line 51):
```python
python_server_script_path = project_root / "src" / "tofusoup" / "rpc" / "server.py"
# Spawns: ["python", "server.py"]
```

### What Should Happen (Server-Side - SHOULD BE LIKE plugin_server.py)

The server being spawned should use the abstraction, not manual implementation.

**Current Reality**:
1. KVClient spawns `server.py` (the problematic file)
2. `server.py` manually constructs handshake
3. Go client reads handshake from stdout
4. Go client connects to gRPC server

**Better Reality (partially implemented)**:
1. KVClient should spawn something using `plugin_server.py` abstraction
2. `plugin_server.py` calls `RPCPluginServer.serve()` 
3. `RPCPluginServer.serve()` handles ALL handshake, negotiation, certificates
4. Go client reads proper handshake from stdout
5. Go client connects to gRPC server

---

## 5. How pyvider-rpcplugin Server Works

### RPCPluginServer.serve() Flow

```python
async def serve(self) -> None:
    # 1. Register signal handlers
    self._register_signal_handlers()
    
    # 2. Negotiate handshake (magic cookie, protocol version, transport)
    await self._negotiate_handshake()
    
    # 3. Setup gRPC server with credentials
    await self._setup_server(client_cert_str=None)
    
    # 4. Watch for shutdown signals
    if self._shutdown_file_path:
        self._shutdown_watcher_task = asyncio.create_task(...)
    
    # 5. BUILD PROPER HANDSHAKE RESPONSE (NOT MANUAL!)
    concrete_transport = cast(RPCPluginTransportType, self._transport)
    response = await build_handshake_response(
        plugin_version=self._protocol_version,
        transport_name=self._transport_name,
        transport=concrete_transport,
        server_cert=self._server_cert_obj,  # Handles cert encoding internally
        port=self._port,
    )
    
    # 6. OUTPUT TO STDOUT (where go-plugin reads it)
    sys.stdout.buffer.write(f"{response}\n".encode())
    sys.stdout.buffer.flush()
    
    # 7. Wait for shutdown
    self._serving_event.set()
    await self._serving_future
```

**Key Differences**:
- Uses `build_handshake_response()` abstraction (not manual string construction)
- Integrates transport negotiation (not hardcoded TCP)
- Manages server certificates automatically
- Integrates with config system
- Proper signal handling
- Rate limiting support
- Health service integration

---

## 6. Proof: The Two Files Side-by-Side

### What plugin_server.py Does (CORRECT)

```python
# plugin_server.py - ABSTRACTION-BASED
from pyvider.rpcplugin.factories import plugin_server

async def main():
    handler = KV()
    protocol = KVProtocol()
    server = plugin_server(protocol=protocol, handler=handler)
    
    try:
        await server.serve()  # HANDLES EVERYTHING!
    except KeyboardInterrupt:
        logger.info("Received shutdown signal")
```

### What server.py Does (PROBLEMATIC)

```python
# server.py - MANUAL IMPLEMENTATION
def start_kv_server(...):
    server = grpc.server(futures.ThreadPoolExecutor(max_workers=10))
    serve(server, storage_dir=storage_dir)
    
    # MANUAL CONFIG
    if tls_mode == "disabled":
        port, server_cert_pem = _configure_tls_disabled(server)
    elif tls_mode == "auto":
        port, server_cert_pem = _configure_tls_auto(server, ...)
    elif tls_mode == "manual":
        port, server_cert_pem = _configure_tls_manual(server, ...)
    
    # MANUAL HANDSHAKE
    _start_server_and_handshake(server, port, server_cert_pem, output_handshake)

def _start_server_and_handshake(...):
    server.start()
    
    if output_handshake:
        # MANUAL STRING CONSTRUCTION (should use build_handshake_response!)
        handshake_line = f"{core_version}|{protocol_version}|{network}|{address}|{protocol}|{cert_b64}"
        print(handshake_line, flush=True)
```

---

## 7. Evidence: How pyvider-rpcplugin Exports Server API

**pyvider/rpcplugin/__init__.py** exports:

```python
from pyvider.rpcplugin.server import RPCPluginServer
from pyvider.rpcplugin.factories import (
    plugin_server,  # <- SERVER FACTORY
    plugin_client,  # <- CLIENT FACTORY
)

__all__ = [
    "RPCPluginClient",
    "RPCPluginServer",      # <- FULL SERVER CLASS
    "plugin_client",
    "plugin_server",        # <- SERVER FACTORY FUNCTION
    "plugin_protocol",
    "create_basic_protocol",
    # ...
]
```

Public API includes:
- `RPCPluginServer` class
- `plugin_server()` factory function
- Full protocol and transport abstractions

**This is deliberately exported and documented for public use.**

---

## 8. What KVClient Actually Spawns (Current State)

### For Python Servers

**From logic.py (line 51)**:
```python
python_server_script_path = project_root / "src" / "tofusoup" / "rpc" / "server.py"

client = KVClient(
    server_path=str(python_server_script_path),
    ...
)
```

**From harness_factory.py (line 173)**:
```python
cmd = ["python", str(server_script)]  # server.py
```

**What actually gets spawned**:
```bash
python /path/to/src/tofusoup/rpc/server.py
```

This runs the __main__ block of server.py (lines 392-411):
```python
if __name__ == "__main__":
    # Check if being run in go-plugin mode
    if os.getenv("PLUGIN_MAGIC_COOKIE_KEY") or os.getenv("PLUGIN_PROTOCOL_VERSIONS"):
        # Plugin mode - output go-plugin handshake
        start_kv_server(
            tls_mode=tls_mode,
            tls_key_type=tls_key_type,
            tls_curve=tls_curve,
            storage_dir=storage_dir,
            output_handshake=True,  # <- OUTPUTS MANUAL HANDSHAKE
        )
    else:
        # Standalone mode
        main()
```

### What SHOULD Be Spawned (Better Approach)

```bash
python /path/to/src/tofusoup/rpc/plugin_server.py
```

This runs the __main__ block of plugin_server.py (lines 83-84):
```python
if __name__ == "__main__":
    asyncio.run(main())  # Calls start_kv_server() which uses pyvider-rpcplugin
```

---

## 9. Why This Matters

### Current Architecture Problems

1. **Code Duplication**: TLS, handshake, certificate handling duplicated
2. **Maintenance Burden**: Changes to go-plugin protocol require manual updates
3. **Missing Features**: No rate limiting, health checks, advanced transport negotiation
4. **Bug Surface**: Manual string parsing more prone to errors
5. **Config Misalignment**: Doesn't respect pyvider-rpcplugin config system

### Benefits of Using pyvider-rpcplugin

1. **Single Source of Truth**: Protocol handling maintained by pyvider team
2. **Feature-Rich**: Auto-mTLS, rate limiting, health checks, shutdown files
3. **Config-Driven**: Integrates with rpcplugin_config
4. **Tested**: Community-maintained, battle-tested implementation
5. **Async-Native**: Full async/await support

---

## 10. Current Working Implementations

### plugin_server.py (CORRECT - Partially Used)

**Status**: Exists, uses pyvider-rpcplugin abstractions correctly

**Usage**: 
- Defined but not the default spawned server
- Shows the right architectural pattern
- Should be the primary implementation

### server.py (PROBLEMATIC - Currently Spawned)

**Status**: Exists, manual handshake implementation

**Usage**:
- Currently spawned by KVClient for Python servers
- Spawned by harness_factory for matrix tests
- Contains manual go-plugin protocol implementation

---

## 11. Explanation of Asymmetry

### Why Client Uses pyvider-rpcplugin

**KVClient** (client.py lines 293-310):
```python
self._client = RPCPluginClient(
    command=server_command,
    config=client_config,
)

await asyncio.wait_for(self._client.start(), timeout=self.connection_timeout)

self._stub = kv_pb2_grpc.KVStub(self._client.grpc_channel)
```

Client-side uses abstractions because:
1. Go clients (soup-go binary) need cross-language compatibility
2. Python client needs to parse handshake from spawned servers
3. RPCPluginClient abstracts all that complexity

### Why Server Doesn't Use pyvider-rpcplugin (Current State)

**server.py** manual implementation exists because:
1. Historical reasons (server.py predates plugin_server.py standardization)
2. Backwards compatibility with existing spawning patterns
3. Simple insecure mode support for testing
4. Gradual migration path (plugin_server.py is the new pattern)

---

## 12. Key Architectural Finding

### The Correct Architecture Pattern

```
KVClient (Python)
    ↓ spawns via subprocess
    ↓ passes magic cookies via env
    ↓
[Server Process - Should Use pyvider-rpcplugin]
    ↓ uses RPCPluginServer.serve()
    ↓ negotiates transport/protocol
    ↓ generates handshake response
    ↓ writes to stdout
    ↓
KVClient reads handshake → connects to gRPC → uses stub
```

### What plugin_server.py Does (RIGHT WAY)

- Respects magic cookies
- Validates handshake
- Negotiates protocol/transport
- Generates proper handshake response
- Uses pyvider abstractions

### What server.py Does (WRONG WAY)

- Checks magic cookies manually
- Constructs TLS manually
- Hardcodes TCP transport
- Manually builds handshake string
- Duplicates pyvider functionality

---

## Summary Table

| Aspect | Client-Side | Server-Side (Current) | Server-Side (Correct) |
|--------|-------------|---------------------|----------------------|
| **Library Usage** | pyvider-rpcplugin.client | Manual implementation | pyvider-rpcplugin.server |
| **Handshake** | RPCPluginClient abstraction | Manual string construction | build_handshake_response() |
| **Protocol Negotiation** | Abstracted | Hardcoded | Abstracted via RPCPluginServer |
| **Transport** | TCP + Unix negotiation | Hardcoded TCP | Negotiated |
| **TLS/mTLS** | Config-driven | Manual cert handling | Auto-mTLS with config |
| **File** | client.py | server.py | plugin_server.py |
| **Location** | Active | Active (spawned) | Defined but not default |
| **Status** | Correct | Needs refactoring | Better pattern |

---

## Conclusion

**Yes, pyvider-rpcplugin has FULL SERVER-SIDE SUPPORT.**

The architecture shows:
1. **RPCPluginServer** class provides complete server implementation
2. **plugin_server()** factory provides convenient instantiation
3. **plugin_server.py** in TofuSoup correctly uses these abstractions
4. **server.py** in TofuSoup reimplements what should be abstracted

The correct approach is already partially implemented in plugin_server.py but not currently the default spawned server. Migration from server.py to plugin_server.py would eliminate code duplication and leverage community-maintained abstractions.

# pyvider-rpcplugin Server-Side Support Investigation

This directory contains a comprehensive investigation into whether pyvider-rpcplugin has server-side support equivalent to go-plugin's `plugin.Serve()`.

## Documents in This Investigation

### 1. **EXECUTIVE_SUMMARY.txt** (Quick Read - 8.4 KB)
**Best for**: Quick understanding of findings
- Concise answer to the investigation question
- Key findings summary
- What the current problem is
- Why it matters
- Next steps

**Key Takeaway**: YES - pyvider-rpcplugin has FULL server-side support via `RPCPluginServer` class and `plugin_server()` factory function, but TofuSoup is NOT using it for spawned servers.

---

### 2. **INVESTIGATION_PYVIDER_SERVER_SUPPORT.md** (Detailed Analysis - 15 KB)
**Best for**: Deep understanding of architecture
- Complete architectural breakdown
- How pyvider-rpcplugin works
- What TofuSoup has implemented
- The asymmetry problem
- Evidence and proof

**Sections**:
1. Does pyvider-rpcplugin have server-side support? (YES)
2. Correct server-side architecture (already exists in TofuSoup)
3. Problematic implementation that exists (server.py)
4. Current asymmetric usage pattern
5. How pyvider-rpcplugin server works
6. Proof of full server-side support
7. Current working implementations
8. Key architectural findings

---

### 3. **ARCHITECTURE_COMPARISON.md** (Side-by-Side Code - 12 KB)
**Best for**: Understanding the technical differences
- Code comparisons
- Feature matrix
- Flow diagrams
- Code quality metrics
- Migration paths

**Key Tables**:
- Quick reference comparison (9 dimensions)
- Feature matrix (13 features)
- Code quality metrics (complexity, test coverage)
- Cyclomatic complexity analysis

---

## Investigation Question

> Does pyvider-rpcplugin have SERVER-SIDE support, similar to how go-plugin has `plugin.Serve()`?

## Investigation Answer

**YES - COMPLETE SERVER-SIDE SUPPORT EXISTS**

### Evidence:
1. **RPCPluginServer class** (630 lines)
   - Full go-plugin protocol implementation
   - Located: `pyvider/rpcplugin/server.py`
   - Exports: Yes, in `pyvider/rpcplugin/__init__.py`

2. **plugin_server() factory function** (29 lines)
   - Convenient server instantiation
   - Located: `pyvider/rpcplugin/factories.py`
   - Exports: Yes, in `pyvider/rpcplugin/__init__.py`

3. **Already used correctly in TofuSoup**
   - File: `src/tofusoup/rpc/plugin_server.py` (87 lines)
   - Demonstrates proper usage pattern
   - Status: Defined but NOT the default spawned server

---

## The Problem

TofuSoup has **TWO different implementations**:

1. **plugin_server.py** (CORRECT - Uses abstractions)
   - Uses `pyvider.rpcplugin.factories.plugin_server()`
   - Uses `RPCPluginServer.serve()`
   - Proper abstraction-based approach
   - Status: Exists but not spawned

2. **server.py** (PROBLEMATIC - Manual implementation)
   - Manually constructs handshake (lines 301-327)
   - Manually configures TLS (4 functions)
   - Hardcoded TCP transport
   - Reimplements what RPCPluginServer already does
   - Status: Currently spawned by KVClient

## Current Asymmetry

| Aspect | Client-Side | Server-Side |
|--------|-------------|------------|
| **Uses pyvider abstractions** | YES | NO |
| **Uses manual implementation** | NO | YES |
| **File** | client.py | server.py |
| **Status** | Correct | Problematic |

The client-side properly uses `RPCPluginClient`, but the server-side reimplements what should be abstracted via `RPCPluginServer`.

---

## What Currently Happens

When KVClient needs a Python server:

```bash
# Current (MANUAL)
python /path/to/src/tofusoup/rpc/server.py
  ├─ Creates grpc.Server manually
  ├─ Configures TLS manually (_configure_tls_*)
  ├─ Manually constructs handshake: "1|1|tcp|IP:PORT|grpc|CERT"
  └─ Prints to stdout

# Should Be (ABSTRACTED)
python /path/to/src/tofusoup/rpc/plugin_server.py
  ├─ Calls plugin_server(protocol=..., handler=...)
  ├─ Calls await server.serve()
  └─ Everything handled by pyvider-rpcplugin
```

---

## Key Findings Summary

### pyvider-rpcplugin Server Features
- Full handshake negotiation
- Protocol version negotiation
- Transport negotiation (TCP/Unix)
- Auto-mTLS certificate generation
- Rate limiting
- Health checks
- Shutdown file watching
- Signal handling
- Config integration
- Complete abstraction of go-plugin protocol

### TofuSoup Implementation Status
- Server-side abstractions: ✓ Exist in pyvider-rpcplugin
- TofuSoup using abstractions: ✗ No (uses manual implementation)
- Correct example in TofuSoup: ✓ Yes (plugin_server.py)
- Default spawned server: ✗ Wrong (server.py, not plugin_server.py)

### Architectural Implications
- Code Duplication: TLS, handshake, certificates duplicated
- Maintenance Burden: Manual implementations harder to maintain
- Missing Features: No rate limiting, health checks, advanced transport
- Bug Surface: Manual string parsing prone to errors
- Inconsistent: Client uses abstractions, server doesn't

---

## Migration Recommendation

**Full Migration (Recommended)**:
1. Update KVClient to spawn `plugin_server.py` instead of `server.py`
2. Remove manual TLS/handshake code from `server.py`
3. Keep `server.py` for standalone/testing mode if needed
4. Leverage pyvider-rpcplugin config system
5. Gain access to rate limiting, health checks, shutdown files

**Benefits**:
- 5x less code (327 lines → 0 lines of manual code)
- Single source of truth (pyvider-rpcplugin maintains protocol)
- Better testing (less mocking required)
- Future-proof (integrates with ecosystem)
- Feature-rich (access to rate limiting, health checks, etc.)

---

## File Locations

**Spawned Server** (Current - MANUAL):
- `/Users/tim/code/gh/provide-io/tofusoup/src/tofusoup/rpc/server.py`
- Lines 301-327: Manual handshake construction
- Lines 241-298: Manual TLS configuration

**Reference Implementation** (Correct - ABSTRACTED):
- `/Users/tim/code/gh/provide-io/tofusoup/src/tofusoup/rpc/plugin_server.py`
- Uses pyvider-rpcplugin abstractions
- Proper go-plugin pattern

**Client** (Currently Correct):
- `/Users/tim/code/gh/provide-io/tofusoup/src/tofusoup/rpc/client.py`
- Uses `pyvider.rpcplugin.client.RPCPluginClient`

**pyvider-rpcplugin Server Library**:
- `/Users/tim/.local/share/uv/tools/pyvider-builder/lib/python3.13/site-packages/pyvider/rpcplugin/server.py` (630 lines)
- `/Users/tim/.local/share/uv/tools/pyvider-builder/lib/python3.13/site-packages/pyvider/rpcplugin/factories.py` (178 lines)

---

## How to Use These Documents

### For Quick Understanding:
1. Start with **EXECUTIVE_SUMMARY.txt**
2. Read the "Key Findings" section

### For Technical Details:
1. Read **INVESTIGATION_PYVIDER_SERVER_SUPPORT.md**
2. Focus on sections:
   - "Does pyvider-rpcplugin Have Server-Side Support?"
   - "Correct Server-Side Architecture"
   - "Evidence: How pyvider-rpcplugin Exports Server API"

### For Implementation Understanding:
1. Read **ARCHITECTURE_COMPARISON.md**
2. Focus on sections:
   - "File Comparison"
   - "Feature Matrix"
   - "Current Spawning Flow"

### For Decision-Making:
1. Read **EXECUTIVE_SUMMARY.txt** summary
2. Review **ARCHITECTURE_COMPARISON.md** "Migration Path"
3. Decide on migration strategy

---

## Conclusion

pyvider-rpcplugin **has FULL, COMPLETE SERVER-SIDE SUPPORT** equivalent in scope and capability to go-plugin's plugin.Serve().

The issue is not that the support doesn't exist, but that:
1. TofuSoup doesn't use it for spawned servers
2. TofuSoup reimplements what should be abstracted
3. This creates code duplication and maintenance burden

The solution is to migrate from manual implementation (server.py) to abstraction-based implementation (plugin_server.py), which already exists and correctly demonstrates the pattern.

---

## Investigation Metadata

- **Investigation Date**: 2025-10-31
- **Investigator**: Claude Code
- **Repository**: /Users/tim/code/gh/provide-io/tofusoup
- **Questions Answered**: 4
- **Code Files Examined**: 6
- **pyvider-rpcplugin Files Examined**: 4
- **Total Lines of Evidence**: 1000+

---


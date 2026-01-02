# Stock Service Design Document

## Overview

The Stock service is a multi-language gRPC service designed to test cross-language compatibility without the complexity of plugin handshakes. It extends the simple key-value pattern from kvproto with additional gRPC patterns (streaming, bidirectional) to provide comprehensive testing coverage.

## Motivation

### Current State
- TofuSoup's RPC tests focus on plugin protocol compatibility (go-plugin framework)
- The existing kvproto project tests direct gRPC but lives outside TofuSoup
- Plugin protocol adds complexity when testing basic gRPC interoperability

### Goals
1. Test pure gRPC compatibility across 10+ languages
2. Provide a standard service that exercises all gRPC communication patterns
3. Integrate kvproto's multi-language implementations into TofuSoup
4. Enable testing of pyvider servers in `--force` mode with non-plugin clients

## Architecture

### Service Name: Stock

The name "Stock" works on multiple levels:
- **Soup stock**: The base/foundation of soup (fitting TofuSoup theme)
- **Inventory stock**: Storage metaphor for key-value operations
- **Stock market**: Streaming updates and trading metaphor for bidirectional streams

### Directory Structure

```
tofusoup/
├── conformance/
│   └── stock/              # Stock service conformance tests
│       ├── __init__.py
│       ├── conftest.py
│       ├── matrix_config.py
│       └── souptest_stock_matrix.py
├── stock/                  # All Stock implementations
│   ├── proto/
│   │   └── stock.proto     # Single source of truth
│   ├── go/
│   │   ├── cmd/
│   │   │   ├── client/
│   │   │   └── server/
│   │   ├── go.mod
│   │   └── Makefile
│   ├── python/
│   │   ├── stock_client.py
│   │   ├── stock_server.py
│   │   └── requirements.txt
│   ├── java/
│   │   ├── pom.xml
│   │   └── src/main/java/
│   ├── ruby/
│   ├── rust/
│   ├── csharp/
│   └── ... (other languages)
└── src/tofusoup/
    └── stock/              # Stock CLI integration
        ├── __init__.py
        ├── cli.py          # CLI commands
        └── harness.py      # Build/management logic
```

### Proto Definition

```protobuf
service Stock {
    // Basic KV operations (unary) - backwards compatible
    rpc Get(GetRequest) returns (GetResponse);
    rpc Put(PutRequest) returns (Empty);
    
    // Server streaming - monitor changes
    rpc Monitor(WatchRequest) returns (stream WatchEvent);
    
    // Client streaming - batch operations
    rpc Batch(stream BatchItem) returns (BatchSummary);
    
    // Bidirectional - trading simulation
    rpc Trade(stream TradeOrder) returns (stream TradeFill);
    
    // Status/health check
    rpc Inventory(Empty) returns (InventoryStatus);
}
```

## CLI Design

### Language-First Commands

```bash
# Start servers
soup stock go server --port 50051
soup stock python server --tls-mode auto
soup stock java server --cert-file server.crt

# Run clients
soup stock ruby client get mykey --server localhost:50051
soup stock rust client put mykey "value" --server localhost:50051
soup stock go client monitor "prefix/*" --server localhost:50051

# Convenience shortcuts (defaults to Python)
soup stock get mykey
soup stock put mykey "value"
soup stock inventory
```

### Why Not Under `soup rpc`?

1. **Clear Separation**: 
   - `soup rpc` = Plugin protocol (handshake, broker, stdio)
   - `soup stock` = Direct gRPC (no handshake)

2. **Different Use Cases**:
   - `soup rpc` tests Terraform provider compatibility
   - `soup stock` tests language interoperability

3. **Simpler Mental Model**:
   - Stock is a standalone service, not a variant of RPC

## Implementation Strategy

### Phase 1: Core Languages (Week 1)
- [ ] Python implementation (base reference)
- [ ] Go implementation (performance baseline)
- [ ] Proto compilation setup for all languages

### Phase 2: Migrate kvproto (Week 2)
- [ ] Move existing kvproto implementations
- [ ] Update to use Stock proto definition
- [ ] Standardize CLI interface across languages

### Phase 3: Testing Infrastructure (Week 3)
- [ ] Matrix test configuration
- [ ] Performance benchmarks
- [ ] TLS/mTLS test scenarios

### Phase 4: Additional Languages (Week 4+)
- [ ] Java, Ruby, C#, Rust implementations
- [ ] JavaScript/Node.js, C++, PHP
- [ ] Kotlin, Scala, Swift (stretch goals)

## Testing Matrix

### Dimensions
1. **Client Language**: 10+ implementations
2. **Server Language**: 10+ implementations  
3. **TLS Configuration**: none, server-only, mTLS
4. **Operations**: get/put, streaming, batch, bidirectional

### Example Test Cases
- Python client → Go server (mTLS, streaming)
- Java client → Ruby server (no TLS, batch operations)
- Rust client → Python server (server TLS, bidirectional)

Total potential combinations: 10 × 10 × 3 × 4 = 1,200 tests

### Optimized Test Subsets
- **Quick**: 3 clients × 3 servers × 1 TLS × 2 ops = 18 tests
- **Standard**: 5 clients × 5 servers × 2 TLS × 3 ops = 150 tests
- **Full**: All combinations (weekend run)

## Integration with Existing Systems

### Works With pyvider --force Mode
```bash
# Start pyvider server without handshake
python my_provider.py provide --force --port 50051

# Connect with any Stock client
soup stock java client get tf_resource_123
soup stock go client monitor "tf_state/*"
```

### Comparison with Plugin RPC
| Feature | Plugin RPC (`soup rpc`) | Stock (`soup stock`) |
|---------|------------------------|-------------------|
| Handshake | Required | None |
| Port Negotiation | Dynamic | Fixed |
| Stdio Forwarding | Yes | No |
| Language Support | Go + Python | 10+ languages |
| Use Case | Terraform providers | General gRPC testing |

## Success Metrics

1. **Coverage**: All 10+ languages have working implementations
2. **Compatibility**: 95%+ of cross-language tests pass
3. **Performance**: Benchmark data for each language pair
4. **Adoption**: Stock becomes the standard for gRPC testing in TofuSoup

## Exploratory Extensions

1. **Additional Patterns**:
   - Request deadlines/timeouts
   - Metadata/header propagation
   - Compression testing
   - Load balancing scenarios

2. **Observability**:
   - OpenTelemetry integration
   - Prometheus metrics
   - Distributed tracing

3. **Chaos Testing**:
   - Network delays
   - Partial failures
   - Message corruption

## Conclusion

The Stock service provides a clean, focused way to test gRPC compatibility across languages without the complexity of plugin protocols. By integrating kvproto's work and extending it with additional RPC patterns, TofuSoup gains comprehensive cross-language testing capabilities that complement its existing plugin-focused tests.

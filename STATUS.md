# TofuSoup Stock Service Integration Status

## Overview
This document tracks the integration of kvproto's multi-language gRPC implementations into TofuSoup as the new Stock service.

## Design Phase ✅

- [x] Created design document (`docs/architecture/07-stock-service-design.md`)
- [x] Defined Stock service proto with multiple RPC patterns
- [x] Established directory structure plan
- [x] Designed CLI interface (`soup stock <language> <role>`)

## Proto Definition ✅

- [x] Created `stock.proto` with Stock service definition
- [x] Added backwards-compatible KV operations
- [x] Added streaming operations (Monitor, Batch)
- [x] Added bidirectional operation (Trade)
- [x] Added status/inventory operation

## Directory Structure 🚧

- [x] Created `tofusoup/direct/` directory structure
- [ ] Rename to `tofusoup/stock/` per design doc
- [ ] Move kvproto implementations to new structure
- [ ] Organize by language subdirectories

## Language Implementations 📋

### Core Languages (Priority 1)
- [ ] Python (reference implementation)
  - [ ] Server implementation
  - [ ] Client implementation
  - [ ] CLI wrapper
- [ ] Go (performance baseline)
  - [ ] Server implementation
  - [ ] Client implementation
  - [ ] CLI wrapper
- [ ] Java
  - [ ] Migrate from kvproto
  - [ ] Update to Stock proto
  - [ ] CLI wrapper

### Additional Languages (Priority 2)
- [ ] Ruby (migrate from kvproto)
- [ ] C# (migrate from kvproto)
- [ ] Rust (migrate from kvproto)
- [ ] C++ (migrate from kvproto)
- [ ] Node.js (migrate from kvproto)
- [ ] Kotlin (migrate from kvproto)
- [ ] Scala (migrate from kvproto)

### Stretch Goals (Priority 3)
- [ ] Swift (migrate from kvproto)
- [ ] PHP (migrate from kvproto)
- [ ] Dart (migrate from kvproto)
- [ ] Objective-C (migrate from kvproto)
- [ ] Perl (migrate from kvproto)
- [ ] Clojure (migrate from kvproto)
- [ ] Elixir
- [ ] Haskell
- [ ] Lua

## CLI Integration 🚧

- [x] Created `stock_cli.py` with command structure
- [ ] Integrate into main TofuSoup CLI (`soup stock`)
- [ ] Add to `src/tofusoup/cli.py` entry point
- [ ] Configure binary paths in `soup.toml`
- [ ] Add harness build support

## Build System ❌

- [ ] Update `soup harness` to build Stock implementations
- [ ] Create Makefiles/build scripts for each language
- [ ] Proto compilation setup for all languages
- [ ] Dependency management for each language

## Testing Infrastructure ❌

- [ ] Create `conformance/stock/` directory
- [ ] Write `matrix_config.py` for test combinations
- [ ] Implement `souptest_stock_matrix.py`
- [ ] Add performance benchmarks
- [ ] TLS/mTLS test scenarios

## Certificate Management 📋

- [ ] Decide: Use kvproto's manual certs or pyvider-rpcplugin?
- [ ] Migrate certificate generation scripts if keeping manual
- [ ] Update cert paths in test configurations
- [ ] Document certificate requirements

## Documentation 🚧

- [x] Design document written
- [x] Status document created
- [ ] Update main README.md
- [ ] Add Stock service user guide
- [ ] Document each language's build requirements
- [ ] Migration guide from kvproto

## Migration from kvproto ❌

- [ ] Copy language implementations to `tofusoup/stock/`
- [ ] Update import paths and package names
- [ ] Convert from `kv.proto` to `stock.proto`
- [ ] Standardize CLI arguments across languages
- [ ] Update test scripts

## Integration Points ❌

- [ ] Test with pyvider `--force` mode
- [ ] Verify compatibility with existing RPC tests
- [ ] Add Stock to `soup test all`
- [ ] Performance comparison with plugin RPC

## Estimated Timeline

- **Week 1**: Core languages (Python, Go, Java)
- **Week 2**: Migrate kvproto implementations
- **Week 3**: Testing infrastructure
- **Week 4**: Additional languages and polish

## Next Steps

1. Rename `direct/` to `stock/` per design
2. Start with Python reference implementation
3. Set up proto compilation pipeline
4. Begin kvproto migration

---

*Last Updated: [Current Date]*
*Status: Design Complete, Implementation Pending*
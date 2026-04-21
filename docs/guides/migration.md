# Migration Guide

This guide helps users migrate from older TofuSoup versions to the current unified harness architecture.

## Unified Harness (`soup-go`)

### What Changed

Previously, TofuSoup used separate Go harnesses for each component:
- `go-cty` - CTY operations
- `go-hcl` - HCL parsing
- `go-rpc` - RPC server/client
- `go-wire` - Wire protocol encoding/decoding

**Now**: All functionality is unified in a single `soup-go` harness with subcommands.

### Command Migration

**Old harness commands:**
```bash
# OLD - separate binaries
./bin/go-cty validate-value ...
./bin/go-hcl parse ...
./bin/go-rpc server-start ...
./bin/go-wire encode ...
```

**New harness commands:**
```bash
# NEW - unified soup-go with subcommands
./harnesses/bin/soup-go cty validate-value ...
./harnesses/bin/soup-go hcl parse ...
./harnesses/bin/soup-go rpc server-start ...
./harnesses/bin/soup-go wire encode ...
```

### Harness Management

**Old commands:**
```bash
# OLD
soup harness build go-cty
soup harness build go-hcl go-rpc go-wire
soup harness verify-cli go-cty
```

**New commands:**
```bash
# NEW
soup harness build soup-go
soup harness list
soup harness verify-cli soup-go
```

### Binary Paths

**Old paths:**
```
tofusoup/src/tofusoup/harness/go/bin/go-cty
tofusoup/src/tofusoup/harness/go/bin/go-hcl
tofusoup/src/tofusoup/harness/go/bin/go-rpc
tofusoup/src/tofusoup/harness/go/bin/go-wire
```

**New paths:**
```
harnesses/bin/soup-go
```

### Configuration File Updates

If you have `soup.toml` configurations referencing old harnesses:

**Before:**
```toml
[harness.go.cty]
build_flags = ["-v"]

[harness.go.rpc]
timeout_seconds = 60
```

**After:**
```toml
[harness.go.soup-go]
build_flags = ["-v"]
timeout_seconds = 60
```

### Testing & Scripts

If you have test scripts or CI/CD pipelines using the old harnesses:

**Before:**
```bash
# In test scripts
GO_CTY_BIN="./bin/go-cty"
$GO_CTY_BIN validate-value ...

# In Python tests
harness_path = Path("bin/go-cty")
```

**After:**
```bash
# In test scripts
SOUP_GO_BIN="./harnesses/bin/soup-go"
$SOUP_GO_BIN cty validate-value ...

# In Python tests
harness_path = Path("harnesses/bin/soup-go")
# Use with subcommand: soup-go cty ...
```

## Deprecated Command Removal

### Test Commands

The following test commands have been removed in favor of the unified `soup test` command:

**Old (Deprecated):**
```bash
soup cty test compat
soup rpc test all
soup wire test compat
```

**New (Current):**
```bash
soup test cty
soup test rpc
soup test wire
soup test all  # Run all suites
```

### Why This Change?

The unified `soup test` command:
- Provides consistent interface across all test suites
- Supports better configuration via `soup.toml`
- Enables easier CI/CD integration
- Allows passing pytest arguments directly

### Migration Steps

1. **Update harness builds:**
   ```bash
   soup harness build soup-go
   ```

2. **Update scripts** to use new harness paths

3. **Update test commands** to use `soup test <suite>`

4. **Update `soup.toml`** if you have harness-specific configurations

5. **Verify** everything works:
   ```bash
   soup harness verify-cli soup-go
   soup test all
   ```

## Troubleshooting Migration

### Harness Not Found

**Error:** `harness 'go-cty' not found`

**Solution:**
```bash
# Remove old references, build new harness
soup harness clean --all
soup harness build soup-go
```

### Path Issues

**Error:** `No such file or directory: 'bin/go-cty'`

**Solution:** Update paths to `harnesses/bin/soup-go`

### Configuration Errors

**Error:** `Unknown harness 'go-rpc' in soup.toml`

**Solution:** Update configuration to use `soup-go` instead of individual harnesses

## Benefits of Migration

1. **Simpler Builds**: One harness to build instead of four
2. **Consistent Interface**: All functionality accessible via subcommands
3. **Smaller Footprint**: Single binary vs multiple binaries
4. **Easier Maintenance**: One codebase for all harness functionality
5. **Better Documentation**: Unified documentation and help system

## Getting Help

If you encounter issues during migration:

1. Check this migration guide
2. Review [Troubleshooting](../troubleshooting.md)
3. Check [FAQ](../faq.md)
4. Open an issue on [GitHub](https://github.com/provide-io/tofusoup/issues)

## See Also

- [Configuration Reference](../reference/configuration.md)
- [Test Harness Development](testing/test-harness-development.md)
- [Quick Start Guide](../getting-started/quick-start.md)

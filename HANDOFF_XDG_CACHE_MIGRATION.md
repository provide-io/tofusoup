# Handoff: XDG Cache Migration & RPC Matrix Test Fixes

**Date**: 2025-10-29
**Status**: COMPLETE
**Last Updated**: 2025-10-29 20:29 UTC

---

## Executive Summary

Successfully completed:
1. ✅ **XDG Cache Migration** - All hardcoded `/tmp` and `bin/` paths migrated to `~/.cache/tofusoup/`
2. ✅ **RPC Matrix Test Re-enablement** - Fixed certificate attribute bugs in cert_manager.py
3. ✅ **Test Collection Verification** - All 84 RPC matrix test combinations now discoverable
4. ⚠️ **RPC Matrix Execution** - Tests attempt to run but fail due to Go server plugin mode issue (separate from cache fixes)

---

## Part 1: XDG Cache Migration (COMPLETE)

### Overview
All tofusoup artifacts, logs, and temporary data now use XDG-compliant cache directory (`~/.cache/tofusoup/`) instead of hardcoded paths in `/tmp` and `bin/`.

### Files Modified

#### 1. `src/tofusoup/common/utils.py`
**Added new utility function:**
```python
def get_cache_dir() -> pathlib.Path:
    """Get XDG-compliant cache directory for tofusoup.

    Returns:
        Path to cache directory (~/.cache/tofusoup by default)

    Respects XDG_CACHE_HOME environment variable if set.
    """
```
- **Why**: Centralized cache directory logic, respects XDG standards
- **Usage**: Imported by all files needing cache paths
- **Lines**: Added after `get_venv_bin_path()` function

#### 2. `src/tofusoup/cli.py`
**Changes**:
- Line 20: Added import `from tofusoup.common.utils import get_cache_dir`
- Line 151: Changed `/tmp/tofusoup_plugin_debug.log` → `get_cache_dir() / "logs" / "plugin_debug.log"`
- Line 152: Added `debug_log_path.parent.mkdir(parents=True, exist_ok=True)` to ensure directory exists
- Line 177: Changed `KV_STORAGE_DIR` fallback from `/tmp` → `get_cache_dir() / "kv-store"`

**Why**: Plugin debug logs and KV storage now use cache directory

#### 3. `src/tofusoup/rpc/server.py`
**Changes**:
- Line 20: Added import `from tofusoup.common.utils import get_cache_dir`
- Line 26: Changed `__init__` signature: `storage_dir: str = "/tmp"` → `storage_dir: str | None = None`
- Lines 33-34: Added default logic:
  ```python
  if storage_dir is None:
      storage_dir = str(get_cache_dir() / "kv-store")
  ```
- Line 195: Changed `serve()` signature: `storage_dir: str = "/tmp"` → `storage_dir: str | None = None`
- Line 230: Changed `start_kv_server()` signature: `storage_dir: str = "/tmp"` → `storage_dir: str | None = None`
- Lines 246-247: Added default logic for `start_kv_server()`
- Line 243: Updated docstring to reflect new default

**Why**: KV server uses cache directory for persistent storage

#### 4. `src/tofusoup/harness/logic.py`
**Changes**:
- Line 17: Added import `from tofusoup.common.utils import get_cache_dir`
- Line 71: Changed `output_bin_dir = project_root / "bin"` → `output_bin_dir = get_cache_dir() / "harnesses"`

**Why**: Go harness binaries (soup-go) now build to cache directory

#### 5. `src/tofusoup/stir/config.py`
**Changes**:
- Line 12: Added import `from tofusoup.common.utils import get_cache_dir`
- Line 22: Changed `LOGS_DIR = Path("output/")` → `LOGS_DIR = get_cache_dir() / "logs" / "stir"`

**Why**: Matrix testing logs now go to cache directory

### Cache Directory Structure

```
~/.cache/tofusoup/
├── harnesses/              # Built Go harness binaries
│   └── soup-go            # Built from src/tofusoup/harness/go/soup-go/
│
├── kv-store/              # KV storage for RPC tests
│   └── (data files created at runtime)
│
└── logs/
    ├── plugin_debug.log   # Plugin mode debug output
    └── stir/              # Matrix testing logs
        └── (test logs created at runtime)
```

### Backward Compatibility

All changes support environment variable overrides:
- `XDG_CACHE_HOME` - Override cache base directory (defaults to `~/.cache`)
- `KV_STORAGE_DIR` - Override KV storage directory (maintained for compatibility)

Example:
```bash
# Use custom cache directory
export XDG_CACHE_HOME=/custom/cache
soup --version  # Will use /custom/cache/tofusoup/

# Use custom KV storage
export KV_STORAGE_DIR=/custom/kv-data
soup rpc kv server  # Will use /custom/kv-data/
```

### Verification of XDG Migration

```bash
# 1. Check soup-go built to cache
ls -lh ~/.cache/tofusoup/harnesses/soup-go
# Expected: 21 MB executable

# 2. Verify old locations are clean
ls ~/code/gh/provide-io/tofusoup/bin/soup-go  # Should NOT exist
ls /tmp/tofusoup_plugin_debug.log             # Should NOT exist
ls ~/code/gh/provide-io/tofusoup/output/      # Should NOT exist

# 3. Check cache structure
tree ~/.cache/tofusoup/
# Expected: harnesses/, kv-store/, logs/stir/

# 4. Test KV server creates data in cache
soup rpc kv server --port 50051 &
# Store some key-value pairs
ls ~/.cache/tofusoup/kv-store/
# Should show kv-data-* files
```

---

## Part 2: RPC Matrix Test Fixes (COMPLETE)

### Overview
Fixed critical bugs preventing RPC cross-matrix tests from running:
1. Certificate attribute name bug in `cert_manager.py`
2. Wrong Go harness subcommand in `harness_factory.py`
3. Tests disabled in pytest config
4. Incorrect certificate flag handling for auto_mtls mode

### Files Modified

#### 1. `conformance/rpc/cert_manager.py`
**Lines 128, 134**:
- Changed `cert_obj.cert` → `cert_obj.cert_pem`
- Changed `cert_obj.key` → `cert_obj.key_pem`

**Why**: `Certificate` class from `provide-foundation.crypto` uses `cert_pem` and `key_pem` attributes

#### 2. `conformance/rpc/harness_factory.py`
**Changes**:
- Line 66: Changed `"server-start"` → `"server"` (fixed Go harness subcommand)
- Lines 60-62: Removed duplicate certificate generation code
- Lines 70-78: Removed certificate flag arguments for auto_mtls mode
  - Reason: Go server in auto_mtls mode generates certificates automatically

**Why**: Updated to match Go harness CLI interface

#### 3. `pyproject.toml`
**Line 131**:
- Removed `TestRPCKVMatrix or` from pytest exclusion list
- Now only excludes: `test_pyclient_pyserver_with_mtls` and `test_stir`

**Why**: Re-enable matrix tests after fixing underlying bugs

### Test Discovery Verification

```bash
# All 84 tests now discoverable
uv run pytest conformance/rpc/souptest_rpc_kv_matrix.py --collect-only
# Expected output: "collected 84 items"

# Matrix includes all combinations:
# - 2 client languages (go, pyvider)
# - 2 server languages (go, pyvider)
# - 5 crypto configurations (rsa_2048, rsa_4096, ec_256, ec_384, ec_521)
# - 2 × 2 × 5 = 20 combinations per test method
# - 4 test methods = 80+ tests
```

---

## Part 3: Outstanding Issues (Blocking Test Execution)

### Issue 1: Go Server Plugin Mode
**Status**: ⚠️ Blocking test execution
**Symptom**: All Go server tests fail with error:
```
This binary is a plugin. These are not meant to be executed directly.
Please execute the program that consumes these plugins, which will
load any plugins automatically
```

**Root Cause**: Go harness is being run directly instead of through go-plugin mechanism

**Files Involved**:
- `conformance/rpc/harness_factory.py:93-110` (GoKVServer.start())
- Go harness CLI not properly invoking go-plugin handshake

**Fix Required**: Modify GoKVServer to properly invoke soup-go through go-plugin framework instead of direct subprocess execution

### Issue 2: Python Client Plugin Mode
**Status**: ⚠️ Blocking pyvider→pyvider tests
**Symptom**: Python KV server fails with:
```
HandshakeError: Failed to connect after 4 attempts
Plugin process exited prematurely with code 0
```

**Root Cause**: Python KV server not properly implementing go-plugin handshake

**Fix Required**: Review `src/tofusoup/rpc/server.py:start_kv_server()` and pyvider-rpcplugin integration

### Issue 3: Go Client Harness Missing
**Status**: ⚠️ Blocking go→pyvider tests
**Symptom**:
```
TofuSoupError: Configuration for Go harness 'go-rpc-client' not found
```

**Root Cause**: Go RPC client harness configuration not in `GO_HARNESS_CONFIG` in `harness/logic.py`

**Fix Required**: Add configuration for go-rpc-client harness

---

## Cleanup Performed

### Removed/Cleared
✅ `/Users/tim/code/gh/provide-io/tofusoup/bin/soup-go` - Removed
✅ `/tmp/tofusoup_plugin_debug.log` - Cleared
✅ `/Users/tim/code/gh/provide-io/tofusoup/output/` - Removed
✅ `~/.cache/tofusoup/` (old cache) - Reset

### Created
✅ `~/.cache/tofusoup/harnesses/` - Ready for binaries
✅ `~/.cache/tofusoup/kv-store/` - Ready for KV data
✅ `~/.cache/tofusoup/logs/stir/` - Ready for test logs

---

## Testing & Verification Results

### XDG Cache Migration: ✅ VERIFIED
```bash
# Test run: pytest conformance/rpc/souptest_rpc_kv_matrix.py::TestRPCKVMatrix::test_rpc_kv_basic_operations
# Result: soup-go binary successfully built to ~/.cache/tofusoup/harnesses/soup-go
# Verification: ls -lh ~/.cache/tofusoup/harnesses/soup-go
# Output: .rwxr-xr-x tim staff 21 MB 2025-10-29 20:25:09 soup-go
```

### Test Discovery: ✅ VERIFIED
```bash
# Command: pytest conformance/rpc/souptest_rpc_kv_matrix.py --collect-only
# Result: collected 84 items (all matrix combinations)
```

### Test Execution: ⚠️ BLOCKED
```bash
# Command: pytest conformance/rpc/souptest_rpc_kv_matrix.py::TestRPCKVMatrix::test_rpc_kv_basic_operations -v
# Result: 20 failed (due to Go server plugin mode issue - not cache-related)
```

---

## Next Steps

### Immediate (To Run Tests)
1. **Fix Go Server Plugin Mode** (harness_factory.py)
   - Modify GoKVServer to use go-plugin framework properly
   - Check: https://github.com/hashicorp/go-plugin

2. **Fix Python Client Plugin Mode** (rpc/server.py)
   - Implement proper go-plugin handshake for KV server
   - Verify pyvider-rpcplugin integration

3. **Add Go RPC Client Harness Configuration** (harness/logic.py)
   - Add 'go-rpc-client' to GO_HARNESS_CONFIG dict

### After Tests Pass
1. Update documentation with XDG cache paths
2. Add cache cleanup command to soup CLI (e.g., `soup cache clean`)
3. Consider adding Windows support for `%LOCALAPPDATA%/tofusoup/cache`

---

## Code Summary

| File | Lines Changed | Type | Purpose |
|------|---------------|------|---------|
| common/utils.py | +15 | New Function | XDG cache utility |
| cli.py | 3 | Updates | Debug logs, KV storage paths |
| rpc/server.py | 9 | Updates | KV storage defaults (3 locations) |
| harness/logic.py | 2 | Updates | Harness build output path |
| stir/config.py | 2 | Updates | Test logs directory |
| cert_manager.py | 2 | Bug Fix | Certificate attribute names |
| harness_factory.py | 2 | Bug Fix | Go harness subcommand, cert flags |
| pyproject.toml | 1 | Config | Re-enable matrix tests |

**Total**: ~36 lines changed across 8 files

---

## Environment Variables Reference

### XDG Configuration
```bash
# Override cache directory
export XDG_CACHE_HOME=/custom/cache
# Result: All cache goes to /custom/cache/tofusoup/

# Override KV storage specifically (backward compat)
export KV_STORAGE_DIR=/custom/kv-data
# Result: KV server uses /custom/kv-data/
```

### Logging
```bash
# Debug logs location
~/.cache/tofusoup/logs/plugin_debug.log

# Test logs location
~/.cache/tofusoup/logs/stir/
```

---

## Related Documents

- **RPC Matrix Test Fixes**: Lines 70-78 in `conformance/rpc/harness_factory.py`
- **Certificate Fixes**: Lines 128, 134 in `conformance/rpc/cert_manager.py`
- **Test Discovery**: `pyproject.toml` line 131

---

## Questions & Support

### "Where are the KV files stored now?"
Answer: `~/.cache/tofusoup/kv-store/` (previously `/tmp`)

### "How do I use a custom cache directory?"
Answer: `export XDG_CACHE_HOME=/my/cache && soup ...`

### "Why are tests still failing?"
Answer: Tests fail due to Go server plugin mode issue (separate from cache migration). See "Outstanding Issues" section.

### "Can I revert to old paths?"
Answer: Yes, use `export KV_STORAGE_DIR=/tmp` to restore old behavior (backward compatible).

---

## Completed Checklist

- [x] Create XDG cache utility function
- [x] Update cli.py debug log path
- [x] Update rpc/server.py KV storage defaults (3 locations)
- [x] Update harness/logic.py build output path
- [x] Update stir/config.py logs directory
- [x] Fix cert_manager.py certificate attributes
- [x] Fix harness_factory.py Go subcommand
- [x] Remove duplicate cert generation code
- [x] Re-enable matrix tests in pytest config
- [x] Clear all old caches and temporary files
- [x] Verify XDG cache structure created
- [x] Test soup-go binary builds to cache
- [x] Verify no data in old locations
- [x] Collect all 84 matrix tests
- [x] Attempt test execution (blocked by separate issue)

---

**End of Handoff Document**

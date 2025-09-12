# Conformance Test Status

## Overview

This document tracks the status of conformance tests after migrating from separate harnesses (go-cty, go-hcl, go-wire) to the unified soup-go implementation.

## Test Results Summary

As of the latest run:
- **31 passed** ✅
- **11 failed** ❌  
- **24 skipped** ⏭️
- **85 deselected**

## Known Issues

### 1. HCL Error Handling

**Issue**: soup-go returns exit code 0 even for parse errors, with errors in JSON output
- Test expects: Exit code 1 for syntax errors
- soup-go returns: Exit code 0 with `{"success": false, "errors": [...]}`

**Affected tests**:
- `test_hcl_cli_parse[parse_syntax_error-soup-go]`

### 2. Wire Protocol Format Differences

**Issue**: The old go-wire harness used base64 encoding, soup-go uses raw binary/msgpack
- Tests expect: Base64-encoded wire format
- soup-go provides: Raw msgpack bytes

**Affected tests**:
- `test_wire_cli_encode_simple_string`
- `test_wire_cli_decode_simple_string`

### 3. Command Structure Changes

All commands now require the subcommand prefix:
- Old: `go-cty validate ...`
- New: `soup-go cty validate-value ...`

- Old: `go-hcl parse ...`
- New: `soup-go hcl parse ...`

- Old: `go-wire encode ...`
- New: `soup-go wire encode ...`

## Migration Notes

### No Backward Compatibility

Per user request, backward compatibility aliases have been removed. All tests must use soup-go directly with the appropriate subcommands.

### Environment Variables

CTY test suite environment variables are properly configured via `conformance/cty/conftest.py` which loads settings from `soup.toml`:
- `TOFUSOUP_TEST_DEFAULT_ENV`
- `TOFUSOUP_CTY_SUITE_ENV`

## Recommendations

1. **Exit Code Behavior**: Consider whether soup-go should return non-zero exit codes for errors to match typical CLI behavior, or if tests should be updated to check JSON success field.

2. **Wire Format**: Decide on standard encoding (raw bytes vs base64) for wire protocol operations.

3. **Test Updates**: Continue updating remaining tests to match soup-go's actual behavior as the reference implementation.
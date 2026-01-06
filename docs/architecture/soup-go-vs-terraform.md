# soup-go vs Terraform: Implementation Differences

## Overview

**soup-go does NOT implement CTY/HCL exactly as Terraform does**. It's a testing harness that exposes the underlying libraries for cross-language compatibility testing, not a Terraform clone.

## Key Differences

### 1. ❌ **Error Handling**

| Aspect | Terraform | soup-go |
|--------|-----------|---------|
| HCL parse errors | Exit code 2 | Exit code 0 + JSON error |
| Error output | Formatted text to stderr | JSON to stdout |
| Error display | Human-readable with line numbers | Machine-readable JSON |

**Example:**
```bash
# Terraform with bad HCL
$ terraform fmt bad.tf
Error: Invalid multi-line string
  on bad.tf line 2...
$ echo $?
2

# soup-go with bad HCL
$ soup-go hcl parse bad.hcl
{"success": false, "errors": [...]}
$ echo $?
0
```

### 2. ❌ **Output Format**

| Aspect | Terraform | soup-go |
|--------|-----------|---------|
| Success output | Direct output | Wrapped in JSON |
| Format | Various (HCL, JSON, text) | Always JSON with metadata |
| Structure | Command-specific | Consistent `{success, body}` |

### 3. ❌ **CLI Structure**

| Aspect | Terraform | soup-go |
|--------|-----------|---------|
| Commands | Domain-specific (plan, apply) | Library-exposing (cty, hcl) |
| Purpose | Infrastructure management | Testing & validation |
| CTY access | Internal only | Direct CLI commands |
| HCL access | Via validate/fmt | Direct parse command |

### 4. ✅ **CTY Unknown Value Handling** (Matches!)

This is where soup-go DOES match Terraform exactly:

- **Cannot marshal unknown values to JSON** ✅
- **Unknown values only work in MessagePack** ✅
- **Returns "value is not known" error** ✅

```go
// Both Terraform and soup-go will fail here:
unknownVal := cty.UnknownVal(cty.String)
_, err := ctyjson.Marshal(unknownVal, cty.String)
// err: "value is not known"
```

### 5. ❌ **Library Usage Intent**

| Aspect | Terraform | soup-go |
|--------|-----------|---------|
| go-cty usage | Internal state/plan management | Direct value manipulation |
| HCL usage | Configuration parsing | Generic HCL parsing |
| Wire protocol | Internal plugin communication | Exposed for testing |
| MessagePack | Internal serialization | Exposed for cross-language tests |

## Why These Differences Exist

### soup-go's Purpose
- **Testing harness** for cross-language compatibility
- **Direct library access** for validation
- **Machine-readable output** for test automation
- **Consistent JSON interface** for programmatic use

### Terraform's Purpose
- **Infrastructure management** tool
- **Human-friendly** CLI interface
- **Domain-specific** operations
- **Libraries are implementation details**, not exposed

## What This Means

1. **soup-go is NOT a drop-in replacement for Terraform commands**
2. **soup-go exposes lower-level operations that Terraform hides**
3. **The only "exact" match is the core library behavior** (like CTY unknown handling)
4. **CLI behavior, error codes, and output formats are intentionally different**

## Recommendations

If exact Terraform behavior is needed:

1. **For error codes**: soup-go should be updated to return non-zero exit codes on errors
2. **For output format**: Remove the JSON wrapper or add a `--raw` flag
3. **For CLI structure**: This is fundamental to soup-go's purpose and should remain different

## Conclusion

soup-go uses the same underlying HashiCorp libraries (go-cty, hcl/v2) as Terraform, ensuring **library-level compatibility**, but wraps them in a **different CLI interface** designed for testing rather than infrastructure management.
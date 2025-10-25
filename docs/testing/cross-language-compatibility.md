# Cross-Language Compatibility Testing

This document describes how to run and verify cross-language compatibility between the Python `soup` CLI and the Go `soup-go` harness, ensuring that data structures (CTY values, HCL, wire protocol) can be correctly exchanged between implementations.

## Prerequisites

### 1. Build the Go Harness

The `soup-go` binary must be built before running tests:

```bash
cd src/tofusoup/harness/go/soup-go
go build -o $TOFUSOUP_ROOT/bin/soup-go .
```

The binary will be placed in `/Users/tim/code/gh/provide-io/tofusoup/bin/soup-go`.

### 2. Python Environment

Ensure the Python environment is activated with all dependencies:

```bash
uv sync  # Sets up .venv with all dependencies
```

## Running Cross-Language Tests

### CTY Compatibility Tests

The primary cross-language compatibility tests are in `conformance/cty/souptest_cty_interop.py`.

#### Run all CTY compatibility tests:
```bash
pytest conformance/cty/souptest_cty_interop.py -v
```

#### Run specific test cases:
```bash
# Test a specific case (e.g., string handling)
pytest conformance/cty/souptest_cty_interop.py -k "string_simple" -v

# Test unknown value handling (will be skipped for JSON input)
pytest conformance/cty/souptest_cty_interop.py -k "unknown" -v
```

## Test Architecture

### Test Flow

The cross-language tests verify bidirectional compatibility:

1. **Python → Go → Python**: Python creates fixtures, Go processes them, Python validates
2. **Go → Python → Go**: Go creates fixtures, Python processes them, Go validates

### Test Cases

The test suite covers:
- **Basic types**: strings, numbers, booleans
- **Null values**: Proper null handling across languages
- **Unknown values**: MessagePack-only (JSON not supported by go-cty)
- **Collections**: Lists, sets, maps
- **Complex types**: Objects, tuples, nested structures
- **Dynamic types**: Dynamic pseudo-type wrapping

### Important Limitations

#### Unknown Values and JSON

**go-cty (and Terraform) CANNOT handle unknown values in JSON format**. This is a fundamental limitation:

- ❌ JSON → Unknown → Go: Will fail with "value is not known"
- ✅ MessagePack → Unknown → Go: Works correctly
- ✅ Go → Unknown → MessagePack: Works correctly
- ❌ Go → Unknown → JSON: Will fail with "value is not known"

Tests involving unknown values through JSON are automatically skipped.

## Manual Verification

### CTY Operations

#### Test basic conversion:
```bash
# JSON to MessagePack
echo '"hello"' | soup-go cty convert - - \
  --input-format json \
  --output-format msgpack \
  --type '"string"' | xxd

# MessagePack roundtrip
echo '"test"' | soup-go cty convert - - \
  --input-format json \
  --output-format msgpack \
  --type '"string"' | \
soup-go cty convert - - \
  --input-format msgpack \
  --output-format json \
  --type '"string"'
```

#### Test validation:
```bash
# Validate a value
soup-go cty validate-value '"hello"' --type '"string"'

# Should output: "Validation Succeeded"
```

### HCL Parsing

#### Create a test HCL file:
```bash
cat > /tmp/test.hcl << 'EOF'
resource "example" "test" {
  name = "hello"
  count = 42
}
EOF
```

#### Parse with soup-go:
```bash
soup-go hcl parse /tmp/test.hcl | python3 -m json.tool
```

Expected output:
```json
{
    "body": {
        "blocks": [
            {
                "body": {
                    "count": 42,
                    "name": "hello"
                },
                "labels": ["example", "test"],
                "type": "resource"
            }
        ]
    },
    "success": true
}
```

#### Validate HCL syntax:
```bash
soup-go hcl validate /tmp/test.hcl
```

### Wire Protocol

#### Test encoding/decoding:
```bash
# JSON to MessagePack wire format
echo '{"key": "value"}' | soup-go wire encode - - \
  --input-format json \
  --output-format msgpack | xxd

# With CTY type awareness
echo '"hello"' | soup-go wire encode - - \
  --input-format json \
  --output-format msgpack \
  --type '"string"' | xxd
```

## Debugging Failed Tests

### 1. Check Binary Version

Ensure soup-go is up to date:
```bash
soup-go --version
# Should show: 0.1.0 or later
```

### 2. Verbose Logging

Run soup-go with verbose logging:
```bash
soup-go --log-level debug cty convert - - \
  --input-format json \
  --output-format msgpack \
  --type '"string"' <<< '"test"'
```

### 3. Check MessagePack Formats

Python and Go use slightly different MessagePack extension formats for unknown values:
- Python: `c70000` (fixext2)
- Go: `d40000` (fixext1)

Both formats are interoperable and correctly handled by both implementations.

### 4. Common Issues

#### "value is not known" Error
This occurs when trying to convert unknown values through JSON. This is expected behavior matching Terraform. Use MessagePack for unknown values.

#### "unknown flag" Error
The soup-go binary is outdated. Rebuild it:
```bash
cd src/tofusoup/harness/go/soup-go
go build -o $TOFUSOUP_ROOT/bin/soup-go .
```

## Continuous Integration

For CI/CD pipelines, ensure:

1. Go is installed (version 1.21+)
2. Build soup-go before running tests:
   ```bash
   make -C src/tofusoup/harness/go/soup-go build
   ```
3. Run the test suite:
   ```bash
   pytest conformance/cty/souptest_cty_interop.py --tb=short
   ```

## Reference Implementation

The Go implementation (`soup-go`) serves as the **reference implementation** that exactly matches Terraform's behavior. No workarounds or Python-specific accommodations should be made in the Go code. Instead, Python tests should adapt to Go/Terraform's limitations (e.g., skipping unknown value tests for JSON input).
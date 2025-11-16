# Working with Wire Protocol

This guide covers TofuSoup's wire protocol utilities for encoding and decoding Terraform's binary protocol format.

## Overview

The Terraform wire protocol is the binary format used for communication between Terraform and providers. It uses MessagePack encoding with Base64 wrapping for transmission.

TofuSoup provides tools to:
- Encode JSON values to wire format
- Decode wire format back to JSON
- Validate cross-language compatibility
- Debug protocol issues

## Wire Protocol Format

The wire format consists of:
1. **MessagePack encoding**: Binary serialization of CTY values
2. **Base64 encoding**: ASCII-safe transport encoding
3. **Type information**: Preserved through encoding/decoding

## Basic Usage

### Encoding to Wire Format

Convert JSON to wire format:

```bash
# Create a JSON value
echo '{"value": "hello", "type": "string"}' > input.json

# Encode to wire format
soup wire encode input.json output.tfw.b64

# View the encoded output
cat output.tfw.b64
```

### Decoding from Wire Format

Convert wire format back to JSON:

```bash
# Decode wire format
soup wire decode output.tfw.b64 decoded.json

# Verify it matches the original
diff input.json decoded.json
```

## Working with Complex Types

### Objects

```bash
cat > object.json <<EOF
{
  "value": {
    "name": "example",
    "count": 42,
    "enabled": true
  },
  "type": {
    "object": {
      "name": "string",
      "count": "number",
      "enabled": "bool"
    }
  }
}
EOF

soup wire encode object.json object.tfw.b64
soup wire decode object.tfw.b64 object_decoded.json
```

### Lists

```bash
cat > list.json <<EOF
{
  "value": ["one", "two", "three"],
  "type": {"list": "string"}
}
EOF

soup wire encode list.json list.tfw.b64
```

### Maps

```bash
cat > map.json <<EOF
{
  "value": {"key1": "value1", "key2": "value2"},
  "type": {"map": "string"}
}
EOF

soup wire encode map.json map.tfw.b64
```

### Dynamic Types

```bash
cat > dynamic.json <<EOF
{
  "value": "any value",
  "type": "dynamic"
}
EOF

soup wire encode dynamic.json dynamic.tfw.b64
```

## Cross-Language Compatibility Testing

Verify that Python and Go implementations produce identical wire format:

```bash
# Run wire protocol conformance tests
soup test wire

# Run with verbose output
soup test wire -v
```

The tests validate:
- ✅ Encoding produces identical binary output
- ✅ Decoding recovers exact original values
- ✅ Type information is preserved
- ✅ Edge cases are handled correctly

## Debugging Protocol Issues

### View Wire Format as Hex

```bash
# Encode to wire format
soup wire encode input.json output.tfw.b64

# Decode Base64 and view as hex
base64 -d output.tfw.b64 | xxd
```

### Compare Python vs Go Encoding

```bash
# Using Python implementation
soup wire encode --implementation python input.json python.tfw.b64

# Using Go harness
./bin/soup-go wire encode input.json go.tfw.b64

# Compare binary output
diff python.tfw.b64 go.tfw.b64
```

## Common Issues

### Binary Mismatch Errors

If you see "Binary mismatch" in conformance tests:

1. Check input format is valid
2. Verify type specifications are correct
3. Review MessagePack encoding differences
4. Check for float precision issues

### Type Preservation

Ensure type information is included:

```json
{
  "value": 42,
  "type": "number"  // Required!
}
```

Without type info, encoding may fail or produce incorrect results.

### Null vs Unknown

CTY distinguishes between:
- **Null**: Explicitly null value
- **Unknown**: Value not yet known (during plan)

```json
// Null value
{"value": null, "type": "string"}

// Unknown value
{"value": null, "type": "string", "unknown": true}
```

## Integration with Pyvider

When building Terraform providers with Pyvider:

```python
from pyvider.wire import encode_value, decode_value
from pyvider.cty import Value, Type

# Create a CTY value
value = Value.from_json({"name": "example"})
type_spec = Type.object({"name": Type.string()})

# Encode to wire format
wire_bytes = encode_value(value, type_spec)

# Decode from wire format
decoded_value = decode_value(wire_bytes, type_spec)
```

## Advanced Usage

### Custom MessagePack Options

For debugging, you can work directly with MessagePack:

```python
import msgpack
from pathlib import Path

# Read wire format
with open("output.tfw.b64", "r") as f:
    import base64
    wire_bytes = base64.b64decode(f.read())

# Unpack MessagePack
data = msgpack.unpackb(wire_bytes, raw=False)
print(data)
```

### Performance Testing

Benchmark encoding/decoding performance:

```bash
# Time encoding operation
time for i in {1..1000}; do
  soup wire encode input.json output.tfw.b64
done

# Compare Python vs Go performance
pytest conformance/wire/test_performance.py
```

## Reference

- [Wire Protocol Details](../../architecture/05-wire-protocol-details/)
- [CTY and HCL Tools](03-using-cty-and-hcl-tools/)
- [Conformance Testing](../testing/01-running-conformance-tests/)
- [Pyvider Wire Documentation](https://github.com/provide-io/pyvider)

## Next Steps

- Run wire protocol conformance tests
- Integrate wire encoding in your provider
- Debug any binary mismatch issues
- Contribute test cases for edge cases

# Guide: Using CTY and HCL Tools

TofuSoup provides powerful command-line utilities for inspecting, converting, and validating CTY and HCL data formats.

## CTY Utilities (`soup cty`)

### View Data Structure

To view the CTY structure of a JSON, Msgpack, or HCL data file, use `soup cty view`. The output is a rich, colorized tree that shows the inferred CTY type and value.

```bash
soup cty view data.json
soup cty view config.tfvars --format hcl
```

### Convert Between Formats

To convert files between CTY-compatible JSON and Msgpack, use `soup cty convert`.

```bash
# Convert JSON to MessagePack
soup cty convert input.json output.msgpack
```

### Validate a Value Against a Type

You can validate a CTY value (as a JSON string) against a CTY type string using the `soup-go` harness. This is useful for checking type compatibility.

```bash
# Validate a simple string
soup cty validate-value '"hello"' --type-string string

# Validate a list of numbers
soup cty validate-value '' --type-string "list(number)"

# Validate an object
soup cty validate-value '{"name":"tofu","age":1}' --type-string "object({name=string,age=number})"
```

## HCL Utilities (`soup hcl`)

### View HCL as CTY

To parse an HCL file (like a `.tf` or `.tfvars` file) and display its structure as a CTY representation, use `soup hcl view`.

```bash
soup hcl view main.tf
```

### Convert HCL to JSON or Msgpack

To convert an HCL file to a more portable format, use `soup hcl convert`. This implicitly uses CTY as the intermediate representation.

```bash
# Convert HCL to JSON
soup hcl convert network.tf network.json
```

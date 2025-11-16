# Quick Start

Get up and running with TofuSoup in minutes.

## Prerequisites

- TofuSoup installed (see [Installation](installation/))
- Python 3.11+
- Go 1.21+ (for harness operations)

## Your First TofuSoup Commands

### 1. Check Installation

```bash
soup --version
```

Expected output:
```
soup, version 0.0.11
```

### 2. Explore Available Commands

```bash
soup --help
```

You'll see commands organized by functionality:
- `cty` - CTY operations
- `hcl` - HCL operations
- `wire` - Wire protocol operations
- `rpc` - RPC testing
- `test` - Conformance tests
- `stir` - Matrix testing
- `registry` - Registry operations
- `harness` - Test harness management

### 3. Work with CTY Values

Create a simple JSON file:

```bash
echo '{"value": "hello", "type": "string"}' > test.json
```

View it as a CTY structure:

```bash
soup cty view test.json
```

### 4. Test Wire Protocol Encoding

Encode a value to Terraform's wire format:

```bash
soup wire encode test.json test.tfw.b64
```

Decode it back:

```bash
soup wire decode test.tfw.b64 decoded.json
cat decoded.json
```

### 5. Run Conformance Tests

Run CTY conformance tests:

```bash
soup test cty
```

This validates that Python and Go implementations produce identical results.

### 6. Build a Test Harness

List available harnesses:

```bash
soup harness list
```

Build the Go harness:

```bash
soup harness build soup-go
```

### 7. Matrix Testing with Stir

If you have Terraform test cases:

```bash
# Create a test directory
mkdir -p my_tests/basic
cd my_tests/basic

# Create main.tf
cat > main.tf <<EOF
terraform {
  required_version = ">= 1.0"
}

output "test" {
  value = "hello world"
}
EOF

# Run tests
cd ..
soup stir basic/
```

## Common Workflows

### Testing a Provider Across Versions

```bash
# Configure matrix in soup.toml
cat > soup.toml <<EOF
[workenv.matrix.versions]
terraform = ["1.5.7", "1.6.0"]
tofu = ["1.8.0", "1.9.0"]
EOF

# Run matrix tests
soup stir my_provider_tests/ --matrix
```

### Validating CTY Compatibility

```bash
# Test Python implementation against Go reference
soup test cty -v

# Check wire protocol compatibility
soup test wire -v
```

### Working with HCL

```bash
# View HCL structure
soup hcl view main.tf

# Convert HCL to JSON
soup hcl convert main.tf main.json
```

### Registry Operations

```bash
# Search for a provider
soup registry search provider aws

# Get provider details
soup registry info hashicorp/aws

# Launch interactive browser
soup sui
```

## Configuration

Create `soup.toml` in your project:

```toml
[global_settings]
default_python_log_level = "INFO"

[harness_defaults.go]
build_flags = ["-v"]

[workenv.matrix.versions]
terraform = ["1.6.0"]
tofu = ["1.8.0"]
```

See [Configuration Reference](../reference/configuration/) for all options.

## Next Steps

### Learn Core Concepts
- [Architecture](../core-concepts/architecture/)
- [Conformance Testing](../core-concepts/conformance-testing/)

### Follow Detailed Guides
- [Using CTY and HCL Tools](../guides/cli-usage/03-using-cty-and-hcl-tools/)
- [Wire Protocol Operations](../guides/cli-usage/wire-protocol/)
- [Running Conformance Tests](../guides/testing/01-running-conformance-tests/)
- [Matrix Testing](../guides/cli-usage/matrix-testing/)

### Reference Documentation
- [API Reference](../reference/api/index/)
- [Configuration](../reference/configuration/)
- [Compatibility Matrix](../reference/compatibility-matrix/)

## Getting Help

- **CLI Help**: `soup <command> --help`
- **[FAQ](../faq/)**: Frequently asked questions
- **[Troubleshooting](../troubleshooting/)**: Common issues and solutions
- **[GitHub Issues](https://github.com/provide-io/tofusoup/issues)**: Report bugs or request features

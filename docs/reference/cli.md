# CLI Command Reference

This page provides a complete reference for all TofuSoup CLI commands.

## Global Options

```console
$ soup --help
$ soup --version
```

## CTY Commands

### soup cty view

View and display CTY structures:

```console
$ soup cty view data.json
# Displays CTY structure as a tree

$ soup cty view data.msgpack
# Works with MessagePack files

$ soup cty view --format json data.hcl
# Convert HCL to JSON on display
```

### soup cty convert

Convert between CTY formats:

```console
$ soup cty convert input.json output.msgpack
# JSON to MessagePack

$ soup cty convert input.msgpack output.json
# MessagePack to JSON

$ soup cty convert input.hcl output.json
# HCL to JSON
```

### soup cty benchmark

Benchmark CTY operations:

```console
$ soup cty benchmark encode --iterations 1000
# Benchmark encoding performance

$ soup cty benchmark decode --format msgpack
# Benchmark decoding performance
```

## HCL Commands

### soup hcl view

Parse and display HCL structure:

```console
$ soup hcl view main.tf
# Display HCL file structure

$ soup hcl view --tree main.tf
# Tree visualization

$ soup hcl view --json main.tf
# Output as JSON
```

### soup hcl convert

Convert HCL to other formats:

```console
$ soup hcl convert config.hcl config.json
# HCL to JSON

$ soup hcl convert config.hcl config.msgpack
# HCL to MessagePack

$ soup hcl convert --pretty config.hcl config.json
# Pretty-printed JSON output
```

## Wire Protocol Commands

### soup wire encode

Encode data to Terraform wire format:

```console
$ soup wire encode value.json value.tfw.b64
# Encode JSON to wire format (MessagePack + Base64)

$ soup wire encode --input-format json value.json value.tfw
# Encode without Base64 wrapping

$ soup wire encode --msgpack-only value.json value.msgpack
# MessagePack only, no Base64
```

### soup wire decode

Decode wire format to JSON:

```console
$ soup wire decode value.tfw.b64 value.json
# Decode wire format to JSON

$ soup wire decode --output-format msgpack value.tfw.b64 value.msgpack
# Decode to MessagePack

$ soup wire decode --no-base64 value.tfw value.json
# Decode MessagePack without Base64 layer
```

## RPC Commands

### soup rpc kv server

Start an RPC key-value server:

```console
$ soup rpc kv server
# Start server with default settings

$ soup rpc kv server --port 5050
# Custom port

$ soup rpc kv server --tls-mode auto
# Enable automatic mTLS

$ soup rpc kv server --tls-mode auto --tls-key-type rsa
# Use RSA keys for TLS

$ soup rpc kv server --tls-mode auto --tls-key-type ec --tls-curve secp384r1
# Use EC keys with specific curve
```

### soup rpc kv client

Connect to RPC server and perform operations:

```console
$ soup rpc kv put mykey "hello world"
# Store a key-value pair

$ soup rpc kv get mykey
# Retrieve a value

$ soup rpc kv delete mykey
# Delete a key

$ soup rpc kv list
# List all keys
```

### soup rpc kv test

Test RPC functionality:

```console
$ soup rpc kv test
# Run basic RPC tests

$ soup rpc kv test --server-path ./soup-go
# Test with specific server binary

$ soup rpc kv test --crypto-config config1
# Test with specific crypto configuration
```

## Test Commands

### soup test

Run conformance test suites:

```console
$ soup test all
# Run all conformance tests

$ soup test cty
# Run only CTY tests

$ soup test hcl
# Run only HCL tests

$ soup test wire
# Run only wire protocol tests

$ soup test rpc
# Run only RPC tests

$ soup test cty -v
# Verbose output

$ soup test all --parallel
# Run tests in parallel

$ soup test rpc --markers "not slow"
# Run with pytest markers
```

## Stir Commands (Matrix Testing)

### soup stir

Run matrix tests across multiple tool versions:

```console
$ soup stir tests/stir_cases
# Run integration tests

$ soup stir tests/stir_cases --matrix
# Run across all configured tool versions

$ soup stir tests/stir_cases --parallel 4
# Parallel execution with 4 jobs

$ soup stir tests/stir_cases --timeout 30
# 30-minute timeout

$ soup stir tests/stir_cases --tools terraform:1.5.0,opentofu:1.6.0
# Test with specific tool versions
```

**Note**: Matrix testing requires the optional `wrknv` package. Install separately: `uv pip install -e /path/to/wrknv`

## Registry Commands

### soup registry search

Search for providers and modules:

```console
$ soup registry search provider aws
# Search for AWS provider

$ soup registry search module vpc
# Search for VPC modules

$ soup registry search provider aws --limit 20
# Limit results

$ soup registry search provider --namespace hashicorp
# Search within specific namespace
```

### soup registry info

Get detailed information about a provider:

```console
$ soup registry info hashicorp/aws
# Provider details

$ soup registry info hashicorp/aws --version 5.0.0
# Specific version information

$ soup registry info hashicorp/aws --docs
# Include documentation URLs
```

### soup registry versions

List available versions:

```console
$ soup registry versions hashicorp/aws
# List all AWS provider versions

$ soup registry versions hashicorp/aws --latest
# Show only latest version
```

### soup sui

Launch interactive TUI browser:

```console
$ soup sui
# Launch interactive browser

$ soup sui --provider aws
# Start with AWS provider search

$ soup sui --cache-dir ~/.cache/soup
# Custom cache directory
```

## Harness Commands

### soup harness list

List available test harnesses:

```console
$ soup harness list
# List all harnesses

$ soup harness list --detailed
# Show build status and versions
```

### soup harness build

Build Go test harnesses:

```console
$ soup harness build soup-go
# Build specific harness

$ soup harness build --all
# Build all harnesses

$ soup harness build soup-go --force
# Force rebuild

$ soup harness build --parallel
# Build harnesses in parallel
```

### soup harness verify-cli

Verify harness CLI functionality:

```console
$ soup harness verify-cli soup-go
# Test soup-go harness

$ soup harness verify-cli --all
# Verify all harnesses

$ soup harness verify-cli soup-go --verbose
# Detailed verification output
```

### soup harness clean

Clean harness build artifacts:

```console
$ soup harness clean
# Clean all harnesses

$ soup harness clean soup-go
# Clean specific harness

$ soup harness clean --cache
# Also clean cache directories
```

## Configuration

### soup config show

Display current configuration:

```console
$ soup config show
# Show all configuration

$ soup config show --section harness_defaults
# Show specific section

$ soup config show --format json
# JSON output
```

### soup config validate

Validate soup.toml configuration:

```console
$ soup config validate
# Validate default config file

$ soup config validate --file custom.toml
# Validate specific file
```

## Environment Variables

TofuSoup recognizes these environment variables:

### Logging
- `LOG_LEVEL` - Set log level (DEBUG, INFO, WARNING, ERROR)
- `PROVIDE_LOG_LEVEL` - Foundation logging level

### RPC
- `KV_STORAGE_DIR` - Storage directory for KV server
- `PLUGIN_AUTO_MTLS` - Enable automatic mTLS (true/false)
- `PLUGIN_MAGIC_COOKIE_KEY` - Magic cookie key for servers
- `BASIC_PLUGIN` - Magic cookie value

### Testing
- `PYTEST_CURRENT_TEST` - Automatically set by pytest
- `SOUP_TEST_PARALLEL` - Enable parallel test execution

### Configuration
- `SOUP_CONFIG_FILE` - Path to soup.toml
- `SOUP_CACHE_DIR` - Cache directory location

## Exit Codes

TofuSoup uses standard exit codes:

- `0` - Success
- `1` - General error
- `2` - Command line syntax error
- `3` - Configuration error
- `4` - Test failure
- `5` - Build failure

## Common Patterns

### Testing Workflow

```console
# 1. Build harnesses
$ soup harness build --all

# 2. Run conformance tests
$ soup test all -v

# 3. Test specific functionality
$ soup test rpc --markers "not slow"

# 4. Run matrix tests (if wrknv available)
$ soup stir tests/stir_cases --matrix
```

### Development Workflow

```console
# 1. Clone and setup
$ git clone https://github.com/provide-io/tofusoup.git
$ cd tofusoup
$ uv sync

# 2. Run tests
$ uv run pytest

# 3. Build harnesses
$ soup harness build --all

# 4. Run CLI tests
$ soup test all
```

### RPC Testing Workflow

```console
# 1. Start server in one terminal
$ soup rpc kv server --tls-mode auto

# 2. Test in another terminal
$ soup rpc kv put test-key "test value"
$ soup rpc kv get test-key

# 3. Run automated tests
$ soup test rpc -v
```

## Getting Help

For any command, use `--help`:

```console
$ soup --help
$ soup cty --help
$ soup rpc --help
$ soup test --help
```

For more information, see:

- [Testing Guide](../guides/testing/01-running-conformance-tests.md)
- [Configuration Reference](configuration.md)

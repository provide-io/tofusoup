# Test Harnesses

This directory contains built test harness binaries used for cross-language conformance testing.

## Build Artifacts

The `bin/` subdirectory contains compiled Go binaries:

```
harnesses/
└── bin/
    └── soup-go    # Unified polyglot harness (generated during build)
```

**Important**: The `bin/` directory and its contents are build artifacts, not tracked in version control.

## Building Harnesses

To build harnesses:

```bash
# Build all harnesses
soup harness build --all

# Build specific harness
soup harness build soup-go

# List available harnesses
soup harness list
```

## Harness Binaries

### soup-go

The unified Go harness providing:
- CTY operations (`soup-go cty ...`)
- HCL parsing (`soup-go hcl ...`)
- Wire protocol (`soup-go wire ...`)
- RPC server/client (`soup-go rpc ...`)

#### Usage Examples

```bash
# CTY validation
./harnesses/bin/soup-go cty validate-value '"hello"' --type-string string

# HCL parsing
./harnesses/bin/soup-go hcl parse config.tf

# Wire protocol encoding
./harnesses/bin/soup-go wire encode input.json output.tfw.b64

# RPC server
./harnesses/bin/soup-go rpc server-start
```

## Prerequisites

- **Go 1.21+**: Required to build harnesses
- **Python 3.11+**: For TofuSoup CLI

## Troubleshooting

### Binary Not Found

If you see `No such file or directory: 'harnesses/bin/soup-go'`:

```bash
# Build the harnesses
soup harness build --all

# Verify they exist
ls -la harnesses/bin/
```

### Build Failures

If harness builds fail:

```bash
# Check Go installation
go version

# Check Go environment
go env GOPATH

# Try manual build
cd src/tofusoup/harness/go/soup-go
go build -o ../../../../../harnesses/bin/soup-go
```

## Source Code

Harness source code is located in:
- `src/tofusoup/harness/go/soup-go/` - Unified Go harness source

## See Also

- [Test Harness Development Guide](../docs/guides/testing/test-harness-development.md)
- [Conformance Testing Documentation](../docs/core-concepts/conformance-testing.md)
- [Troubleshooting Guide](../docs/troubleshooting.md)

# What is TofuSoup?

TofuSoup is a comprehensive cross-language conformance testing suite and tooling framework for the OpenTofu/Terraform ecosystem. It ensures compatibility and correctness across different language implementations of Terraform-compatible tools.

## Purpose

TofuSoup addresses a critical need in the Terraform ecosystem: **ensuring that different language implementations (Python, Go, Rust, etc.) correctly implement Terraform's specifications**. As the OpenTofu/Terraform ecosystem grows, maintaining compatibility across implementations becomes increasingly important.

## Key Features

### 🧪 Conformance Testing
- Cross-language compatibility tests
- Protocol compliance validation
- Binary-level equivalence testing
- Automated test generation and execution

### 🛠️ Developer Tools
- **CTY Operations**: Work with Terraform's Configuration Type System
- **HCL Processing**: Parse and convert HashiCorp Configuration Language
- **Wire Protocol**: Encode/decode Terraform wire protocol messages
- **RPC Testing**: gRPC service validation and plugin testing

### 🔄 Matrix Testing
- Test providers across multiple Terraform/OpenTofu versions
- Parallel test execution
- Comprehensive compatibility matrices
- CI/CD integration

### 📊 Test Harnesses
- Go reference implementations
- Python implementations via Pyvider
- CLI-based testing tools
- Automated harness management

## Why TofuSoup?

**Cross-Language Compatibility**: When building Terraform providers in languages other than Go (like Python via Pyvider), you need confidence that your implementation behaves identically to the official Go implementation.

**Conformance Testing**: TofuSoup provides automated tests that verify:
- CTY value encoding/decoding matches across languages
- HCL parsing produces identical results
- Wire protocol binary output is byte-for-byte identical
- RPC communication works across language boundaries

**Development Velocity**: Instead of manually testing compatibility, TofuSoup automates the process with comprehensive test suites that run in CI/CD.

## Core Components

### 1. CLI Tools
Command-line utilities for working with Terraform technologies:
```bash
soup cty view data.json        # Inspect CTY values
soup hcl convert main.tf       # Parse HCL files
soup wire encode value.json    # Wire protocol operations
soup rpc kv put mykey value    # RPC testing
```

### 2. Test Framework
Pytest-based conformance test suites:
```bash
soup test all                  # Run all tests
soup test cty                  # Test CTY compatibility
soup test rpc                  # Test RPC compatibility
```

### 3. Matrix Testing (Stir)
Multi-version testing framework:
```bash
soup stir tests/ --matrix      # Test across TF/Tofu versions
```

### 4. Test Harnesses
Language-specific reference implementations:
```bash
soup harness build --all       # Build Go harnesses
soup harness list              # List available harnesses
```

## Who Should Use TofuSoup?

- **Provider Developers**: Building Terraform providers in Python, Rust, or other languages
- **OpenTofu Contributors**: Ensuring OpenTofu compatibility with Terraform
- **Library Authors**: Developing Terraform-adjacent libraries (CTY, HCL parsers, etc.)
- **QA Engineers**: Validating cross-platform provider behavior
- **CI/CD Pipelines**: Automated compatibility testing

## Architecture

TofuSoup follows a modular architecture:

```
┌─────────────────────────────────────────┐
│           CLI Commands (soup)            │
├───────────┬───────────┬────────┬────────┤
│    cty    │    hcl    │  wire  │   rpc  │
├───────────┴───────────┴────────┴────────┤
│         Conformance Test Suites         │
├────────────────┬────────────────────────┤
│  Test Harnesses│    Matrix Testing      │
│  (Go/Python)   │       (Stir)           │
└────────────────┴────────────────────────┘
```

## Next Steps

- **[Installation](installation.md)**: Get TofuSoup installed and configured
- **[Quick Start](quick-start.md)**: Run your first conformance test
- **[Core Concepts](../core-concepts/architecture.md)**: Deep dive into the architecture

## Related Projects

TofuSoup is part of the Provide.io ecosystem:

- **[Pyvider](https://github.com/provide-io/pyvider)**: Python framework for building Terraform providers
- **[Pyvider-CTY](https://github.com/provide-io/pyvider-cty)**: Python implementation of CTY
- **[Pyvider-HCL](https://github.com/provide-io/pyvider-hcl)**: Python HCL parser
- **[Pyvider-RPCPlugin](https://github.com/provide-io/pyvider-rpcplugin)**: gRPC plugin infrastructure

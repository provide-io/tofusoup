# Polyglot CLI Strategy

This document outlines the architectural strategy for creating a family of TofuSoup command-line interfaces across multiple languages, ensuring a consistent developer experience and robust, symmetric testing capabilities.

## 1. Core Principle: Feature Parity

The primary goal is to achieve **feature parity** between the main Python-based `soup` CLI and its counterparts in other languages, starting with Go (`soup-go`). This means that where applicable, a developer should be able to use the same commands, subcommands, and flags in `soup-go` as they would in `soup`.

This creates a predictable and powerful ecosystem where developers can use the tools in their preferred language, and the testing suite can validate Python components against Go components using an identical set of commands.

## 2. Go Implementation: `soup-go`

The Go implementation of the TofuSoup CLI will be named `soup-go` and will be built using the **Cobra** library to provide a robust and familiar CLI structure. The existing Go harnesses (`go-cty`, `go-hcl`, etc.) will be refactored and integrated into this single, unified `soup-go` binary.

### Target `soup-go` Structure

The `soup-go` CLI will mirror the structure of the Python `soup` CLI.

**Hypothetical `soup-go --help` Output:**
```
A Go implementation of the TofuSoup conformance and utility toolkit.

Usage:
  soup-go [command]

Available Commands:
  cty         Utilities for CTY data (view, convert, validate)
  hcl         Utilities for HCL file processing (view, convert)
  rpc         Utilities for testing RPC components (kv get, kv put)
  wire        Tools for encoding/decoding Terraform Wire Protocol objects
  help        Help about any command

Flags:
  -h, --help          help for soup-go
      --log-level string   Set the logging level (default "info")
```

## 3. Role in Conformance Testing

This strategy transforms the Go harnesses from simple, single-purpose test executables into a full-featured, language-specific implementation of the TofuSoup toolkit. This enables a powerful, symmetric testing model:

-   **Python vs. Go**: The `soup test` command can invoke `soup-go` to get canonical outputs for comparison.
-   **Go vs. Python**: A future Go-based test runner could invoke the Python `soup` CLI to validate Go components.

This ensures that the entire toolchain, not just the underlying libraries, is conformant across languages.

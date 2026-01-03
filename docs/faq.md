# Frequently Asked Questions

## General

### What is TofuSoup?

TofuSoup is a cross-language conformance testing suite for the OpenTofu/Terraform ecosystem. See [What is TofuSoup?](getting-started/what-is-tofusoup/) for details.

### Who should use TofuSoup?

Provider developers, library authors, QA engineers, and anyone building Terraform-compatible tools in languages other than Go.

### Is TofuSoup affiliated with HashiCorp or OpenTofu?

No. TofuSoup is an independent project by provide.io that helps ensure compatibility across Terraform implementations.

## Installation & Setup

### How do I install TofuSoup?

```bash
uv tool install tofusoup
```

See [Installation Guide](getting-started/installation/) for details.

### Do I need Go installed?

Yes, if you want to build and use test harnesses. The harnesses provide reference Go implementations for compatibility testing.

### What Python versions are supported?

Python 3.11 and higher.

## Usage

### How do I run conformance tests?

```bash
soup test all          # Run all tests
soup test cty          # Test CTY compatibility
soup test rpc          # Test RPC compatibility
```

See [Running Conformance Tests](guides/testing/01-running-conformance-tests/).

### How do I test across multiple Terraform versions?

Use the `stir` command with matrix testing:

```bash
soup stir tests/ --matrix
```

Configure versions in `soup.toml`. See [Matrix Testing](guides/cli-usage/matrix-testing/).

### Can I use TofuSoup in CI/CD?

Yes! TofuSoup is designed for CI/CD integration. All commands support non-interactive execution and return appropriate exit codes.

## Troubleshooting

### Tests are failing with "Connection timeout"

This usually means the Go server harness isn't starting properly. Check:
1. Go is installed and in PATH
2. Harnesses are built: `soup harness build --all`
3. Firewall isn't blocking connections

See [Troubleshooting](troubleshooting/) for more.

### Binary mismatch errors in wire tests

This indicates Python and Go implementations are producing different binary output. This is a real compatibility issue that needs investigation. See the [Wire Protocol Guide](guides/cli-usage/wire-protocol/).

### Command not found: soup

Ensure Python's bin directory is in your PATH. See [Installation Troubleshooting](getting-started/installation/#troubleshooting).

## Development

### How do I contribute to TofuSoup?

See [CONTRIBUTING.md](https://github.com/provide-io/tofusoup/blob/main/CONTRIBUTING/).

### How do I add a new conformance test?

Tests are in `conformance/` directory. Follow the pattern of existing tests and use the `souptest_` prefix.

### Can I use TofuSoup with my own provider?

Yes! TofuSoup's tools work with any Terraform provider. Use the CLI tools for validation and the test framework for compatibility testing.

## Compatibility

### Which Terraform versions are supported?

TofuSoup supports Terraform 1.0+ and OpenTofu 1.6+. Configure specific versions in `soup.toml` for matrix testing.

### Does TofuSoup work with Pyvider?

Yes! TofuSoup and Pyvider are complementary projects from provide.io. TofuSoup provides the testing infrastructure, while Pyvider provides the provider framework.

### Can I test non-Python providers?

TofuSoup's CLI tools work with any language. The conformance tests currently focus on Python-Go compatibility, but the framework is extensible.

## More Questions?

- Check [Troubleshooting](troubleshooting/)
- Browse [GitHub Issues](https://github.com/provide-io/tofusoup/issues)
- Read the [Glossary](glossary/) for term definitions

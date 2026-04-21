# Examples

This directory contains example configurations and usage patterns for TofuSoup.

## Available Examples

- **[soup-profiles.toml](soup-profiles.toml)** - Example configuration profiles for different environments

## Example Configurations

### Basic Configuration

```toml
# soup.toml
[global_settings]
default_python_log_level = "INFO"

[harness_defaults.go]
build_flags = ["-v"]
timeout_seconds = 300
```

### Development Configuration

```toml
# soup.toml
[global_settings]
default_python_log_level = "DEBUG"

[harness_defaults.go]
build_flags = ["-v", "-race"]

[test_suite_defaults]
extra_pytest_args = ["-v", "--tb=long"]
```

### CI/CD Configuration

```toml
# soup.toml
[global_settings]
default_python_log_level = "INFO"

[test_suite_defaults]
extra_pytest_args = ["-v", "--tb=short", "--color=yes"]

[workenv.matrix]
parallel_jobs = 8
timeout_minutes = 20

[workenv.matrix.versions]
terraform = ["1.5.7", "1.6.0"]
tofu = ["1.6.2", "1.7.0"]
```

## Example Test Cases

See `conformance/` directory for extensive test examples:
- `conformance/cty/` - CTY conformance tests
- `conformance/hcl/` - HCL parsing tests
- `conformance/wire/` - Wire protocol tests
- `conformance/rpc/` - RPC communication tests

## More Examples

For more examples, see:
- **[Quick Start](../getting-started/quick-start.md)** - Getting started examples
- **[CLI Reference](../reference/cli.md)** - Command usage examples
- **[Configuration Reference](../reference/configuration.md)** - Complete configuration examples

## Contributing Examples

Have useful examples to share? See CONTRIBUTING.md in the project root for contribution guidelines.

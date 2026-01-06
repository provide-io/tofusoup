# Guide: Matrix Testing with Stir

The `soup stir` command is a powerful tool for running parallel integration tests. It includes **matrix testing** capabilities to validate your Terraform configurations against multiple versions of Terraform or OpenTofu.

## Prerequisites

Matrix testing is an **optional feature** that requires the `wrknv` package:

```bash
# Install wrknv from PyPI
uv tool install wrknv

# Or install from local source (development)
uv add --editable /path/to/wrknv
```

**Note**: All other TofuSoup features work without `wrknv`. Only the `soup stir --matrix` flag requires this dependency. Install `wrknv` separately.

## What is Matrix Testing?

Matrix testing executes your test suite across multiple tool versions to ensure broad compatibility. This is essential for:
- Validating provider compatibility across Terraform versions
- Testing migration paths between OpenTofu and Terraform
- Ensuring backward compatibility
- Catching version-specific bugs

## Basic Usage

Run tests across all configured tool versions:

```bash
# Run tests with matrix testing
soup stir tests/stir_cases --matrix

# Save detailed results
soup stir tests/stir_cases --matrix --matrix-output results.json
```

## Configuration

Configure matrix testing in your `soup.toml` file:

```toml
[workenv.matrix]
parallel_jobs = 4              # Number of parallel test jobs
timeout_minutes = 30           # Timeout per test run

[workenv.matrix.versions]
terraform = ["1.5.7", "1.6.0", "1.6.1"]
tofu = ["1.6.2", "1.7.0", "1.8.0"]
```

### Configuration Options

- **`parallel_jobs`**: Number of tool versions to test concurrently (default: 4)
- **`timeout_minutes`**: Maximum time for each test run (default: 30)
- **`versions`**: Map of tool names to version lists

## How Matrix Testing Works

When you run `soup stir --matrix`, the following happens:

1. **Load Configuration**: Reads matrix versions from `soup.toml` or `wrkenv.toml`
2. **Tool Management**: Automatically downloads and manages required tool versions
3. **Parallel Execution**: Runs tests across versions concurrently (respects `parallel_jobs` setting)
4. **Result Collection**: Aggregates results from all version runs
5. **Report Generation**: Creates detailed report showing compatibility across versions

The stir framework handles all version management automatically - you don't need to manually switch versions or manage tool installations.

## Test Directory Structure

Organize your test cases in subdirectories:

```
tests/stir_cases/
├── basic/
│   ├── main.tf
│   └── variables.tf
├── complex_resources/
│   ├── main.tf
│   └── outputs.tf
└── state_operations/
    ├── main.tf
    └── backend.tf
```

Each subdirectory represents a test case. Stir will:
- Run `terraform init` in each directory
- Execute `terraform plan` and `terraform apply`
- Verify successful execution
- Clean up resources

## Running Tests

### Single Version (No Matrix)

Run tests with the default Terraform/OpenTofu version:

```bash
soup stir tests/stir_cases
```

### Matrix Testing

Run tests across all configured versions:

```bash
soup stir tests/stir_cases --matrix
```

### With Results Output

Save detailed results for analysis:

```bash
soup stir tests/stir_cases --matrix --matrix-output results.json
```

The output includes:
- Pass/fail status for each version
- Execution times
- Error messages
- Version-specific differences

## Example Configuration Scenarios

### Testing OpenTofu Compatibility

```toml
[workenv.matrix.versions]
terraform = ["1.5.7"]      # Last pre-fork version
tofu = ["1.6.0", "1.6.2"]  # OpenTofu versions
```

### Comprehensive Version Coverage

```toml
[workenv.matrix]
parallel_jobs = 8           # More parallelism
timeout_minutes = 45        # Longer timeout

[workenv.matrix.versions]
terraform = [
    "1.5.7",   # Stable
    "1.6.0",   # Latest 1.6
    "1.6.1",   # Patch release
]
tofu = [
    "1.6.2",   # Current stable
    "1.7.0",   # Latest release
    "1.8.0",   # Beta/RC testing
]
```

### CI/CD Configuration

```toml
[workenv.matrix]
parallel_jobs = 4
timeout_minutes = 20        # Stricter timeout for CI

[workenv.matrix.versions]
terraform = ["1.5.7", "1.6.0"]
tofu = ["1.6.2"]
```

## Interpreting Results

### Success Output

```
✓ terraform 1.5.7: All tests passed (45.2s)
✓ terraform 1.6.0: All tests passed (43.8s)
✓ tofu 1.6.2: All tests passed (44.1s)

Matrix Test Summary: 3/3 passed
```

### Failure Output

```
✓ terraform 1.5.7: All tests passed (45.2s)
✗ terraform 1.6.0: 1/3 tests failed (38.1s)
  - complex_resources: Provider compatibility issue
✓ tofu 1.6.2: All tests passed (44.1s)

Matrix Test Summary: 2/3 passed (1 failed)
```

## Troubleshooting

### Tests Timeout

If tests consistently timeout:

```toml
[workenv.matrix]
timeout_minutes = 60  # Increase timeout
```

### Tool Download Failures

The framework automatically downloads tool versions. If downloads fail:
- Check internet connectivity
- Verify version numbers are correct
- Check disk space

### Version Not Found

If a specified version doesn't exist:
```
Error: Version 'terraform 1.9.9' not found
```

Solution: Verify version exists at:
- Terraform: https://releases.hashicorp.com/terraform/
- OpenTofu: https://github.com/opentofu/opentofu/releases

## Best Practices

1. **Start Small**: Begin with 2-3 versions, expand as needed
2. **Include Edge Cases**: Test both oldest and newest supported versions
3. **Regular Updates**: Update matrix versions quarterly
4. **CI Integration**: Run matrix tests in pull requests
5. **Monitor Execution Time**: Adjust `parallel_jobs` based on available resources

## Advanced: Workenv Integration

TofuSoup's matrix testing integrates with the `wrkenv` tool management system. You can also configure versions in `wrkenv.toml`:

```toml
# wrkenv.toml (alternative to soup.toml)
terraform_flavor = "opentofu"

[tools]
terraform = "1.5.7"
tofu = "1.6.2"

[matrix.versions]
terraform = ["1.5.7", "1.6.0"]
tofu = ["1.6.2", "1.7.0"]
```

**Note**: Settings in `soup.toml` take precedence over `wrkenv.toml`.

## See Also

- [Configuration Reference](../../reference/configuration.md) - Complete `soup.toml` documentation
- [Quick Start](../../getting-started/quick-start.md) - Basic stir usage
- [Troubleshooting](../../troubleshooting.md) - Common issues and solutions

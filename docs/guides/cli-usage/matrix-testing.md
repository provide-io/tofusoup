# Guide: Matrix Testing with Stir

The `soup stir` command is a powerful tool for running parallel integration tests. It includes built-in **matrix testing** capabilities to validate your Terraform configurations against multiple versions of Terraform or OpenTofu.

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

The goal of matrix testing is to ensure your provider works correctly across the different IaC runtimes your users might have. The workflow is:

1.  **Define Versions**: Use the matrix configuration in `wrkenv.toml` to define the Terraform/Tofu versions you want to test against.
2.  **Switch Runtime**: Use `wrkenv` to switch the active `terraform` or `tofu` binary in the environment.
3.  **Run Tests**: Use `soup stir` to execute the full suite of integration tests using the currently active runtime.
4.  **Repeat**: Loop through all defined versions, switching the runtime and re-running the tests for each one.

## Example Configuration

You can configure matrix testing in your `soup.toml` file:

```toml
# In soup.toml

[workenv.matrix]
parallel_jobs = 4
timeout_minutes = 30

[workenv.matrix.versions]
# Additional versions to test against
tofu = ["1.6.2", "1.7.0-alpha1"]
terraform = ["1.5.7", "1.6.0"]
```

Note: You can alternatively use `wrkenv.toml` for this configuration, but soup.toml takes precedence.

## Example Test Execution Script

You can automate this workflow with a simple shell script.

```bash
#!/bin/bash
# 🧪 Provider Matrix Test Runner
set -eo pipefail

# The directory containing all your 'stir' test cases
STIR_TEST_DIR="tests/stir_cases"

# Tools and versions to test, defined as "tool_name:version1,version2,..."
TOOL_MATRIX=(
  "tofu:1.6.2,1.7.0"
  "terraform:1.5.7,1.6.0"
)

echo "🍲 Starting Provider Matrix Test..."

for entry in "${TOOL_MATRIX[@]}"; do
  TOOL_NAME="${entry%%:*}"
  VERSIONS="${entry#*:}"

  # Split versions by comma
  IFS=',' read -ra VERSION_ARRAY <<< "$VERSIONS"

  for VERSION in "${VERSION_ARRAY[@]}"; do
    echo ""
    echo "======================================================"
    echo "➡️  Testing with ${TOOL_NAME} version ${VERSION}"
    echo "======================================================"

    # Step 1: Install and switch to the target version using wrkenv
    echo "🔧 Setting up ${TOOL_NAME} ${VERSION}..."
    wrkenv "${TOOL_NAME}" "${VERSION}"

    # Step 2: Run the stir test suite
    echo "🚀 Running 'stir' test suite..."
    soup stir "${STIR_TEST_DIR}"

    echo "✅ Completed tests for ${TOOL_NAME} ${VERSION}"
  done
done

echo ""
echo "🎉 All matrix tests completed successfully!"
```

This script iterates through your defined matrix, uses `soup workenv` to prepare the environment for each case, and then runs `soup stir` to validate the provider's behavior, ensuring broad compatibility.

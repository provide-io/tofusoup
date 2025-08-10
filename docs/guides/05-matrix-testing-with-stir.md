# Guide: Matrix Testing with `stir`

The `soup stir` command is a powerful tool for running parallel integration tests for a provider. It now includes built-in **matrix testing** capabilities to validate your provider's behavior against multiple versions of Terraform or OpenTofu.

## Built-in Matrix Testing (New!)

As of the latest version, `soup stir` includes integrated matrix testing:

```bash
# Run tests across all configured tool versions
soup stir tests/stir_cases --matrix

# Save results to a file
soup stir tests/stir_cases --matrix --matrix-output results.json
```

This uses the matrix configuration from your `wrkenv.toml` file.

## Manual Matrix Testing

You can also manually control matrix testing using wrkenv:

## The Concept

The goal of matrix testing is to ensure your provider works correctly across the different IaC runtimes your users might have. The workflow is:

1.  **Define Versions**: Use the matrix configuration in `wrkenv.toml` to define the Terraform/Tofu versions you want to test against.
2.  **Switch Runtime**: Use `wrkenv` to switch the active `terraform` or `tofu` binary in the environment.
3.  **Run Tests**: Use `soup stir` to execute the full suite of integration tests using the currently active runtime.
4.  **Repeat**: Loop through all defined versions, switching the runtime and re-running the tests for each one.

## Example `wrkenv.toml` Configuration

First, configure the matrix settings in your `wrkenv.toml`. This tells the matrix testing system which versions to test.

```toml
# In wrkenv.toml

[matrix]
parallel_jobs = 4
timeout_minutes = 30

[matrix.versions]
# Additional versions to test against
tofu = ["1.6.2", "1.7.0-alpha1"]
terraform = ["1.5.7", "1.6.0"]
```

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

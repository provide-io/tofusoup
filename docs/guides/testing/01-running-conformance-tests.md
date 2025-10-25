# Guide: Running Conformance Tests

The `soup test` command is the unified entry point for running all Pytest-based conformance test suites. These tests (`souptest_*.py`) are specifically for verifying cross-language compatibility against the Go harnesses.

## Running All Suites

To execute every defined test suite, use the `all` subcommand. This is the most common command for a full regression check.

```bash
soup test all
```

## Running a Specific Suite

You can run a specific suite by name. This is useful for focusing on a particular area of compatibility during development.

```bash
# Run only the CTY compatibility tests
soup test cty

# Run only the RPC compatibility tests
soup test rpc
```

Available suites include `cty`, `rpc`, `wire`, `hcl`, and more.

## Passing Arguments to Pytest

Any arguments provided after the suite name are passed directly to `pytest`. This allows you to use any standard `pytest` flag, such as running tests by keyword (`-k`) or by marker (`-m`).

```bash
# Run only tests with "some_test_name" in their name within the 'cty' suite
soup test cty -k "some_test_name"

# Run all 'rpc' tests except those marked as 'slow'
soup test rpc -m "not slow"
```

## Configuration

Test behavior, such as environment variables, default `pytest` arguments, and tests to skip, can be configured globally or per-suite in your `soup.toml` file.

**Example `soup.toml`:**
```toml
[test_suite_defaults]
extra_pytest_args = ["-m", "not slow"]

[test_suite.rpc]
# Set an environment variable only for the RPC test suite
env_vars = { SKIP_RUBY_RPC_TESTS = "1" }```

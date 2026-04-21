# TofuSoup Configuration (`soup.toml`)

TofuSoup uses a TOML file named `soup.toml` for configuration. This file allows users to customize default behaviors for various commands, harness settings, and test execution parameters.

## Location

TofuSoup searches for `soup.toml` in the following order:
1.  Path specified by the global `--config-file <path>` CLI option.
2.  `./soup.toml` (in the current working directory).
3.  `<project_root>/soup/soup.toml` (recommended default location).

If no configuration file is found, TofuSoup operates with built-in defaults.

## Precedence

For settings that can be defined in multiple places, the following order of precedence applies (highest to lowest):
1.  Command-line arguments.
2.  Environment variables (e.g., `TOFUSOUP_LOG_LEVEL`).
3.  Settings in `soup.toml`.
4.  Hardcoded application defaults.

## Top-Level Tables

### `[global_settings]`

Settings that apply across the TofuSoup application.

-   `default_python_log_level` (String): Sets the default logging level for TofuSoup's own Python-based logging. Valid values: "TRACE", "DEBUG", "INFO", "WARNING", "ERROR", "CRITICAL".
-   `default_harness_log_level` (String): A general default log level for external Go harnesses. Valid values for Go harnesses: "TRACE", "DEBUG", "INFO", "WARN", "ERROR".

### `[harness_defaults.<language>]`

Provides default settings for all harnesses of a specific language (e.g., `[harness_defaults.go]`).

-   `build_flags` (Array of Strings): Default flags passed to `go build`.
-   `common_env_vars` (Table): Environment variables to set for all Go harness operations.
-   `default_log_level` (String): Default log level specifically for Go harnesses.
-   `timeout_seconds` (Integer): Default timeout for running Go harness commands.

### `[harness.<language>."<component_id>"]`

Specific settings for an individual harness, overriding language defaults. Example: `[harness.go.cty]`.

-   `build_flags`, `custom_env_vars`, `log_level`, `timeout_seconds`.

### `[command_options."<command_group>.<command_name>"]`

Provides default values for specific CLI command options.

**Example:**
```toml
[command_options."hcl.convert"]
default_output_format = "json"
```

### `[test_suite_defaults]`

Default settings applicable to all test suites run via `soup test`.

-   `env_vars` (Table): Environment variables to set for all test runs.
-   `extra_pytest_args` (Array of Strings): Additional arguments always passed to `pytest`.
-   `skip_tests` (Array of Strings): Test items to skip.

### `[test_suite.<suite_name>]`

Specific settings for a named test suite (e.g., `[test_suite.rpc]`), overriding defaults.

-   `env_vars`, `extra_pytest_args`, `skip_tests`.

### `[workenv]`

Configuration for tool management, powered by wrkenv. When configured in soup.toml, these settings are injected into wrkenv, making wrkenv.toml optional.

-   `terraform_flavor` (String): Default terraform flavor - "terraform" or "opentofu"
-   `tools` (Table): Tool versions to use (e.g., `terraform = "1.5.7"`)
-   `settings` (Table): Various settings like `verify_checksums` and `cache_downloads`

### `[workenv.matrix]`

Configuration for matrix testing with `soup stir --matrix`.

-   `versions` (Table): Additional versions to test for each tool
-   `parallel_jobs` (Integer): Number of parallel test jobs (default: 4)
-   `timeout_minutes` (Integer): Timeout for each test run (default: 30)

Example:
```toml
[workenv]
terraform_flavor = "opentofu"

[workenv.tools]
terraform = "1.8.5"
tofu = "1.10.5"

[workenv.settings]
verify_checksums = true
cache_downloads = true

[workenv.matrix]
parallel_jobs = 8
timeout_minutes = 45

[workenv.matrix.versions]
terraform = ["1.5.7", "1.6.0", "1.6.1"]
tofu = ["1.6.2", "1.7.0", "1.8.0"]
```

Note: You can alternatively configure wrkenv using a `wrkenv.toml` file. Settings in soup.toml take precedence over wrkenv.toml.

# Guide: Configuration Management

TofuSoup uses a `soup.toml` configuration file to customize behavior. The `soup config` command helps you inspect and manage your configuration.

## Viewing Configuration

Display the currently loaded configuration:

```bash
soup config show
```

This displays a hierarchical tree view of your active configuration, showing all settings loaded from:
- Your project's `soup.toml` file
- Default values
- Environment variables

### Example Output

```
🍲 Loaded TofuSoup Configuration
└── Config Root
    ├── global_settings
    │   ├── default_python_log_level: INFO
    │   └── default_harness_log_level: DEBUG
    ├── harness_defaults
    │   └── go
    │       ├── build_flags: ["-v"]
    │       └── timeout_seconds: 300
    └── test_suite
        └── rpc
            └── env_vars
                └── KV_STORAGE_DIR: /tmp
```

## Configuration File Location

TofuSoup searches for `soup.toml` in the following order:

1. Path specified by `--config-file` CLI option
2. `./soup.toml` (current directory)
3. Project root (directory containing `pyproject.toml`)

If no configuration file is found, TofuSoup uses built-in defaults.

## Configuration Sections

### Global Settings

```toml
[global_settings]
default_python_log_level = "INFO"
default_harness_log_level = "DEBUG"
```

### Harness Configuration

```toml
[harness_defaults.go]
build_flags = ["-v"]
timeout_seconds = 300

[harness.go.soup-go]
log_level = "TRACE"
```

### Test Suite Configuration

```toml
[test_suite_defaults]
extra_pytest_args = ["-v"]

[test_suite.rpc]
env_vars = { KV_STORAGE_DIR = "/tmp" }
```

### Matrix Testing Configuration

```toml
[workenv.matrix]
parallel_jobs = 4
timeout_minutes = 30

[workenv.matrix.versions]
terraform = ["1.5.7", "1.6.0"]
tofu = ["1.8.0", "1.9.0"]
```

## Using Configuration in Commands

Most TofuSoup commands respect configuration file settings:

```bash
# Use default configuration
soup test cty

# Use specific configuration file
soup --config-file /path/to/custom.toml test cty

# Override with environment variable
export TOFUSOUP_LOG_LEVEL=DEBUG
soup test cty
```

## Configuration Precedence

Settings are resolved in this order (highest to lowest priority):

1. **Command-line arguments**: `--log-level DEBUG`
2. **Environment variables**: `TOFUSOUP_LOG_LEVEL=DEBUG`
3. **Configuration file**: `soup.toml` settings
4. **Built-in defaults**: Hardcoded application defaults

## Debugging Configuration Issues

If you're experiencing unexpected behavior:

```bash
# 1. Check what configuration is loaded
soup config show

# 2. Verify configuration file syntax
python -c "import tomllib; tomllib.load(open('soup.toml', 'rb'))"

# 3. Use explicit configuration file
soup --config-file ./soup.toml config show

# 4. Enable debug logging
soup --log-level DEBUG config show
```

## Common Configuration Patterns

### Development Environment

```toml
[global_settings]
default_python_log_level = "DEBUG"

[harness_defaults.go]
build_flags = ["-v", "-race"]
```

### CI/CD Environment

```toml
[global_settings]
default_python_log_level = "INFO"

[test_suite_defaults]
extra_pytest_args = ["-v", "--tb=short", "--color=yes"]

[workenv.matrix]
parallel_jobs = 8
```

### Production Testing

```toml
[test_suite_defaults]
extra_pytest_args = ["-m", "not slow"]

[harness_defaults.go]
timeout_seconds = 600
```

## See Also

- [Configuration Reference](../../reference/configuration.md) - Complete configuration file documentation
- [Troubleshooting](../../troubleshooting.md) - Common configuration issues
- [Quick Start](../../getting-started/quick-start.md) - Basic configuration examples

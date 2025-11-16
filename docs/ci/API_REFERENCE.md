# API Reference

Complete reference for all CLI flags, environment variables, configuration options, and programmatic APIs related to CI/CD improvements.

## Table of Contents

- [Command Line Flags](#command-line-flags)
- [Environment Variables](#environment-variables)
- [Exit Codes](#exit-codes)
- [Configuration File](#configuration-file)
- [Programmatic API](#programmatic-api)

---

## Command Line Flags

All new flags for `soup stir` command.

### Output Format Flags

#### `--format=MODE`

Control output format.

**Type**: Choice
**Values**: `table`, `plain`, `json`, `github`, `quiet`
**Default**: Auto-detected (`table` if interactive, `plain` if CI)
**Since**: v2.0.0

**Description**:
- `table`: Rich Live table with continuous updates (interactive mode)
- `plain`: Line-by-line text output (CI-friendly)
- `json`: Structured JSON output to stdout
- `github`: GitHub Actions annotations
- `quiet`: Minimal output (summary only)

**Examples**:
```bash
soup stir --format=plain tests/
soup stir --format=json tests/ | jq '.summary.passed'
soup stir --format=github tests/  # In GitHub Actions
```

**Conflicts**:
- Mutually exclusive with `--json` (use `--format=json` instead)

**See Also**: [OUTPUT_FORMATS.md](./OUTPUT_FORMATS/)

---

#### `--json`

Output results as JSON.

**Type**: Boolean flag
**Default**: `false`
**Since**: v2.0.0

**Description**:
Equivalent to `--format=json`. Outputs structured JSON to stdout and suppresses all other output.

**Examples**:
```bash
soup stir --json tests/ > results.json
soup stir --json tests/ | jq '.tests[] | select(.status=="failed")'
```

**Conflicts**:
- Cannot be used with `--format` (except `--format=json`)

---

#### `--json-pretty`

Pretty-print JSON output.

**Type**: Boolean flag
**Default**: `false`
**Since**: v2.0.0

**Description**:
When used with `--json`, outputs indented JSON (2 spaces) for human readability.

**Examples**:
```bash
soup stir --json --json-pretty tests/
```

**Requires**: `--json` or `--format=json`

---

#### `--junit-xml=FILE`

Generate JUnit XML test report.

**Type**: File path
**Default**: None (not generated)
**Since**: v2.0.0

**Description**:
Writes JUnit XML formatted test results to specified file. Compatible with Jenkins, GitHub Actions, GitLab CI, CircleCI, and other CI systems.

**Examples**:
```bash
soup stir --junit-xml=results.xml tests/
soup stir --junit-xml=/tmp/test-results/soup-stir.xml tests/
```

**Notes**:
- Parent directories are created automatically
- File is overwritten if it exists
- Can be used simultaneously with other output formats

**See Also**: [OUTPUT_FORMATS.md#junit-xml-format](./OUTPUT_FORMATS/#junit-xml-format)

---

#### `--junit-suite-name=NAME`

Set test suite name in JUnit XML.

**Type**: String
**Default**: `"soup-stir"`
**Since**: v2.0.0

**Description**:
Customizes the `name` attribute of the `<testsuites>` element in JUnit XML output.

**Examples**:
```bash
soup stir --junit-xml=results.xml --junit-suite-name="Provider Tests" tests/
```

**Requires**: `--junit-xml`

---

### CI/CD Flags

#### `--ci`

Force CI mode (non-interactive output).

**Type**: Boolean flag
**Default**: Auto-detected
**Since**: v2.0.0

**Description**:
Forces CI-friendly output mode (line-by-line, timestamps, no live updates) regardless of TTY status or environment variables.

**Examples**:
```bash
soup stir --ci tests/  # Force CI mode even in terminal
```

**Conflicts**:
- Mutually exclusive with `--no-ci`

---

#### `--no-ci`

Force interactive mode.

**Type**: Boolean flag
**Default**: Auto-detected
**Since**: v2.0.0

**Description**:
Forces interactive table mode even in CI environments or non-TTY contexts.

**Examples**:
```bash
soup stir --no-ci tests/ | tee output.log  # Force table even when piping
```

**Conflicts**:
- Mutually exclusive with `--ci`

---

### Timeout Flags

#### `--timeout=SECONDS`

Global timeout for entire test suite.

**Type**: Integer (seconds)
**Default**: Unlimited
**Since**: v2.0.0

**Description**:
Sets maximum duration for the entire test suite. If exceeded, running tests are terminated and pending tests are skipped.

**Examples**:
```bash
soup stir --timeout=600 tests/          # 10 minutes max
soup stir --timeout=1800 tests/         # 30 minutes max
```

**Exit Code**: 124 if global timeout exceeded

**Notes**:
- Timer starts when first test begins execution
- Running tests get graceful termination (SIGTERM → 5s → SIGKILL)
- Pending tests are marked as skipped

---

#### `--test-timeout=SECONDS`

Timeout for individual tests.

**Type**: Integer (seconds)
**Default**: Unlimited
**Since**: v2.0.0

**Description**:
Sets maximum duration for each individual test. If a test exceeds this timeout, it is terminated and marked as failed.

**Examples**:
```bash
soup stir --test-timeout=300 tests/     # 5 minutes per test
soup stir --timeout=1800 --test-timeout=300 tests/  # Combined
```

**Exit Code**: 125 if any test timeout exceeded

**Notes**:
- Timer starts when test begins (CLEANING phase)
- Test gets graceful termination (SIGTERM → 5s → SIGKILL)
- Remaining tests continue executing

---

### Parallelism Flags

#### `--jobs=N`, `-j N`

Control test parallelism.

**Type**: Integer or `auto`
**Default**: `auto` (uses all CPU cores)
**Since**: v2.0.0

**Description**:
Limits the number of tests running in parallel.

**Special Values**:
- `0` or `auto`: Auto-detect (uses `os.cpu_count()`)
- `1`: Serial execution (one test at a time)
- `N`: Run up to N tests in parallel

**Examples**:
```bash
soup stir --jobs=1 tests/               # Serial (debugging)
soup stir -j 1 tests/                   # Same as above
soup stir --jobs=2 tests/               # Max 2 parallel
soup stir --jobs=auto tests/            # All CPUs (default)
soup stir -j tests/                     # Short form for auto
```

**Notes**:
- Serial mode (`-j 1`) runs tests in deterministic sorted order
- Useful for debugging race conditions or resource constraints

---

### Timestamp Flags

#### `--timestamps`

Enable timestamps on each output line.

**Type**: Boolean flag
**Default**: Auto-enabled in CI mode
**Since**: v2.0.0

**Description**:
Prefixes each output line with a timestamp. Automatically enabled in CI mode.

**Examples**:
```bash
soup stir --timestamps tests/           # Force timestamps
soup stir --no-timestamps tests/        # Disable even in CI
```

**Conflicts**:
- Mutually exclusive with `--no-timestamps`

---

#### `--no-timestamps`

Disable timestamps.

**Type**: Boolean flag
**Default**: `false`
**Since**: v2.0.0

**Description**:
Disables timestamp output, even in CI mode.

**Examples**:
```bash
soup stir --no-timestamps tests/
```

---

#### `--timestamp-format=FORMAT`

Set timestamp format.

**Type**: Choice
**Values**: `iso8601`, `iso8601-simple`, `relative`, `elapsed`, `unix`
**Default**: `iso8601`
**Since**: v2.0.0

**Description**:
Controls the format of timestamps when enabled.

**Formats**:
- `iso8601`: Full ISO 8601 with microseconds (e.g., `2025-11-02T10:30:15.123456Z`)
- `iso8601-simple`: ISO 8601 without microseconds (e.g., `2025-11-02T10:30:15Z`)
- `relative`: Relative to suite start (e.g., `[+00:15.2s]`)
- `elapsed`: Same as relative, different format (e.g., `[00:15.2]`)
- `unix`: Unix timestamp with microseconds (e.g., `1699012215.123456`)

**Examples**:
```bash
soup stir --timestamps --timestamp-format=relative tests/
soup stir --timestamp-format=unix tests/
```

**Requires**: `--timestamps` (or auto-enabled in CI)

---

### Display Flags

#### `--show-progress`

Show progress percentage.

**Type**: Boolean flag
**Default**: Auto-enabled in CI mode
**Since**: v2.0.0

**Description**:
Displays test progress as percentage (e.g., `[40%]`).

**Examples**:
```bash
soup stir --show-progress tests/
```

**Output Example**:
```
[20%] (1/5) ✅ test-auth - PASS
[40%] (2/5) ✅ test-network - PASS
```

---

#### `--show-eta`

Show estimated time remaining.

**Type**: Boolean flag
**Default**: `false`
**Since**: v2.0.0

**Description**:
Displays estimated time remaining based on average test duration.

**Examples**:
```bash
soup stir --show-progress --show-eta tests/
```

**Output Example**:
```
[40%] (2/5) ✅ test-network - PASS - est. 45s remaining
```

**Requires**: `--show-progress` (or enabled by default)

---

#### `--show-phase-timing`

Display per-phase timing breakdown.

**Type**: Boolean flag
**Default**: `false`
**Since**: v2.0.0

**Description**:
Shows timing breakdown for each phase (CLEANING, INIT, APPLYING, etc.) after test completion.

**Examples**:
```bash
soup stir --show-phase-timing tests/
```

**Output Example**:
```
✅ test-auth - PASS (12.5s total)
   CLEANING:   0.5s (  4%)
   INIT:       2.0s ( 16%)
   APPLYING:   8.0s ( 64%)
   ANALYZING:  0.5s (  4%)
   DESTROYING: 1.5s ( 12%)
```

---

#### `--refresh-rate=RATE`

Set live display refresh rate.

**Type**: Float (Hz - updates per second)
**Default**: `0.77` (~1.3 seconds per update)
**Since**: v2.0.0

**Description**:
Controls how frequently the live table display updates.

**Examples**:
```bash
soup stir --refresh-rate=2.0 tests/     # Fast (2x per second)
soup stir --refresh-rate=0.2 tests/     # Slow (every 5 seconds)
```

**Notes**:
- Only applies to `--format=table` (interactive mode)
- CI mode uses `--no-refresh` by default

---

#### `--no-refresh`

Disable periodic refresh.

**Type**: Boolean flag
**Default**: `false` (interactive), `true` (CI)
**Since**: v2.0.0

**Description**:
Disables periodic display updates. Only updates on actual status changes.

**Examples**:
```bash
soup stir --no-refresh tests/
```

**Notes**:
- Reduces CPU usage
- Automatically enabled in CI mode
- Event-driven instead of polling

---

### Color Flags

#### `--color=WHEN`

Control color output.

**Type**: Choice
**Values**: `auto`, `always`, `never`
**Default**: `auto`
**Since**: v2.0.0

**Description**:
Controls ANSI color output.

**Values**:
- `auto`: Auto-detect based on TTY and environment variables
- `always`: Force colors even in non-TTY
- `never`: Disable all colors

**Examples**:
```bash
soup stir --color=never tests/          # No colors
soup stir --color=always tests/ | less -R  # Force colors in pipe
```

**See Also**: `NO_COLOR` environment variable

---

#### `--no-color`

Disable color output.

**Type**: Boolean flag
**Default**: `false`
**Since**: v2.0.0

**Description**:
Shorthand for `--color=never`.

**Examples**:
```bash
soup stir --no-color tests/
```

**Equivalent To**: `--color=never`

---

### Failure Handling Flags

#### `--fail-fast`

Stop after first test failure.

**Type**: Boolean flag
**Default**: `false`
**Since**: v2.0.0

**Description**:
Stops test execution immediately after the first test fails. Running tests complete, but pending tests are skipped.

**Examples**:
```bash
soup stir --fail-fast tests/
```

**Exit Code**: Still 1 (failure), not changed by fail-fast

**Output Example**:
```
✅ test-auth - PASS
❌ test-network - FAIL
⏭️ test-database - SKIPPED (fail-fast mode)
⏭️ test-storage - SKIPPED (fail-fast mode)
```

---

#### `--fail-threshold=N`

Stop after N test failures.

**Type**: Integer
**Default**: Unlimited
**Since**: v2.0.0

**Description**:
Stops test execution after N tests have failed.

**Examples**:
```bash
soup stir --fail-threshold=3 tests/     # Stop after 3 failures
```

**Exit Code**: Still 1 (failure)

---

### Log Flags

#### `--stream-logs`

Stream all Terraform logs to stdout.

**Type**: Boolean flag
**Default**: `false`
**Since**: v2.0.0

**Description**:
Streams all Terraform output to stdout in real-time, prefixed with test name and phase.

**Examples**:
```bash
soup stir --stream-logs tests/
```

**Output Example**:
```
[test-auth:init] Initializing the backend...
[test-auth:apply] Creating aws_instance.example...
[test-network:init] Initializing the backend...
```

**Notes**:
- Interleaves logs from parallel tests
- Useful for debugging
- Can be very verbose

---

#### `--aggregate-logs=FILE`

Aggregate all logs into single file.

**Type**: File path
**Default**: None
**Since**: v2.0.0

**Description**:
Writes all test logs to a single aggregated file, sectioned by test and phase.

**Examples**:
```bash
soup stir --aggregate-logs=all-tests.log tests/
soup stir --aggregate-logs=/tmp/logs/combined.log tests/
```

**Notes**:
- Parent directories created automatically
- File organized with clear section headers
- Useful for CI artifact collection

---

#### `--logs-dir=DIR`

Custom directory for log files.

**Type**: Directory path
**Default**: `~/.cache/tofusoup/logs/stir/`
**Since**: v2.0.0

**Description**:
Overrides default log file location.

**Examples**:
```bash
soup stir --logs-dir=/tmp/stir-logs tests/
soup stir --logs-dir=./test-logs tests/
```

**Notes**:
- Directory created if doesn't exist
- Useful for ephemeral CI environments
- Easier artifact collection

---

### Summary Flags

#### `--summary-file=FILE`

Save test summary to file.

**Type**: File path
**Default**: None
**Since**: v2.0.0

**Description**:
Writes test summary to specified file for later analysis or CI artifact collection.

**Examples**:
```bash
soup stir --summary-file=summary.json tests/
soup stir --summary-file=summary.md --summary-format=markdown tests/
```

**Notes**:
- Parent directories created automatically
- Works with all output formats (also shows on terminal)

---

#### `--summary-format=FORMAT`

Set summary file format.

**Type**: Choice
**Values**: `json`, `text`, `markdown`
**Default**: `json`
**Since**: v2.0.0

**Description**:
Controls format of summary file.

**Examples**:
```bash
soup stir --summary-file=summary.txt --summary-format=text tests/
soup stir --summary-file=summary.md --summary-format=markdown tests/
```

**Requires**: `--summary-file`

---

## Environment Variables

All environment variables that affect `soup stir` behavior.

### CI Detection

| Variable | Values | Default | Description |
|----------|--------|---------|-------------|
| `CI` | `true`/`false` | - | Generic CI indicator (standard) |
| `GITHUB_ACTIONS` | `true`/`false` | - | GitHub Actions environment |
| `GITLAB_CI` | `true`/`false` | - | GitLab CI environment |
| `JENKINS_URL` | any | - | Jenkins environment |
| `CIRCLECI` | `true`/`false` | - | CircleCI environment |
| `TRAVIS` | `true`/`false` | - | Travis CI environment |
| `BUILDKITE` | `true`/`false` | - | Buildkite environment |
| `TEAMCITY_VERSION` | any | - | TeamCity environment |
| `TF_BUILD` | `true`/`false` | - | Azure Pipelines environment |

### TofuSoup Configuration

| Variable | Values | Default | Description |
|----------|--------|---------|-------------|
| `SOUP_STIR_CI_MODE` | `true`/`false`/`auto` | `auto` | Override CI detection |
| `SOUP_STIR_FORMAT` | `table`/`plain`/`json`/`github`/`quiet` | - | Default output format |
| `SOUP_STIR_TIMEOUT` | integer (seconds) | unlimited | Default global timeout |
| `SOUP_STIR_TEST_TIMEOUT` | integer (seconds) | unlimited | Default per-test timeout |
| `SOUP_STIR_JOBS` | integer/`auto` | `auto` | Default parallelism |
| `SOUP_STIR_TIMESTAMPS` | `true`/`false`/`auto` | `auto` | Enable timestamps |
| `SOUP_STIR_TIMESTAMP_FORMAT` | format name | `iso8601` | Timestamp format |
| `SOUP_STIR_REFRESH_RATE` | float (Hz) | `0.77` | Display refresh rate |
| `SOUP_STIR_LOGS_DIR` | path | cache dir | Default logs directory |
| `SOUP_STIR_STREAM_LOGS` | `true`/`false` | `false` | Enable log streaming |

### Color Control

| Variable | Values | Default | Description |
|----------|--------|---------|-------------|
| `NO_COLOR` | any value | - | Disable colors (standard convention) |
| `FORCE_COLOR` | any value | - | Force colors even in non-TTY |
| `SOUP_STIR_COLOR` | `auto`/`always`/`never` | `auto` | Color mode override |

### Examples

```bash
# Force CI mode with timestamps
export SOUP_STIR_CI_MODE=true
export SOUP_STIR_TIMESTAMPS=true
soup stir tests/

# Set default timeouts
export SOUP_STIR_TIMEOUT=1800
export SOUP_STIR_TEST_TIMEOUT=300
soup stir tests/

# Disable colors
export NO_COLOR=1
soup stir tests/

# GitHub Actions (auto-detected)
# These are set automatically by GitHub Actions:
# CI=true
# GITHUB_ACTIONS=true
soup stir --format=github tests/
```

---

## Exit Codes

| Code | Name | Description |
|------|------|-------------|
| `0` | Success | All tests passed |
| `1` | Failure | One or more tests failed |
| `2` | Error | Command-line argument error or invalid usage |
| `124` | Global Timeout | Global timeout exceeded (follows GNU timeout convention) |
| `125` | Test Timeout | One or more tests exceeded per-test timeout |
| `130` | Interrupted | User interrupted (Ctrl+C) |

### Usage Examples

```bash
# In scripts
soup stir tests/
if [ $? -eq 0 ]; then
    echo "All tests passed"
elif [ $? -eq 124 ]; then
    echo "Global timeout exceeded"
else
    echo "Tests failed"
fi

# In CI (GitHub Actions)
- name: Run tests
  run: soup stir tests/
  timeout-minutes: 30
  continue-on-error: false

# Get exit code
- name: Check exit code
  if: failure()
  run: echo "Tests failed with exit code $?"
```

---

## Configuration File

TofuSoup can be configured via `soup.toml` or `pyproject.toml`.

### soup.toml

```toml
[tool.soup.stir]
# Default output format
format = "plain"  # or "table", "json", "github", "quiet"

# Timeouts (seconds)
timeout = 1800              # Global timeout: 30 minutes
test_timeout = 300          # Per-test timeout: 5 minutes

# Parallelism
jobs = "auto"               # or integer

# Timestamps
timestamps = true           # or false, "auto"
timestamp_format = "iso8601"  # or "relative", "unix", etc.

# Display options
show_progress = true
show_eta = true
show_phase_timing = false
refresh_rate = 0.77

# Colors
color = "auto"              # or "always", "never"

# Log options
stream_logs = false
logs_dir = "/custom/path"

# Failure handling
fail_fast = false
fail_threshold = null       # or integer

# Output files
summary_file = "summary.json"
summary_format = "json"
junit_xml = "results.xml"
junit_suite_name = "My Tests"
```

### pyproject.toml

```toml
[tool.soup.stir]
format = "json"
timeout = 1800
test_timeout = 300
```

### Precedence

Configuration precedence (highest to lowest):
1. Command-line flags
2. Environment variables
3. `soup.toml` / `pyproject.toml`
4. Built-in defaults

---

## Programmatic API

For programmatic use of the stir functionality.

### Python API

```python
from tofusoup.stir import run_stir_tests
from tofusoup.stir.models import TestResult
from pathlib import Path

# Basic usage
results = run_stir_tests(
    test_dirs=[Path("tests/test-auth"), Path("tests/test-network")],
    format="json",
    timeout=600,
    test_timeout=300,
    jobs=2,
)

# Access results
for result in results:
    print(f"{result.directory}: {result.status}")
    if not result.success:
        print(f"  Failed at: {result.failed_stage}")
        print(f"  Error: {result.error_message}")

# Generate reports
from tofusoup.stir.junit import generate_junit_xml

xml = generate_junit_xml(results, suite_name="My Tests")
Path("results.xml").write_text(xml)

# Use renderers directly
from tofusoup.stir.renderers import get_renderer
from rich.console import Console

renderer = get_renderer(
    mode="plain",
    console=Console(),
    config={"timestamps": True}
)

renderer.start(total_tests=len(test_dirs))
# ... execute tests ...
renderer.update_status("test-auth", status_dict)
renderer.complete(results)
```

### API Functions

#### `run_stir_tests()`

```python
def run_stir_tests(
    test_dirs: list[Path],
    *,
    format: str = "table",
    timeout: int | None = None,
    test_timeout: int | None = None,
    jobs: int | str = "auto",
    timestamps: bool = False,
    timestamp_format: str = "iso8601",
    show_progress: bool = False,
    fail_fast: bool = False,
    fail_threshold: int | None = None,
) -> list[TestResult]:
    """
    Run terraform tests in specified directories.

    Args:
        test_dirs: List of test directory paths
        format: Output format (table/plain/json/github/quiet)
        timeout: Global timeout in seconds
        test_timeout: Per-test timeout in seconds
        jobs: Parallelism (integer or "auto")
        timestamps: Enable timestamps
        timestamp_format: Timestamp format
        show_progress: Show progress percentage
        fail_fast: Stop after first failure
        fail_threshold: Stop after N failures

    Returns:
        List of TestResult objects

    Raises:
        TimeoutError: If global timeout exceeded
        ValueError: If invalid arguments
    """
```

#### `generate_junit_xml()`

```python
def generate_junit_xml(
    results: list[TestResult],
    *,
    suite_name: str = "soup-stir",
) -> str:
    """
    Generate JUnit XML from test results.

    Args:
        results: List of TestResult objects
        suite_name: Name for test suite

    Returns:
        XML string
    """
```

#### `generate_json_output()`

```python
def generate_json_output(
    results: list[TestResult],
    *,
    pretty: bool = False,
) -> str:
    """
    Generate JSON from test results.

    Args:
        results: List of TestResult objects
        pretty: Pretty-print with indentation

    Returns:
        JSON string
    """
```

---

**Document Version**: 1.0.0
**Last Updated**: 2025-11-02
**Status**: Draft API Reference

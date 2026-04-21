# CI/CD Improvements - Detailed Specifications

This document provides complete technical specifications for all 15 proposed improvements to `soup stir` for CI/CD environments.

## Table of Contents

- [High Priority Improvements](#high-priority-improvements)
  - [#1 Auto-Detect CI/CD Environments](#1-auto-detect-cicd-environments)
  - [#2 JSON Output for Standard Mode](#2-json-output-for-standard-mode)
  - [#3 JUnit XML Output](#3-junit-xml-output)
  - [#4 Format Flag with Multiple Output Modes](#4-format-flag-with-multiple-output-modes)
  - [#5 Timeout Controls](#5-timeout-controls)
  - [#6 Parallelism Control](#6-parallelism-control)
- [Medium Priority Improvements](#medium-priority-improvements)
  - [#7 Timestamps in CI Mode](#7-timestamps-in-ci-mode)
  - [#8 Populate Error Fields](#8-populate-failed_stage-and-error_message-fields)
  - [#9 Log Aggregation & Streaming](#9-log-aggregation--streaming)
  - [#10 Summary File Output](#10-summary-file-output)
  - [#11 Per-Phase Timing Breakdown](#11-per-phase-timing-breakdown)
  - [#12 Progress Percentage Indicator](#12-progress-percentage-indicator)
  - [#13 Configurable Refresh Rate](#13-configurable-refresh-rate)
- [Low Priority Improvements](#low-priority-improvements)
  - [#14 Colored Output Control](#14-colored-output-control)
  - [#15 Failure-Only Mode](#15-failure-only-mode)

---

## High Priority Improvements

### #1: Auto-Detect CI/CD Environments

**Priority**: 🔥 High
**Effort**: Medium
**Files to Modify**: `cli.py`, `display.py`

#### Description
Automatically detect when `soup stir` is running in a CI/CD environment and adapt the output format to be more suitable for non-interactive contexts.

#### Problem Statement
The current Rich Live display generates ANSI control codes and frequent updates that clutter CI logs and don't render properly in non-TTY environments. CI build logs become difficult to read and parse.

#### Solution
Detect CI environment and automatically switch to line-by-line output mode instead of live table updates.

#### CI Environment Detection

Detect CI by checking (in order):
1. TTY detection: `not sys.stdout.isatty()`
2. Environment variables (any of):
   - `CI=true` (generic)
   - `GITHUB_ACTIONS=true` (GitHub Actions)
   - `GITLAB_CI=true` (GitLab CI)
   - `JENKINS_URL` (Jenkins)
   - `CIRCLECI=true` (CircleCI)
   - `TRAVIS=true` (Travis CI)
   - `BUILDKITE=true` (Buildkite)
   - `TEAMCITY_VERSION` (TeamCity)
   - `TF_BUILD=true` (Azure Pipelines)

#### Behavior Changes in CI Mode

When CI is detected:
- **Disable live table updates** - Don't use `rich.Live()`
- **Use line-by-line output** - Each status change prints a new line
- **Reduce refresh rate** - Only output on actual status changes
- **Add timestamps** - Prefix each line with timestamp (see #7)
- **Simplify formatting** - Reduce visual complexity

#### Output Format in CI Mode

```
[2025-11-02T10:30:00.123Z] 💤 PENDING    1/5  test-auth
[2025-11-02T10:30:01.234Z] 🧹 CLEANING   1/5  test-auth
[2025-11-02T10:30:02.345Z] 🔄 INIT       1/5  test-auth
[2025-11-02T10:30:05.456Z] 🚀 APPLYING   1/5  test-auth - Creating aws_instance.example
[2025-11-02T10:30:12.567Z] 🔬 ANALYZING  1/5  test-auth
[2025-11-02T10:30:13.678Z] 💥 DESTROYING 1/5  test-auth
[2025-11-02T10:30:15.789Z] ✅ PASS       1/5  test-auth (15.7s) - 2 providers, 5 resources
[2025-11-02T10:30:15.890Z] 🧹 CLEANING   2/5  test-network
```

#### CLI Flags

| Flag | Type | Default | Description |
|------|------|---------|-------------|
| `--ci` | boolean | auto-detect | Force CI mode even in TTY |
| `--no-ci` | boolean | auto-detect | Force interactive mode even in CI |

#### Environment Variables

| Variable | Values | Description |
|----------|--------|-------------|
| `SOUP_STIR_CI_MODE` | `true`/`false`/`auto` | Override CI detection |

#### Acceptance Criteria

- [ ] CI environment is detected correctly in all major CI systems
- [ ] Non-TTY environments automatically use line-by-line output
- [ ] `--ci` flag forces CI mode regardless of environment
- [ ] `--no-ci` flag forces interactive mode regardless of environment
- [ ] Line-by-line output is clean and parseable
- [ ] Status changes are printed immediately (not buffered)
- [ ] All emoji and color are preserved (unless `--no-color` is used)

---

### #2: JSON Output for Standard Mode

**Priority**: 🔥 High
**Effort**: Low
**Files to Modify**: `cli.py`, `models.py`, `reporting.py`

#### Description
Add `--json` flag to output test results in JSON format for standard (non-matrix) mode.

#### Problem Statement
Currently `--json` only works with `--matrix` mode. Standard test runs have no machine-readable output format, making it difficult to parse results programmatically or integrate with custom tooling.

#### Solution
Add `--json` flag that outputs structured JSON to stdout after tests complete.

#### CLI Flags

| Flag | Type | Default | Description |
|------|------|---------|-------------|
| `--json` | boolean | false | Output results as JSON |
| `--json-pretty` | boolean | false | Pretty-print JSON output |

#### JSON Output Schema

```json
{
  "summary": {
    "total": 5,
    "passed": 4,
    "failed": 1,
    "skipped": 0,
    "duration_seconds": 45.23,
    "start_time": "2025-11-02T10:30:00.123456Z",
    "end_time": "2025-11-02T10:30:45.356789Z",
    "terraform_version": "1.5.7",
    "command": "soup stir /path/to/tests"
  },
  "tests": [
    {
      "name": "test-auth",
      "directory": "/full/path/to/test-auth",
      "status": "passed",
      "duration_seconds": 12.5,
      "start_time": "2025-11-02T10:30:00.123456Z",
      "end_time": "2025-11-02T10:30:12.623456Z",
      "providers": 2,
      "resources": 5,
      "data_sources": 1,
      "functions": 0,
      "ephemeral_functions": 0,
      "outputs": 3,
      "warnings": false,
      "failed_stage": null,
      "error_message": null,
      "logs": {
        "stdout": "/path/to/stdout.log",
        "stderr": "/path/to/stderr.log",
        "terraform": "/path/to/terraform.log"
      }
    },
    {
      "name": "test-network",
      "directory": "/full/path/to/test-network",
      "status": "failed",
      "duration_seconds": 5.2,
      "start_time": "2025-11-02T10:30:12.623456Z",
      "end_time": "2025-11-02T10:30:17.823456Z",
      "providers": 1,
      "resources": 0,
      "data_sources": 0,
      "functions": 0,
      "ephemeral_functions": 0,
      "outputs": 0,
      "warnings": true,
      "failed_stage": "APPLY",
      "error_message": "Error: aws_instance.example: InvalidAMI: The image id '[ami-12345]' does not exist",
      "logs": {
        "stdout": "/path/to/stdout.log",
        "stderr": "/path/to/stderr.log",
        "terraform": "/path/to/terraform.log"
      }
    }
  ],
  "provider_cache": {
    "status": "success",
    "duration_seconds": 2.3,
    "providers_downloaded": 3
  }
}
```

#### Behavior

- When `--json` is used:
  - Suppress all Rich display output (no live table, no summary panel)
  - Suppress all console output except JSON
  - Write JSON to stdout after all tests complete
  - Write any errors to stderr
  - Exit with appropriate code (0 for success, non-zero for failure)

- When `--json-pretty` is used:
  - Same as `--json` but with indentation (2 spaces)
  - Useful for human review

#### Compatibility

- Mutually exclusive with: `--format` (if format is not `json`)
- Compatible with: all other flags (timeouts, parallelism, etc.)
- `--json` implies `--no-ci` for display purposes (no live updates)

#### Acceptance Criteria

- [ ] `--json` outputs valid JSON to stdout
- [ ] JSON schema matches specification
- [ ] All test result fields are populated correctly
- [ ] Failed tests include `failed_stage` and `error_message`
- [ ] No other output appears on stdout when using `--json`
- [ ] Errors and warnings go to stderr, not stdout
- [ ] JSON is parseable by `jq` and other tools
- [ ] Exit code reflects test results (0=all passed, non-zero=failures)

---

### #3: JUnit XML Output

**Priority**: 🔥 High
**Effort**: Medium
**Files to Modify**: `cli.py`, `reporting.py`

#### Description
Generate JUnit XML test reports for integration with CI/CD systems.

#### Problem Statement
Most CI/CD systems (Jenkins, GitHub Actions, GitLab CI, CircleCI, etc.) have native support for displaying JUnit XML test results. This enables:
- Visual test result dashboards
- Historical trending
- Flaky test detection
- Test failure notifications

#### Solution
Add `--junit-xml` flag to generate JUnit XML compatible test reports.

#### CLI Flags

| Flag | Type | Default | Description |
|------|------|---------|-------------|
| `--junit-xml=FILE` | path | none | Write JUnit XML to FILE |
| `--junit-suite-name=NAME` | string | `"soup-stir"` | Test suite name in XML |

#### JUnit XML Format

```xml
<?xml version="1.0" encoding="UTF-8"?>
<testsuites name="soup-stir" tests="5" failures="1" errors="0" skipped="0" time="45.23" timestamp="2025-11-02T10:30:00.123456Z">
  <testsuite name="terraform-tests" tests="5" failures="1" errors="0" skipped="0" time="45.23" timestamp="2025-11-02T10:30:00.123456Z">

    <!-- Passed test -->
    <testcase name="test-auth" classname="terraform.test-auth" time="12.5" timestamp="2025-11-02T10:30:00.123456Z">
      <system-out><![CDATA[
Providers: 2
Resources: 5
Data Sources: 1
Outputs: 3
Warnings: false
      ]]></system-out>
    </testcase>

    <!-- Failed test -->
    <testcase name="test-network" classname="terraform.test-network" time="5.2" timestamp="2025-11-02T10:30:12.623456Z">
      <failure message="Terraform apply failed" type="TerraformApplyError"><![CDATA[
Stage: APPLY
Error: aws_instance.example: InvalidAMI: The image id '[ami-12345]' does not exist

Terraform Log: /path/to/terraform.log
Stdout Log: /path/to/stdout.log
Stderr Log: /path/to/stderr.log
      ]]></failure>
      <system-out><![CDATA[
Providers: 1
Resources: 0
      ]]></system-out>
      <system-err><![CDATA[
Error: aws_instance.example: InvalidAMI: The image id '[ami-12345]' does not exist
      ]]></system-err>
    </testcase>

    <!-- Skipped test -->
    <testcase name="test-empty" classname="terraform.test-empty" time="0.1" timestamp="2025-11-02T10:30:17.823456Z">
      <skipped message="No .tf files found" />
    </testcase>

  </testsuite>
</testsuites>
```

#### Field Mapping

| JUnit Field | Source | Notes |
|-------------|--------|-------|
| `testsuite/@name` | `--junit-suite-name` or `"terraform-tests"` | Suite name |
| `testsuite/@tests` | Count of all tests | Total tests run |
| `testsuite/@failures` | Count of failed tests | Tests with `status="failed"` |
| `testsuite/@errors` | Count of error tests | Tests with `ERROR` state (exception in harness) |
| `testsuite/@skipped` | Count of skipped tests | Tests with `status="skipped"` |
| `testsuite/@time` | Total duration in seconds | Sum of all test times |
| `testcase/@name` | Test directory name | e.g., `test-auth` |
| `testcase/@classname` | `"terraform." + test name` | Namespacing for CI systems |
| `testcase/@time` | Test duration in seconds | From `TestResult.duration` |
| `testcase/failure/@message` | `error_message` field | First line of error |
| `testcase/failure/@type` | Derived from `failed_stage` | e.g., `TerraformInitError`, `TerraformApplyError` |
| `testcase/failure/text()` | Full error with context | Error message + logs paths |
| `testcase/system-out` | Test metadata | Providers, resources, outputs counts |
| `testcase/system-err` | Error logs | Terraform error output |

#### Behavior

- Write XML to specified file path
- Create parent directories if they don't exist
- Overwrite file if it already exists
- Continue to display results to terminal (unless `--quiet`)
- Compatible with `--json` (both files can be generated)

#### Acceptance Criteria

- [ ] `--junit-xml` creates valid JUnit XML file
- [ ] XML validates against JUnit XSD schema
- [ ] All test results are represented correctly
- [ ] Failed tests include failure message and details
- [ ] Skipped tests are marked with `<skipped>` element
- [ ] Timestamps use ISO 8601 format
- [ ] File is created even if tests fail
- [ ] XML is parseable by Jenkins, GitHub Actions, GitLab CI
- [ ] Parent directories are created automatically
- [ ] Existing file is overwritten

---

### #4: Format Flag with Multiple Output Modes

**Priority**: 🔥 High
**Effort**: Medium
**Files to Modify**: `cli.py`, `display.py`, `reporting.py`

#### Description
Unified `--format` flag to control output style for different use cases.

#### Problem Statement
Different contexts require different output styles. A single flag to control output format is more intuitive than multiple boolean flags.

#### Solution
Add `--format` flag with multiple predefined output modes.

#### CLI Flags

| Flag | Type | Values | Default | Description |
|------|------|--------|---------|-------------|
| `--format` | choice | `table`, `plain`, `json`, `github`, `quiet` | `table` (or `plain` if CI detected) | Output format |

#### Format Modes

##### 1. `table` - Rich Live Table (Default Interactive)
- Current behavior: Rich live table with colors and emoji
- Auto-refresh at configured rate
- Full visual display with all columns
- Best for: Interactive terminal use

##### 2. `plain` - Plain Text Line-by-Line (Default CI)
- Line-by-line status updates
- Timestamps on each line
- Emoji preserved, colors preserved
- No live updates (only print on change)
- Best for: CI/CD logs, file output

Example:
```
[2025-11-02T10:30:00Z] 💤 PENDING    1/5  test-auth
[2025-11-02T10:30:01Z] 🔄 INIT       1/5  test-auth
[2025-11-02T10:30:05Z] 🚀 APPLYING   1/5  test-auth
[2025-11-02T10:30:12Z] ✅ PASS       1/5  test-auth (12.5s)
```

##### 3. `json` - JSON Output
- Same as `--json` flag
- Outputs structured JSON to stdout
- Suppresses all other output
- Best for: Programmatic consumption, custom tooling

##### 4. `github` - GitHub Actions Annotations
- Outputs GitHub Actions workflow commands
- Groups tests with `::group::` / `::endgroup::`
- Errors use `::error::` annotations
- Warnings use `::warning::` annotations
- Best for: GitHub Actions workflows

Example:
```
::group::Test: test-auth
🔄 Running test-auth...
✅ test-auth passed in 12.5s
  Providers: 2, Resources: 5, Outputs: 3
::endgroup::

::group::Test: test-network
🔄 Running test-network...
::error file=test-network/main.tf,line=15::Terraform apply failed: InvalidAMI: The image id '[ami-12345]' does not exist
❌ test-network failed in 5.2s
::endgroup::
```

##### 5. `quiet` - Minimal Output
- Only print summary at end
- No progress updates
- No live display
- Errors still printed
- Best for: Scripts, when you only care about final result

Example:
```
Running 5 tests...
Done. 4 passed, 1 failed in 45.2s
```

#### Behavior

- `--format` is mutually exclusive with `--json` (or `--json` implies `--format=json`)
- Auto-detection: If CI detected and no `--format` specified, use `plain`
- Can be overridden: `--format=table` forces table even in CI

#### Environment Variables

| Variable | Values | Description |
|----------|--------|-------------|
| `SOUP_STIR_FORMAT` | `table`/`plain`/`json`/`github`/`quiet` | Default format |

#### Acceptance Criteria

- [ ] `--format=table` uses Rich live table
- [ ] `--format=plain` uses line-by-line output
- [ ] `--format=json` outputs valid JSON
- [ ] `--format=github` outputs valid GitHub Actions annotations
- [ ] `--format=quiet` shows only summary
- [ ] Auto-detection works (CI → plain, interactive → table)
- [ ] `SOUP_STIR_FORMAT` environment variable works
- [ ] Each format is properly tested

---

### #5: Timeout Controls

**Priority**: 🔥 High
**Effort**: Medium
**Files to Modify**: `cli.py`, `executor.py`, `runtime.py`

#### Description
Add timeout controls for tests to prevent hanging in CI/CD environments.

#### Problem Statement
Currently, standard tests have no timeout mechanism. A misbehaving test can run indefinitely, blocking CI pipelines and wasting resources. Matrix testing has timeouts, but standard mode does not.

#### Solution
Add global and per-test timeout controls.

#### CLI Flags

| Flag | Type | Default | Description |
|------|------|---------|-------------|
| `--timeout=SECONDS` | int | unlimited | Global timeout for entire test suite (seconds) |
| `--test-timeout=SECONDS` | int | unlimited | Timeout per individual test (seconds) |

#### Environment Variables

| Variable | Type | Description |
|----------|------|-------------|
| `SOUP_STIR_TIMEOUT` | int | Default global timeout (seconds) |
| `SOUP_STIR_TEST_TIMEOUT` | int | Default per-test timeout (seconds) |

#### Timeout Behavior

##### Per-Test Timeout (`--test-timeout`)
- Applies to each individual test
- Timer starts when test begins execution (CLEANING phase)
- Timer stops when test completes (PASS/FAIL/SKIP)
- If timeout is exceeded:
  - Test is terminated (SIGTERM, then SIGKILL after grace period)
  - Test is marked with special status: `TIMEOUT`
  - Test counts as failure in summary
  - Remaining tests continue

##### Global Timeout (`--timeout`)
- Applies to entire test suite
- Timer starts when first test begins
- Timer stops when all tests complete or timeout is hit
- If timeout is exceeded:
  - All running tests are terminated
  - Pending tests are marked as `SKIPPED`
  - Summary shows incomplete status
  - Exit with timeout-specific exit code (124)

##### Timeout Grace Period
- When timeout is hit, send SIGTERM to subprocess
- Wait 5 seconds for graceful termination
- If still running, send SIGKILL
- Mark test as `TIMEOUT` with message about forceful termination

#### Output Examples

**Test Timeout**:
```
⏱️  TIMEOUT   3/5  test-slow (300.0s) - Exceeded --test-timeout=300
```

**Global Timeout**:
```
⏱️  Suite timed out after 600s (--timeout=600)
   Completed: 3/5 tests
   Running: 2 tests (terminated)
   Pending: 0 tests
```

#### Exit Codes

| Code | Meaning |
|------|---------|
| 0 | All tests passed |
| 1 | One or more tests failed |
| 124 | Global timeout exceeded (follows GNU timeout convention) |
| 125 | Test timeout exceeded |

#### JSON Output with Timeouts

```json
{
  "summary": {
    "total": 5,
    "passed": 2,
    "failed": 1,
    "timeout": 1,
    "skipped": 1,
    "duration_seconds": 600.0,
    "timeout_exceeded": true,
    "timeout_type": "global"
  },
  "tests": [
    {
      "name": "test-slow",
      "status": "timeout",
      "duration_seconds": 300.0,
      "timeout_seconds": 300,
      "error_message": "Test exceeded timeout of 300 seconds"
    }
  ]
}
```

#### Acceptance Criteria

- [ ] `--timeout` enforces global timeout
- [ ] `--test-timeout` enforces per-test timeout
- [ ] Timeout tests are marked distinctly (TIMEOUT status)
- [ ] Timeout tests show in summary as separate category
- [ ] Exit code is 124 for global timeout, 125 for test timeout
- [ ] Graceful termination is attempted (SIGTERM before SIGKILL)
- [ ] JSON output includes timeout information
- [ ] JUnit XML marks timeout tests appropriately
- [ ] Environment variables work as defaults

---

### #6: Parallelism Control

**Priority**: 🔥 High
**Effort**: Low
**Files to Modify**: `cli.py`, `executor.py`, `config.py`

#### Description
Add control over test parallelism to allow serial execution or custom concurrency limits.

#### Problem Statement
Currently, parallelism is hardcoded to `os.cpu_count()`. This is not always optimal:
- In CI with limited resources, may want to reduce parallelism
- For debugging, serial execution (`-j 1`) is often necessary
- Some CI environments have quotas that limit concurrent operations

#### Solution
Add `--jobs` flag to control parallelism, similar to `make -j`.

#### CLI Flags

| Flag | Type | Default | Description |
|------|------|---------|-------------|
| `--jobs=N`, `-j N` | int | `auto` | Number of tests to run in parallel |
| `-j` (no value) | flag | `auto` | Use auto-detection (all CPUs) |

Special values:
- `--jobs=1` or `-j 1`: Serial execution (one test at a time)
- `--jobs=0` or `--jobs=auto`: Auto-detect (current behavior: `os.cpu_count()`)
- `--jobs=N`: Run up to N tests in parallel

#### Environment Variables

| Variable | Type | Description |
|----------|------|-------------|
| `SOUP_STIR_JOBS` | int/`auto` | Default parallelism level |

#### Examples

```bash
# Serial execution (debugging)
soup stir --jobs=1
soup stir -j 1

# Limit to 2 parallel tests
soup stir --jobs=2
soup stir -j 2

# Use all CPUs (default)
soup stir --jobs=auto
soup stir -j

# Environment variable
export SOUP_STIR_JOBS=4
soup stir
```

#### Output Changes

Display effective parallelism at start:

```
Running 5 tests with parallelism=1 (serial mode)...
```

```
Running 5 tests with parallelism=4 (4 concurrent)...
```

```
Running 5 tests with parallelism=12 (auto-detected CPUs)...
```

#### Behavior

- Parallelism controls semaphore in `execute_tests()`
- Serial mode (`-j 1`) is deterministic (tests run in sorted order)
- Progress is easier to follow in serial mode
- Useful for:
  - Debugging test failures
  - CI environments with resource constraints
  - Avoiding rate limits on cloud providers
  - Ensuring deterministic test order

#### Acceptance Criteria

- [ ] `--jobs=N` limits concurrent tests to N
- [ ] `-j 1` runs tests serially (one at a time)
- [ ] `-j` (no value) or `--jobs=auto` uses all CPUs
- [ ] Effective parallelism is displayed at start
- [ ] `SOUP_STIR_JOBS` environment variable works
- [ ] Serial mode runs tests in deterministic order
- [ ] Parallelism is reflected in live display (number of active tests)

---

## Medium Priority Improvements

### #7: Timestamps in CI Mode

**Priority**: 🟡 Medium
**Effort**: Low
**Files to Modify**: `display.py`

#### Description
Add timestamps to each output line when running in CI/CD mode.

#### Problem Statement
In CI logs, it's difficult to correlate events or understand when things happened without timestamps. This is especially problematic for long-running tests or when debugging timing issues.

#### Solution
Automatically add timestamps when in CI mode or when explicitly requested.

#### CLI Flags

| Flag | Type | Default | Description |
|------|------|---------|-------------|
| `--timestamps` | boolean | auto (true in CI) | Show timestamps on each line |
| `--no-timestamps` | boolean | false | Disable timestamps even in CI |
| `--timestamp-format` | choice | `iso8601` | Timestamp format |

#### Timestamp Formats

| Format | Example | Description |
|--------|---------|-------------|
| `iso8601` | `2025-11-02T10:30:15.123456Z` | ISO 8601 with microseconds (default) |
| `iso8601-simple` | `2025-11-02T10:30:15Z` | ISO 8601 without microseconds |
| `relative` | `[+00:15.2s]` | Relative to test suite start |
| `elapsed` | `[00:15.2]` | Same as relative but different format |
| `unix` | `1699012215.123456` | Unix timestamp with microseconds |

#### Output Examples

**ISO 8601** (default):
```
[2025-11-02T10:30:00.123456Z] 💤 PENDING    1/5  test-auth
[2025-11-02T10:30:01.234567Z] 🔄 INIT       1/5  test-auth
```

**Relative**:
```
[+00:00.0s] 💤 PENDING    1/5  test-auth
[+00:01.1s] 🔄 INIT       1/5  test-auth
[+00:15.2s] ✅ PASS       1/5  test-auth
```

#### Behavior

- Auto-enabled in CI mode
- Can be forced with `--timestamps`
- Can be disabled with `--no-timestamps`
- Format controlled by `--timestamp-format`
- Timestamps use UTC for consistency across CI environments

#### Environment Variables

| Variable | Values | Description |
|----------|--------|-------------|
| `SOUP_STIR_TIMESTAMPS` | `true`/`false`/`auto` | Enable timestamps |
| `SOUP_STIR_TIMESTAMP_FORMAT` | Format name | Timestamp format |

#### Acceptance Criteria

- [ ] Timestamps are auto-enabled in CI mode
- [ ] `--timestamps` forces timestamps in interactive mode
- [ ] `--no-timestamps` disables in CI mode
- [ ] All timestamp formats work correctly
- [ ] Timestamps are aligned and don't break formatting
- [ ] Timestamps use UTC timezone

---

### #8: Populate `failed_stage` and `error_message` Fields

**Priority**: 🟡 Medium
**Effort**: Low
**Files to Modify**: `executor.py`, `models.py`

#### Description
Populate the currently-empty `failed_stage` and `error_message` fields in `TestResult`.

#### Problem Statement
The `TestResult` data structure has `failed_stage` and `error_message` fields, but they are never populated. This makes it harder to analyze failures programmatically.

#### Solution
Track which stage failed and extract the error message.

#### Failed Stage Values

| Stage | When Set | Description |
|-------|----------|-------------|
| `null` | Test passed | No failure |
| `"INIT"` | `terraform init` failed | Initialization failure |
| `"APPLY"` | `terraform apply` failed | Apply failure |
| `"DESTROY"` | `terraform destroy` failed | Destroy failure (rare) |
| `"ANALYZING"` | JSON parsing failed | State analysis failure |
| `"HARNESS"` | Python exception | Test harness error (not terraform) |

#### Error Message Extraction

Extract error message from parsed Terraform logs:
1. Find first log entry with `@level == "error"`
2. Extract `@message` field
3. If error is structured, extract relevant fields
4. Truncate to reasonable length (e.g., 500 chars)
5. Store in `error_message` field

#### Example

**Before** (current):
```python
TestResult(
    directory="test-network",
    success=False,
    failed_stage=None,  # Not populated!
    error_message=None,  # Not populated!
    ...
)
```

**After** (improved):
```python
TestResult(
    directory="test-network",
    success=False,
    failed_stage="APPLY",
    error_message="Error: aws_instance.example: InvalidAMI: The image id '[ami-12345]' does not exist",
    ...
)
```

#### JSON Output

```json
{
  "name": "test-network",
  "status": "failed",
  "failed_stage": "APPLY",
  "error_message": "Error: aws_instance.example: InvalidAMI: The image id '[ami-12345]' does not exist"
}
```

#### JUnit XML Output

```xml
<testcase name="test-network" classname="terraform.test-network" time="5.2">
  <failure message="Error: aws_instance.example: InvalidAMI" type="TerraformApplyError">
    Stage: APPLY
    Error: aws_instance.example: InvalidAMI: The image id '[ami-12345]' does not exist
  </failure>
</testcase>
```

#### Acceptance Criteria

- [ ] `failed_stage` is populated for all failures
- [ ] `error_message` contains first error from logs
- [ ] Harness exceptions set `failed_stage="HARNESS"`
- [ ] Error messages are truncated if too long
- [ ] JSON output includes these fields
- [ ] JUnit XML uses these fields
- [ ] Passed tests have `null` for both fields

---

### #9: Log Aggregation & Streaming

**Priority**: 🟡 Medium
**Effort**: High
**Files to Modify**: `terraform.py`, `cli.py`, `executor.py`

#### Description
Provide options to aggregate logs or stream them to stdout for better CI integration.

#### Problem Statement
Logs are scattered across multiple directories, making them hard to access in CI environments. Developers need to download artifacts and navigate directory structures to find relevant logs.

#### Solution
Add options to stream logs in real-time or aggregate them into a single file.

#### CLI Flags

| Flag | Type | Default | Description |
|------|------|---------|-------------|
| `--stream-logs` | boolean | false | Stream all terraform logs to stdout |
| `--aggregate-logs=FILE` | path | none | Aggregate all logs into single file |
| `--logs-dir=DIR` | path | auto | Custom directory for log files |

#### Stream Logs Mode (`--stream-logs`)

Stream all Terraform output to stdout in real-time:

```
[test-auth:init] Initializing the backend...
[test-auth:init] Initializing provider plugins...
[test-auth:apply] Terraform will perform the following actions:
[test-auth:apply]   # aws_instance.example will be created
[test-network:init] Initializing the backend...
```

Features:
- Prefix each line with test name and phase
- Color-code by test (if colors enabled)
- Interleave logs from parallel tests
- Include timestamps

#### Aggregate Logs Mode (`--aggregate-logs`)

Write all logs to a single file:

```bash
soup stir --aggregate-logs=all-tests.log
```

File format:
```
========================================
Test: test-auth
Phase: init
Start: 2025-11-02T10:30:00Z
========================================
Initializing the backend...
Initializing provider plugins...
...

========================================
Test: test-auth
Phase: apply
Start: 2025-11-02T10:30:05Z
========================================
Terraform will perform the following actions:
...
```

#### Custom Logs Directory (`--logs-dir`)

Override default log location:

```bash
soup stir --logs-dir=/tmp/stir-logs
```

- All log files written to specified directory
- Useful for CI artifact collection
- Can be ephemeral or persistent

#### Environment Variables

| Variable | Description |
|----------|-------------|
| `SOUP_STIR_STREAM_LOGS` | `true`/`false` - Enable log streaming |
| `SOUP_STIR_LOGS_DIR` | Path - Default logs directory |

#### Acceptance Criteria

- [ ] `--stream-logs` streams all logs to stdout
- [ ] Logs are prefixed with test name and phase
- [ ] Parallel test logs are interleaved correctly
- [ ] `--aggregate-logs` creates single log file
- [ ] Aggregated logs are properly sectioned by test
- [ ] `--logs-dir` changes log output directory
- [ ] Directory is created if it doesn't exist
- [ ] Compatible with other output formats

---

### #10: Summary File Output

**Priority**: 🟡 Medium
**Effort**: Low
**Files to Modify**: `cli.py`, `reporting.py`

#### Description
Save test summary to a file for later analysis or CI artifact collection.

#### Problem Statement
Test summary is only printed to terminal and is not persisted. In CI, it's useful to have a summary file that can be:
- Uploaded as an artifact
- Parsed by other tools
- Used for notifications or reports

#### Solution
Add `--summary-file` flag to save summary in various formats.

#### CLI Flags

| Flag | Type | Default | Description |
|------|------|---------|-------------|
| `--summary-file=FILE` | path | none | Save summary to file |
| `--summary-format` | choice | `json` | Summary file format (`json`/`text`/`markdown`) |

#### Summary Formats

##### JSON Format
```json
{
  "summary": {
    "total": 5,
    "passed": 4,
    "failed": 1,
    "skipped": 0,
    "timeout": 0,
    "duration_seconds": 45.23,
    "start_time": "2025-11-02T10:30:00Z",
    "end_time": "2025-11-02T10:30:45Z"
  },
  "passed": ["test-auth", "test-network", "test-storage", "test-compute"],
  "failed": ["test-database"],
  "skipped": [],
  "timeout": []
}
```

##### Text Format
```
TofuSoup Test Summary
=====================
Total:    5
Passed:   4
Failed:   1
Skipped:  0
Duration: 45.2s

Passed Tests:
  - test-auth
  - test-network
  - test-storage
  - test-compute

Failed Tests:
  - test-database

Generated: 2025-11-02T10:30:45Z
```

##### Markdown Format
```markdown
# TofuSoup Test Summary

**Duration**: 45.2s
**Generated**: 2025-11-02T10:30:45Z

## Results

| Metric | Count |
|--------|-------|
| Total | 5 |
| ✅ Passed | 4 |
| ❌ Failed | 1 |
| ⏭️ Skipped | 0 |

## Passed Tests

- ✅ test-auth
- ✅ test-network
- ✅ test-storage
- ✅ test-compute

## Failed Tests

- ❌ test-database
```

#### Behavior

- Write summary file after all tests complete
- Create parent directories if needed
- Overwrite existing file
- Continue to show summary on terminal (unless `--quiet`)

#### Acceptance Criteria

- [ ] `--summary-file` creates summary file
- [ ] JSON format is valid and parseable
- [ ] Text format is human-readable
- [ ] Markdown format renders properly
- [ ] `--summary-format` controls format
- [ ] Parent directories are created automatically
- [ ] File is created even if tests fail

---

### #11: Per-Phase Timing Breakdown

**Priority**: 🟡 Medium
**Effort**: Medium
**Files to Modify**: `executor.py`, `display.py`, `models.py`

#### Description
Track and display timing for each phase of test execution.

#### Problem Statement
Currently only total test time is shown. When optimizing tests or diagnosing slow CI builds, it's helpful to know which phase is slow (INIT, APPLY, DESTROY, etc.).

#### Solution
Track timestamp at each phase transition and calculate phase durations.

#### Implementation

Add phase timing to `TestResult`:
```python
class TestResult(NamedTuple):
    # ... existing fields ...
    phase_timings: dict[str, float]  # Phase name -> duration in seconds
```

Example:
```python
{
    "CLEANING": 0.5,
    "INIT": 2.0,
    "APPLYING": 8.0,
    "ANALYZING": 0.5,
    "DESTROYING": 1.5
}
```

#### CLI Flags

| Flag | Type | Default | Description |
|------|------|---------|-------------|
| `--show-phase-timing` | boolean | false | Show per-phase timing in output |

#### Output Examples

**Terminal Output** (with `--show-phase-timing`):
```
✅ test-auth - PASS (12.5s total)
   CLEANING:   0.5s (  4%)
   INIT:       2.0s ( 16%)
   APPLYING:   8.0s ( 64%)
   ANALYZING:  0.5s (  4%)
   DESTROYING: 1.5s ( 12%)
```

**JSON Output**:
```json
{
  "name": "test-auth",
  "duration_seconds": 12.5,
  "phase_timings": {
    "CLEANING": 0.5,
    "INIT": 2.0,
    "APPLYING": 8.0,
    "ANALYZING": 0.5,
    "DESTROYING": 1.5
  }
}
```

#### Acceptance Criteria

- [ ] Phase timings are tracked for all tests
- [ ] `--show-phase-timing` displays breakdown
- [ ] Percentages are calculated correctly
- [ ] JSON output includes phase timings
- [ ] Works with all output formats
- [ ] Timing is accurate (uses monotonic clock)

---

### #12: Progress Percentage Indicator

**Priority**: 🟡 Medium
**Effort**: Low
**Files to Modify**: `display.py`

#### Description
Show overall progress as a percentage.

#### Problem Statement
In CI logs or when running many tests, it's hard to gauge overall progress. A simple percentage helps set expectations.

#### Solution
Calculate and display progress percentage.

#### Formula

```
Progress % = (completed_tests / total_tests) * 100
```

Where `completed_tests` = passed + failed + skipped + timeout

#### Output Examples

**Plain Format**:
```
[20%] (1/5) ✅ test-auth - PASS
[40%] (2/5) ✅ test-network - PASS
[60%] (3/5) ❌ test-database - FAIL
[80%] (4/5) ✅ test-storage - PASS
[100%] (5/5) ✅ test-compute - PASS
```

**With Estimated Time Remaining**:
```
[20%] (1/5) ✅ test-auth - PASS - est. 60s remaining
[40%] (2/5) ✅ test-network - PASS - est. 45s remaining
```

#### CLI Flags

| Flag | Type | Default | Description |
|------|------|---------|-------------|
| `--show-progress` | boolean | auto (true in CI) | Show progress percentage |
| `--show-eta` | boolean | false | Show estimated time remaining |

#### Estimation Algorithm

For time remaining estimation:
1. Calculate average time per completed test
2. Multiply by remaining tests
3. Display as `est. Xs remaining`
4. Update after each test completes

#### Acceptance Criteria

- [ ] Progress percentage is calculated correctly
- [ ] Progress shown in plain/CI format
- [ ] `--show-progress` controls display
- [ ] `--show-eta` shows time estimate
- [ ] Estimation becomes more accurate as tests complete

---

### #13: Configurable Refresh Rate

**Priority**: 🟡 Medium
**Effort**: Low
**Files to Modify**: `cli.py`, `display.py`

#### Description
Allow customization of live display refresh rate.

#### Problem Statement
Current refresh rate (0.77 Hz ≈ 1.3 seconds) is hardcoded. Different scenarios benefit from different rates:
- Fast refresh for local development (smoother UX)
- Slow refresh for CI (less log spam)
- No refresh for file output or very long tests

#### Solution
Add `--refresh-rate` flag and `--no-refresh` mode.

#### CLI Flags

| Flag | Type | Default | Description |
|------|------|---------|-------------|
| `--refresh-rate=RATE` | float | `0.77` | Refresh rate in Hz (updates/second) |
| `--no-refresh` | boolean | false | Disable periodic refresh, update only on changes |

#### Examples

```bash
# Fast refresh (2x per second)
soup stir --refresh-rate=2.0

# Slow refresh (every 5 seconds)
soup stir --refresh-rate=0.2

# Only update on actual changes
soup stir --no-refresh
```

#### Auto-Adjustment

In CI mode:
- Default to `--no-refresh` (only output on changes)
- If refresh rate is specified, honor it

#### Environment Variables

| Variable | Type | Description |
|----------|------|-------------|
| `SOUP_STIR_REFRESH_RATE` | float | Default refresh rate |

#### Acceptance Criteria

- [ ] `--refresh-rate` controls update frequency
- [ ] `--no-refresh` only outputs on changes
- [ ] CI mode defaults to `--no-refresh`
- [ ] Refresh rate is accurate (not drifting)
- [ ] Very high refresh rates don't cause performance issues

---

## Low Priority Improvements

### #14: Colored Output Control

**Priority**: 🟢 Low
**Effort**: Low
**Files to Modify**: `cli.py`, `display.py`

#### Description
Add control over ANSI color output.

#### Problem Statement
Some CI systems don't render ANSI colors well. Users should be able to disable colors or force them on.

#### Solution
Add `--color` flag and respect `NO_COLOR` environment variable.

#### CLI Flags

| Flag | Type | Default | Description |
|------|------|---------|-------------|
| `--color=WHEN` | choice | `auto` | When to use colors: `auto`, `always`, `never` |
| `--no-color` | boolean | false | Shorthand for `--color=never` |

#### Color Detection (auto mode)

```
if --color=always:
    use colors
elif --color=never or NO_COLOR env var set:
    no colors
elif stdout is TTY and TERM != "dumb":
    use colors
else:
    no colors
```

#### Environment Variables

| Variable | Effect |
|----------|--------|
| `NO_COLOR` | Disable colors (standard convention) |
| `FORCE_COLOR` | Force colors even in non-TTY |
| `SOUP_STIR_COLOR` | `auto`/`always`/`never` |

#### Examples

```bash
# Disable colors
soup stir --no-color
soup stir --color=never
NO_COLOR=1 soup stir

# Force colors (e.g., when piping to less -R)
soup stir --color=always
FORCE_COLOR=1 soup stir
```

#### Acceptance Criteria

- [ ] `--color=auto` auto-detects TTY
- [ ] `--color=always` forces colors
- [ ] `--color=never` disables colors
- [ ] `NO_COLOR` environment variable works
- [ ] `FORCE_COLOR` environment variable works
- [ ] Emoji are preserved even when colors are disabled

---

### #15: Failure-Only Mode

**Priority**: 🟢 Low
**Effort**: Low
**Files to Modify**: `executor.py`, `cli.py`

#### Description
Stop test execution after first failure or after N failures.

#### Problem Statement
In CI, sometimes you want fast feedback and don't need to run all tests if one fails. Stopping early saves time and resources.

#### Solution
Add `--fail-fast` and `--fail-threshold` flags.

#### CLI Flags

| Flag | Type | Default | Description |
|------|------|---------|-------------|
| `--fail-fast` | boolean | false | Stop after first failure |
| `--fail-threshold=N` | int | unlimited | Stop after N failures |

#### Behavior

##### Fail Fast (`--fail-fast`)
- Stop immediately when any test fails
- Running tests are allowed to complete
- Pending tests are marked as `SKIPPED`
- Summary shows incomplete status

##### Fail Threshold (`--fail-threshold=N`)
- Stop after N tests have failed
- Useful for "stop after a few failures" scenarios
- More flexible than `--fail-fast`

#### Examples

```bash
# Stop at first failure
soup stir --fail-fast

# Stop after 3 failures
soup stir --fail-threshold=3
```

#### Output Example

```
✅ test-auth - PASS
❌ test-network - FAIL
⏭️ test-database - SKIPPED (fail-fast mode)
⏭️ test-storage - SKIPPED (fail-fast mode)

Stopped early: --fail-fast triggered after 1 failure
Completed: 2/5 tests
```

#### Exit Codes

| Code | Meaning |
|------|---------|
| 1 | Tests failed (normal failure exit code) |
| Exit early, but still use code 1 | Fail-fast doesn't change exit code |

#### Acceptance Criteria

- [ ] `--fail-fast` stops after first failure
- [ ] `--fail-threshold=N` stops after N failures
- [ ] Running tests complete before stopping
- [ ] Pending tests are marked as skipped
- [ ] Summary indicates early stop
- [ ] Exit code is still 1 (failure)
- [ ] JSON output shows which tests were skipped due to fail-fast

---

## Summary Table

| # | Improvement | Priority | Effort | Files | Key Features |
|---|-------------|----------|--------|-------|--------------|
| 1 | CI Auto-Detection | 🔥 High | Medium | cli.py, display.py | Auto-detect CI, line-by-line output |
| 2 | JSON Output | 🔥 High | Low | cli.py, models.py, reporting.py | `--json` flag, structured output |
| 3 | JUnit XML | 🔥 High | Medium | cli.py, reporting.py | `--junit-xml`, CI integration |
| 4 | Format Flag | 🔥 High | Medium | cli.py, display.py, reporting.py | table/plain/json/github/quiet |
| 5 | Timeouts | 🔥 High | Medium | cli.py, executor.py, runtime.py | `--timeout`, `--test-timeout` |
| 6 | Parallelism | 🔥 High | Low | cli.py, executor.py, config.py | `--jobs=N`, `-j 1` for serial |
| 7 | Timestamps | 🟡 Medium | Low | display.py | Auto in CI, ISO 8601 / relative |
| 8 | Error Fields | 🟡 Medium | Low | executor.py, models.py | Populate failed_stage, error_message |
| 9 | Log Aggregation | 🟡 Medium | High | terraform.py, cli.py, executor.py | `--stream-logs`, `--aggregate-logs` |
| 10 | Summary File | 🟡 Medium | Low | cli.py, reporting.py | `--summary-file`, json/text/markdown |
| 11 | Phase Timing | 🟡 Medium | Medium | executor.py, display.py, models.py | Per-phase duration tracking |
| 12 | Progress % | 🟡 Medium | Low | display.py | Percentage complete, ETA |
| 13 | Refresh Rate | 🟡 Medium | Low | cli.py, display.py | `--refresh-rate`, `--no-refresh` |
| 14 | Color Control | 🟢 Low | Low | cli.py, display.py | `--color`, respect NO_COLOR |
| 15 | Fail Fast | 🟢 Low | Low | executor.py, cli.py | `--fail-fast`, `--fail-threshold` |

---

**Document Version**: 1.0.0
**Last Updated**: 2025-11-02
**Status**: Draft Specification

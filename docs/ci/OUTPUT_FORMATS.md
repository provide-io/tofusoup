# Output Format Specifications

This document provides detailed specifications for all output formats supported by `soup stir`.

## Table of Contents

- [JSON Format](#json-format)
- [JUnit XML Format](#junit-xml-format)
- [Plain Text Format](#plain-text-format)
- [GitHub Actions Format](#github-actions-format)
- [Quiet Format](#quiet-format)
- [Table Format](#table-format-current)

---

## JSON Format

### Trigger
- `--json` flag
- `--format=json`

### Output Destination
- **stdout** (exclusively - no other output on stdout)
- Errors/warnings go to **stderr**

### Schema

```json
{
  "$schema": "https://json-schema.org/draft/2020-12/schema",
  "type": "object",
  "required": ["summary", "tests"],
  "properties": {
    "summary": {
      "type": "object",
      "required": ["total", "passed", "failed", "skipped", "duration_seconds", "start_time", "end_time"],
      "properties": {
        "total": {"type": "integer", "minimum": 0},
        "passed": {"type": "integer", "minimum": 0},
        "failed": {"type": "integer", "minimum": 0},
        "skipped": {"type": "integer", "minimum": 0},
        "timeout": {"type": "integer", "minimum": 0},
        "duration_seconds": {"type": "number", "minimum": 0},
        "start_time": {"type": "string", "format": "date-time"},
        "end_time": {"type": "string", "format": "date-time"},
        "terraform_version": {"type": "string"},
        "command": {"type": "string"},
        "timeout_exceeded": {"type": "boolean"},
        "timeout_type": {"type": "string", "enum": ["global", "test", null]}
      }
    },
    "tests": {
      "type": "array",
      "items": {
        "type": "object",
        "required": ["name", "status", "duration_seconds"],
        "properties": {
          "name": {"type": "string"},
          "directory": {"type": "string"},
          "status": {"type": "string", "enum": ["passed", "failed", "skipped", "timeout"]},
          "duration_seconds": {"type": "number", "minimum": 0},
          "start_time": {"type": "string", "format": "date-time"},
          "end_time": {"type": "string", "format": "date-time"},
          "providers": {"type": "integer", "minimum": 0},
          "resources": {"type": "integer", "minimum": 0},
          "data_sources": {"type": "integer", "minimum": 0},
          "functions": {"type": "integer", "minimum": 0},
          "ephemeral_functions": {"type": "integer", "minimum": 0},
          "outputs": {"type": "integer", "minimum": 0},
          "warnings": {"type": "boolean"},
          "failed_stage": {"type": ["string", "null"], "enum": ["INIT", "APPLY", "DESTROY", "ANALYZING", "HARNESS", null]},
          "error_message": {"type": ["string", "null"]},
          "timeout_seconds": {"type": ["number", "null"]},
          "logs": {
            "type": "object",
            "properties": {
              "stdout": {"type": "string"},
              "stderr": {"type": "string"},
              "terraform": {"type": "string"}
            }
          },
          "phase_timings": {
            "type": "object",
            "patternProperties": {
              "^[A-Z_]+$": {"type": "number", "minimum": 0}
            }
          }
        }
      }
    },
    "provider_cache": {
      "type": "object",
      "properties": {
        "status": {"type": "string", "enum": ["success", "failed", "skipped"]},
        "duration_seconds": {"type": "number", "minimum": 0},
        "providers_downloaded": {"type": "integer", "minimum": 0},
        "error_message": {"type": ["string", "null"]}
      }
    }
  }
}
```

### Complete Example

```json
{
  "summary": {
    "total": 5,
    "passed": 3,
    "failed": 1,
    "skipped": 1,
    "timeout": 0,
    "duration_seconds": 45.234,
    "start_time": "2025-11-02T10:30:00.123456Z",
    "end_time": "2025-11-02T10:30:45.357890Z",
    "terraform_version": "1.5.7",
    "command": "soup stir /path/to/tests",
    "timeout_exceeded": false,
    "timeout_type": null
  },
  "tests": [
    {
      "name": "test-auth",
      "directory": "/full/path/to/test-auth",
      "status": "passed",
      "duration_seconds": 12.543,
      "start_time": "2025-11-02T10:30:00.123456Z",
      "end_time": "2025-11-02T10:30:12.666456Z",
      "providers": 2,
      "resources": 5,
      "data_sources": 1,
      "functions": 0,
      "ephemeral_functions": 0,
      "outputs": 3,
      "warnings": false,
      "failed_stage": null,
      "error_message": null,
      "timeout_seconds": null,
      "logs": {
        "stdout": "/path/to/cache/logs/test-auth.stdout.log",
        "stderr": "/path/to/cache/logs/test-auth.stderr.log",
        "terraform": "/path/to/test-auth/.soup/logs/terraform.log"
      },
      "phase_timings": {
        "CLEANING": 0.543,
        "INIT": 2.134,
        "APPLYING": 8.234,
        "ANALYZING": 0.432,
        "DESTROYING": 1.200
      }
    },
    {
      "name": "test-network",
      "directory": "/full/path/to/test-network",
      "status": "failed",
      "duration_seconds": 5.234,
      "start_time": "2025-11-02T10:30:12.666456Z",
      "end_time": "2025-11-02T10:30:17.900456Z",
      "providers": 1,
      "resources": 0,
      "data_sources": 0,
      "functions": 0,
      "ephemeral_functions": 0,
      "outputs": 0,
      "warnings": true,
      "failed_stage": "APPLY",
      "error_message": "Error: aws_instance.example: InvalidAMI: The image id '[ami-12345]' does not exist",
      "timeout_seconds": null,
      "logs": {
        "stdout": "/path/to/cache/logs/test-network.stdout.log",
        "stderr": "/path/to/cache/logs/test-network.stderr.log",
        "terraform": "/path/to/test-network/.soup/logs/terraform.log"
      },
      "phase_timings": {
        "CLEANING": 0.234,
        "INIT": 1.500,
        "APPLYING": 2.500,
        "DESTROYING": 1.000
      }
    },
    {
      "name": "test-empty",
      "directory": "/full/path/to/test-empty",
      "status": "skipped",
      "duration_seconds": 0.123,
      "start_time": "2025-11-02T10:30:17.900456Z",
      "end_time": "2025-11-02T10:30:18.023456Z",
      "providers": 0,
      "resources": 0,
      "data_sources": 0,
      "functions": 0,
      "ephemeral_functions": 0,
      "outputs": 0,
      "warnings": false,
      "failed_stage": null,
      "error_message": null,
      "timeout_seconds": null,
      "logs": null,
      "phase_timings": {}
    }
  ],
  "provider_cache": {
    "status": "success",
    "duration_seconds": 2.345,
    "providers_downloaded": 3,
    "error_message": null
  }
}
```

### Pretty-Print Mode

When `--json-pretty` is used, output is indented with 2 spaces for human readability.

### Validation

The JSON output must:
- Be valid JSON (parseable by `json.loads()` or `jq`)
- Conform to the schema above
- Use ISO 8601 format for all timestamps (UTC timezone)
- Include all required fields
- Use `null` for optional fields when not available

---

## JUnit XML Format

### Trigger
- `--junit-xml=FILE`

### Output Destination
- **file** specified by flag
- Parent directories created automatically
- File overwritten if exists

### XML Schema

Based on the de-facto standard JUnit XML format used by Jenkins, GitHub Actions, GitLab CI, etc.

```xml
<?xml version="1.0" encoding="UTF-8"?>
<testsuites
    name="string"
    tests="integer"
    failures="integer"
    errors="integer"
    skipped="integer"
    time="float"
    timestamp="ISO-8601">

  <testsuite
      name="string"
      tests="integer"
      failures="integer"
      errors="integer"
      skipped="integer"
      time="float"
      timestamp="ISO-8601">

    <!-- Passed test -->
    <testcase
        name="string"
        classname="string"
        time="float"
        timestamp="ISO-8601">
      <system-out><![CDATA[...]]></system-out>
    </testcase>

    <!-- Failed test -->
    <testcase
        name="string"
        classname="string"
        time="float"
        timestamp="ISO-8601">
      <failure message="string" type="string"><![CDATA[...]]></failure>
      <system-out><![CDATA[...]]></system-out>
      <system-err><![CDATA[...]]></system-err>
    </testcase>

    <!-- Test with harness error (exception) -->
    <testcase
        name="string"
        classname="string"
        time="float"
        timestamp="ISO-8601">
      <error message="string" type="string"><![CDATA[...]]></error>
      <system-err><![CDATA[...]]></system-err>
    </testcase>

    <!-- Skipped test -->
    <testcase
        name="string"
        classname="string"
        time="float"
        timestamp="ISO-8601">
      <skipped message="string" />
    </testcase>

  </testsuite>
</testsuites>
```

### Field Mapping

| Element/Attribute | Value | Notes |
|-------------------|-------|-------|
| `testsuites/@name` | `--junit-suite-name` or `"soup-stir"` | Top-level suite name |
| `testsuites/@tests` | Total test count | Sum of all tests |
| `testsuites/@failures` | Count of failed tests | `status == "failed"` |
| `testsuites/@errors` | Count of error tests | `failed_stage == "HARNESS"` |
| `testsuites/@skipped` | Count of skipped tests | `status == "skipped"` |
| `testsuites/@time` | Total duration (seconds) | Float with 3 decimal places |
| `testsuites/@timestamp` | Suite start time | ISO 8601 format |
| `testsuite/@name` | `"terraform-tests"` | Fixed suite name |
| `testsuite/@tests` | Total test count | Same as testsuites |
| `testsuite/@failures` | Failed test count | Same as testsuites |
| `testsuite/@errors` | Error test count | Same as testsuites |
| `testsuite/@skipped` | Skipped test count | Same as testsuites |
| `testsuite/@time` | Total duration | Same as testsuites |
| `testsuite/@timestamp` | Suite start time | Same as testsuites |
| `testcase/@name` | Test directory name | e.g., `"test-auth"` |
| `testcase/@classname` | `"terraform." + test name` | e.g., `"terraform.test-auth"` |
| `testcase/@time` | Test duration (seconds) | Float with 3 decimal places |
| `testcase/@timestamp` | Test start time | ISO 8601 format |
| `failure/@message` | First line of error | Truncated to 200 chars |
| `failure/@type` | Error type from stage | See mapping below |
| `failure/text()` | Full error details | Multi-line with context |
| `error/@message` | Exception message | For harness errors |
| `error/@type` | Exception type | e.g., `"PythonException"` |
| `error/text()` | Stack trace | Full traceback |
| `skipped/@message` | Skip reason | e.g., `"No .tf files found"` |
| `system-out` | Test metadata | Providers, resources, outputs |
| `system-err` | Error logs | Terraform error output |

### Failure Types

| `failed_stage` | `failure/@type` |
|----------------|-----------------|
| `"INIT"` | `TerraformInitError` |
| `"APPLY"` | `TerraformApplyError` |
| `"DESTROY"` | `TerraformDestroyError` |
| `"ANALYZING"` | `StateAnalysisError` |
| `"HARNESS"` | `PythonException` (uses `<error>` instead of `<failure>`) |

### Complete Example

```xml
<?xml version="1.0" encoding="UTF-8"?>
<testsuites name="soup-stir" tests="5" failures="1" errors="0" skipped="1" time="45.234" timestamp="2025-11-02T10:30:00.123456Z">
  <testsuite name="terraform-tests" tests="5" failures="1" errors="0" skipped="1" time="45.234" timestamp="2025-11-02T10:30:00.123456Z">

    <!-- Passed test with full metadata -->
    <testcase name="test-auth" classname="terraform.test-auth" time="12.543" timestamp="2025-11-02T10:30:00.123456Z">
      <system-out><![CDATA[
Test: test-auth
Status: PASSED
Duration: 12.543s

Resources:
  Providers: 2
  Resources: 5
  Data Sources: 1
  Functions: 0
  Outputs: 3

Phase Timings:
  CLEANING: 0.543s
  INIT: 2.134s
  APPLYING: 8.234s
  ANALYZING: 0.432s
  DESTROYING: 1.200s

Logs:
  Terraform: /path/to/test-auth/.soup/logs/terraform.log
  Stdout: /path/to/cache/logs/test-auth.stdout.log
  Stderr: /path/to/cache/logs/test-auth.stderr.log
      ]]></system-out>
    </testcase>

    <!-- Failed test with error details -->
    <testcase name="test-network" classname="terraform.test-network" time="5.234" timestamp="2025-11-02T10:30:12.666456Z">
      <failure message="Error: aws_instance.example: InvalidAMI: The image id '[ami-12345]' does not exist" type="TerraformApplyError"><![CDATA[
Stage: APPLY
Duration: 5.234s

Error Message:
Error: aws_instance.example: InvalidAMI: The image id '[ami-12345]' does not exist

Phase Timings:
  CLEANING: 0.234s
  INIT: 1.500s
  APPLYING: 2.500s (FAILED)
  DESTROYING: 1.000s

Logs:
  Terraform: /path/to/test-network/.soup/logs/terraform.log
  Stdout: /path/to/cache/logs/test-network.stdout.log
  Stderr: /path/to/cache/logs/test-network.stderr.log

For full error details, see the log files above.
      ]]></failure>
      <system-out><![CDATA[
Test: test-network
Status: FAILED
Duration: 5.234s

Resources:
  Providers: 1
  Resources: 0
  Data Sources: 0
  Outputs: 0

Warnings: true
      ]]></system-out>
      <system-err><![CDATA[
Error: aws_instance.example: InvalidAMI: The image id '[ami-12345]' does not exist

  on main.tf line 15, in resource "aws_instance" "example":
  15: resource "aws_instance" "example" {
      ]]></system-err>
    </testcase>

    <!-- Skipped test -->
    <testcase name="test-empty" classname="terraform.test-empty" time="0.123" timestamp="2025-11-02T10:30:17.900456Z">
      <skipped message="No .tf files found in test directory" />
    </testcase>

    <!-- Test with timeout -->
    <testcase name="test-slow" classname="terraform.test-slow" time="300.000" timestamp="2025-11-02T10:30:18.023456Z">
      <failure message="Test exceeded timeout of 300 seconds" type="TestTimeoutError"><![CDATA[
Stage: APPLYING (timed out)
Duration: 300.000s
Timeout: 300s

The test exceeded the per-test timeout (--test-timeout=300).
The test process was terminated.

Last known phase: APPLYING

Logs:
  Terraform: /path/to/test-slow/.soup/logs/terraform.log
  Stdout: /path/to/cache/logs/test-slow.stdout.log
  Stderr: /path/to/cache/logs/test-slow.stderr.log
      ]]></failure>
    </testcase>

    <!-- Test with harness error (exception) -->
    <testcase name="test-crash" classname="terraform.test-crash" time="1.234" timestamp="2025-11-02T10:35:18.023456Z">
      <error message="Unexpected Python exception in test harness" type="PythonException"><![CDATA[
Stage: HARNESS
Duration: 1.234s

Exception Type: FileNotFoundError
Exception Message: [Errno 2] No such file or directory: '/missing/path'

Stack Trace:
Traceback (most recent call last):
  File "src/tofusoup/stir/executor.py", line 123, in run_test_lifecycle
    result = await some_operation(path)
  File "src/tofusoup/stir/runtime.py", line 456, in some_operation
    with open(path) as f:
FileNotFoundError: [Errno 2] No such file or directory: '/missing/path'

This is a bug in the test harness, not your Terraform code.
Please report this issue.
      ]]></error>
      <system-err><![CDATA[
Traceback (most recent call last):
  ...full traceback...
      ]]></system-err>
    </testcase>

  </testsuite>
</testsuites>
```

### Validation

The XML must:
- Be valid XML (parseable by standard XML parsers)
- Use CDATA for all multi-line text content
- Escape special characters (`&`, `<`, `>`) in attributes
- Use UTF-8 encoding
- Include XML declaration
- Follow JUnit XML schema conventions

---

## Plain Text Format

### Trigger
- `--format=plain`
- Auto-enabled in CI mode (non-TTY or CI env var detected)

### Output Destination
- **stdout** (mixed with stderr for errors)

### Format

Line-by-line output with timestamps, emoji, and status updates.

### Line Format

```
[timestamp] emoji phase test# test-name [- message]
```

Components:
- **timestamp**: ISO 8601 or relative time (see SPEC.md #7)
- **emoji**: Status/phase emoji (💤🔄🚀✅❌ etc.)
- **phase**: Current phase name (PENDING, INIT, APPLYING, etc.)
- **test#**: Test progress (e.g., `1/5`, `2/5`)
- **test-name**: Test directory name
- **message**: Optional context (log tail, error, metadata)

### Examples

**Startup**:
```
[2025-11-02T10:30:00.123Z] Running 5 tests with parallelism=4...
[2025-11-02T10:30:00.234Z]
[2025-11-02T10:30:00.234Z] 💤 PENDING    1/5  test-auth
[2025-11-02T10:30:00.234Z] 💤 PENDING    2/5  test-network
[2025-11-02T10:30:00.234Z] 💤 PENDING    3/5  test-database
[2025-11-02T10:30:00.234Z] 💤 PENDING    4/5  test-storage
[2025-11-02T10:30:00.234Z] 💤 PENDING    5/5  test-compute
```

**Execution**:
```
[2025-11-02T10:30:01.123Z] 🧹 CLEANING   1/5  test-auth
[2025-11-02T10:30:01.456Z] 🔄 INIT       1/5  test-auth
[2025-11-02T10:30:02.123Z] 🧹 CLEANING   2/5  test-network
[2025-11-02T10:30:03.789Z] 🚀 APPLYING   1/5  test-auth - Creating aws_instance.example
[2025-11-02T10:30:04.234Z] 🔄 INIT       2/5  test-network
[2025-11-02T10:30:07.567Z] 🚀 APPLYING   2/5  test-network - Creating aws_vpc.main
[2025-11-02T10:30:10.123Z] 🔬 ANALYZING  1/5  test-auth
[2025-11-02T10:30:11.456Z] 💥 DESTROYING 1/5  test-auth
```

**Completion**:
```
[2025-11-02T10:30:12.789Z] ✅ PASS       1/5  test-auth (12.5s) - 2 providers, 5 resources, 3 outputs
[2025-11-02T10:30:15.123Z] ❌ FAIL       2/5  test-network (11.1s) - APPLY failed
[2025-11-02T10:30:15.456Z] 🧹 CLEANING   3/5  test-database
[2025-11-02T10:30:16.789Z] ⏭️ SKIPPED    3/5  test-database - No .tf files found
[2025-11-02T10:30:17.123Z] 🔄 INIT       4/5  test-storage
```

**Summary**:
```
[2025-11-02T10:30:45.678Z]
[2025-11-02T10:30:45.678Z] ================================================================================
[2025-11-02T10:30:45.678Z] Test Summary
[2025-11-02T10:30:45.678Z] ================================================================================
[2025-11-02T10:30:45.678Z] Total:    5
[2025-11-02T10:30:45.678Z] Passed:   3 ✅
[2025-11-02T10:30:45.678Z] Failed:   1 ❌
[2025-11-02T10:30:45.678Z] Skipped:  1 ⏭️
[2025-11-02T10:30:45.678Z] Duration: 45.2s
[2025-11-02T10:30:45.678Z]
[2025-11-02T10:30:45.678Z] Failed Tests:
[2025-11-02T10:30:45.678Z]   ❌ test-network (APPLY failed)
[2025-11-02T10:30:45.678Z]
[2025-11-02T10:30:45.678Z] ================================================================================
```

### With Progress Percentage

If `--show-progress` is enabled:

```
[2025-11-02T10:30:12.789Z] [20%] ✅ PASS 1/5 test-auth (12.5s)
[2025-11-02T10:30:15.123Z] [40%] ❌ FAIL 2/5 test-network (11.1s)
[2025-11-02T10:30:16.789Z] [60%] ⏭️ SKIP 3/5 test-database (0.1s)
[2025-11-02T10:30:30.456Z] [80%] ✅ PASS 4/5 test-storage (13.7s)
[2025-11-02T10:30:42.123Z] [100%] ✅ PASS 5/5 test-compute (11.7s)
```

### Relative Timestamps

If `--timestamp-format=relative`:

```
[+00:00.0s] Running 5 tests...
[+00:01.1s] 🧹 CLEANING 1/5 test-auth
[+00:02.5s] 🔄 INIT     1/5 test-auth
[+00:12.5s] ✅ PASS     1/5 test-auth
[+00:23.6s] ❌ FAIL     2/5 test-network
[+00:45.2s] Done. 3 passed, 1 failed
```

---

## GitHub Actions Format

### Trigger
- `--format=github`

### Output Destination
- **stdout** (workflow commands)

### GitHub Actions Workflow Commands

Uses GitHub Actions [workflow commands](https://docs.github.com/en/actions/using-workflows/workflow-commands-for-github-actions):

- `::group::` / `::endgroup::` - Collapsible log sections
- `::error::` - Error annotations
- `::warning::` - Warning annotations
- `::notice::` - Info annotations
- `::set-output::` - Set step outputs (deprecated, but still supported)

### Format

```
::group::Test: test-name
...test execution output...
::endgroup::
```

### Examples

**Test Execution**:

```
::group::Test 1/5: test-auth
🔄 Running test-auth...
  🧹 CLEANING
  🔄 INIT
  🚀 APPLYING - Creating aws_instance.example
  🔬 ANALYZING
  💥 DESTROYING
✅ test-auth passed in 12.5s
  Providers: 2
  Resources: 5
  Data Sources: 1
  Outputs: 3
::endgroup::

::group::Test 2/5: test-network
🔄 Running test-network...
  🧹 CLEANING
  🔄 INIT
  🚀 APPLYING - Creating aws_vpc.main
::error file=test-network/main.tf,line=15,title=Terraform Apply Failed::Error: aws_instance.example: InvalidAMI: The image id '[ami-12345]' does not exist
❌ test-network failed in 5.2s
  Stage: APPLY
  Error: InvalidAMI: The image id '[ami-12345]' does not exist
  Logs: /path/to/test-network/.soup/logs/terraform.log
::endgroup::

::group::Test 3/5: test-database
⏭️ test-database skipped
  Reason: No .tf files found
::endgroup::
```

**Summary**:

```
::group::Summary
Total: 5 tests
✅ Passed: 3
❌ Failed: 1
⏭️ Skipped: 1
Duration: 45.2s

Failed Tests:
  - test-network (APPLY failed)
::endgroup::

::error title=Tests Failed::1 out of 5 tests failed
```

**With Warnings**:

```
::group::Test: test-with-warnings
🔄 Running test-with-warnings...
::warning file=test-with-warnings/main.tf,line=20::Deprecated attribute: "availability_zone" is deprecated. Use "availability_zones" instead
✅ test-with-warnings passed in 8.3s (with warnings)
::endgroup::
```

### Error Annotation Format

```
::error file={file},line={line},col={col},endColumn={endColumn},title={title}::{message}
```

Fields:
- `file`: Path to file (if available from terraform error)
- `line`: Line number (if available)
- `col`: Column number (if available)
- `endColumn`: End column (if available)
- `title`: Error title (e.g., "Terraform Apply Failed")
- `message`: Error message

### Warning Annotation Format

Same as error, but uses `::warning::` instead of `::error::`.

---

## Quiet Format

### Trigger
- `--format=quiet`

### Output Destination
- **stdout** (minimal)
- **stderr** (errors only)

### Format

Only output:
1. A single line at start
2. Errors as they occur (stderr)
3. Final summary

### Examples

**Successful Run**:
```
Running 5 tests...
Done. 5 passed in 45.2s
```

**With Failures**:
```
Running 5 tests...
Error in test-network: Terraform apply failed
Done. 4 passed, 1 failed in 45.2s
```

**With Skipped**:
```
Running 5 tests...
Done. 4 passed, 1 skipped in 23.1s
```

**No Progress Updates**
- No live updates
- No phase changes
- No log messages
- Only start and end

---

## Table Format (Current)

### Trigger
- `--format=table` (default in interactive mode)
- Default when stdout is TTY and no CI detected

### Output Destination
- **stdout** via Rich Live display

### Format

Rich Live table with continuous updates (current behavior).

See main codebase `display.py` for implementation.

### Columns

| Column | Width | Description |
|--------|-------|-------------|
| Status | 4 | Status emoji (💤🔄✅❌) |
| Phase | 4 | Phase emoji (💤🔍🧹🔄🚀💥) |
| # | 7 | Test progress (1/5, 2/5, etc.) |
| Test Suite | flex | Test directory name |
| Elapsed | 10 | Elapsed time (12.5s) |
| Prov | 5 | Provider count |
| Res | 5 | Resource count |
| Data | 5 | Data source count |
| Func | 5 | Function count |
| Eph. Func | 9 | Ephemeral function count (conditional) |
| Outs | 5 | Output count |
| Last Log | flex | Last significant log message |

### Visual Example

```
┌────────┬───────┬─────────┬──────────────┬─────────┬──────┬─────┬──────┬──────┬──────┬───────────────────┐
│ Status │ Phase │    #    │ Test Suite   │ Elapsed │ Prov │ Res │ Data │ Func │ Outs │ Last Log          │
├────────┼───────┼─────────┼──────────────┼─────────┼──────┼─────┼──────┼──────┼──────┼───────────────────┤
│   ✅   │       │   1/5   │ test-auth    │  12.5s  │  2   │  5  │  1   │  0   │  3   │                   │
│   🔄   │   🚀  │   2/5   │ test-network │   8.3s  │  1   │  3  │  0   │  0   │  0   │ Creating aws_vpc  │
│   💤   │   💤  │   3/5   │ test-db      │         │      │     │      │      │      │                   │
│   💤   │   💤  │   4/5   │ test-storage │         │      │     │      │      │      │                   │
│   💤   │   💤  │   5/5   │ test-compute │         │      │     │      │      │      │                   │
└────────┴───────┴─────────┴──────────────┴─────────┴──────┴─────┴──────┴──────┴──────┴───────────────────┘
```

### Features

- Live updates (refresh rate configurable)
- Color coding (green=pass, red=fail, yellow=active, dim=pending)
- Emoji indicators
- Real-time log tailing
- Resource counts
- Elapsed time

---

## Format Comparison Matrix

| Feature | Table | Plain | JSON | GitHub | Quiet |
|---------|-------|-------|------|--------|-------|
| **Interactive** | ✅ | ❌ | ❌ | ❌ | ❌ |
| **CI-Friendly** | ❌ | ✅ | ✅ | ✅ | ✅ |
| **Live Updates** | ✅ | ✅ | ❌ | ✅ | ❌ |
| **Machine Readable** | ❌ | ❌ | ✅ | ❌ | ❌ |
| **Color** | ✅ | ✅* | ❌ | ✅* | ✅* |
| **Emoji** | ✅ | ✅ | ❌ | ✅ | ✅ |
| **Timestamps** | ❌** | ✅ | ✅ | ✅ | ❌ |
| **Progress %** | ❌*** | ✅* | ✅ | ✅ | ❌ |
| **Log Tail** | ✅ | ✅ | ❌ | ✅ | ❌ |
| **File Output** | ❌ | ✅ | ✅ | ✅ | ✅ |
| **Annotations** | ❌ | ❌ | ❌ | ✅ | ❌ |

\* = With flag
\** = Shows elapsed time, not wall clock time
\*** = Shows test count (1/5) not percentage

---

**Document Version**: 1.0.0
**Last Updated**: 2025-11-02
**Status**: Draft Format Specifications

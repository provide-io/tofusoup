# Implementation Guide

This document provides a step-by-step guide for implementing the 15 CI/CD improvements to `soup stir`.

## Table of Contents

- [Implementation Phases](#implementation-phases)
- [Phase 1: Quick Wins](#phase-1-quick-wins-1-2-days)
- [Phase 2: Core CI Features](#phase-2-core-ci-features-3-5-days)
- [Phase 3: Enhanced UX](#phase-3-enhanced-ux-3-4-days)
- [Phase 4: Advanced Features](#phase-4-advanced-features-5-7-days)
- [Testing Strategy](#testing-strategy)
- [Rollout Plan](#rollout-plan)

---

## Implementation Phases

The improvements are organized into 4 phases based on dependencies, complexity, and priority.

### Dependency Graph

```
Phase 1 (Foundation):
  #1 CI Detection ─┬──▶ #4 Format Flag ──▶ #3 JUnit XML
                   │
                   ├──▶ #7 Timestamps
                   │
                   └──▶ #14 Color Control

  #6 Parallelism ───────▶ (Independent)

  #2 JSON Output ───────▶ (Independent)

Phase 2 (Build on Foundation):
  #4 Format Flag ───────▶ #3 JUnit XML
                    └───▶ (GitHub format, quiet)

  #5 Timeouts ──────────▶ (Executor changes)

  #8 Error Fields ──────▶ #2, #3 (Enhances JSON/XML)

  #10 Summary File ─────▶ (Independent)

Phase 3 (Enhancements):
  #11 Phase Timing ─────▶ #2, #3, #10 (Adds to outputs)

  #12 Progress % ───────▶ #4 (Plain format enhancement)

  #15 Fail-fast ────────▶ (Independent)

Phase 4 (Advanced):
  #9 Log Aggregation ───▶ (Complex, depends on stability)

  #13 Refresh Rate ─────▶ #4 (Table format option)
```

---

## Phase 1: Quick Wins (1-2 days)

**Goal**: Foundational improvements that provide immediate value.

### #1: CI Detection & Auto-Adaptation

**Estimated Time**: 3-4 hours

**Files to Create**:
- `src/tofusoup/stir/detection.py` (new)

**Files to Modify**:
- `src/tofusoup/stir/cli.py`
- `src/tofusoup/stir/display.py`

**Steps**:

1. **Create detection module** (`detection.py`):
   ```python
   # Core functions needed:
   def is_ci_environment() -> bool
   def is_tty() -> bool
   def detect_display_mode(...) -> DisplayMode
   ```

2. **Update CLI** (`cli.py`):
   - Add `--ci` / `--no-ci` flags
   - Call `detect_display_mode()` early in run
   - Pass mode to display initialization

3. **Update display** (`display.py`):
   - Add conditional logic for CI mode
   - Implement line-by-line output as alternative to Live table
   - Keep Live table as default for interactive

**Testing**:
- Unit tests for `is_ci_environment()` with mocked env vars
- Unit tests for `is_tty()` with mocked stdout
- Integration test in actual CI (GitHub Actions)
- Manual test in TTY and non-TTY

**Acceptance Criteria**:
- ✅ CI environments auto-detected
- ✅ Line-by-line output in CI
- ✅ `--ci` forces CI mode
- ✅ `--no-ci` forces interactive mode

---

### #7: Timestamps

**Estimated Time**: 2-3 hours

**Dependencies**: #1 (CI Detection)

**Files to Modify**:
- `src/tofusoup/stir/display.py`
- `src/tofusoup/stir/cli.py`

**Steps**:

1. **Add CLI flags**:
   - `--timestamps` / `--no-timestamps`
   - `--timestamp-format=iso8601|relative|unix`

2. **Implement timestamp generation**:
   ```python
   def format_timestamp(format_type: str, start_time: float) -> str:
       if format_type == "iso8601":
           return datetime.utcnow().isoformat() + "Z"
       elif format_type == "relative":
           elapsed = time.time() - start_time
           return f"[+{elapsed:06.1f}s]"
       # ... etc
   ```

3. **Integrate into display**:
   - Auto-enable in CI mode
   - Prefix each line in line-by-line output
   - Don't show in table mode (uses Elapsed column instead)

**Testing**:
- Test all timestamp formats
- Verify auto-enable in CI
- Verify disable with `--no-timestamps`

**Acceptance Criteria**:
- ✅ Timestamps auto-enabled in CI
- ✅ All formats work correctly
- ✅ Flags control behavior

---

### #14: Color Control

**Estimated Time**: 1-2 hours

**Dependencies**: #1 (CI Detection)

**Files to Modify**:
- `src/tofusoup/stir/cli.py`
- `src/tofusoup/stir/display.py`

**Steps**:

1. **Add CLI flag**:
   - `--color=auto|always|never`
   - `--no-color` (shorthand)

2. **Check environment variables**:
   - `NO_COLOR`
   - `FORCE_COLOR`
   - `SOUP_STIR_COLOR`

3. **Configure Rich console**:
   ```python
   console = Console(
       force_terminal=color_mode == "always",
       no_color=color_mode == "never",
       ...
   )
   ```

**Testing**:
- Test with `NO_COLOR=1`
- Test with `--color=never`
- Test with `--color=always` in non-TTY
- Visual verification of colors

**Acceptance Criteria**:
- ✅ `--color` controls output
- ✅ `NO_COLOR` env var respected
- ✅ Auto-detection works

---

### #6: Parallelism Control

**Estimated Time**: 2-3 hours

**Files to Modify**:
- `src/tofusoup/stir/cli.py`
- `src/tofusoup/stir/executor.py`
- `src/tofusoup/stir/config.py`

**Steps**:

1. **Add CLI flag**:
   - `--jobs=N` / `-j N`
   - Handle `N=0` or `auto` as current behavior
   - Handle `N=1` for serial

2. **Update executor**:
   ```python
   def get_parallelism(jobs_flag: int | str | None) -> int:
       if jobs_flag is None or jobs_flag == "auto" or jobs_flag == 0:
           return os.cpu_count() or 4
       return max(1, int(jobs_flag))

   semaphore = asyncio.Semaphore(parallelism)
   ```

3. **Display parallelism**:
   - Show at start: "Running N tests with parallelism=M..."

**Testing**:
- Test with `-j 1` (serial)
- Test with `-j 2`
- Test with `--jobs=auto`
- Verify deterministic order with `-j 1`

**Acceptance Criteria**:
- ✅ `-j N` limits parallelism
- ✅ `-j 1` runs serially
- ✅ Auto-detection works
- ✅ Parallelism displayed at start

---

### #2: JSON Output

**Estimated Time**: 3-4 hours

**Files to Modify**:
- `src/tofusoup/stir/cli.py`
- `src/tofusoup/stir/models.py`
- `src/tofusoup/stir/reporting.py` (new functions)

**Steps**:

1. **Add CLI flags**:
   - `--json`
   - `--json-pretty`

2. **Create JSON builder**:
   ```python
   def build_json_output(results: list[TestResult], ...) -> dict:
       return {
           "summary": {...},
           "tests": [...],
           "provider_cache": {...}
       }
   ```

3. **Suppress other output when `--json`**:
   - No live display
   - No summary panel
   - Only JSON to stdout
   - Errors to stderr

4. **Output JSON**:
   ```python
   if args.json:
       json_data = build_json_output(results, ...)
       print(json.dumps(json_data, indent=2 if args.json_pretty else None))
   ```

**Testing**:
- Test JSON validity (`json.loads(output)`)
- Test with `jq`
- Verify schema compliance
- Test error handling (errors go to stderr)

**Acceptance Criteria**:
- ✅ `--json` outputs valid JSON
- ✅ Schema matches specification
- ✅ No other output on stdout
- ✅ Pretty-print option works

---

## Phase 2: Core CI Features (3-5 days)

**Goal**: Essential CI/CD integrations

### #4: Format Flag (Renderer System)

**Estimated Time**: 1 day

**Dependencies**: #1 (CI Detection)

**Files to Create**:
- `src/tofusoup/stir/renderers/base.py`
- `src/tofusoup/stir/renderers/table.py`
- `src/tofusoup/stir/renderers/plain.py`
- `src/tofusoup/stir/renderers/json.py`
- `src/tofusoup/stir/renderers/github.py`
- `src/tofusoup/stir/renderers/quiet.py`
- `src/tofusoup/stir/renderers/__init__.py`

**Files to Modify**:
- `src/tofusoup/stir/cli.py`
- `src/tofusoup/stir/executor.py`
- `src/tofusoup/stir/display.py` (refactor into table.py)

**Steps**:

1. **Create base renderer interface**:
   ```python
   class BaseRenderer(ABC):
       @abstractmethod
       def start(self, total_tests: int): pass
       @abstractmethod
       def update_status(self, test_name: str, status: dict): pass
       @abstractmethod
       def complete(self, results: list[TestResult]): pass
   ```

2. **Implement renderers**:
   - `TableRenderer`: Refactor existing Live table code
   - `PlainRenderer`: Line-by-line from #1
   - `JSONRenderer`: JSON output from #2
   - `GitHubRenderer`: GitHub Actions annotations
   - `QuietRenderer`: Minimal output

3. **Create registry**:
   ```python
   RENDERERS = {
       "table": TableRenderer,
       "plain": PlainRenderer,
       "json": JSONRenderer,
       "github": GitHubRenderer,
       "quiet": QuietRenderer,
   }
   ```

4. **Integrate into CLI**:
   ```python
   renderer = get_renderer(mode=format, console=console, config={...})
   renderer.start(total_tests=len(test_dirs))
   # ... during execution ...
   renderer.update_status(test_name, status)
   # ... after completion ...
   renderer.complete(results)
   ```

**Testing**:
- Unit test each renderer independently
- Integration tests for each format
- Verify format switching works
- Test in CI for GitHub format

**Acceptance Criteria**:
- ✅ All 5 formats work
- ✅ Renderer system is extensible
- ✅ `--format` controls output
- ✅ Auto-detection uses appropriate format

---

### #3: JUnit XML Output

**Estimated Time**: 4-6 hours

**Dependencies**: #4 (Renderer system provides structure)

**Files to Create**:
- `src/tofusoup/stir/junit.py` (new module for XML generation)

**Files to Modify**:
- `src/tofusoup/stir/cli.py`
- `src/tofusoup/stir/reporting.py`

**Steps**:

1. **Add CLI flag**:
   - `--junit-xml=FILE`
   - `--junit-suite-name=NAME`

2. **Create XML builder**:
   ```python
   def build_junit_xml(results: list[TestResult], ...) -> str:
       # Use xml.etree.ElementTree or lxml
       testsuites = ET.Element("testsuites", ...)
       testsuite = ET.SubElement(testsuites, "testsuite", ...)
       for result in results:
           testcase = ET.SubElement(testsuite, "testcase", ...)
           if result.failed_stage:
               failure = ET.SubElement(testcase, "failure", ...)
       return ET.tostring(testsuites, encoding="unicode")
   ```

3. **Write to file**:
   ```python
   if args.junit_xml:
       xml_path = Path(args.junit_xml)
       xml_path.parent.mkdir(parents=True, exist_ok=True)
       xml_path.write_text(build_junit_xml(results, ...))
   ```

4. **Map fields correctly**:
   - Use proper failure types
   - Include all metadata in system-out
   - Put errors in system-err

**Testing**:
- Validate XML with XSD schema
- Test in Jenkins
- Test in GitHub Actions (upload-artifact + test reporter)
- Test in GitLab CI
- Verify file creation with missing dirs

**Acceptance Criteria**:
- ✅ Valid JUnit XML generated
- ✅ Works in major CI systems
- ✅ All test states represented correctly
- ✅ Parent dirs created automatically

---

### #5: Timeout Controls

**Estimated Time**: 4-6 hours

**Files to Modify**:
- `src/tofusoup/stir/cli.py`
- `src/tofusoup/stir/executor.py`

**Steps**:

1. **Add CLI flags**:
   - `--timeout=SECONDS`
   - `--test-timeout=SECONDS`

2. **Wrap test execution**:
   ```python
   async def run_test_with_timeout(..., timeout: float | None):
       try:
           if timeout:
               return await asyncio.wait_for(
                   run_test_lifecycle(...),
                   timeout=timeout
               )
           else:
               return await run_test_lifecycle(...)
       except asyncio.TimeoutError:
           # Handle timeout
           return TestResult(status="timeout", ...)
   ```

3. **Wrap suite execution**:
   ```python
   async def execute_tests_with_timeout(..., global_timeout: float | None):
       try:
           if global_timeout:
               return await asyncio.wait_for(
                   execute_tests(...),
                   timeout=global_timeout
               )
           # ...
       except asyncio.TimeoutError:
           # Cancel pending, return partial results
   ```

4. **Graceful termination**:
   - SIGTERM → wait 5s → SIGKILL
   - Mark as TIMEOUT status

5. **Update exit codes**:
   - 124 for global timeout
   - 125 for test timeout

**Testing**:
- Test with actual long-running terraform
- Test with `sleep` commands
- Verify graceful termination
- Verify exit codes
- Test timeout in JSON/XML output

**Acceptance Criteria**:
- ✅ Per-test timeout works
- ✅ Global timeout works
- ✅ Graceful termination attempted
- ✅ Exit codes correct
- ✅ Timeout status in outputs

---

### #8: Populate Error Fields

**Estimated Time**: 2-3 hours

**Dependencies**: None (enhances #2, #3)

**Files to Modify**:
- `src/tofusoup/stir/executor.py`
- `src/tofusoup/stir/models.py` (if needed)

**Steps**:

1. **Track failed stage**:
   ```python
   # When init fails:
   return TestResult(
       ...,
       failed_stage="INIT",
       error_message=extract_error_from_logs(...)
   )
   ```

2. **Extract error message**:
   ```python
   def extract_error_message(parsed_logs: list[dict]) -> str | None:
       for log in parsed_logs:
           if log.get("@level") == "error":
               return log.get("@message", "")[:500]  # Truncate
       return None
   ```

3. **Handle exceptions**:
   ```python
   except Exception as e:
       return TestResult(
           ...,
           failed_stage="HARNESS",
           error_message=str(e)
       )
   ```

**Testing**:
- Test with failing init
- Test with failing apply
- Test with Python exception
- Verify fields populated in JSON
- Verify used in JUnit XML

**Acceptance Criteria**:
- ✅ `failed_stage` populated for all failures
- ✅ `error_message` contains first error
- ✅ Harness exceptions marked correctly

---

### #10: Summary File Output

**Estimated Time**: 2-3 hours

**Files to Modify**:
- `src/tofusoup/stir/cli.py`
- `src/tofusoup/stir/reporting.py`

**Steps**:

1. **Add CLI flags**:
   - `--summary-file=FILE`
   - `--summary-format=json|text|markdown`

2. **Implement formatters**:
   ```python
   def format_summary_json(results: list[TestResult]) -> str:
       # Similar to --json but summary-focused

   def format_summary_text(results: list[TestResult]) -> str:
       # Human-readable text

   def format_summary_markdown(results: list[TestResult]) -> str:
       # Markdown with tables
   ```

3. **Write to file**:
   ```python
   if args.summary_file:
       summary = format_summary(results, format=args.summary_format)
       Path(args.summary_file).write_text(summary)
   ```

**Testing**:
- Test all 3 formats
- Verify file creation
- Test markdown rendering (GitHub/GitLab)

**Acceptance Criteria**:
- ✅ All formats work
- ✅ Files created correctly
- ✅ Markdown renders properly

---

## Phase 3: Enhanced UX (3-4 days)

### #11: Per-Phase Timing

**Estimated Time**: 4-5 hours

**Files to Modify**:
- `src/tofusoup/stir/executor.py`
- `src/tofusoup/stir/models.py`
- `src/tofusoup/stir/display.py`

**Steps**:

1. **Track phase timestamps**:
   ```python
   phase_times = {}
   phase_start = time.monotonic()

   # At each phase transition:
   phase_times[prev_phase] = time.monotonic() - phase_start
   phase_start = time.monotonic()
   ```

2. **Add to TestResult**:
   ```python
   class TestResult(NamedTuple):
       # ...
       phase_timings: dict[str, float]
   ```

3. **Add CLI flag**:
   - `--show-phase-timing`

4. **Display in output**:
   - Terminal: breakdown after test completes
   - JSON: include in test object
   - JUnit: in system-out

**Testing**:
- Verify timing accuracy
- Test display flag
- Verify in JSON output

**Acceptance Criteria**:
- ✅ Phase timings tracked
- ✅ Display flag works
- ✅ Included in JSON/XML

---

### #12: Progress Percentage

**Estimated Time**: 2-3 hours

**Dependencies**: #4 (Renderer system)

**Files to Modify**:
- `src/tofusoup/stir/renderers/plain.py`
- `src/tofusoup/stir/cli.py`

**Steps**:

1. **Add CLI flags**:
   - `--show-progress`
   - `--show-eta`

2. **Calculate progress**:
   ```python
   completed = passed + failed + skipped + timeout
   progress = (completed / total) * 100
   ```

3. **Calculate ETA**:
   ```python
   if completed > 0:
       avg_time = total_elapsed / completed
       remaining = total - completed
       eta = avg_time * remaining
   ```

4. **Display**:
   ```
   [40%] (2/5) ✅ test-name - PASS - est. 30s remaining
   ```

**Testing**:
- Test percentage calculation
- Test ETA estimation
- Verify auto-enable in CI

**Acceptance Criteria**:
- ✅ Progress % displayed
- ✅ ETA estimation works
- ✅ Auto-enabled in CI

---

### #15: Fail-Fast Mode

**Estimated Time**: 2-3 hours

**Files to Modify**:
- `src/tofusoup/stir/executor.py`
- `src/tofusoup/stir/cli.py`

**Steps**:

1. **Add CLI flags**:
   - `--fail-fast`
   - `--fail-threshold=N`

2. **Check after each test**:
   ```python
   failure_count = 0
   for result in results:
       if not result.success:
           failure_count += 1
           if fail_fast or (fail_threshold and failure_count >= fail_threshold):
               # Cancel pending tests
               break
   ```

3. **Mark skipped tests**:
   - Tests not yet started marked as skipped
   - Include skip reason in output

**Testing**:
- Test with `--fail-fast`
- Test with `--fail-threshold=2`
- Verify running tests complete
- Verify exit code still 1

**Acceptance Criteria**:
- ✅ Stops after first failure (fail-fast)
- ✅ Stops after N failures (threshold)
- ✅ Pending tests skipped
- ✅ Exit code correct

---

## Phase 4: Advanced Features (5-7 days)

### #9: Log Aggregation & Streaming

**Estimated Time**: 1-2 days

**Files to Modify**:
- `src/tofusoup/stir/terraform.py`
- `src/tofusoup/stir/cli.py`
- `src/tofusoup/stir/executor.py`

**Steps**:

1. **Add CLI flags**:
   - `--stream-logs`
   - `--aggregate-logs=FILE`
   - `--logs-dir=DIR`

2. **Stream logs**:
   ```python
   # In log tailing:
   if stream_logs:
       print(f"[{test_name}:{phase}] {log_line}")
   ```

3. **Aggregate logs**:
   ```python
   # Collect all logs in memory or stream to file
   with open(aggregate_file, "a") as f:
       f.write(f"=== {test_name} {phase} ===\n")
       f.write(log_content)
   ```

4. **Custom logs directory**:
   ```python
   logs_dir = Path(args.logs_dir) if args.logs_dir else default_logs_dir
   ```

**Testing**:
- Test log streaming with parallel tests
- Test log aggregation
- Verify custom logs dir

**Acceptance Criteria**:
- ✅ Logs stream to stdout
- ✅ Logs aggregate to file
- ✅ Custom dir works

---

### #13: Configurable Refresh Rate

**Estimated Time**: 1-2 hours

**Files to Modify**:
- `src/tofusoup/stir/cli.py`
- `src/tofusoup/stir/display.py`

**Steps**:

1. **Add CLI flags**:
   - `--refresh-rate=RATE`
   - `--no-refresh`

2. **Update Live display**:
   ```python
   Live(..., refresh_per_second=refresh_rate)
   ```

3. **Implement no-refresh**:
   - Only update on status change
   - Use event-based updates instead of polling

**Testing**:
- Test different refresh rates
- Test `--no-refresh`
- Verify performance

**Acceptance Criteria**:
- ✅ Refresh rate configurable
- ✅ No-refresh mode works
- ✅ Auto-adjust in CI

---

## Testing Strategy

### Unit Tests

Create unit tests for each new module:

```python
# tests/stir/test_detection.py
def test_is_ci_environment_github():
    with mock.patch.dict(os.environ, {"GITHUB_ACTIONS": "true"}):
        assert is_ci_environment() is True

def test_is_ci_environment_none():
    with mock.patch.dict(os.environ, {}, clear=True):
        assert is_ci_environment() is False

# tests/stir/test_renderers.py
def test_json_renderer_valid_json():
    renderer = JSONRenderer(console, config={})
    renderer.start(3)
    # ... execute ...
    output = renderer.complete(results)
    data = json.loads(output)
    assert "summary" in data
    assert "tests" in data
```

### Integration Tests

Test complete workflows:

```python
# tests/stir/test_integration.py
def test_json_output_integration(tmp_path):
    """Test complete run with JSON output"""
    result = subprocess.run(
        ["soup", "stir", "--json", "tests/fixtures"],
        capture_output=True,
        text=True
    )
    assert result.returncode == 0
    data = json.loads(result.stdout)
    assert data["summary"]["total"] > 0

def test_junit_xml_output(tmp_path):
    """Test complete run with JUnit XML"""
    xml_file = tmp_path / "results.xml"
    subprocess.run(
        ["soup", "stir", f"--junit-xml={xml_file}", "tests/fixtures"],
        check=True
    )
    assert xml_file.exists()
    tree = ET.parse(xml_file)
    root = tree.getroot()
    assert root.tag == "testsuites"
```

### CI Testing

Test in actual CI environments:

```yaml
# .github/workflows/test-soup-stir.yml
name: Test soup stir CI features

on: [push, pull_request]

jobs:
  test-ci-detection:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v3
      - name: Setup Python
        uses: actions/setup-python@v4
      - name: Install
        run: pip install -e .
      - name: Test CI detection
        run: |
          # Should auto-use plain format in CI
          soup stir tests/fixtures
      - name: Test JSON output
        run: |
          soup stir --json tests/fixtures > results.json
          jq . results.json  # Validate JSON
      - name: Test JUnit XML
        run: |
          soup stir --junit-xml=results.xml tests/fixtures
      - name: Upload test results
        if: always()
        uses: actions/upload-artifact@v3
        with:
          name: test-results
          path: results.xml
```

### Manual Testing Checklist

Before each release:

- [ ] Test in interactive terminal (table format)
- [ ] Test in non-TTY (plain format)
- [ ] Test in GitHub Actions
- [ ] Test in GitLab CI
- [ ] Test with `--json` and pipe to `jq`
- [ ] Test with `--junit-xml` and upload to Jenkins
- [ ] Test all timeout scenarios
- [ ] Test with `--jobs=1` (serial)
- [ ] Test with `--fail-fast`
- [ ] Test with `--no-color`

---

## Rollout Plan

### Alpha Release (Internal Testing)

**Target**: Development team only

**Features**:
- Phase 1 complete (#1, #2, #6, #7, #14)
- Basic JSON output
- CI detection

**Testing**:
- Internal CI pipelines
- Developer machines
- Collect feedback

**Duration**: 1 week

### Beta Release (Early Adopters)

**Target**: Early adopters, selected users

**Features**:
- Phase 1 + Phase 2 complete
- All output formats
- JUnit XML
- Timeouts

**Testing**:
- Real-world CI environments
- Various test suites
- Performance testing

**Duration**: 2 weeks

### RC (Release Candidate)

**Target**: All users (opt-in)

**Features**:
- Phase 1-3 complete
- All enhancements
- Documentation complete

**Testing**:
- Wide deployment
- Monitor for issues
- Gather metrics

**Duration**: 1 week

### Stable Release

**Target**: All users (default)

**Features**:
- All phases complete
- Fully documented
- Thoroughly tested

**Rollout**:
- Announce in CHANGELOG
- Update documentation
- Blog post / release notes

---

## File Modification Summary

### New Files

```
src/tofusoup/stir/
├── detection.py                 # CI detection logic
├── junit.py                     # JUnit XML generation
└── renderers/
    ├── __init__.py
    ├── base.py
    ├── table.py
    ├── plain.py
    ├── json.py
    ├── github.py
    └── quiet.py
```

### Modified Files

```
src/tofusoup/stir/
├── cli.py                       # All new CLI flags
├── config.py                    # New constants
├── display.py                   # Refactor into renderers
├── executor.py                  # Timeouts, fail-fast, phase timing
├── models.py                    # New fields in TestResult
├── reporting.py                 # Summary file, JUnit XML
└── terraform.py                 # Log streaming
```

### Test Files

```
tests/stir/
├── test_detection.py            # NEW
├── test_renderers.py            # NEW
├── test_junit.py                # NEW
├── test_timeouts.py             # NEW
├── test_integration.py          # Modified
└── fixtures/                    # Test fixtures
    ├── passing-test/
    ├── failing-test/
    ├── timeout-test/
    └── empty-test/
```

---

## Migration Checklist

For users upgrading from previous versions:

- [ ] No breaking changes - existing commands work as-is
- [ ] New flags are opt-in
- [ ] CI detection improves logs automatically
- [ ] Documentation updated
- [ ] CHANGELOG includes all changes
- [ ] Migration guide (if needed)
- [ ] Deprecation notices (none currently)

---

**Document Version**: 1.0.0
**Last Updated**: 2025-11-02
**Status**: Draft Implementation Guide

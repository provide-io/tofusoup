# CI/CD Improvements - Architecture & Design

This document describes the architectural decisions and design patterns for implementing CI/CD improvements to `soup stir`.

## Table of Contents

- [Design Principles](#design-principles)
- [CI Detection Architecture](#ci-detection-architecture)
- [Output Format Plugin System](#output-format-plugin-system)
- [Display System Refactoring](#display-system-refactoring)
- [Timeout Implementation](#timeout-implementation)
- [Backwards Compatibility](#backwards-compatibility)
- [Extensibility Points](#extensibility-points)
- [Performance Considerations](#performance-considerations)

---

## Design Principles

All improvements follow these core principles:

### 1. **Auto-Adaptive Behavior**
The tool should automatically adapt to its environment without requiring user configuration:
- Detect CI/CD environments and adjust output accordingly
- Detect TTY vs non-TTY and choose appropriate display mode
- Respect standard environment variables (`NO_COLOR`, `CI`, etc.)

### 2. **Backwards Compatibility**
All changes must maintain backwards compatibility:
- Default behavior remains unchanged for interactive use
- New features are opt-in unless auto-detected
- Existing scripts and workflows continue to work
- Exit codes remain consistent

### 3. **Progressive Enhancement**
Features build on each other:
- Basic functionality works without advanced features
- Advanced features can be layered on
- Flags can be combined meaningfully
- No feature should break another

### 4. **Unix Philosophy**
Follow Unix conventions:
- Do one thing well (test execution)
- Compose with other tools (pipes, redirects)
- Use standard formats (JSON, XML)
- Respect standard env vars (`NO_COLOR`, `CI`, `TERM`)
- Follow exit code conventions

### 5. **Fail-Safe Defaults**
When in doubt, choose the safer option:
- Disable fancy features in CI (prefer simple output)
- Show more rather than less (verbose > terse)
- Preserve data (don't truncate errors)
- Timeout rather than hang forever

---

## CI Detection Architecture

### Detection Flow

```
┌─────────────────────────────────┐
│ Start: Determine Display Mode  │
└────────────┬────────────────────┘
             │
             ▼
     ┌───────────────────┐
     │ User specified    │───Yes───▶ Use specified mode
     │ --format or --ci? │
     └────┬──────────────┘
          │ No
          ▼
     ┌───────────────────┐
     │ Check SOUP_STIR_  │───Set───▶ Use env var setting
     │ FORMAT env var    │
     └────┬──────────────┘
          │ Not set
          ▼
     ┌───────────────────┐
     │ Is stdout a TTY?  │───No────▶ Use plain format (CI mode)
     └────┬──────────────┘
          │ Yes
          ▼
     ┌───────────────────┐
     │ Check CI env vars │───Found──▶ Use plain format (CI mode)
     │ (CI, GITHUB_      │
     │ ACTIONS, etc.)    │
     └────┬──────────────┘
          │ None found
          ▼
     ┌───────────────────┐
     │ Use table format  │
     │ (Interactive)     │
     └───────────────────┘
```

### CI Environment Variables

The system checks for these variables (in order of preference):

1. **Generic CI Indicators**:
   - `CI=true` - Standard CI indicator

2. **Specific CI Systems** (alphabetical):
   - `BUILDKITE=true` - Buildkite
   - `CIRCLECI=true` - CircleCI
   - `GITHUB_ACTIONS=true` - GitHub Actions
   - `GITLAB_CI=true` - GitLab CI
   - `JENKINS_URL` - Jenkins (any value)
   - `TEAMCITY_VERSION` - TeamCity (any value)
   - `TF_BUILD=true` - Azure Pipelines
   - `TRAVIS=true` - Travis CI

3. **TofuSoup Overrides**:
   - `SOUP_STIR_CI_MODE=true|false|auto` - Explicit override
   - `SOUP_STIR_FORMAT=table|plain|json|github|quiet` - Format override

### Implementation

```python
# File: src/tofusoup/stir/detection.py (new file)

import os
import sys
from enum import Enum

class DisplayMode(Enum):
    TABLE = "table"      # Rich Live table (interactive)
    PLAIN = "plain"      # Line-by-line (CI-friendly)
    JSON = "json"        # JSON output
    GITHUB = "github"    # GitHub Actions annotations
    QUIET = "quiet"      # Minimal output

def is_ci_environment() -> bool:
    """Detect if running in CI/CD environment."""
    # Check standard CI indicators
    ci_vars = [
        "CI",
        "GITHUB_ACTIONS",
        "GITLAB_CI",
        "JENKINS_URL",
        "CIRCLECI",
        "TRAVIS",
        "BUILDKITE",
        "TEAMCITY_VERSION",
        "TF_BUILD",
    ]
    return any(os.getenv(var) for var in ci_vars)

def is_tty() -> bool:
    """Check if stdout is a TTY."""
    return sys.stdout.isatty()

def detect_display_mode(
    format_flag: str | None = None,
    ci_flag: bool | None = None,
) -> DisplayMode:
    """
    Detect appropriate display mode.

    Priority:
    1. Explicit --format flag
    2. Explicit --ci/--no-ci flag
    3. SOUP_STIR_FORMAT environment variable
    4. SOUP_STIR_CI_MODE environment variable
    5. TTY detection
    6. CI environment detection
    7. Default to table mode
    """
    # 1. Explicit format flag
    if format_flag:
        return DisplayMode(format_flag)

    # 2. Explicit CI flag
    if ci_flag is True:
        return DisplayMode.PLAIN
    elif ci_flag is False:
        return DisplayMode.TABLE

    # 3. Environment variable override
    env_format = os.getenv("SOUP_STIR_FORMAT")
    if env_format:
        return DisplayMode(env_format)

    # 4. CI mode environment variable
    env_ci_mode = os.getenv("SOUP_STIR_CI_MODE", "auto").lower()
    if env_ci_mode == "true":
        return DisplayMode.PLAIN
    elif env_ci_mode == "false":
        return DisplayMode.TABLE

    # 5. TTY detection
    if not is_tty():
        return DisplayMode.PLAIN

    # 6. CI environment detection
    if is_ci_environment():
        return DisplayMode.PLAIN

    # 7. Default to interactive table
    return DisplayMode.TABLE
```

---

## Output Format Plugin System

### Architecture

Rather than hard-coding output formats throughout the codebase, we implement a plugin-based system where each format is a separate renderer.

### Base Renderer Interface

```python
# File: src/tofusoup/stir/renderers/base.py (new file)

from abc import ABC, abstractmethod
from typing import Any
from tofusoup.stir.models import TestResult

class BaseRenderer(ABC):
    """Base class for output renderers."""

    def __init__(self, console: Console, config: dict[str, Any]):
        self.console = console
        self.config = config

    @abstractmethod
    def start(self, total_tests: int):
        """Called when test execution starts."""
        pass

    @abstractmethod
    def update_status(self, test_name: str, status: dict[str, Any]):
        """Called when a test's status changes."""
        pass

    @abstractmethod
    def complete(self, results: list[TestResult]):
        """Called when all tests are complete."""
        pass

    @abstractmethod
    def error(self, message: str):
        """Called when an error occurs."""
        pass
```

### Renderer Implementations

Each output format implements the base renderer:

```
src/tofusoup/stir/renderers/
├── base.py           # Base renderer interface
├── table.py          # Rich Live table (current behavior)
├── plain.py          # Line-by-line plain text
├── json.py           # JSON output
├── github.py         # GitHub Actions annotations
├── quiet.py          # Minimal output
└── __init__.py       # Renderer registry
```

### Renderer Registry

```python
# File: src/tofusoup/stir/renderers/__init__.py

from .table import TableRenderer
from .plain import PlainRenderer
from .json import JSONRenderer
from .github import GitHubRenderer
from .quiet import QuietRenderer

RENDERERS = {
    "table": TableRenderer,
    "plain": PlainRenderer,
    "json": JSONRenderer,
    "github": GitHubRenderer,
    "quiet": QuietRenderer,
}

def get_renderer(mode: str, console: Console, config: dict) -> BaseRenderer:
    """Get renderer for specified mode."""
    renderer_class = RENDERERS.get(mode)
    if not renderer_class:
        raise ValueError(f"Unknown renderer: {mode}")
    return renderer_class(console, config)
```

### Integration with Existing Code

The display system is refactored to use renderers:

```python
# File: src/tofusoup/stir/cli.py (modified)

from tofusoup.stir.renderers import get_renderer
from tofusoup.stir.detection import detect_display_mode

def run_tests(...):
    # Detect display mode
    mode = detect_display_mode(format_flag=format, ci_flag=ci)

    # Create renderer
    renderer = get_renderer(
        mode=mode.value,
        console=console,
        config={
            "timestamps": timestamps,
            "show_progress": show_progress,
            "refresh_rate": refresh_rate,
        }
    )

    # Use renderer throughout execution
    renderer.start(total_tests=len(test_dirs))

    # ... execute tests ...

    for test_name, status in test_statuses.items():
        renderer.update_status(test_name, status)

    # ... tests complete ...

    renderer.complete(results=results)
```

---

## Display System Refactoring

### Current Architecture

```
┌─────────────┐
│ cli.py      │ - Creates Live() display
│             │ - Calls execute_tests()
└──────┬──────┘
       │
       ▼
┌─────────────┐
│ executor.py │ - Modifies global test_statuses dict
│             │ - No awareness of display
└──────┬──────┘
       │
       ▼
┌─────────────┐
│ display.py  │ - Reads test_statuses dict
│             │ - Generates Rich table
│             │ - live_updater() async task
└─────────────┘
```

**Issues**:
- Global mutable state (`test_statuses` dict)
- Tight coupling between executor and display
- Hard to add alternative output formats
- Display logic mixed with business logic

### Proposed Architecture

```
┌─────────────┐
│ cli.py      │ - Detects display mode
│             │ - Creates appropriate renderer
│             │ - Orchestrates execution
└──────┬──────┘
       │
       ├────────────────────────┐
       │                        │
       ▼                        ▼
┌─────────────┐         ┌─────────────┐
│ executor.py │────────▶│ renderer    │
│             │ Events  │ (interface) │
│             │────────▶│             │
└─────────────┘         └──────┬──────┘
                               │
                   ┌───────────┼───────────┐
                   │           │           │
                   ▼           ▼           ▼
            ┌──────────┐ ┌──────────┐ ┌──────────┐
            │  table   │ │  plain   │ │  json    │
            │ renderer │ │ renderer │ │ renderer │
            └──────────┘ └──────────┘ └──────────┘
```

**Benefits**:
- Clean separation of concerns
- Event-driven updates (not polling)
- Easy to add new formats
- Testable renderers
- No global state

### Event System

Instead of polling a global dict, use event-driven updates:

```python
# File: src/tofusoup/stir/events.py (new file)

from dataclasses import dataclass
from enum import Enum

class EventType(Enum):
    TEST_STARTED = "test_started"
    TEST_PHASE_CHANGED = "test_phase_changed"
    TEST_LOG_MESSAGE = "test_log_message"
    TEST_COMPLETED = "test_completed"
    SUITE_STARTED = "suite_started"
    SUITE_COMPLETED = "suite_completed"

@dataclass
class Event:
    type: EventType
    test_name: str | None
    data: dict

class EventBus:
    """Simple event bus for test execution events."""

    def __init__(self):
        self.listeners = []

    def subscribe(self, listener):
        self.listeners.append(listener)

    def publish(self, event: Event):
        for listener in self.listeners:
            listener.on_event(event)
```

Executor publishes events, renderers listen:

```python
# In executor.py
event_bus.publish(Event(
    type=EventType.TEST_PHASE_CHANGED,
    test_name="test-auth",
    data={"phase": "INIT", "timestamp": time.time()}
))

# In renderer
def on_event(self, event: Event):
    if event.type == EventType.TEST_PHASE_CHANGED:
        self.update_display(event.test_name, event.data)
```

---

## Timeout Implementation

### Architecture

Timeouts are implemented using `asyncio.wait_for()` at two levels:

1. **Per-Test Timeout**: Wraps individual test execution
2. **Global Timeout**: Wraps entire test suite

### Per-Test Timeout

```python
# File: src/tofusoup/stir/executor.py (modified)

async def run_test_with_timeout(
    test_dir: Path,
    semaphore: asyncio.Semaphore,
    runtime: StirRuntime,
    timeout: float | None,
) -> TestResult:
    """Run test with optional timeout."""
    try:
        if timeout:
            return await asyncio.wait_for(
                run_test_lifecycle(test_dir, semaphore, runtime),
                timeout=timeout
            )
        else:
            return await run_test_lifecycle(test_dir, semaphore, runtime)

    except asyncio.TimeoutError:
        # Test exceeded timeout
        return TestResult(
            directory=test_dir.name,
            success=False,
            status="timeout",
            duration=timeout,
            error_message=f"Test exceeded timeout of {timeout} seconds"
        )
```

### Global Timeout

```python
# File: src/tofusoup/stir/cli.py (modified)

async def execute_tests_with_timeout(
    test_dirs: list[Path],
    runtime: StirRuntime,
    test_timeout: float | None,
    global_timeout: float | None,
) -> list[TestResult]:
    """Execute tests with optional global timeout."""
    try:
        if global_timeout:
            return await asyncio.wait_for(
                execute_tests(test_dirs, runtime, test_timeout),
                timeout=global_timeout
            )
        else:
            return await execute_tests(test_dirs, runtime, test_timeout)

    except asyncio.TimeoutError:
        # Global timeout exceeded - cancel pending tests
        # Return partial results
        return handle_global_timeout(test_dirs)
```

### Graceful Termination

When timeout occurs, attempt graceful shutdown:

```python
async def terminate_test_gracefully(process: asyncio.subprocess.Process):
    """Terminate test process gracefully."""
    # Send SIGTERM
    process.terminate()

    try:
        # Wait up to 5 seconds for graceful exit
        await asyncio.wait_for(process.wait(), timeout=5.0)
    except asyncio.TimeoutError:
        # Process didn't exit, force kill
        process.kill()
        await process.wait()
```

---

## Backwards Compatibility

### Compatibility Matrix

| Feature | Default Behavior | Change from Current |
|---------|------------------|---------------------|
| Display Mode | Auto-detect (table if interactive, plain if CI) | ✅ Same for interactive, improves CI |
| Output | Terminal display | ✅ No change |
| Exit Codes | 0=success, 1=failure | ✅ No change (added: 124=timeout, 125=test timeout) |
| Log Files | Per-test logs in cache | ✅ No change |
| Parallelism | Auto (all CPUs) | ✅ No change |
| Refresh Rate | 0.77 Hz | ✅ No change |
| Colors | Auto-detect TTY | ✅ No change |

### Migration Path

Users don't need to change anything unless they want new features:

**Phase 1: Passive Improvements** (no action needed)
- CI auto-detection improves CI logs automatically
- All existing commands work unchanged
- Better error messages (failed_stage, error_message populated)

**Phase 2: Opt-In Features** (use new flags)
- `--json` for programmatic output
- `--junit-xml` for CI integration
- `--timeout` for safety
- `--jobs` for control

**Phase 3: Advanced** (power users)
- `--format=github` for GitHub Actions
- `--stream-logs` for debugging
- `--show-phase-timing` for optimization

### Deprecation Policy

No existing features are deprecated. If later versions need to change behavior:

1. **Announce**: Document in CHANGELOG
2. **Warn**: Add deprecation warning (at least one major version)
3. **Migrate**: Provide automatic migration or compatibility flags
4. **Remove**: Only after sufficient warning period

---

## Extensibility Points

The architecture provides several extension points for potential enhancements:

### 1. Custom Renderers

Users can add custom output formats:

```python
# File: custom_renderer.py

from tofusoup.stir.renderers.base import BaseRenderer

class CustomRenderer(BaseRenderer):
    def start(self, total_tests: int):
        # Custom start logic
        pass

    def update_status(self, test_name: str, status: dict):
        # Custom update logic
        pass

    def complete(self, results: list[TestResult]):
        # Custom completion logic
        pass

# Register custom renderer
from tofusoup.stir.renderers import RENDERERS
RENDERERS["custom"] = CustomRenderer

# Use it
soup stir --format=custom
```

### 2. Event Hooks

Subscribe to test execution events:

```python
# File: hooks.py

from tofusoup.stir.events import EventBus, EventType

def on_test_failed(event):
    # Send notification, log to external system, etc.
    if event.type == EventType.TEST_COMPLETED and not event.data["success"]:
        send_slack_notification(f"Test {event.test_name} failed!")

event_bus.subscribe(on_test_failed)
```

### 3. Custom Log Parsers

Parse custom Terraform output:

```python
# File: custom_parser.py

from tofusoup.stir.terraform import LogParser

class CustomLogParser(LogParser):
    def extract_message(self, log_entry: dict) -> str:
        # Custom parsing logic
        pass

# Register parser
LogParser.register("custom", CustomLogParser)
```

### 4. Result Exporters

Export results in custom formats:

```python
# File: exporters.py

class SlackExporter:
    def export(self, results: list[TestResult]):
        # Format results for Slack
        # Post to webhook
        pass

# Use after tests complete
exporter = SlackExporter()
exporter.export(results)
```

---

## Performance Considerations

### Live Display Updates

**Current**: Polling every 1.3 seconds (0.77 Hz)
- ❌ Wastes CPU checking for changes
- ❌ Fixed update rate regardless of activity
- ✅ Simple implementation

**Improved**: Event-driven updates
- ✅ Only update when state changes
- ✅ Reduced CPU usage
- ✅ Faster updates on actual changes
- ❌ Slightly more complex

### Log Tailing

**Current**: Async log tailing per test
- ✅ Real-time updates
- ✅ Non-blocking
- ❌ File I/O overhead

**Optimization**: Log debouncing
- Group log updates (current: 0.5s debounce)
- Batch file writes
- Consider memory buffer for very chatty tests

### Parallel Execution

**Current**: `asyncio.Semaphore` with `os.cpu_count()` limit
- ✅ Good CPU utilization
- ✅ Prevents overload
- ❌ No I/O vs CPU awareness

**Future Enhancement**: Adaptive parallelism
- Detect I/O-bound vs CPU-bound tests
- Adjust parallelism dynamically
- Monitor system load

### JSON Generation

**Trade-off**: Structured logging vs memory

Option 1: Stream JSON to stdout (current plan)
- Build entire result structure in memory
- Generate JSON at end
- ✅ Simple, works for most cases
- ❌ Memory usage for very large suites

Option 2: Streaming JSON (exploratory)
- Use `ijson` or similar
- Stream results as they complete
- ✅ Constant memory
- ❌ More complex, harder to read

**Decision**: Use Option 1 for MVP, Option 2 if needed

### CI Detection

**Performance**: Detection is O(1), happens once at startup
- Check ~10 environment variables: negligible
- TTY check: single syscall
- **Total overhead**: < 1ms

---

## Security Considerations

### Log Sanitization

Terraform logs may contain sensitive data. Consider:

1. **Secrets in Errors**: Terraform errors might expose secrets
   - Solution: Add `--sanitize-logs` flag (exploratory enhancement)
   - Redact patterns like API keys, passwords

2. **File Paths**: Full paths might expose directory structure
   - Solution: Allow relative path display with `--relative-paths`

3. **State Files**: Never log state file contents
   - Already handled: state is only analyzed, not logged

### Artifact Upload

If implementing artifact upload (#9):
- Use secure protocols (HTTPS, S3 with proper auth)
- Respect `.terraformignore` or similar
- Allow opt-out for sensitive environments

### Exit Codes

Exit codes should not leak information:
- ✅ 0 = success, 1 = failure (standard)
- ✅ 124 = timeout (GNU timeout convention)
- ❌ Don't use exit codes to encode test counts or error types

---

## Testing Strategy

### Unit Tests

Test each component in isolation:

```python
# File: tests/test_renderers.py

def test_plain_renderer():
    renderer = PlainRenderer(console, config={})
    renderer.start(total_tests=3)
    renderer.update_status("test1", {"phase": "INIT"})
    output = capture_output()
    assert "test1" in output
    assert "INIT" in output
```

### Integration Tests

Test renderer with actual test execution:

```python
# File: tests/test_integration.py

def test_json_output():
    result = run_soup_stir(["--json", "tests/fixtures"])
    data = json.loads(result.stdout)
    assert data["summary"]["total"] == 3
    assert "tests" in data
```

### End-to-End Tests

Test in actual CI environment:
- GitHub Actions workflow
- GitLab CI pipeline
- Docker container (non-TTY)

---

## File Organization

Proposed new file structure:

```
src/tofusoup/stir/
├── __init__.py
├── cli.py                  # Modified: Use renderers, detect CI
├── config.py               # Modified: Add new config constants
├── detection.py            # NEW: CI detection logic
├── display.py              # Deprecated: Migrate to renderers
├── events.py               # NEW: Event bus for test execution
├── executor.py             # Modified: Emit events, support timeouts
├── models.py               # Modified: Add new fields to TestResult
├── reporting.py            # Modified: Generate JUnit XML, summaries
├── runtime.py              # Modified: Support timeouts
├── terraform.py            # No major changes
├── discovery.py            # No changes
│
└── renderers/              # NEW: Output format renderers
    ├── __init__.py         # Renderer registry
    ├── base.py             # Base renderer interface
    ├── table.py            # Rich Live table (refactored from display.py)
    ├── plain.py            # Plain text line-by-line
    ├── json.py             # JSON output
    ├── github.py           # GitHub Actions annotations
    └── quiet.py            # Minimal output
```

---

**Document Version**: 1.0.0
**Last Updated**: 2025-11-02
**Status**: Draft Architecture

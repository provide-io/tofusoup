# CI/CD Improvements for `soup stir`

This directory contains comprehensive documentation for CI/CD and observability improvements to the `soup stir` command.

## Overview

The `soup stir` command currently provides excellent interactive developer experience with its Rich-based live table display. However, when running in CI/CD pipelines, there are opportunities to improve observability, output formats, and integration with common CI systems.

This documentation suite specifies **15 improvements** categorized by priority:

- **6 High Priority** improvements essential for CI/CD environments
- **7 Medium Priority** improvements for enhanced UX
- **2 Low Priority** nice-to-have features

## Current State

As of today, `soup stir`:
- ✅ Provides beautiful interactive table display using Rich
- ✅ Tracks test progress in real-time with emoji indicators
- ✅ Displays provider/resource/output counts
- ✅ Tails Terraform logs and extracts semantic meaning
- ✅ Supports matrix testing with JSON output
- ❌ **Does NOT detect CI/CD environments**
- ❌ **Does NOT provide alternative output formats for standard mode**
- ❌ **Does NOT have timeout controls for standard tests**
- ❌ **Does NOT allow parallelism customization**
- ❌ **Does NOT generate machine-readable reports (JSON, JUnit XML)**

## Documentation Structure

This suite consists of the following documents:

### 1. [SPEC.md](./SPEC/) - Feature Specifications
Complete technical specifications for all 15 improvements including:
- Feature descriptions
- Acceptance criteria
- CLI flag definitions
- Environment variables
- Configuration options
- Priority and effort estimates

### 2. [ARCHITECTURE.md](./ARCHITECTURE/) - Architecture & Design
Architectural decisions and design patterns:
- CI/CD detection mechanism
- Output format plugin architecture
- Display system refactoring
- Backwards compatibility strategy
- Extensibility points

### 3. [OUTPUT_FORMATS.md](./OUTPUT_FORMATS/) - Output Format Specifications
Detailed specifications for all output formats:
- JSON schema and examples
- JUnit XML schema and examples
- GitHub Actions annotations format
- Plain text format
- TAP (Test Anything Protocol) format

### 4. [IMPLEMENTATION.md](./IMPLEMENTATION/) - Implementation Guide
Step-by-step implementation guide:
- Implementation phases and order
- Files to modify per improvement
- Dependencies between features
- Testing strategy
- Rollout plan

### 5. [API_REFERENCE.md](./API_REFERENCE/) - API & CLI Reference
Complete reference documentation:
- All new CLI flags and arguments
- Environment variable reference
- Configuration file options
- Exit codes
- Signal handling

### 6. [EXAMPLES.md](./EXAMPLES/) - Practical Examples
Real-world usage examples:
- GitHub Actions workflows
- GitLab CI pipelines
- Jenkins pipelines
- CircleCI configuration
- Common patterns and troubleshooting

## Quick Reference: Which Improvement to Use When

### Running in GitHub Actions?
→ Use `--format=github` for native annotations ([#4](./SPEC/#4-format-flag-with-multiple-output-modes))

### Need test results in CI dashboard?
→ Use `--junit-xml=results.xml` ([#3](./SPEC/#3-junit-xml-output))

### Need to parse results programmatically?
→ Use `--json` ([#2](./SPEC/#2-json-output-for-standard-mode))

### Tests running too long?
→ Use `--timeout=600 --test-timeout=300` ([#5](./SPEC/#5-timeout-controls))

### Want cleaner CI logs?
→ Auto-detects CI and adapts ([#1](./SPEC/#1-auto-detect-cicd-environments))

### Debugging test failures?
→ Use `--jobs=1 --stream-logs` ([#6](./SPEC/#6-parallelism-control), [#9](./SPEC/#9-log-aggregation-streaming))

### Want minimal noise in CI?
→ Use `--format=quiet` or `--format=plain` ([#4](./SPEC/#4-format-flag-with-multiple-output-modes))

### Need to know which phase is slow?
→ Use `--show-phase-timing` ([#11](./SPEC/#11-per-phase-timing-breakdown))

### Stop at first failure?
→ Use `--fail-fast` ([#15](./SPEC/#15-failure-only-mode))

## Priority Matrix

| Priority | Count | Improvements |
|----------|-------|--------------|
| 🔥 **High** | 6 | CI Detection, JSON Output, JUnit XML, Format Flag, Timeouts, Parallelism Control |
| 🟡 **Medium** | 7 | Timestamps, Error Fields, Log Aggregation, Summary File, Phase Timing, Progress %, Refresh Rate |
| 🟢 **Low** | 2 | Color Control, Fail-fast |

## Implementation Roadmap

### Phase 1: Quick Wins (1-2 days)
Priority improvements that provide immediate value with minimal effort:
- #1 CI/CD Auto-Detection
- #2 JSON Output
- #6 Parallelism Control
- #7 Timestamps
- #14 Color Control

### Phase 2: Core CI Features (3-5 days)
Essential CI/CD integrations:
- #3 JUnit XML
- #4 Format Flag
- #5 Timeout Controls
- #8 Error Field Population
- #10 Summary File

### Phase 3: Enhanced UX (3-4 days)
Improved observability and diagnostics:
- #11 Per-Phase Timing
- #12 Progress Percentage
- #15 Fail-fast Mode

### Phase 4: Advanced Features (5-7 days)
Power user features:
- #9 Log Aggregation & Streaming
- #13 Configurable Refresh Rate

**Total Estimated Effort**: 12-18 days

## Contributing

When implementing these improvements:

1. Follow the specifications in [SPEC.md](./SPEC/)
2. Adhere to architecture decisions in [ARCHITECTURE.md](./ARCHITECTURE/)
3. Ensure output formats match [OUTPUT_FORMATS.md](./OUTPUT_FORMATS/)
4. Follow implementation order in [IMPLEMENTATION.md](./IMPLEMENTATION/)
5. Add examples to [EXAMPLES.md](./EXAMPLES/)

## Related Documentation

- [soup stir command reference](../commands/stir/) _(if exists)_
- [Matrix testing documentation](../matrix-testing/) _(if exists)_
- [TofuSoup configuration](../configuration/) _(if exists)_

## Feedback & Questions

For questions or feedback on these improvements, please:
- Open an issue on GitHub
- Discuss in team channels
- Update these docs with learnings from implementation

---

**Last Updated**: 2025-11-02
**Status**: Specification Phase
**Version**: 1.0.0

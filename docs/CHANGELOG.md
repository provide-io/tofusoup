# Changelog

All notable changes to this project will be documented in this file.

## [Unreleased] - 2025-10-25

### Removed
- **Provider scaffolding feature** - Removed `tofusoup.provider` and `tofusoup.scaffolding` modules completely (no deprecation period)

### Added
- **New CLI command documentation**:
  - `soup config` command documentation with comprehensive configuration management guide
  - `soup state` command documentation with state inspection, decryption, and validation guides
  - Complete API documentation with extensive usage examples and integration patterns
- **Documentation infrastructure**:
  - Placeholder READMEs for exploratory content (tutorials, development guides, production guides, examples; scope may change)
  - Historical documentation index at `docs/historical/README.md` explaining archived documents
  - Build artifact documentation for `harnesses/bin/` directory with troubleshooting
  - Configuration management guide with examples for dev/CI/production environments
  - State inspection guide with security considerations and workflows

### Changed
- **Matrix testing is now optional** - `wrknv` package no longer required for basic TofuSoup usage
  - Only `soup stir --matrix` flag requires wrknv installation
  - Graceful degradation with clear error messages if wrknv not installed
  - Install separately: `uv tool install wrknv` or `uv pip install -e /path/to/wrknv`
- **Updated all package references** from `wrkenv` to `wrknv` throughout codebase
- **Conformance test documentation** updated to reflect actual directory structure (not aspirational)
- **Matrix testing documentation** completely rewritten:
  - Removed obsolete `soup workenv` command references
  - Clarified built-in matrix testing via `soup stir --matrix`
  - Added comprehensive configuration examples and troubleshooting
- **Documentation organization**:
  - Fixed all broken CONTRIBUTING.md and CLAUDE.md references
  - Updated all internal cross-references
  - Added extensive examples to API documentation

### Fixed
- Build artifact documentation - added note that `harnesses/bin/` is created during build
- Empty documentation directories now have informative placeholder READMEs
- Conformance test documentation structure now matches actual implementation
- All cross-references and "See Also" sections in documentation
- mkdocs build configuration - removed unused `autorefs` plugin

### Documentation
- Documentation builds successfully with `mkdocs build --strict` (no errors)
- All CLI commands now fully documented with examples
- API reference massively expanded with quick examples, integration patterns, and error handling
- Troubleshooting guide updated with matrix testing and build artifact issues
- Installation guide clarified optional dependencies

---

## [Previous Releases]

### Added
- Initial implementation of the `soup` CLI with lazy-loading commands.
- Core modules for `cty`, `hcl`, `wire`, `rpc`, `harness`, and `testing`.
- Go harnesses for CTY, HCL, Wire, and RPC (K/V store).
- Pytest-based conformance testing framework.

- `workenv` tool management system for managing TF, Tofu, Go, etc.
- `stir` command for parallel Terraform integration testing.
- **New migration guide** (`docs/guides/migration.md`) for transitioning from old harness names to unified `soup-go` harness.

### Changed
- Refactored `pyvider-cty` dependencies and stabilized APIs.
- Consolidated test suites under the `soup test` command.
- Standardized on `soup.toml` for all configuration.
- **BREAKING: Unified Go harnesses** - Replaced individual harnesses (`go-cty`, `go-hcl`, `go-rpc`, `go-wire`) with single `soup-go` polyglot harness.
- **Updated harness binary paths** - Changed from `tofusoup/src/tofusoup/harness/go/bin/` to `harnesses/bin/`.
- **Documentation restructure** - Updated all documentation to reflect unified harness architecture.
- **Configuration file references** - Updated from `docs/CONFIG_TOML.md` to `docs/reference/configuration.md`.
- **Removed deprecated commands** - `soup cty test`, `soup rpc test`, and `soup wire test` (use `soup test <suite>` instead).

### Fixed
- Addressed binary mismatches between Python and Go encoders for CTY and Wire protocols.
- **Fixed all harness naming inconsistencies** across README.md, CLAUDE.md, and documentation.
- **Fixed broken documentation links** after file reorganization.
- **Removed stale content** - Moved STATUS.md, PHASE_1_FINDINGS.md, and PHASE_2_COMPLETE.md to `docs/historical/`.

- **Removed empty CLI reference directory** (`docs/reference/cli/`).

### Removed
- **Deprecated test commands**: `soup cty test`, `soup rpc test`, `soup wire test` (replaced by `soup test <suite>`).
- **Individual Go harnesses**: `go-cty`, `go-hcl`, `go-rpc`, `go-wire` (replaced by unified `soup-go`).

### Documentation
- All references to old harness names updated to `soup-go`.
- All file paths updated to new harness binary location.
- Migration guide created to help users transition.
- Stale status documents moved to historical archive.
- Documentation build verification: `mkdocs build --strict` passes with no errors.

### Known Issues
- The `pyvider-builder` project requires a significant refactoring to consolidate Go and Python logic.
- The conformance test suite structure needs to be reorganized according to the architectural plan to better separate unit, integration, and other test types.

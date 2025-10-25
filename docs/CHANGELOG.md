# Changelog

All notable changes to this project will be documented in this file.

## [Unreleased]

### Added
- Initial implementation of the `soup` CLI with lazy-loading commands.
- Core modules for `cty`, `hcl`, `wire`, `rpc`, `harness`, and `testing`.
- Go harnesses for CTY, HCL, Wire, and RPC (K/V store).
- Pytest-based conformance testing framework.
- `.garnish` documentation system with `scaffold` and `render` commands.
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
- **Removed garnish references** from architecture documentation (moved to separate `plating` package).
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

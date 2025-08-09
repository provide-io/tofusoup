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

### Changed
- Refactored `pyvider-cty` dependencies and stabilized APIs.
- Consolidated test suites under the `soup test` command.
- Standardized on `soup.toml` for all configuration.

### Fixed
- Addressed binary mismatches between Python and Go encoders for CTY and Wire protocols.

### Known Issues
- The `pyvider-builder` project requires a significant refactoring to consolidate Go and Python logic.
- The conformance test suite structure needs to be reorganized according to the architectural plan to better separate unit, integration, and other test types.

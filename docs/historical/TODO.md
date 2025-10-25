# TofuSoup Project TODO List

## Overall Goal
Integrate `ctytool` and other components into a comprehensive cross-language testing suite `tofusoup`, focusing on DX, modularity, and extensibility. TofuSoup CLI and testing logic should utilize canonical `pyvider` libraries where available (e.g., `pyvider.wire`, `pyvider.cty`). This document consolidates the TODOs from `tofusoup`, `pyvider-builder`, and `pyvider-cty`.

---

## ✅ **Completed Tasks**

- **[✔] Environment Setup:** Successfully set up Python environment using `uv` and sourced `env.sh`.
- **[✔] Initial Code Exploration:** Explored directory structure, READMEs, and existing `tofusoup` CLI and core logic.
- **[✔] Architecture Design:** Outlined new architecture and CLI structure for `tofusoup` (`cty`, `hcl`, `wire`, `rpc`, `harness`, `testing` modules) and planned `rich` integration.
- **[✔] `tofusoup.cty` Module & CLI:** Implemented and integrated `view`, `convert`, `validate-value`, `test`, and `benchmark` commands.
- **[✔] `tofusoup.hcl` Module & CLI:** Implemented and integrated `view` and `convert` commands.
- **[✔] `tofusoup.wire` Module & CLI Refactored:** Refactored to use `pyvider.conversion.terraform` and `pyvider.cty`, deleting obsolete internal modules.
- **[✔] `tofusoup.rpc` Module & CLI Refactored:** Basic structure in place, RPC Server testability improved, and Python client vs. Python server tests enabled.
- **[✔] `tofusoup.harness` and `generate-harness` CLI:** Implemented logic for building and managing Go test harness.
- **[✔] Unified `tofusoup.testing` and `test` CLI:** Implemented a unified testing framework to run pytest suites.
- **[✔] Pytest Configuration & Project Settings:** Configured `pyproject.toml` to correctly manage test paths.
- **[✔] Code Cleanup and Structure:** Migrated test data and scripts, and removed several obsolete directories and files.
- **[✔] `rich` Integration:** Integrated `pyvider-telemetry` with `rich.logging.RichHandler` for enhanced CLI output.
- **[✔] Documentation:** Updated `tofusoup/README.md` and `docs/PLAN.md`.
- **[✔] `pyvider-builder` Go Component Maturation:** Go builder CLI (`build`, `keygen`, `verify`) matured with Cobra and hclog; Flavor v1.0 packaging implemented.
- **[✔] `pyvider-builder` Python Component Alignment:** Python models (`PsfpFooter`) and signing logic updated to align with Flavor v1.0.
- **[✔] `pyvider-builder` Verifier Roles Clarified:** Go builder's `verify` command is the canonical verifier. Python's `PsfpVerifier` is updated, though interop issues with Go-signed packages persist.
- **[✔] `pyvider-builder` Test Fixtures Updated:** `conftest.py`'s `compiled_go_runtime` fixture refactored to compile the actual Go launcher.
- **[✔] `pyvider-cty` Code Quality:** Ran `pytest`, `ruff`, and fixed a circular import.

---

## 📋 **Pending Tasks**

### **`tofusoup` Project**

-   [ ] **Final Code Cleanup & Verification:**
    -   [ ] Verify deletion of old directories (`ctytool/`, `go-harnesses/`, `kvproto/`, `python-drivers/`).
    -   [ ] Search for and remove any remaining unused files or code snippets (e.g., `tofusoup/src/tf_wire/`).
-   [ ] **Enhance Benchmark Capabilities:**
    -   [ ] Develop or adapt a Go harness for CTY conversion benchmarks to enable Python vs. Go performance comparisons.
    -   [ ] Consider adding benchmark commands/logic for `hcl`, `wire`, and `rpc` modules.
-   [ ] **Refine RPC Module (Future `counter_helper.proto`):**
    -   [ ] (Future) Create, generate stubs for, and adapt `tofusoup.rpc` for `counter_helper.proto`.
-   [ ] **Complete `soup test all` Orchestration:**
    -   [ ] Ensure `soup test all` correctly runs all test suites and aggregates results gracefully.
-   [ ] **Thorough End-to-End Testing & DX Review:**
    -   [ ] Manually test all CLI commands.
    -   [ ] Execute `soup test all` and visually confirm results.
    -   [ ] Review overall Developer Experience.
-   [ ] **Final Documentation Pass:**
    -   [ ] Ensure `env.sh` is fully functional and documented.
    -   [ ] Create/update `CONTRIBUTING.md`.
    -   [ ] Review all documentation for accuracy.

### **`pyvider-builder` Project**

-   [ ] **Directory Restructuring:**
    -   [ ] Create `go/` directory and move `builder/` and `runtime/` into it.
    -   [ ] Rename `go/runtime/` to `go/launcher/`.
    -   [ ] Move `go.mod` and `go.sum` into the `go/` directory.
    -   [ ] Create Python sub-packages: `src/pyvider/builder/packaging/` and `src/pyvider/builder/scaffolding/`.
    -   [ ] Update all Python imports to reflect the new structure.
-   [ ] **Code and Logic Consolidation:**
    -   [ ] Refactor `BuildOrchestrator` in Python to invoke the compiled Go builder binary instead of re-implementing the logic.
    -   [ ] Update `cli.py` to use the refactored `BuildOrchestrator`.
-   [ ] **Implement Scaffolding Templates:**
    -   [ ] Convert hardcoded Python strings in `scaffolding/generator.py` into Jinja2 templates.
    -   [ ] Add `Jinja2` as a dependency.
-   [ ] **Update Testing and CI:**
    -   [ ] Update `tests/` directory structure to mirror the new `src/` layout.
    -   [ ] Create tests for the scaffolding generator.
-   [ ] **Documentation and Cleanup:**
    -   [ ] Update `README.md` to explain the new structure.
    -   [ ] Add comments to the `Makefile`.
    -   [ ] Add docstrings to new/refactored modules.
-   [ ] **Future Enhancements (Post Flavor v1.1):**
    -   [ ] Implement a venv content blocklist feature in `config.json` and the Go launcher.
    -   [ ] Add a CLI command to push a built Flavor package to a provider registry.

### **`pyvider-cty` Project**

-   [ ] **Type Safety:**
    -   [ ] Address remaining `mypy` errors to improve type safety.
-   [ ] **Documentation:**
    -   [ ] Write comprehensive documentation in the `docs/` directory.
-   [ ] **Final Verification:**
    -   [ ] Perform a final verification of all tests and code quality checks.

# 🍲 TofuSoup Conformance Suite

TofuSoup is a comprehensive, cross-language conformance testing suite and utility toolkit for ensuring compatibility and correctness across various implementations of OpenTofu-related technologies, including CTY, HCL, RPC mechanisms, and the Terraform Wire Protocol.

### Core Philosophy

-   **Cross-Language Compatibility:** Ensure that data formats and protocol behaviors are consistent across Go, Python, and other languages in the OpenTofu ecosystem.
-   **Developer Experience (DX):** Provide intuitive tools and clear feedback to developers working on or with these core components.
-   **Modularity & Extensibility:** Structure the suite and CLI in a way that's easy to understand, maintain, and extend with new tests or utilities.

## Installation and Setup

This project uses `uv` for Python environment and package management.

1.  **Clone the Repository:**
    ```bash
    git clone <repository_url>
    cd tofusoup
    ```

2.  **Setup Environment:**
    The `env.sh` script in the project root is the recommended way to set up your development environment.
    ```bash
    source env.sh
    ```
    This script will create a Python virtual environment, install all required dependencies in editable mode using `uv`, and make the `soup` CLI available in your shell.

3.  **Verify Installation:**
    ```bash
    soup --version
    ```

## The `soup` Command-Line Interface (CLI)

The `soup` CLI is your primary interface for interacting with the suite. It is organized into logical subcommands.

---
```
Usage: soup [OPTIONS] COMMAND [ARGS]...

Options:
  --help  Show this message and exit.

Commands:
  cty      Utilities for CTY data.
  garnish  Manage component asset bundles (docs, examples, tests).
  harness  Build and manage language-specific CLI implementations.
  hcl      Utilities for HCL file processing.
  stir     Run parallel Terraform integration tests.
  test     Run cross-language conformance tests.
  ...
```
---

### 🛠️ `soup harness`

Builds and manages language-specific implementations of the TofuSoup CLI, such as `soup-go`.

```ascii
                            ┌──────────────────┐
[Go Source Code] ────► soup harness build ────► │ 🍲 soup-go │
                            └──────────────────┘
```

This command group allows you to `build`, `list`, `clean`, and `verify` the programs that provide feature parity with the main Python CLI in other languages.

*See the [Managing Language CLIs Guide](./guides/02-managing-language-clis.md) for more details.*

---
```
Usage: soup [OPTIONS] COMMAND [ARGS]...

Options:
  --help  Show this message and exit.

Commands:
  cty      Utilities for CTY data.
  garnish  Manage component asset bundles (docs, examples, tests).
  harness  Build and manage language-specific CLI implementations.
  hcl      Utilities for HCL file processing.
  stir     Run parallel Terraform integration tests.
  test     Run cross-language conformance tests.
  ...
```
---

### ✅ `soup test`

Runs the Pytest-based conformance test suites.

```ascii
                                 ┌────────────┐
[Python Conformance Tests] ────► │ 🍲 soup-go │
 (souptest_*.py)           │     └────────────┘
                           ▼
                     soup test all
                           │
                           ▼
                    [PASS / FAIL]
```

This is the primary command for validating cross-language compatibility. It executes tests (prefixed with `souptest_`) that compare the behavior of Python implementations against the language-specific CLIs like `soup-go`. Note that `pytest` is reserved for testing the `tofusoup` tool itself.

*See the [Conformance Testing Guide](./guides/01-running-conformance-tests.md) for more details.*

---
```
Usage: soup [OPTIONS] COMMAND [ARGS]...

Options:
  --help  Show this message and exit.

Commands:
  cty      Utilities for CTY data.
  garnish  Manage component asset bundles (docs, examples, tests).
  harness  Build and manage language-specific CLI implementations.
  hcl      Utilities for HCL file processing.
  stir     Run parallel Terraform integration tests.
  test     Run cross-language conformance tests.
  ...
```
---

### 🧱 `soup cty` & `soup hcl`

Provides utilities for inspecting, converting, and validating CTY and HCL data formats.

```ascii
┌──────────┐     ┌─────────────────┐     ┌───────────┐
│ file.hcl │───► │ soup hcl convert│ ───►│ file.json │
└──────────┘     └─────────────────┘     └───────────┘
```

These commands are invaluable for debugging data structures. You can `view` HCL files as CTY, `convert` between formats, and `validate` CTY values against a type schema.

*See the [CTY and HCL Tools Guide](./guides/03-using-cty-and-hcl-tools.md) for more details.*

---
```
Usage: soup [OPTIONS] COMMAND [ARGS]...

Options:
  --help  Show this message and exit.

Commands:
  cty      Utilities for CTY data.
  garnish  Manage component asset bundles (docs, examples, tests).
  harness  Build and manage language-specific CLI implementations.
  hcl      Utilities for HCL file processing.
  stir     Run parallel Terraform integration tests.
  test     Run cross-language conformance tests.
  ...
```
---

### 📄 `soup garnish`

Manages **Component Asset Bundles** (`.garnish/`), which co-locate documentation, examples, and tests with component source code.

```ascii
[component.py] + [*.garnish/] ────► soup garnish render ────► [docs.md]
                                │
                                └─► soup garnish test ──────► [Test Results]
```

This powerful system allows you to `scaffold` new bundles, `render` Terraform Registry-compliant documentation, and `test` the component using its co-located conformance tests.

*See the [Authoring Garnish Bundles Guide](./guides/04-authoring-garnish-bundles.md) for more details.*

---
```
Usage: soup [OPTIONS] COMMAND [ARGS]...

Options:
  --help  Show this message and exit.

Commands:
  cty      Utilities for CTY data.
  garnish  Manage component asset bundles (docs, examples, tests).
  harness  Build and manage language-specific CLI implementations.
  hcl      Utilities for HCL file processing.
  stir     Run parallel Terraform integration tests.
  test     Run cross-language conformance tests.
  ...```
---

### 🍲 `soup stir`

Runs parallel, multi-threaded Terraform integration tests against a provider.

```ascii
┌──────────┐   ┌─────────────┐     ┌───────────┐     ┌────────────────┐
│ Provider │ + │ Test *.tf's │───► │ soup stir │───► │ Matrix Results │
└──────────┘   └─────────────┘     └───────────┘     └────────────────┘
```

`stir` discovers test cases in subdirectories and runs a full `init`, `apply`, and `destroy` lifecycle for each in parallel. It is also designed for **matrix testing**, allowing you to validate a provider's behavior across multiple versions of Terraform and OpenTofu.

*See the [Matrix Testing Guide](./guides/05-matrix-testing-with-stir.md) for more details.*

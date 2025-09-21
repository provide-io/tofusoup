# Garnish Component Asset Bundle System: Design Specification

> **NOTE:** This functionality has been moved to the separate `plating` package. This document is kept for historical reference. See the `plating` package documentation for current implementation details.

This document specifies the design for the `.garnish` system, a robust, automated, and developer-friendly system for managing all non-code assets related to a `pyvider` framework component.

## 1. Guiding Principles

-   **Schema as the Source of Truth:** The in-code `PvsSchema` definition is the definitive source for all technical details.
-   **Co-location of Assets:** A component's documentation, examples, and tests are physically co-located with its Python source code.
-   **Developer Experience:** The system is intuitive, works well with standard development tools, and minimizes boilerplate.
-   **Non-Destructive Workflow:** The tool will never overwrite developer-authored source assets like templates or examples.

## 2. Core Concepts

-   **Component:** A single unit within a provider (Resource, Data Source, or Function).
-   **Garnish Bundle:** A version-controlled `.garnish` directory containing all non-Python assets for one or more components. This includes documentation templates, examples, and co-located conformance tests.
-   **Template:** A Jinja2 file (`.tmpl.md`) that serves as the blueprint for a documentation page.
-   **Partial:** A reusable snippet of content (static Markdown or a dynamic template).

## 3. Workflow Commands

The system is driven by three primary CLI commands under `soup garnish`:

### `soup garnish scaffold`

-   **Purpose:** To **scaffold new, missing asset bundles** for components.
-   **Behavior:** The tool scans for components and creates a default `.garnish` bundle with standard templates, examples, and test stubs if one does not already exist. **This command is non-destructive and will never overwrite existing files.**

### `soup garnish render`

-   **Purpose:** To **render all existing templates** into final, static Markdown documentation.
-   **Behavior:** The tool discovers all `.garnish` bundles, introspects the live Python schema for each component, and renders the corresponding template to an output directory (e.g., `docs/`). **This command always overwrites the output files** to ensure they are up-to-date.

### `soup garnish test`

-   **Purpose:** To **discover and run all co-located conformance tests** for one or more components.
-   **Behavior:** The tool will scan the `tests/` subdirectory within `.garnish` bundles and execute any `souptest_*.py` files found. This provides a powerful way to run targeted conformance tests for a specific component or a group of related components, aggregating them into a single test run.

## 4. File and Directory Conventions

The `.garnish` directory is the core convention.

### Single-Component Bundle (Sidecar)

This is the standard for most components.

```
src/pyvider/components/resources/
├── my_resource.py
└── my_resource.garnish/
    ├── docs/
    │   ├── my_resource.tmpl.md
    │   └── notes.md
    ├── examples/
    │   └── basic.tf
    └── tests/
        └── souptest_my_resource.py
```

### Multi-Component Bundle (Sidecar)

For `.py` files containing multiple components (e.g., `numeric_functions.py`), the `.garnish` directory contains subdirectories for each component.

```
src/pyvider/components/functions/
├── numeric_functions.py
└── numeric_functions.garnish/
    ├── add/
    │   ├── docs/
    │   │   └── add.tmpl.md
    │   ├── examples/
    │   │   └── example.tf
    │   └── tests/
    │       └── souptest_add_function.py
    └── subtract/
        ├── docs/
        │   └── subtract.tmpl.md
        └── examples/
            └── example.tf```

## 5. Template Engine and Context

The system uses **Jinja2** as its template engine. Each template is rendered with a rich context object and a set of custom functions.

-   `{{ schema() }}`: Renders the complete "Argument Reference" section.
-   `{{ example('name') }}`: Injects a named code example.
-   `{{ include('filename') }}`: Injects a static partial.
-   `{{ render('filename') }}`: Injects and renders a dynamic template partial.

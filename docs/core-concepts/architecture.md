# Architecture Overview

The `TofuSoup` project is a modular, CLI-driven framework designed for cross-language conformance testing and development tooling within the OpenTofu ecosystem.

The architecture is segmented into several key domains:

1.  **Main CLI (`cli.py`)**: The central entry point, built with `click`. It uses a `LazyGroup` to ensure fast startup times by only loading the code for a specific subcommand when it is invoked.

2.  **Core Utilities (`common/`)**: Provides shared services for all other components, including:
    -   **Configuration (`config.py`)**: Loads and parses the `soup.toml` file.
    -   **Exceptions (`exceptions.py`)**: Defines custom, project-specific exceptions.
    -   **Rich Output (`rich_utils.py`)**: Helpers for creating enhanced terminal output with the `rich` library.

3.  **Protocol/Component Tooling**: Each core technology (`cty`, `hcl`, `rpc`, `wire`) has a dedicated module containing its CLI implementation and business logic. This modular design makes the system easy to extend.

4.  **Harness Management (`harness/`)**: This component is responsible for the lifecycle of external test harnesses, which are primarily Go binaries. It abstracts the details of building, locating, and cleaning these executables, with behavior configurable via `soup.toml`.

5.  **Conformance Testing (`testing/`, `conformance/`)**: This is the core of the suite. The `testing/` module provides the `soup test` CLI and logic for invoking `pytest`. The actual test suites reside in `conformance/`.



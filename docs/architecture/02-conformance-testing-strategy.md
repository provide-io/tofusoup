# Conformance Testing Strategy

This document outlines the architecture for the TofuSoup conformance testing suite.

## Testing Philosophy: `souptest` vs. `pytest`

A core distinction in this project is the separation of concerns in testing:
-   **Conformance Tests (`souptest_*.py`)**: These tests, located in `tofusoup/conformance/`, are for verifying **cross-language compatibility**. They compare the behavior of Python implementations against the canonical Go harnesses. They are run via the `soup test` command.
-   **Internal Tests (`test_*.py`)**: These are standard unit and integration tests for the `tofusoup` tool **itself**. They are located in `tofusoup/tests/` and are run using `pytest` directly.

## Architectural Design

The conformance suite is organized into a hierarchical and purpose-driven structure to ensure clarity, prevent duplication, and provide a scalable foundation for comprehensive testing.

### Design Principles

1.  **Hierarchical Organization**: Reflect test complexity and dependencies.
2.  **Cross-Cutting Separation**: Create dedicated areas for security, performance, and integration.
3.  **Single Source of Truth**: Eliminate duplication in test scenarios and fixtures.
4.  **Clear Purpose**: Each directory has an explicit, non-overlapping responsibility.

### Directory Structure

```
conformance/
├── README.md                           # Testing strategy and execution guide
├── conftest.py                         # Global fixtures and matrix configurations
│
├── unit/                               # Individual protocol conformance
│   ├── souptest_cty_conformance.py
│   ├── souptest_wire_conformance.py
│   └── souptest_rpc_conformance.py
│
├── integration/                        # Cross-protocol integration testing
│   ├── souptest_full_stack_matrix.py      # Complete CTY→Wire→RPC flow
│   └── souptest_provider_lifecycle.py     # Full Terraform provider scenarios
│
├── security/                           # Security-focused conformance
│   └── souptest_crypto_matrix.py          # All cipher/curve combinations
│
├── scenarios/                          # End-to-end BDD-style scenario testing
│   ├── terraform_equivalence/
│   │   ├── basic_operations.feature
│   │   └── step_definitions/
│   └── souptest_scenario_runner.py
│
└── fixtures/                           # Shared test data and configuration
    ├── cty_data/
    └── certificates/
```

This architecture provides a robust framework for implementing matrix-based testing and ensuring systematic validation of TofuSoup components against their canonical Go counterparts.

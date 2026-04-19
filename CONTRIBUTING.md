# Contributing to tofusoup

Thanks for contributing to tofusoup — the OpenTofu/Terraform state + registry inspection toolkit. This guide covers day-to-day development, quality gates, and PR expectations.

## Prerequisites

- Python 3.11+
- `uv` (`curl -LsSf https://astral.sh/uv/install.sh | sh`)
- Terraform 1.5+ or OpenTofu 1.6+ (for conformance tests against real binaries)

## Development Setup

```bash
git clone https://github.com/provide-io/tofusoup
cd tofusoup
uv sync
```

## Quality Gates

Before opening a PR:

```bash
make quality         # ruff lint + format, mypy strict, pytest with coverage gate
make test            # unit + integration
make test-conformance  # conformance suite against real terraform / opentofu binaries
```

Requirements:
- **100% branch coverage** on `src/tofusoup/**` (enforced).
- **mypy strict mode**. No `type: ignore` without an inline justification.
- **ruff** lint + format must pass.
- Files ≤ 500 lines.
- SPDX headers on every source/config file (`Apache-2.0`).

## Commits

- Conventional prefixes: `feat(registry): …`, `fix(state): …`, `refactor(hcl): …`, `test(conformance): …`, `docs: …`, `chore: …`.
- Subject ≤ 72 chars.
- Do not mention AI assistance. No `Co-Authored-By:` trailers.
- Canonical email: `code@tim.life` or `code@provide.io`.

## Pull Requests

1. Run `make quality` (must pass).
2. For state-format / registry changes, run `make test-conformance` against both terraform and opentofu.
3. PR description notes any changes to state schema handling or registry query semantics.

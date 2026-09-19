# Provider Lint Suite Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Ship a public `soup lint` command that verifies provider-defined validation diagnostics directly and through an isolated OpenTofu native-lint run.

**Architecture:** A versioned TOML suite is parsed into immutable models. The direct runner launches a tfprotov6 provider with the existing generic driver and dispatches only declared cases; the native runner installs the same binary into a temporary filesystem mirror, then runs `tofu init` and `tofu validate -json -lint`. Their results remain separate in the JSON and terminal renderers.

**Tech Stack:** Python 3.11+, Click, attrs, Rich, `pyvider.protocols.tfprotov6`, pytest, OpenTofu CLI.

______________________________________________________________________

## File map

- `src/tofusoup/lint/models.py`: frozen suite, case, diagnostic expectation, and result models.
- `src/tofusoup/lint/suite.py`: TOML loading and semantic validation.
- `src/tofusoup/lint/direct.py`: protocol-level dispatch and diagnostic normalization.
- `src/tofusoup/lint/opentofu.py`: isolated filesystem-mirror installation and OpenTofu subprocess lane.
- `src/tofusoup/lint/render.py`: stable terminal and JSON output.
- `src/tofusoup/lint/cli.py`: public Click command and exit policy.
- `src/tofusoup/cli.py`: lazy registration for `soup lint`.
- `tests/lint/`: unit and integration-style TDD tests for every public behavior.
- `docs/reference/cli.md`, `docs/guides/provider-linting.md`, `docs/architecture/08-provider-linting.md`, `mkdocs.yml`: user documentation and navigation.
- `VERSION`, `CHANGELOG.md`: release version and release notes after all verification is green.

### Task 1: Register the public command

**Files:**

- Modify: `src/tofusoup/cli.py`

- Create: `src/tofusoup/lint/__init__.py`

- Create: `src/tofusoup/lint/cli.py`

- Create: `tests/lint/__init__.py`

- Create: `tests/lint/test_cli.py`

- [ ] **Step 1: Write the failing CLI-help test.**

```python
from click.testing import CliRunner

from tofusoup.cli import main_cli


def test_lint_command_is_listed_and_describes_both_lanes() -> None:
    result = CliRunner().invoke(main_cli, ["lint", "--help"])

    assert result.exit_code == 0, result.output
    assert "Direct provider validation" in result.output
    assert "OpenTofu native linting" in result.output
    assert "--provider" in result.output
    assert "--opentofu" in result.output
```

- [ ] **Step 2: Run the test to verify RED.**

Run: `uv run pytest tests/lint/test_cli.py::test_lint_command_is_listed_and_describes_both_lanes -v`

Expected: FAIL because Click reports `No such command 'lint'`.

- [ ] **Step 3: Add the minimum lazy command.**

```python
# src/tofusoup/cli.py
LAZY_COMMANDS["lint"] = ("tofusoup.lint.cli", "lint_cli")

# src/tofusoup/lint/cli.py
@click.command("lint")
@click.argument("suite", type=click.Path(exists=True, dir_okay=False, path_type=Path))
@click.option("--provider", type=click.Path(exists=True, dir_okay=False, path_type=Path), required=True)
@click.option("--opentofu", type=click.Path(exists=True, dir_okay=False, path_type=Path))
def lint_cli(suite: Path, provider: Path, opentofu: Path | None) -> None:
    """Run Direct provider validation and optional OpenTofu native linting."""
```

- [ ] **Step 4: Run the test to verify GREEN.**

Run: `uv run pytest tests/lint/test_cli.py::test_lint_command_is_listed_and_describes_both_lanes -v`

Expected: PASS.

- [ ] **Step 5: Commit.**

```bash
git add src/tofusoup/cli.py src/tofusoup/lint tests/lint
git commit -m "feat: register provider lint command"
```

### Task 2: Parse and validate versioned suites

**Files:**

- Create: `src/tofusoup/lint/models.py`

- Create: `src/tofusoup/lint/suite.py`

- Create: `tests/lint/test_suite.py`

- [ ] **Step 1: Write failing parser tests.**

```python
def test_load_suite_parses_direct_and_native_lanes(tmp_path: Path) -> None:
    suite_path = tmp_path / "lint.soup.toml"
    suite_path.write_text(
        """version = 1
[provider]
source = "registry.opentofu.org/example/demo"
[provider.environment]
EXAMPLE_LINT = "example:all"
[[case]]
kind = "resource"
type_name = "example_thing"
config = { insecure = true }
expect = [{ severity = "warning", summary = "Insecure thing" }]
[opentofu]
fixture = "native"
lint = "all"
"""
    )

    suite = load_suite(suite_path)

    assert suite.version == 1
    assert suite.provider.source == "registry.opentofu.org/example/demo"
    assert suite.cases[0].kind is ComponentKind.RESOURCE
    assert suite.opentofu is not None


def test_load_suite_rejects_type_name_for_provider_case(tmp_path: Path) -> None:
    suite_path = tmp_path / "lint.soup.toml"
    suite_path.write_text('version = 1\n[provider]\nsource = "x/y"\n[[case]]\nkind = "provider"\ntype_name = "wrong"\nconfig = {}\n')

    with pytest.raises(SuiteError, match="provider cases must not declare type_name"):
        load_suite(suite_path)
```

- [ ] **Step 2: Run the parser tests to verify RED.**

Run: `uv run pytest tests/lint/test_suite.py -v`

Expected: FAIL because `tofusoup.lint.suite` and `load_suite` do not exist.

- [ ] **Step 3: Implement immutable models and strict TOML loading.**

```python
@define(frozen=True)
class LintSuite:
    version: int
    provider: ProviderSpec
    cases: Sequence[ValidationCase]  # one case per declared RPC invocation
    opentofu: OpenTofuSpec | None


def load_suite(path: Path) -> LintSuite:
    raw = tomllib.loads(path.read_text(encoding="utf-8"))
    if raw.get("version") != 1:
        raise SuiteError("only lint suite version 1 is supported")
    return parse_suite(raw, path.parent)
```

Validate every `kind`, require `type_name` for typed kinds, prohibit it for provider, require a mapping `config`, restrict diagnostic severities to the protocol values, resolve the fixture inside the suite directory, and reject an OpenTofu lane without a fixture or selector.

- [ ] **Step 4: Run the parser tests to verify GREEN.**

Run: `uv run pytest tests/lint/test_suite.py -v`

Expected: PASS.

- [ ] **Step 5: Commit.**

```bash
git add src/tofusoup/lint/models.py src/tofusoup/lint/suite.py tests/lint/test_suite.py
git commit -m "feat: parse provider lint suites"
```

### Task 3: Run direct tfprotov6 validation cases

**Files:**

- Create: `src/tofusoup/lint/direct.py`

- Create: `tests/lint/test_direct.py`

- [ ] **Step 1: Write failing dispatch tests with a fake provider stub.**

```python
@pytest.mark.asyncio
@pytest.mark.parametrize(
    ("kind", "method", "request_type"),
    [
        (ComponentKind.PROVIDER, "ValidateProviderConfig", pb.ValidateProviderConfig.Request),
        (ComponentKind.RESOURCE, "ValidateResourceConfig", pb.ValidateResourceConfig.Request),
        (ComponentKind.DATA_SOURCE, "ValidateDataResourceConfig", pb.ValidateDataResourceConfig.Request),
        (ComponentKind.EPHEMERAL, "ValidateEphemeralResourceConfig", pb.ValidateEphemeralResourceConfig.Request),
        (ComponentKind.LIST, "ValidateListResourceConfig", pb.ValidateListResourceConfig.Request),
        (ComponentKind.ACTION, "ValidateActionConfig", pb.ValidateActionConfig.Request),
        (ComponentKind.STATE_STORE, "ValidateStateStoreConfig", pb.ValidateStateStoreConfig.Request),
    ],
)
async def test_direct_runner_dispatches_the_declared_validation_rpc(kind, method, request_type) -> None:
    provider = FakeProvider(schema=full_schema(), diagnostics=[warning("rule")])
    result = await run_direct(provider, ValidationCase(kind=kind, type_name=type_name_for(kind), config={}))

    assert provider.calls[0].method == method
    assert isinstance(provider.calls[0].request, request_type)
    assert result.kind is kind
```

- [ ] **Step 2: Run dispatch tests to verify RED.**

Run: `uv run pytest tests/lint/test_direct.py -v`

Expected: FAIL because `run_direct` does not exist.

- [ ] **Step 3: Implement schema-aware dispatch and normalized findings.**

```python
DIRECT_METHODS = {
    ComponentKind.PROVIDER: ("ValidateProviderConfig", pb.ValidateProviderConfig.Request),
    ComponentKind.RESOURCE: ("ValidateResourceConfig", pb.ValidateResourceConfig.Request),
    ComponentKind.DATA_SOURCE: ("ValidateDataResourceConfig", pb.ValidateDataResourceConfig.Request),
    ComponentKind.EPHEMERAL: ("ValidateEphemeralResourceConfig", pb.ValidateEphemeralResourceConfig.Request),
    ComponentKind.LIST: ("ValidateListResourceConfig", pb.ValidateListResourceConfig.Request),
    ComponentKind.ACTION: ("ValidateActionConfig", pb.ValidateActionConfig.Request),
    ComponentKind.STATE_STORE: ("ValidateStateStoreConfig", pb.ValidateStateStoreConfig.Request),
}


async def run_direct(provider: TfPluginProvider, case: ValidationCase) -> DirectCaseResult:
    method_name, request_type = DIRECT_METHODS[case.kind]
    request = build_request(request_type, case, provider.schema)
    response = await getattr(provider.stub, method_name)(request)
    return DirectCaseResult(case=case, diagnostics=normalize(response.diagnostics))
```

Fetch the schema once, configure the provider once with its declared provider case, encode configuration using `tfplugin.pack`, and always stop the provider in a `finally` block. Treat error diagnostics and missing expected diagnostics as failures while preserving warning findings.

- [ ] **Step 4: Run dispatch tests to verify GREEN.**

Run: `uv run pytest tests/lint/test_direct.py -v`

Expected: PASS, including all seven method assertions and error/missing-finding tests.

- [ ] **Step 5: Commit.**

```bash
git add src/tofusoup/lint/direct.py tests/lint/test_direct.py
git commit -m "feat: run direct provider lint suites"
```

### Task 4: Run isolated OpenTofu native linting

**Files:**

- Create: `src/tofusoup/lint/opentofu.py`

- Create: `tests/lint/test_opentofu.py`

- [ ] **Step 1: Write a failing fake-OpenTofu subprocess test.**

```python
def test_native_runner_installs_binary_and_invokes_lint(tmp_path: Path) -> None:
    tofu = fake_tofu(tmp_path, expected_commands=["init", "validate"])
    provider = executable(tmp_path / "terraform-provider-demo")
    suite = native_suite(tmp_path, source="registry.opentofu.org/example/demo", lint="all")

    result = run_opentofu(suite, provider, tofu)

    assert result.returncode == 0
    assert fake_tofu_log(tofu) == [
        ["init", "-backend=false", "-input=false", "-no-color"],
        ["validate", "-json", "-no-color", "-lint=all"],
    ]
    assert result.diagnostics == ()
```

- [ ] **Step 2: Run the native-runner test to verify RED.**

Run: `uv run pytest tests/lint/test_opentofu.py::test_native_runner_installs_binary_and_invokes_lint -v`

Expected: FAIL because `run_opentofu` does not exist.

- [ ] **Step 3: Implement isolated installation and JSON diagnostic parsing.**

```python
def run_opentofu(suite: LintSuite, provider: Path, tofu: Path) -> OpenTofuResult:
    with TemporaryDirectory(prefix="tofusoup-lint-") as temporary:
        root = Path(temporary)
        mirror = install_filesystem_mirror(root, suite.provider.source, provider)
        environment = native_environment(root, mirror, suite.provider.environment)
        run_checked([tofu, "init", "-backend=false", "-input=false", "-no-color"], cwd=suite.opentofu.fixture, env=environment)
        completed = run_checked([tofu, "validate", "-json", "-no-color", f"-lint={suite.opentofu.lint}"], cwd=suite.opentofu.fixture, env=environment)
        return parse_validate_json(completed.stdout)
```

Copy the HCL fixture into the temporary root before executing it so no state, lock file, or `.terraform` directory is written into the checked-in suite. Scrub inherited `TF_`, `TOFU_`, and suite-provider variables before adding the isolated values. Include stdout/stderr in failure objects but not rendered environment values.

- [ ] **Step 4: Run native tests to verify GREEN.**

Run: `uv run pytest tests/lint/test_opentofu.py -v`

Expected: PASS for invocation, mirror layout, fixture isolation, JSON warnings, and failed init/validate behavior.

- [ ] **Step 5: Commit.**

```bash
git add src/tofusoup/lint/opentofu.py tests/lint/test_opentofu.py
git commit -m "feat: run native OpenTofu lint lane"
```

### Task 5: Integrate execution, stable output, and exit behavior

**Files:**

- Create: `src/tofusoup/lint/render.py`

- Modify: `src/tofusoup/lint/cli.py`

- Modify: `tests/lint/test_cli.py`

- [ ] **Step 1: Write failing end-to-end CLI tests.**

```python
def test_cli_renders_separate_direct_and_opentofu_sections(monkeypatch, tmp_path: Path) -> None:
    monkeypatch.setattr("tofusoup.lint.cli.run_suite", lambda *args: successful_dual_result())

    result = CliRunner().invoke(lint_cli, [str(valid_suite(tmp_path)), "--provider", str(executable(tmp_path / "provider")), "--opentofu", str(fake_tofu(tmp_path))])

    assert result.exit_code == 0, result.output
    assert "Direct provider validation: 7/7 cases" in result.output
    assert "OpenTofu native linting:" in result.output
    assert "OpenTofu coverage is separate from direct provider coverage" in result.output


def test_cli_json_has_stable_lane_keys(monkeypatch, tmp_path: Path) -> None:
    monkeypatch.setattr("tofusoup.lint.cli.run_suite", lambda *args: successful_dual_result())

    result = CliRunner().invoke(lint_cli, [str(valid_suite(tmp_path)), "--provider", str(executable(tmp_path / "provider")), "--json"])

    assert json.loads(result.output).keys() == {"direct", "opentofu", "version"}
```

- [ ] **Step 2: Run the CLI tests to verify RED.**

Run: `uv run pytest tests/lint/test_cli.py -v`

Expected: FAIL because suite execution and renderers do not exist.

- [ ] **Step 3: Implement orchestration and renderers.**

```python
def run_suite(suite: LintSuite, provider: Path, opentofu: Path | None) -> LintRunResult:
    direct = asyncio.run(run_direct_lane(suite, provider))
    native = None if suite.opentofu is None else run_opentofu_lane_or_raise(suite, provider, opentofu)
    return LintRunResult(direct=direct, opentofu=native)


@click.option("--json", "as_json", is_flag=True, help="Emit stable machine-readable results.")
def lint_cli(suite_path: Path, provider: Path, opentofu: Path | None, as_json: bool) -> None:
    result = run_suite(load_suite(suite_path), provider, opentofu)
    click.echo(render_json(result) if as_json else render_terminal(result))
    if not result.success:
        raise click.ClickException("provider lint suite failed")
```

Require `--opentofu` when the suite declares that lane; reject it otherwise only when an explicit `--require-opentofu` option is later introduced. Ensure terminal text never says OpenTofu exercised a direct-only kind.

- [ ] **Step 4: Run the CLI tests to verify GREEN.**

Run: `uv run pytest tests/lint/test_cli.py -v`

Expected: PASS for terminal output, JSON schema, missing `--opentofu`, warning findings, protocol errors, and native failures.

- [ ] **Step 5: Commit.**

```bash
git add src/tofusoup/lint tests/lint/test_cli.py
git commit -m "feat: render provider lint results"
```

### Task 6: Publish documentation and diagram contracts

**Files:**

- Modify: `docs/reference/cli.md`

- Create: `docs/guides/provider-linting.md`

- Modify: `docs/architecture/08-provider-linting.md`

- Modify: `mkdocs.yml`

- Create: `tests/lint/test_docs.py`

- [ ] **Step 1: Write failing documentation-contract tests.**

```python
def test_provider_linting_docs_show_only_public_commands() -> None:
    guide = Path("docs/guides/provider-linting.md").read_text(encoding="utf-8")

    assert "soup lint" in guide
    assert "--provider" in guide
    assert "--opentofu" in guide
    assert "run-provider-linting-rpcs.py" not in guide
    assert "OpenTofu coverage is separate" in guide


def test_architecture_diagram_has_direct_and_native_lanes() -> None:
    architecture = Path("docs/architecture/08-provider-linting.md").read_text(encoding="utf-8")

    assert "Direct tfprotov6 lane" in architecture
    assert "OpenTofu native lane" in architecture
```

- [ ] **Step 2: Run documentation tests to verify RED.**

Run: `uv run pytest tests/lint/test_docs.py -v`

Expected: FAIL because the guide and navigation entry do not exist.

- [ ] **Step 3: Write user documentation.**

Document a complete `lint.soup.toml`, the public command, direct/native result meaning, exit rules, isolated provider installation, and the fact that current OpenTofu native linting is experimental and core-only. Add the guide and architecture page to `mkdocs.yml`; add the command syntax to `docs/reference/cli.md`.

- [ ] **Step 4: Run documentation tests to verify GREEN.**

Run: `uv run pytest tests/lint/test_docs.py -v`

Expected: PASS.

- [ ] **Step 5: Commit.**

```bash
git add docs tests/lint/test_docs.py mkdocs.yml
git commit -m "docs: document provider lint suites"
```

### Task 7: Verify, release, and prove against Pyvider

**Files:**

- Modify: `VERSION`

- Modify: `CHANGELOG.md`

- Add downstream after publication: Pyvider suite and recording changes in its own plan.

- [ ] **Step 1: Add the real packaged-Pyvider suite test before changing Pyvider proof scripts.**

```python
@pytest.mark.integration
def test_released_soup_lint_runs_pyvider_direct_and_opentofu(tmp_path: Path) -> None:
    completed = subprocess.run(
        ["soup", "lint", str(PYVIDER_SUITE), "--provider", str(PYVIDER_PACKAGE), "--opentofu", str(OPENTOFU_BETA)],
        text=True,
        capture_output=True,
        check=False,
    )

    assert completed.returncode == 0, completed.stdout + completed.stderr
    assert "Direct provider validation: 7/7 cases" in completed.stdout
    assert "OpenTofu native linting:" in completed.stdout
```

- [ ] **Step 2: Run it first against the unreleased package to verify the end-to-end contract.**

Run: `uv run pytest tests/lint/test_pyvider_e2e.py -m integration -v`

Expected: PASS only after the prior TDD tasks are complete; retain its output as pre-release evidence.

- [ ] **Step 3: Run full release verification.**

Run:

```bash
uv run pytest
uv run ruff check .
uv run ruff format --check .
uv run mypy src/
uv build
```

Expected: every command exits 0 and `uv build` produces both wheel and source distribution.

- [ ] **Step 4: Bump the version and add a precise release note.**

Set the next feature release in `VERSION`; state that `soup lint` has direct tfprotov6 and optional OpenTofu-native lanes, and that native provider linting is not an OpenTofu protocol standard.

- [ ] **Step 5: Re-run release verification after the version bump and commit.**

```bash
git add VERSION CHANGELOG.md tests src docs mkdocs.yml
git commit -m "release: add provider lint suites"
```

- [ ] **Step 6: Publish through the repository's GitHub Release-triggered workflow, then install the published artifact into a clean environment.**

Run the documented release workflow for the exact version tag. After the release is available, create a clean virtual environment and run:

```bash
uvx --from "tofusoup==<released-version>" soup lint \
  tests/e2e/provider-linting/lint.soup.toml \
  --provider ./dist/terraform-provider-pyvider \
  --opentofu tofu
```

Expected: the direct and native sections are present; the run uses no Pyvider internal Python driver.

- [ ] **Step 7: Commit downstream proof separately and record two public casts.**

The direct cast invokes released `soup lint` with only the direct lane. The native cast invokes the same released command with `--opentofu`. Verify both casts from their checked-in JSON evidence before changing pyvider.com.

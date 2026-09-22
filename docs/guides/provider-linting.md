# Provider lint suites

`soup lint` gives a provider author one reproducible entry point for two related checks:

1. Direct provider validation invokes the validation RPCs declared by the suite.
1. OpenTofu native linting runs a normal HCL fixture through `tofu init` and `tofu validate -lint`.

The results are always separate. Direct coverage can include provider, resource, data source, ephemeral, list, action, and state-store validation. OpenTofu only reports the paths it actually ran.

## Write a suite

Check a `lint.soup.toml` file in next to the provider test fixtures:

```toml
version = 1

[provider]
source = "registry.opentofu.org/example/demo"
version = "1.2.3"

# This is explicit provider-process configuration, not an OpenTofu protocol setting.
[provider.environment]
EXAMPLE_LINT = "example:all"

[[case]]
kind = "provider"
config = { insecure = true }
expect = [{ severity = "warning", summary = "Insecure provider setting" }]

[[case]]
kind = "resource"
type_name = "example_thing"
config = { insecure = true }
expect = [{ severity = "warning", summary = "Insecure thing" }]

[opentofu]
fixture = "native"
lint = "all"
```

`provider.source` and `provider.version` identify the package layout TofuSoup builds in an isolated filesystem mirror. `provider.environment` is passed only to the test provider process. It is useful for provider-owned feature switches during an upstream transition, but it does not turn that switch into an OpenTofu-native protocol feature.

Each direct case has a `kind`, a `config` table, and—except for `provider`—a `type_name`. Supported kinds are `provider`, `resource`, `data-source`, `ephemeral`, `list`, `action`, and `state-store`.

## Run it

Run both declared lanes:

```console
$ soup lint tests/lint/lint.soup.toml \
    --provider ./dist/terraform-provider-demo \
    --opentofu tofu
```

Record or verify the lanes independently with public commands:

```console
$ soup lint tests/lint/lint.soup.toml \
    --provider ./dist/terraform-provider-demo \
    --lane direct

$ soup lint tests/lint/lint.soup.toml \
    --provider ./dist/terraform-provider-demo \
    --opentofu tofu \
    --lane opentofu
```

`--lane all` is the default. The native lane requires both an `[opentofu]` suite table and `--opentofu`; to omit `--opentofu`, select `--lane direct`. `--opentofu` accepts either a path or an executable name available on `PATH`. TofuSoup resolves it before entering the isolated fixture, then copies the fixture, provider binary, installation configuration, and Terraform data directory into a temporary workspace. The checked-in HCL directory is not modified.

## Read the output

Terminal output deliberately says which lane produced each result. JSON uses stable `direct`, `opentofu`, and `version` keys; a lane not requested is `null`.

OpenTofu coverage is separate from direct provider coverage. OpenTofu's current linting work is experimental and provides core lint selection; it has not released a standard provider-defined lint-selection protocol. Consequently, a direct provider finding is evidence that the provider hook ran, not a claim that OpenTofu reached that hook.

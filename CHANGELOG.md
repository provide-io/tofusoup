# Changelog

## [Unreleased]

## [0.6.1] - 2026-08-25

### Added

- **An example can declare the version floor it needs.** `opentofu_min` and `terraform_min` sit alongside the existing `opentofu` flag, so an example that needs a recent runtime no longer has to exclude OpenTofu wholesale and lose the versions that do work.

  The case that forced it: terraform-provider-pyvider's `pyvider_secret_note` failed on OpenTofu 1.10.6 with `planned an invalid value for ...secret_value: planned value cty.NullVal(cty.String) does not match config value`, which reads as a provider bug and is not one. The provider nulls a write-only attribute, which is correct; 1.10.6 has no concept of write-only and enforces the ordinary rule that a planned value must equal its config value. Measured rather than assumed -- 1.10.6 fails, 1.11.0 and 1.12.5 both plan cleanly -- so the floor is 1.11.0.

  The two floors are separate because the implementations version independently, and a directory takes the highest floor its examples declare. The binary's version is read once per run and cached rather than once per directory, and a binary that will not report one blocks nothing: refusing to run over a version we could not read turns a diagnostic aid into an obstacle. Comparison is numeric, so `1.9.0` does not sort above `1.11.0`.

- **`TOFUSOUP_OFFLINE` skips examples that reach the network.** Requirements could already declare `network`, and `skip_reason` accepted an `allow_network` argument, but nothing ever passed it, so the declaration was inert. An example failing because a third party is unreachable says nothing about the provider. An explicit `allow_network=` still overrides the environment.

### Fixed

- The sigstore action pin was `v3.0.0`, whose bundled TUF trust root no longer verifies -- signing failed with `root was signed by 0/3 keys`. Now `v3.5.0`, with dependabot configured to keep the pins moving so a pin cannot rot unnoticed again.

## [0.6.0] - 2026-08-24

### Added

- **`soup stir` honours the requirements an example declares.** An example compiled from a `.plating` bundle can ship a sidecar naming what it needs -- a Terraform floor, an OpenTofu incompatibility, extra `init` flags, environment variables, network egress -- and stir reads it.

  A directory whose requirements this machine cannot meet is now skipped with the declared reason instead of run and failed. Three action examples and the state store use blocks OpenTofu has no concept of, and running them under `tofu` produced "Unsupported block type", an error indistinguishable from a real defect. That was the unexplained difference between 48 example directories and the 44 that ever passed.

  A directory can also name flags it needs at `init`, which is what finally makes the filesystem state store reachable: it needs `-enable-pluggable-state-storage-experiment`, and nothing could previously say so.

  Requirements are merged across every sidecar in a directory, because a compiled component directory holds several examples and is run as a unit -- one example that cannot run under OpenTofu makes the directory unrunnable there. OpenTofu is detected by binary name rather than by asking the binary, which would cost a subprocess per directory; `terraform` is frequently an alias for `tofu`, so a wrong guess costs a confusing error rather than a wrongly skipped test.

  `StirTestResult` carries `skip_reason`, because a skip nobody can explain is indistinguishable from a directory nobody bothered to write.

## [0.5.1] - 2026-08-23

### Fixed

- **`soup stir` aborted every run at 0 of 48 directories.** The provider-requirement scan had three separate faults that only showed together against a suite using tfprotov6.11 state stores. Its legacy `provider "name" {` pattern was unanchored, so it matched the `provider` block nested inside a `state_store` block and invented a registry requirement for it. It scanned each `.tf` file alone, so a directory whose `required_providers` sat in a sibling file looked like it declared nothing. And the `required_providers` body was matched with a regex that consumed the closing brace of the last entry, so a multi-provider block yielded only the first. Block bodies are now extracted by real brace matching, `.tf` files are joined per directory before scanning, and the legacy pattern is anchored to the line start.
- **Three conformance curve tests were dead everywhere but one laptop.** `souptest_curve_support.py` named an absolute `.venv/bin/soup` under a single developer's home directory, three times, so every other machine -- CI included -- took the `pytest.skip` branch and all three reported passing while checking nothing. They now resolve the server with `shutil.which("soup")`, matching the rest of the conformance suite. The skip remains for a genuinely unbuilt server and says so instead of naming a path nobody else has.
- The cross-language compatibility doc named that same checkout for where `go build` writes the binary; it now says `$TOFUSOUP_ROOT/bin/soup-go`, which is what the command above it actually produces.
- `soup-go`: `parseCtyType` refuses a wire type description with extra elements, as go-cty's own `cty.Type.UnmarshalJSON` does -- two elements for `list`/`set`/`map`/`tuple`, two or three for `object`. It used to read the first two and return, so `["list", "string", "junk"]` parsed as `list(string)` and the oracle answered a malformed-type probe that go-cty refuses. Generated differential inputs are well-formed, so no recorded parity result changes; a hand-written probe of a malformed type can now trust the oracle.

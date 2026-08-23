# Changelog

## [Unreleased]

## [0.5.1] - 2026-08-23

### Fixed

- **`soup stir` aborted every run at 0 of 48 directories.** The provider-requirement scan had three separate faults that only showed together against a suite using tfprotov6.11 state stores. Its legacy `provider "name" {` pattern was unanchored, so it matched the `provider` block nested inside a `state_store` block and invented a registry requirement for it. It scanned each `.tf` file alone, so a directory whose `required_providers` sat in a sibling file looked like it declared nothing. And the `required_providers` body was matched with a regex that consumed the closing brace of the last entry, so a multi-provider block yielded only the first. Block bodies are now extracted by real brace matching, `.tf` files are joined per directory before scanning, and the legacy pattern is anchored to the line start.
- **Three conformance curve tests were dead everywhere but one laptop.** `souptest_curve_support.py` named an absolute `.venv/bin/soup` under a single developer's home directory, three times, so every other machine -- CI included -- took the `pytest.skip` branch and all three reported passing while checking nothing. They now resolve the server with `shutil.which("soup")`, matching the rest of the conformance suite. The skip remains for a genuinely unbuilt server and says so instead of naming a path nobody else has.
- The cross-language compatibility doc named that same checkout for where `go build` writes the binary; it now says `$TOFUSOUP_ROOT/bin/soup-go`, which is what the command above it actually produces.
- `soup-go`: `parseCtyType` refuses a wire type description with extra elements, as go-cty's own `cty.Type.UnmarshalJSON` does -- two elements for `list`/`set`/`map`/`tuple`, two or three for `object`. It used to read the first two and return, so `["list", "string", "junk"]` parsed as `list(string)` and the oracle answered a malformed-type probe that go-cty refuses. Generated differential inputs are well-formed, so no recorded parity result changes; a hand-written probe of a malformed type can now trust the oracle.

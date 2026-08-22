# Changelog

## [Unreleased]

### Fixed

- `soup-go`: `parseCtyType` refuses a wire type description with extra elements, as go-cty's own `cty.Type.UnmarshalJSON` does -- two elements for `list`/`set`/`map`/`tuple`, two or three for `object`. It used to read the first two and return, so `["list", "string", "junk"]` parsed as `list(string)` and the oracle answered a malformed-type probe that go-cty refuses. Generated differential inputs are well-formed, so no recorded parity result changes; a hand-written probe of a malformed type can now trust the oracle.

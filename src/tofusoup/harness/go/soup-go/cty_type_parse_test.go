package main

import (
	"encoding/json"
	"testing"

	"github.com/zclconf/go-cty/cty"
)

// parseCtyType is this harness's own reading of the wire type format, not
// go-cty's, so it has to agree with cty.Type.UnmarshalJSON about what is
// malformed. It used to read the first two elements of a type array and
// return, which accepted ["list", "string", "junk"] -- a description go-cty
// refuses with "unexpected extra data in type description". A differential
// probe of exactly that input then reported the oracle accepting what go-cty
// does not.
func TestParseCtyTypeAgreesWithGoCtyOnArity(t *testing.T) {
	accepted := []struct {
		name string
		in   string
		want cty.Type
	}{
		{"list of two", `["list", "string"]`, cty.List(cty.String)},
		{"set of two", `["set", "number"]`, cty.Set(cty.Number)},
		{"map of two", `["map", "bool"]`, cty.Map(cty.Bool)},
		{"tuple of two", `["tuple", ["string"]]`, cty.Tuple([]cty.Type{cty.String})},
		{"object of two", `["object", {"a": "string"}]`, cty.Object(map[string]cty.Type{"a": cty.String})},
		{"object with optionals", `["object", {"a": "string"}, ["a"]]`,
			cty.ObjectWithOptionalAttrs(map[string]cty.Type{"a": cty.String}, []string{"a"})},
	}
	for _, tc := range accepted {
		t.Run(tc.name, func(t *testing.T) {
			got, err := parseCtyType(json.RawMessage(tc.in))
			if err != nil {
				t.Fatalf("parseCtyType(%s): %v", tc.in, err)
			}
			if !got.Equals(tc.want) {
				t.Fatalf("parseCtyType(%s) = %#v, want %#v", tc.in, got, tc.want)
			}
			var ref cty.Type
			if err := json.Unmarshal([]byte(tc.in), &ref); err != nil {
				t.Fatalf("go-cty refused %s, which this parser accepted: %v", tc.in, err)
			}
			if !ref.Equals(got) {
				t.Fatalf("go-cty reads %s as %#v, this parser as %#v", tc.in, ref, got)
			}
		})
	}

	// Each of these must be refused here *and* by go-cty: a refusal go-cty does
	// not share would be this parser inventing a divergence.
	refused := []struct{ name, in string }{
		{"list with a third element", `["list", "string", ["a"]]`},
		{"set with a third element", `["set", "string", "junk"]`},
		{"map with a third element", `["map", "string", []]`},
		{"tuple with a third element", `["tuple", ["string"], ["a"]]`},
		{"object with a fourth element", `["object", {"a": "string"}, ["a"], "x"]`},
		{"object with non-string optionals", `["object", {"a": "string"}, [1]]`},
	}
	for _, tc := range refused {
		t.Run(tc.name, func(t *testing.T) {
			if got, err := parseCtyType(json.RawMessage(tc.in)); err == nil {
				t.Fatalf("parseCtyType(%s) = %#v, want an error", tc.in, got)
			}
			var ref cty.Type
			if err := json.Unmarshal([]byte(tc.in), &ref); err == nil {
				t.Fatalf("go-cty accepted %s; refusing it here would be a divergence", tc.in)
			}
		})
	}
}

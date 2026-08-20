// SPDX-FileCopyrightText: Copyright (c) provide.io llc. All rights reserved.
// SPDX-License-Identifier: Apache-2.0

package main

import (
	"encoding/json"
	"math/big"
	"testing"

	"github.com/zclconf/go-cty/cty"
)

// The rich dialect is the harness's own invention rather than go-cty's, so
// nothing upstream checks it. Everything here is a property the dialect claims:
// that decode and encode are inverses, that a number survives at its full
// precision, and that anything the dialect cannot say unambiguously is refused
// rather than guessed at. Each of the last group is a fault that shipped.

// roundTrip decodes a rich value at a type and encodes it again.
func roundTrip(t *testing.T, ty cty.Type, in string) string {
	t.Helper()
	val, err := decodeRich(ty, json.RawMessage(in))
	if err != nil {
		t.Fatalf("decodeRich(%s): %v", in, err)
	}
	out, err := encodeRich(val)
	if err != nil {
		t.Fatalf("encodeRich after decoding %s: %v", in, err)
	}
	return string(out)
}

func TestRichValuesRoundTrip(t *testing.T) {
	strings := cty.List(cty.String)
	tests := []struct {
		name string
		ty   cty.Type
		in   string
		want string
	}{
		{
			name: "a mark at depth, not on the whole value",
			ty:   cty.List(cty.Map(cty.String)),
			in:   `[{"a":{"$marks":["sensitive"],"$value":"hi"}}]`,
			want: `[{"a":{"$marks":["sensitive"],"$value":"hi"}}]`,
		},
		{
			name: "two marks on one value, in sorted order",
			ty:   cty.String,
			in:   `{"$marks":["sensitive","zebra"],"$value":"hi"}`,
			want: `{"$marks":["sensitive","zebra"],"$value":"hi"}`,
		},
		{
			name: "a null inside a container",
			ty:   strings,
			in:   `["a",{"$null":true}]`,
			want: `["a",{"$null":true}]`,
		},
		{
			name: "a bare unknown inside a container",
			ty:   strings,
			in:   `["a",{"$unknown":true}]`,
			want: `["a",{"$unknown":true}]`,
		},
		{
			name: "a not-null refinement",
			ty:   cty.String,
			in:   `{"$unknown":true,"$refine":{"is_known_null":false}}`,
			want: `{"$refine":{"is_known_null":false},"$unknown":true}`,
		},
		{
			name: "a string prefix, untrimmed",
			ty:   cty.String,
			in:   `{"$unknown":true,"$refine":{"is_known_null":false,"string_prefix":"hello"}}`,
			want: `{"$refine":{"is_known_null":false,"string_prefix":"hello"},"$unknown":true}`,
		},
		{
			name: "a number bound at 2^70, past what a float64 holds",
			ty:   cty.Number,
			in:   `{"$unknown":true,"$refine":{"number_lower_bound":["1180591620717411303424",true]}}`,
			want: `{"$refine":{"number_lower_bound":["1180591620717411303424",true]},"$unknown":true}`,
		},
		{
			name: "both number bounds, one exclusive",
			ty:   cty.Number,
			in:   `{"$unknown":true,"$refine":{"number_lower_bound":["1",true],"number_upper_bound":["10",false]}}`,
			want: `{"$refine":{"number_lower_bound":["1",true],"number_upper_bound":["10",false]},"$unknown":true}`,
		},
		{
			name: "a length bound at 2^53+1, exactly",
			ty:   strings,
			in:   `{"$unknown":true,"$refine":{"collection_length_lower_bound":9007199254740993}}`,
			want: `{"$refine":{"collection_length_lower_bound":9007199254740993},"$unknown":true}`,
		},
		{
			name: "both length bounds",
			ty:   strings,
			in:   `{"$unknown":true,"$refine":{"collection_length_lower_bound":2,"collection_length_upper_bound":5}}`,
			want: `{"$refine":{"collection_length_lower_bound":2,"collection_length_upper_bound":5},"$unknown":true}`,
		},
		{
			name: "a positive infinity, which JSON has no literal for",
			ty:   cty.Number,
			in:   `{"$number":"Infinity"}`,
			want: `{"$number":"Infinity"}`,
		},
		{
			name: "a negative infinity",
			ty:   cty.Number,
			in:   `{"$number":"-Infinity"}`,
			want: `{"$number":"-Infinity"}`,
		},
		{
			name: "a negative zero, whose sign is the whole answer",
			ty:   cty.Number,
			in:   `{"$number":"-0"}`,
			want: `-0`,
		},
		{
			name: "a bytes buffer",
			ty:   cty.String, // ignored: $bytes carries its own capsule type
			in:   `{"$bytes":"aGVsbG8="}`,
			want: `{"$bytes":"aGVsbG8="}`,
		},
		{
			name: "a dynamic position given a concrete list type",
			ty:   cty.DynamicPseudoType,
			in:   `{"$dynamic":{"type":["list","string"],"value":["a"]}}`,
			want: `["a"]`,
		},
	}

	for _, tc := range tests {
		t.Run(tc.name, func(t *testing.T) {
			if got := roundTrip(t, tc.ty, tc.in); got != tc.want {
				t.Errorf("round trip gave %s, want %s", got, tc.want)
			}
		})
	}
}

func TestANegativeZeroKeepsItsSign(t *testing.T) {
	// Decimal("-0") == Decimal("0"), so a caller comparing numbers as decimals
	// cannot see this difference unless the harness transmits the sign.
	val, err := decodeRich(cty.Number, json.RawMessage(`{"$number":"-0"}`))
	if err != nil {
		t.Fatalf("decodeRich: %v", err)
	}
	if sign := val.AsBigFloat().Signbit(); !sign {
		t.Error("a negative zero came back unsigned")
	}
}

func TestAStringSpelledNumberKeepsEveryDigit(t *testing.T) {
	// 2^64+1. `new(big.Float).SetString` starts at 64 bits of mantissa, so this
	// used to come back as 2^64 while go-cty's own `cty json unmarshal`
	// answered exactly -- the harness disagreeing with the library it exists to
	// speak for, in the direction that blames the caller.
	const exact = "18446744073709551617"

	val, err := decodeRich(cty.Number, json.RawMessage(`"`+exact+`"`))
	if err != nil {
		t.Fatalf("decodeRich: %v", err)
	}
	if got := val.AsBigFloat().Text('f', -1); got != exact {
		t.Errorf("%s decoded as %s", exact, got)
	}

	// And the same digits arriving as a bare JSON token, so the two spellings
	// cannot drift apart.
	token, err := decodeRich(cty.Number, json.RawMessage(exact))
	if err != nil {
		t.Fatalf("decodeRich on a JSON number token: %v", err)
	}
	if got := token.AsBigFloat().Text('f', -1); got != exact {
		t.Errorf("the JSON number token decoded as %s", got)
	}
}

func TestParseExactNumberMatchesGoCtysOwnPrecision(t *testing.T) {
	// cty.ParseNumberVal is big.ParseFloat(s, 10, 512, ToNearestEven); pinned
	// here so the harness's number rule cannot quietly diverge from go-cty's.
	const huge = "1180591620717411303424" // 2^70

	mine, err := parseExactNumber(huge)
	if err != nil {
		t.Fatalf("parseExactNumber: %v", err)
	}
	theirs, err := cty.ParseNumberVal(huge)
	if err != nil {
		t.Fatalf("cty.ParseNumberVal: %v", err)
	}
	if mine.Cmp(theirs.AsBigFloat()) != 0 {
		t.Errorf("parseExactNumber gave %s, go-cty gives %s", mine.Text('f', -1), theirs.AsBigFloat().Text('f', -1))
	}
}

func TestALengthBoundIsTakenExactlyOrRefused(t *testing.T) {
	// Routed through a float64, math.MaxInt overflowed the conversion to int
	// and 2^53+1 rounded down, so the bound applied was not the bound sent.
	tests := []struct {
		name  string
		given string
		want  int
		fails bool
	}{
		{name: "2^53+1, past float64's exact range", given: `9007199254740993`, want: 9007199254740993},
		{name: "math.MaxInt", given: `9223372036854775807`, want: 9223372036854775807},
		{name: "zero", given: `0`, want: 0},
		{name: "past what an int holds", given: `92233720368547758070`, fails: true},
		{name: "negative", given: `-1`, fails: true},
		{name: "fractional", given: `1.5`, fails: true},
		{name: "a string", given: `"3"`, fails: true},
		{name: "a bool", given: `true`, fails: true},
	}

	for _, tc := range tests {
		t.Run(tc.name, func(t *testing.T) {
			got, err := parseLengthBound("collection_length_lower_bound", json.RawMessage(tc.given))
			if tc.fails {
				if err == nil {
					t.Fatalf("%s was accepted as %d", tc.given, got)
				}
				return
			}
			if err != nil {
				t.Fatalf("%s was refused: %v", tc.given, err)
			}
			if got != tc.want {
				t.Errorf("%s became %d", tc.given, got)
			}
		})
	}
}

func TestASentinelKeyIsOnlyASentinelInItsOwnShape(t *testing.T) {
	// Each of these used to decode successfully as something other than what it
	// says -- a null map, a wholly unknown map with a key discarded, an
	// unrefined unknown -- and report ok. An oracle answering a question the
	// caller did not ask is worse than one that refuses.
	strings := cty.Map(cty.String)
	tests := []struct {
		name  string
		ty    cty.Type
		given string
	}{
		{name: "$null carrying a value rather than true", ty: strings, given: `{"$null":"x"}`},
		{name: "$null written as false", ty: strings, given: `{"$null":false}`},
		{name: "$unknown carrying a value rather than true", ty: strings, given: `{"$unknown":"x","k":"y"}`},
		{name: "$unknown alongside a map key", ty: strings, given: `{"$unknown":true,"k":"y"}`},
		{name: "$marks without $value", ty: cty.String, given: `{"$marks":["sensitive"]}`},
		{name: "$marks that are not strings", ty: cty.String, given: `{"$marks":[1],"$value":"hi"}`},
		{name: "$marks alongside a stray key", ty: cty.String, given: `{"$marks":["s"],"$value":"hi","k":"y"}`},
		{name: "$bytes that is not a string", ty: cty.String, given: `{"$bytes":42}`},
		{name: "$number that is not a string", ty: cty.Number, given: `{"$number":42}`},
		{name: "$dynamic that is not an object", ty: cty.DynamicPseudoType, given: `{"$dynamic":"x"}`},
		{name: "two sentinels at once", ty: strings, given: `{"$null":true,"$unknown":true}`},
	}

	for _, tc := range tests {
		t.Run(tc.name, func(t *testing.T) {
			val, err := decodeRich(tc.ty, json.RawMessage(tc.given))
			if err == nil {
				t.Fatalf("%s decoded as %#v instead of being refused", tc.given, val)
			}
		})
	}
}

func TestAnUnreadRefinementKeyIsRefused(t *testing.T) {
	// A key that is not read is a constraint that is not applied, and a bare
	// unknown compares equal to every other bare unknown: the comparison passes
	// on an answer nobody gave.
	tests := []struct {
		name  string
		ty    cty.Type
		given string
	}{
		{name: "a misspelled key", ty: cty.String, given: `{"$unknown":true,"$refine":{"typo_prefix":"x"}}`},
		{name: "a bound that is not a pair", ty: cty.Number, given: `{"$unknown":true,"$refine":{"number_lower_bound":"10"}}`},
		{name: "a pair of the wrong length", ty: cty.Number, given: `{"$unknown":true,"$refine":{"number_upper_bound":["10"]}}`},
		{name: "a bound whose digits are a number", ty: cty.Number, given: `{"$unknown":true,"$refine":{"number_lower_bound":[10,true]}}`},
		{name: "inclusiveness that is not a bool", ty: cty.Number, given: `{"$unknown":true,"$refine":{"number_lower_bound":["10","yes"]}}`},
		{name: "is_known_null that is not a bool", ty: cty.String, given: `{"$unknown":true,"$refine":{"is_known_null":"no"}}`},
		{name: "a prefix that is not a string", ty: cty.String, given: `{"$unknown":true,"$refine":{"string_prefix":7}}`},
		{name: "$refine that is not an object", ty: cty.String, given: `{"$unknown":true,"$refine":[]}`},
	}

	for _, tc := range tests {
		t.Run(tc.name, func(t *testing.T) {
			val, err := decodeRich(tc.ty, json.RawMessage(tc.given))
			if err == nil {
				t.Fatalf("%s decoded as %#v instead of being refused", tc.given, val)
			}
		})
	}
}

func TestAMapKeyCollidingWithASentinelIsRefusedOnTheWayOut(t *testing.T) {
	// The decoder's strictness is only symmetric because of this: the dialect
	// cannot spell such a map in either direction, and says so both times.
	val := cty.MapVal(map[string]cty.Value{"$null": cty.StringVal("x")})

	if _, err := encodeRich(val); err == nil {
		t.Fatal("a map keyed on a sentinel was encoded rather than refused")
	}
}

func TestRefinementsAreReportedTheWayGoCtyHoldsThem(t *testing.T) {
	// encodeRefinements reads Value.Range(), so its answers are go-cty's. What
	// is pinned here is that the harness's spelling of them does not drift.
	bound, _ := new(big.Float).SetPrec(512).SetString("1180591620717411303424")
	val := cty.UnknownVal(cty.Number).Refine().
		NumberRangeLowerBound(cty.NumberVal(bound), true).
		NewValue()

	got, err := encodeRefinements(val)
	if err != nil {
		t.Fatalf("encodeRefinements: %v", err)
	}
	pair, ok := got["number_lower_bound"].([]any)
	if !ok {
		t.Fatalf("number_lower_bound is %#v", got["number_lower_bound"])
	}
	if pair[0] != "1180591620717411303424" {
		t.Errorf("the bound came back as %v", pair[0])
	}
	if pair[1] != true {
		t.Errorf("inclusiveness came back as %v", pair[1])
	}
}

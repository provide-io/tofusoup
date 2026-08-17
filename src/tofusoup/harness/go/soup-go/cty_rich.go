// SPDX-FileCopyrightText: Copyright (c) provide.io llc. All rights reserved.
// SPDX-License-Identifier: Apache-2.0

package main

// A JSON dialect for cty values that survives the trip.
//
// `cty call` already compares stdlib answers against real go-cty, but its
// argument and result encoding can only say "unknown", "null" or "marked"
// about the *whole* value. That is enough for a function's top-level answer
// and not enough for anything else in cty: UnknownAsNull exists precisely to
// rewrite unknowns nested inside containers, MarkWithPaths exists to put marks
// back at depth, and a refined unknown carries constraints that no plain JSON
// value can express.
//
// So the four features below were unreachable from this harness, which meant
// the only thing checking a second implementation of them was that
// implementation's own reading of go-cty's source. This file is the dialect
// that closes that gap:
//
//	{"$null": true}                         a null of the type at this position
//	{"$unknown": true, "$refine": {...}}    an unknown, optionally refined
//	{"$marks": ["sensitive"], "$value": x}  marks applied at this position
//	{"$bytes": "aGk="}                      a stdlib.Bytes buffer
//	{"$number": "Infinity"}                 a number JSON cannot spell
//	anything else                           an ordinary value
//
// Encoding and decoding are inverses, and `cty rich` exists to prove that on
// any input rather than leaving it asserted here.
//
// The one thing the dialect cannot express is a map key or object attribute
// beginning with "$". Encoding such a value is an error rather than a silent
// mis-spelling: an oracle that quietly renders a value as something else is
// worse than one that refuses, because the comparison still passes.

import (
	"bytes"
	"encoding/base64"
	"encoding/json"
	"fmt"
	"math"
	"math/big"
	"sort"
	"strings"

	"github.com/zclconf/go-cty/cty"
	"github.com/zclconf/go-cty/cty/function/stdlib"
)

// sentinelKeys are the keys that make a JSON object mean something other than
// a cty map or object value.
var sentinelKeys = []string{"$null", "$unknown", "$marks", "$bytes", "$number", "$dynamic"}

func markNames(marks cty.ValueMarks) []string {
	names := make([]string, 0, len(marks))
	for m := range marks {
		if s, ok := m.(string); ok {
			names = append(names, s)
		} else {
			names = append(names, fmt.Sprintf("%v", m))
		}
	}
	sort.Strings(names)
	return names
}

// encodeRich renders any cty value, including one that is unknown, null or
// marked at any depth.
func encodeRich(val cty.Value) (json.RawMessage, error) {
	if val.IsMarked() {
		inner, marks := val.Unmark()
		encoded, err := encodeRich(inner)
		if err != nil {
			return nil, err
		}
		return json.Marshal(map[string]any{"$marks": markNames(marks), "$value": encoded})
	}

	if !val.IsKnown() {
		out := map[string]any{"$unknown": true}
		refinements, err := encodeRefinements(val)
		if err != nil {
			return nil, err
		}
		if len(refinements) > 0 {
			out["$refine"] = refinements
		}
		return json.Marshal(out)
	}

	if val.IsNull() {
		return json.Marshal(map[string]any{"$null": true})
	}

	return encodeKnownRich(val)
}

func encodeKnownRich(val cty.Value) (json.RawMessage, error) {
	ty := val.Type()
	switch {
	case ty.Equals(stdlib.Bytes):
		buf, ok := val.EncapsulatedValue().(*[]byte)
		if !ok {
			return nil, fmt.Errorf("bytes value does not encapsulate a *[]byte")
		}
		return json.Marshal(map[string]any{"$bytes": base64.StdEncoding.EncodeToString(*buf)})
	case ty == cty.String:
		return json.Marshal(val.AsString())
	case ty == cty.Bool:
		return json.Marshal(val.True())
	case ty == cty.Number:
		return encodeRichNumber(val.AsBigFloat())
	case ty.IsListType(), ty.IsSetType(), ty.IsTupleType():
		return encodeRichSequence(val)
	case ty.IsMapType(), ty.IsObjectType():
		return encodeRichMapping(val)
	}
	return nil, fmt.Errorf("no rich encoding for %s", ty.FriendlyName())
}

// encodeRichNumber writes a number as its exact decimal digits.
//
// Not as a float: go-cty numbers are big.Float, and rounding one through a
// float64 on the way out would make the oracle disagree with itself above
// 2^53. Infinities have no JSON literal at all, so they travel as a string.
func encodeRichNumber(bf *big.Float) (json.RawMessage, error) {
	if bf.IsInf() {
		if bf.Sign() > 0 {
			return json.Marshal(map[string]any{"$number": "Infinity"})
		}
		return json.Marshal(map[string]any{"$number": "-Infinity"})
	}
	return json.RawMessage(bf.Text('f', -1)), nil
}

// encodeRichSequence writes elements in iteration order.
//
// For a set that order is go-cty's own internal ordering, which is part of
// what a second implementation has to reproduce: the wire bytes of a set
// depend on it.
func encodeRichSequence(val cty.Value) (json.RawMessage, error) {
	items := make([]json.RawMessage, 0, val.LengthInt())
	for it := val.ElementIterator(); it.Next(); {
		_, elem := it.Element()
		encoded, err := encodeRich(elem)
		if err != nil {
			return nil, err
		}
		items = append(items, encoded)
	}
	return json.Marshal(items)
}

func encodeRichMapping(val cty.Value) (json.RawMessage, error) {
	fields := make(map[string]json.RawMessage)
	for it := val.ElementIterator(); it.Next(); {
		key, elem := it.Element()
		name := key.AsString()
		if strings.HasPrefix(name, "$") {
			return nil, fmt.Errorf("key %q cannot be expressed: it collides with a rich-value sentinel", name)
		}
		encoded, err := encodeRich(elem)
		if err != nil {
			return nil, err
		}
		fields[name] = encoded
	}
	return json.Marshal(fields)
}

// encodeRefinements reads an unknown's constraints back out through Range().
//
// Keys match the ones buildRefinedUnknown accepts, so the dialect has one
// spelling in each direction and `cty rich` can prove the round trip.
func encodeRefinements(val cty.Value) (map[string]any, error) {
	rng := val.Range()
	out := make(map[string]any)
	if rng.DefinitelyNotNull() {
		out["is_known_null"] = false
	}

	ty := rng.TypeConstraint()
	switch {
	case ty == cty.String:
		if prefix := rng.StringPrefix(); prefix != "" {
			out["string_prefix"] = prefix
		}
	case ty == cty.Number:
		if bound, inclusive := rng.NumberLowerBound(); bound.IsKnown() && !bound.IsNull() && !bound.AsBigFloat().IsInf() {
			out["number_lower_bound"] = []any{bound.AsBigFloat().Text('f', -1), inclusive}
		}
		if bound, inclusive := rng.NumberUpperBound(); bound.IsKnown() && !bound.IsNull() && !bound.AsBigFloat().IsInf() {
			out["number_upper_bound"] = []any{bound.AsBigFloat().Text('f', -1), inclusive}
		}
	case ty.IsCollectionType():
		if lower := rng.LengthLowerBound(); lower != 0 {
			out["collection_length_lower_bound"] = lower
		}
		if upper := rng.LengthUpperBound(); upper != math.MaxInt {
			out["collection_length_upper_bound"] = upper
		}
	}
	return out, nil
}

// decodeRich builds a cty value of the given type from the rich dialect.
func decodeRich(ty cty.Type, raw json.RawMessage) (cty.Value, error) {
	// A literal JSON null, before anything else. Unmarshalling `null` into a map
	// *succeeds* and leaves the map nil, so without this a null element read as
	// an object with no sentinel keys and was refused -- and plain JSON nulls
	// are how every caller that predates this dialect writes one.
	if string(bytes.TrimSpace(raw)) == "null" {
		return cty.NullVal(ty), nil
	}

	var fields map[string]json.RawMessage
	if err := json.Unmarshal(raw, &fields); err == nil && fields != nil {
		if val, handled, err := decodeSentinel(ty, fields); err != nil {
			return cty.NilVal, err
		} else if handled {
			return val, nil
		}
		if ty.IsMapType() || ty.IsObjectType() {
			return decodeRichMapping(ty, fields)
		}
		// A dynamic position: hand the object back to type inference.
		if ty == cty.DynamicPseudoType {
			return buildCtyValueFromJSON(ty, raw)
		}
		return cty.NilVal, fmt.Errorf("JSON object given for %s", ty.FriendlyName())
	}

	var items []json.RawMessage
	if err := json.Unmarshal(raw, &items); err == nil {
		if ty.IsListType() || ty.IsSetType() || ty.IsTupleType() {
			return decodeRichSequence(ty, items)
		}
	}

	return buildCtyValueFromJSON(ty, raw)
}

// decodeSentinel handles the dialect's special objects. The second result
// distinguishes "this was a sentinel" from "this was a map that happens to
// decode to the zero value".
func decodeSentinel(ty cty.Type, fields map[string]json.RawMessage) (cty.Value, bool, error) {
	which := ""
	for _, key := range sentinelKeys {
		if _, ok := fields[key]; ok {
			if which != "" {
				return cty.NilVal, false, fmt.Errorf("both %s and %s given", which, key)
			}
			which = key
		}
	}

	switch which {
	case "":
		return cty.NilVal, false, nil
	case "$null":
		return cty.NullVal(ty), true, nil
	case "$unknown":
		val, err := decodeUnknown(ty, fields)
		return val, true, err
	case "$marks":
		val, err := decodeMarked(ty, fields)
		return val, true, err
	case "$bytes":
		val, err := decodeBytes(fields["$bytes"])
		return val, true, err
	case "$number":
		val, err := decodeSpelledNumber(fields["$number"])
		return val, true, err
	case "$dynamic":
		val, err := decodeDynamic(fields["$dynamic"])
		return val, true, err
	}
	return cty.NilVal, false, fmt.Errorf("unhandled sentinel %s", which)
}

func decodeUnknown(ty cty.Type, fields map[string]json.RawMessage) (cty.Value, error) {
	raw, refined := fields["$refine"]
	if !refined {
		return cty.UnknownVal(ty), nil
	}
	var data any
	if err := json.Unmarshal(raw, &data); err != nil {
		return cty.NilVal, fmt.Errorf("$refine is not an object: %w", err)
	}
	return buildRefinedUnknown(ty, data)
}

func decodeMarked(ty cty.Type, fields map[string]json.RawMessage) (cty.Value, error) {
	var names []string
	if err := json.Unmarshal(fields["$marks"], &names); err != nil {
		return cty.NilVal, fmt.Errorf("$marks is not a list of strings: %w", err)
	}
	inner, ok := fields["$value"]
	if !ok {
		return cty.NilVal, fmt.Errorf("$marks given without $value")
	}
	val, err := decodeRich(ty, inner)
	if err != nil {
		return cty.NilVal, err
	}
	for _, name := range names {
		val = val.Mark(name)
	}
	return val, nil
}

func decodeBytes(raw json.RawMessage) (cty.Value, error) {
	var encoded string
	if err := json.Unmarshal(raw, &encoded); err != nil {
		return cty.NilVal, fmt.Errorf("$bytes is not a string: %w", err)
	}
	buf, err := base64.StdEncoding.DecodeString(encoded)
	if err != nil {
		return cty.NilVal, fmt.Errorf("$bytes is not base64: %w", err)
	}
	if buf == nil {
		// BytesVal panics on a nil slice, and decoding "" produces one.
		buf = []byte{}
	}
	return stdlib.BytesVal(buf), nil
}

// decodeDynamic gives a dynamic position a concrete type.
//
// Input-only sugar, and it exists because inference is not good enough here: a
// JSON array at a dynamic position implies a *tuple*, so sending a list through
// `--type dynamic` silently changed the value's type before the operation under
// test ever ran, and the resulting "divergence" was in the harness.
//
// There is no encoding counterpart. In go-cty a known value always has a
// concrete type -- `DynamicPseudoType` is a constraint, not something a value
// carries -- so nothing on the way out needs this spelling.
func decodeDynamic(raw json.RawMessage) (cty.Value, error) {
	var envelope struct {
		Type  json.RawMessage `json:"type"`
		Value json.RawMessage `json:"value"`
	}
	if err := json.Unmarshal(raw, &envelope); err != nil {
		return cty.NilVal, fmt.Errorf("$dynamic is not a {type, value} object: %w", err)
	}
	if len(envelope.Type) == 0 {
		return cty.NilVal, fmt.Errorf("$dynamic is missing a type")
	}
	ty, err := parseCtyType(envelope.Type)
	if err != nil {
		return cty.NilVal, fmt.Errorf("$dynamic type: %w", err)
	}
	return decodeRich(ty, envelope.Value)
}

func decodeSpelledNumber(raw json.RawMessage) (cty.Value, error) {
	var text string
	if err := json.Unmarshal(raw, &text); err != nil {
		return cty.NilVal, fmt.Errorf("$number is not a string: %w", err)
	}
	switch text {
	case "Infinity":
		return cty.PositiveInfinity, nil
	case "-Infinity":
		return cty.NegativeInfinity, nil
	}
	bf, _, err := big.ParseFloat(text, 10, 512, big.ToNearestEven)
	if err != nil {
		return cty.NilVal, fmt.Errorf("$number %q is not a number: %w", text, err)
	}
	return cty.NumberVal(bf), nil
}

func decodeRichSequence(ty cty.Type, items []json.RawMessage) (cty.Value, error) {
	vals := make([]cty.Value, len(items))
	for i, raw := range items {
		// Asked for only where it applies: ElementType panics on a tuple and
		// TupleElementType panics on a list.
		var elemTy cty.Type
		if ty.IsTupleType() {
			if i >= len(ty.TupleElementTypes()) {
				return cty.NilVal, fmt.Errorf("tuple has %d elements, got %d", len(ty.TupleElementTypes()), len(items))
			}
			elemTy = ty.TupleElementType(i)
		} else {
			elemTy = ty.ElementType()
		}
		val, err := decodeRich(elemTy, raw)
		if err != nil {
			return cty.NilVal, fmt.Errorf("element %d: %w", i, err)
		}
		vals[i] = val
	}

	switch {
	case ty.IsTupleType():
		if len(vals) != len(ty.TupleElementTypes()) {
			return cty.NilVal, fmt.Errorf("tuple has %d elements, got %d", len(ty.TupleElementTypes()), len(vals))
		}
		return cty.TupleVal(vals), nil
	case ty.IsSetType():
		if len(vals) == 0 {
			return cty.SetValEmpty(ty.ElementType()), nil
		}
		return cty.SetVal(vals), nil
	default:
		if len(vals) == 0 {
			return cty.ListValEmpty(ty.ElementType()), nil
		}
		return cty.ListVal(vals), nil
	}
}

func decodeRichMapping(ty cty.Type, fields map[string]json.RawMessage) (cty.Value, error) {
	vals := make(map[string]cty.Value, len(fields))
	for name, raw := range fields {
		// Same asymmetry as sequences: ElementType panics on an object type.
		var elemTy cty.Type
		if ty.IsObjectType() {
			if !ty.HasAttribute(name) {
				return cty.NilVal, fmt.Errorf("type has no attribute %q", name)
			}
			elemTy = ty.AttributeType(name)
		} else {
			elemTy = ty.ElementType()
		}
		val, err := decodeRich(elemTy, raw)
		if err != nil {
			return cty.NilVal, fmt.Errorf("%q: %w", name, err)
		}
		vals[name] = val
	}

	if ty.IsObjectType() {
		for name := range ty.AttributeTypes() {
			if _, given := vals[name]; !given {
				return cty.NilVal, fmt.Errorf("attribute %q was not given", name)
			}
		}
		return cty.ObjectVal(vals), nil
	}
	if len(vals) == 0 {
		return cty.MapValEmpty(ty.ElementType()), nil
	}
	return cty.MapVal(vals), nil
}

// encodePath renders a cty.Path structurally rather than as a display string.
//
// Comparing rendered paths across two implementations compares their spelling
// conventions, which is not the thing under test; comparing steps compares
// where the path actually points.
func encodePath(path cty.Path) ([]any, error) {
	steps := make([]any, 0, len(path))
	for _, step := range path {
		switch s := step.(type) {
		case cty.GetAttrStep:
			steps = append(steps, map[string]any{"attr": s.Name})
		case cty.IndexStep:
			key, err := encodeRich(s.Key)
			if err != nil {
				return nil, err
			}
			steps = append(steps, map[string]any{"index": key})
		default:
			return nil, fmt.Errorf("unsupported path step %T", step)
		}
	}
	return steps, nil
}

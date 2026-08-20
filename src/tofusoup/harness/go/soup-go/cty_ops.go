// SPDX-FileCopyrightText: Copyright (c) provide.io llc. All rights reserved.
// SPDX-License-Identifier: Apache-2.0

package main

// The go-cty features that `cty call` cannot reach.
//
// `cty call` is an oracle for the standard library. Everything below sits in
// the cty package itself rather than in stdlib, so no function call exposes it
// and a second implementation had nothing to compare against:
//
//	cty unknown-as-null   cty.UnknownAsNull
//	cty marks             Value.UnmarkDeepWithPaths and Value.MarkWithPaths
//	cty conformance       Type.TestConformance
//	cty json              the cty/json value codec, distinct from jsonencode
//	cty range             Value.Range, Value.Refine and ValueRange.Includes
//	cty safe-known-prefix ctystrings.SafeKnownPrefix
//	cty rich              the value dialect itself, round-tripped
//	cty convert-value     convert.Convert, and the safe/unsafe distinction
//	cty walk              cty.Walk's visit order, paths and pruning
//	cty transform         cty.Transform, applying a rewrite named by both sides
//	cty msgpack           the wire codec, with unknowns and refinements
//	cty equals            Value.Equals and Value.RawEquals, not the stdlib's
//
// Every command reports go-cty's refusals and panics as data rather than
// exiting, because "go-cty will not do this" is one of the answers a parity run
// needs to record. A command that died on the first refusal would make the
// caller's comparison stop at the first interesting case.

import (
	"encoding/base64"
	"encoding/hex"
	"encoding/json"
	"fmt"
	"math"
	"sort"
	"strings"

	"github.com/spf13/cobra"
	"github.com/zclconf/go-cty/cty"
	"github.com/zclconf/go-cty/cty/convert"
	"github.com/zclconf/go-cty/cty/ctystrings"
	ctyjson "github.com/zclconf/go-cty/cty/json"
	ctymsgpack "github.com/zclconf/go-cty/cty/msgpack"
)

// emit writes one JSON object per invocation, so callers can parse without
// caring which command produced it.
func emit(cmd *cobra.Command, payload any) error {
	encoded, err := json.Marshal(payload)
	if err != nil {
		return fmt.Errorf("failed to encode result: %w", err)
	}
	fmt.Fprintln(cmd.OutOrStdout(), string(encoded))
	return nil
}

// recovered runs fn and turns a go-cty panic into a reportable string.
//
// go-cty panics on questions that are wrong for a type -- a string prefix of a
// number, a Range of a marked value -- and those panics are part of its
// contract, so an oracle has to be able to report them.
func recovered(fn func()) (panicked string) {
	defer func() {
		if r := recover(); r != nil {
			panicked = fmt.Sprintf("%v", r)
		}
	}()
	fn()
	return ""
}

// typeFlag adds the --type flag shared by the value commands.
func typeFlag(cmd *cobra.Command, target *string) {
	cmd.Flags().StringVar(target, "type", "", "cty type of the value, as JSON")
	_ = cmd.MarkFlagRequired("type")
}

func decodeTypedArg(typeJSON string, valueJSON string) (cty.Value, error) {
	ty, err := parseCtyType(json.RawMessage(typeJSON))
	if err != nil {
		return cty.NilVal, fmt.Errorf("failed to parse type: %w", err)
	}
	val, err := decodeRich(ty, json.RawMessage(valueJSON))
	if err != nil {
		return cty.NilVal, fmt.Errorf("failed to build value: %w", err)
	}
	return val, nil
}

func initCtyRichCmd() *cobra.Command {
	var typeJSON string
	cmd := &cobra.Command{
		Use:   "rich [value-json]",
		Short: "Round-trip a value through the rich JSON dialect",
		Long: `Decode a rich value and encode it again, reporting both halves.

Exists so the dialect is proven rather than assumed. If decode and encode
disagree, every other command that uses them is comparing against a value the
caller did not send.

  soup-go cty rich --type '["list","string"]' '["a",{"$unknown":true}]'`,
		Args: cobra.ExactArgs(1),
		RunE: func(cmd *cobra.Command, args []string) error {
			val, err := decodeTypedArg(typeJSON, args[0])
			if err != nil {
				return emit(cmd, map[string]any{"ok": false, "error": err.Error()})
			}
			encoded, err := encodeRich(val)
			if err != nil {
				return emit(cmd, map[string]any{"ok": false, "error": err.Error()})
			}
			return emit(cmd, map[string]any{
				"ok":        true,
				"value":     encoded,
				"go_string": val.GoString(),
			})
		},
	}
	typeFlag(cmd, &typeJSON)
	return cmd
}

func initCtyUnknownAsNullCmd() *cobra.Command {
	var typeJSON string
	cmd := &cobra.Command{
		Use:   "unknown-as-null [value-json]",
		Short: "Apply cty.UnknownAsNull and report the result",
		Long: `Rewrite every unknown in a value, at any depth, as a null of the same type.

  soup-go cty unknown-as-null --type '["list","string"]' '["a",{"$unknown":true}]'`,
		Args: cobra.ExactArgs(1),
		RunE: func(cmd *cobra.Command, args []string) error {
			val, err := decodeTypedArg(typeJSON, args[0])
			if err != nil {
				return emit(cmd, map[string]any{"ok": false, "error": err.Error()})
			}

			var result cty.Value
			if panicked := recovered(func() { result = cty.UnknownAsNull(val) }); panicked != "" {
				return emit(cmd, map[string]any{"ok": false, "panic": panicked})
			}
			encoded, err := encodeRich(result)
			if err != nil {
				return emit(cmd, map[string]any{"ok": false, "error": err.Error()})
			}
			resultType, err := marshalResultType(result.Type())
			if err != nil {
				return emit(cmd, map[string]any{"ok": false, "error": err.Error()})
			}
			return emit(cmd, map[string]any{"ok": true, "value": encoded, "type": resultType})
		},
	}
	typeFlag(cmd, &typeJSON)
	return cmd
}

func initCtyMarksCmd() *cobra.Command {
	var typeJSON string
	cmd := &cobra.Command{
		Use:   "marks [value-json]",
		Short: "Report UnmarkDeepWithPaths, then put the marks back",
		Long: `Strip every mark in a value and report where each one was, then re-apply them.

The round trip is reported rather than assumed: MarkWithPaths is the half that
a caller depends on when it strips marks, computes, and restores them, and a
path that does not point back at the same place is exactly the failure that
silently loses a sensitivity flag.

  soup-go cty marks --type '["list","string"]' '[{"$marks":["sensitive"],"$value":"a"}]'`,
		Args: cobra.ExactArgs(1),
		RunE: func(cmd *cobra.Command, args []string) error {
			val, err := decodeTypedArg(typeJSON, args[0])
			if err != nil {
				return emit(cmd, map[string]any{"ok": false, "error": err.Error()})
			}

			unmarked, pvms := val.UnmarkDeepWithPaths()
			paths := make([]any, 0, len(pvms))
			for _, pvm := range pvms {
				steps, err := encodePath(pvm.Path)
				if err != nil {
					return emit(cmd, map[string]any{"ok": false, "error": err.Error()})
				}
				paths = append(paths, map[string]any{"path": steps, "marks": markNames(pvm.Marks)})
			}

			encoded, err := encodeRich(unmarked)
			if err != nil {
				return emit(cmd, map[string]any{"ok": false, "error": err.Error()})
			}

			remarked := unmarked.MarkWithPaths(pvms)
			return emit(cmd, map[string]any{
				"ok":               true,
				"unmarked":         encoded,
				"paths":            paths,
				"round_trip_equal": remarked.RawEquals(val),
			})
		},
	}
	typeFlag(cmd, &typeJSON)
	return cmd
}

func initCtyConformanceCmd() *cobra.Command {
	var givenJSON, wantJSON string
	cmd := &cobra.Command{
		Use:   "conformance",
		Short: "Report Type.TestConformance errors",
		Long: `Test whether one type conforms to another, reporting every non-conformity.

Conformance is not type equality: cty.DynamicPseudoType in the wanted type
accepts anything, and that asymmetry is the whole point of the operation.

  soup-go cty conformance --given '["object",{"a":"string"}]' --want '["object",{"a":"number"}]'`,
		RunE: func(cmd *cobra.Command, args []string) error {
			given, err := parseCtyType(json.RawMessage(givenJSON))
			if err != nil {
				return emit(cmd, map[string]any{"ok": false, "error": fmt.Sprintf("given: %s", err)})
			}
			want, err := parseCtyType(json.RawMessage(wantJSON))
			if err != nil {
				return emit(cmd, map[string]any{"ok": false, "error": fmt.Sprintf("want: %s", err)})
			}

			errs := given.TestConformance(want)
			reported := make([]any, 0, len(errs))
			for _, err := range errs {
				entry := map[string]any{"message": err.Error()}
				if pathErr, ok := err.(cty.PathError); ok {
					steps, encodeErr := encodePath(pathErr.Path)
					if encodeErr != nil {
						return emit(cmd, map[string]any{"ok": false, "error": encodeErr.Error()})
					}
					entry["path"] = steps
				}
				reported = append(reported, entry)
			}
			return emit(cmd, map[string]any{"ok": true, "conforms": len(errs) == 0, "errors": reported})
		},
	}
	cmd.Flags().StringVar(&givenJSON, "given", "", "the type being tested, as JSON")
	cmd.Flags().StringVar(&wantJSON, "want", "", "the type constraint, as JSON")
	_ = cmd.MarkFlagRequired("given")
	_ = cmd.MarkFlagRequired("want")
	return cmd
}

func initCtyJSONCmd() *cobra.Command {
	cmd := &cobra.Command{
		Use:   "json",
		Short: "The cty/json value codec",
		Long: `Marshal and unmarshal values with cty/json.

Distinct from the jsonencode and jsondecode stdlib functions, which produce a
string value inside cty. This codec is how a value crosses a process boundary
as JSON, and it makes different choices: a dynamic-typed position is wrapped in
a {"value":..., "type":...} envelope so the type survives the trip.`,
	}
	cmd.AddCommand(initCtyJSONMarshalCmd(), initCtyJSONUnmarshalCmd(), initCtyJSONImpliedTypeCmd())
	return cmd
}

func initCtyJSONMarshalCmd() *cobra.Command {
	var typeJSON string
	cmd := &cobra.Command{
		Use:   "marshal [value-json]",
		Short: "ctyjson.Marshal a value",
		Args:  cobra.ExactArgs(1),
		RunE: func(cmd *cobra.Command, args []string) error {
			ty, err := parseCtyType(json.RawMessage(typeJSON))
			if err != nil {
				return emit(cmd, map[string]any{"ok": false, "error": err.Error()})
			}
			val, err := decodeRich(ty, json.RawMessage(args[0]))
			if err != nil {
				return emit(cmd, map[string]any{"ok": false, "error": err.Error()})
			}

			var encoded []byte
			var marshalErr error
			if panicked := recovered(func() { encoded, marshalErr = ctyjson.Marshal(val, ty) }); panicked != "" {
				return emit(cmd, map[string]any{"ok": false, "panic": panicked})
			}
			if marshalErr != nil {
				return emit(cmd, map[string]any{"ok": false, "error": marshalErr.Error()})
			}
			// Both the parsed form and the exact bytes. A caller comparing
			// serializers has to compare bytes: 1E-7 and 0.0000001 parse to the
			// same number and are not the same state file, and Go's encoder
			// escapes < > & where Python's does not.
			return emit(cmd, map[string]any{
				"ok":   true,
				"json": json.RawMessage(encoded),
				"text": string(encoded),
			})
		},
	}
	typeFlag(cmd, &typeJSON)
	return cmd
}

func initCtyJSONUnmarshalCmd() *cobra.Command {
	var typeJSON string
	cmd := &cobra.Command{
		Use:   "unmarshal [json]",
		Short: "ctyjson.Unmarshal into a type",
		Args:  cobra.ExactArgs(1),
		RunE: func(cmd *cobra.Command, args []string) error {
			ty, err := parseCtyType(json.RawMessage(typeJSON))
			if err != nil {
				return emit(cmd, map[string]any{"ok": false, "error": err.Error()})
			}

			var val cty.Value
			var unmarshalErr error
			if panicked := recovered(func() {
				val, unmarshalErr = ctyjson.Unmarshal([]byte(args[0]), ty)
			}); panicked != "" {
				return emit(cmd, map[string]any{"ok": false, "panic": panicked})
			}
			if unmarshalErr != nil {
				return emit(cmd, map[string]any{"ok": false, "error": unmarshalErr.Error()})
			}

			encoded, err := encodeRich(val)
			if err != nil {
				return emit(cmd, map[string]any{"ok": false, "error": err.Error()})
			}
			resultType, err := marshalResultType(val.Type())
			if err != nil {
				return emit(cmd, map[string]any{"ok": false, "error": err.Error()})
			}
			return emit(cmd, map[string]any{"ok": true, "value": encoded, "type": resultType})
		},
	}
	typeFlag(cmd, &typeJSON)
	return cmd
}

func initCtyJSONImpliedTypeCmd() *cobra.Command {
	return &cobra.Command{
		Use:   "implied-type [json]",
		Short: "ctyjson.ImpliedType for a JSON document",
		Args:  cobra.ExactArgs(1),
		RunE: func(cmd *cobra.Command, args []string) error {
			var ty cty.Type
			var impliedErr error
			if panicked := recovered(func() { ty, impliedErr = ctyjson.ImpliedType([]byte(args[0])) }); panicked != "" {
				return emit(cmd, map[string]any{"ok": false, "panic": panicked})
			}
			if impliedErr != nil {
				return emit(cmd, map[string]any{"ok": false, "error": impliedErr.Error()})
			}
			encoded, err := marshalResultType(ty)
			if err != nil {
				return emit(cmd, map[string]any{"ok": false, "error": err.Error()})
			}
			return emit(cmd, map[string]any{"ok": true, "type": encoded})
		},
	}
}

func initCtyRangeCmd() *cobra.Command {
	var typeJSON, includesJSON string
	cmd := &cobra.Command{
		Use:   "range [value-json]",
		Short: "Report Value.Range, and optionally ValueRange.Includes",
		Long: `Report everything go-cty's Value.Range can say about a value.

Refinements are given as part of the value, so this covers Value.Refine too:

  soup-go cty range --type string '{"$unknown":true,"$refine":{"string_prefix":"ht"}}'
  soup-go cty range --type number '{"$unknown":true}' --includes '5'

Bounds are reported exactly as go-cty returns them, infinities included. The
docstrings say an unbounded number range returns an unknown number; the code
returns an infinity, and this reports what the code does.`,
		Args: cobra.ExactArgs(1),
		RunE: func(cmd *cobra.Command, args []string) error {
			val, err := decodeTypedArg(typeJSON, args[0])
			if err != nil {
				return emit(cmd, map[string]any{"ok": false, "error": err.Error()})
			}

			out := map[string]any{"ok": true}
			var rng cty.ValueRange
			if panicked := recovered(func() { rng = val.Range() }); panicked != "" {
				return emit(cmd, map[string]any{"ok": false, "panic": panicked})
			}

			if err := describeRange(rng, out); err != nil {
				return emit(cmd, map[string]any{"ok": false, "error": err.Error()})
			}

			if includesJSON != "" {
				if err := describeIncludes(rng, includesJSON, out); err != nil {
					return emit(cmd, map[string]any{"ok": false, "error": err.Error()})
				}
			}
			return emit(cmd, out)
		},
	}
	typeFlag(cmd, &typeJSON)
	cmd.Flags().StringVar(&includesJSON, "includes", "", "a candidate value to test for membership, as a rich value of the same type")
	return cmd
}

func describeRange(rng cty.ValueRange, out map[string]any) error {
	constraint, err := marshalResultType(rng.TypeConstraint())
	if err != nil {
		return err
	}
	out["type_constraint"] = constraint
	out["could_be_null"] = rng.CouldBeNull()
	out["definitely_not_null"] = rng.DefinitelyNotNull()

	// Each accessor panics for a type it does not apply to, so ask only the
	// questions the type admits. A dynamic constraint admits all of them.
	ty := rng.TypeConstraint()
	dynamic := ty == cty.DynamicPseudoType
	if dynamic || ty == cty.String {
		out["string_prefix"] = rng.StringPrefix()
	}
	if dynamic || ty == cty.Number {
		lower, lowerInc := rng.NumberLowerBound()
		upper, upperInc := rng.NumberUpperBound()
		encodedLower, err := encodeRich(lower)
		if err != nil {
			return err
		}
		encodedUpper, err := encodeRich(upper)
		if err != nil {
			return err
		}
		out["number_lower_bound"] = []any{encodedLower, lowerInc}
		out["number_upper_bound"] = []any{encodedUpper, upperInc}
	}
	if dynamic || ty.IsCollectionType() {
		out["length_lower_bound"] = rng.LengthLowerBound()
		upper := rng.LengthUpperBound()
		out["length_upper_bound"] = upper
		out["length_upper_bound_is_maxint"] = upper == math.MaxInt
	}
	return nil
}

func describeIncludes(rng cty.ValueRange, includesJSON string, out map[string]any) error {
	candidate, err := decodeRich(rng.TypeConstraint(), json.RawMessage(includesJSON))
	if err != nil {
		return fmt.Errorf("failed to build the candidate: %w", err)
	}

	var answer cty.Value
	if panicked := recovered(func() { answer = rng.Includes(candidate) }); panicked != "" {
		out["includes_panic"] = panicked
		return nil
	}

	// Reported field by field rather than as a rich value: the interesting part
	// is the three-valuedness, and go-cty's undecided answer is not a bare
	// unknown -- it carries a not-null refinement, which a caller can observe.
	described := map[string]any{"known": answer.IsKnown()}
	if answer.IsKnown() {
		described["value"] = answer.True()
	} else {
		described["definitely_not_null"] = answer.Range().DefinitelyNotNull()
	}
	out["includes"] = described
	return nil
}

func initCtySafeKnownPrefixCmd() *cobra.Command {
	return &cobra.Command{
		Use:   "safe-known-prefix [string]",
		Short: "ctystrings.SafeKnownPrefix for a string prefix",
		Long: `Trim a string prefix back to a point where appending anything is safe.

A prefix may end part-way through a grapheme cluster, and a later append could
combine with it -- so the safe prefix is shorter than the given one whenever
the last cluster could still grow.

  soup-go cty safe-known-prefix 'hello'`,
		Args: cobra.ExactArgs(1),
		RunE: func(cmd *cobra.Command, args []string) error {
			var prefix string
			if panicked := recovered(func() { prefix = ctystrings.SafeKnownPrefix(args[0]) }); panicked != "" {
				return emit(cmd, map[string]any{"ok": false, "panic": panicked})
			}
			return emit(cmd, map[string]any{"ok": true, "prefix": prefix})
		},
	}
}

func initCtyConvertValueCmd() *cobra.Command {
	var fromJSON, toJSON string
	cmd := &cobra.Command{
		Use:   "convert-value [value-json]",
		Short: "Report convert.Convert, and whether the conversion is safe",
		Long: `Convert a value to another type, the way go-cty's convert package does.

Distinct from ` + "`cty convert`" + `, which converts between *serialization formats*.
This is type conversion: the thing Terraform does when a practitioner writes a
number where a string is wanted.

Three answers, because they are three different questions. GetConversion finds
only the safe conversions -- ones that cannot lose information -- while
GetConversionUnsafe also allows those that can fail at runtime, and Convert
itself uses the unsafe set. MismatchMessage is the sentence a practitioner sees
when none of them applies.

  soup-go cty convert-value --from '"number"' --to '"string"' '5'`,
		Args: cobra.ExactArgs(1),
		RunE: func(cmd *cobra.Command, args []string) error {
			from, err := parseCtyType(json.RawMessage(fromJSON))
			if err != nil {
				return emit(cmd, map[string]any{"ok": false, "error": fmt.Sprintf("from: %s", err)})
			}
			to, err := parseCtyType(json.RawMessage(toJSON))
			if err != nil {
				return emit(cmd, map[string]any{"ok": false, "error": fmt.Sprintf("to: %s", err)})
			}
			val, err := decodeRich(from, json.RawMessage(args[0]))
			if err != nil {
				return emit(cmd, map[string]any{"ok": false, "error": err.Error()})
			}

			// Identical types are convertible without a *conversion*: go-cty
			// returns nil there because nothing needs doing, and `Convert`
			// short-circuits before ever asking. Reporting the bare nil as
			// "not convertible" made string-to-string look like a divergence.
			identical := from.Equals(to.WithoutOptionalAttributesDeep())
			out := map[string]any{
				"safe":             identical || convert.GetConversion(from, to) != nil,
				"unsafe":           identical || convert.GetConversionUnsafe(from, to) != nil,
				"mismatch_message": convert.MismatchMessage(from, to),
			}

			var converted cty.Value
			var convertErr error
			if panicked := recovered(func() { converted, convertErr = convert.Convert(val, to) }); panicked != "" {
				out["ok"] = false
				out["panic"] = panicked
				return emit(cmd, out)
			}
			if convertErr != nil {
				out["ok"] = false
				out["error"] = convertErr.Error()
				return emit(cmd, out)
			}

			encoded, err := encodeRich(converted)
			if err != nil {
				out["ok"] = false
				out["error"] = err.Error()
				return emit(cmd, out)
			}
			resultType, err := marshalResultType(converted.Type())
			if err != nil {
				out["ok"] = false
				out["error"] = err.Error()
				return emit(cmd, out)
			}
			out["ok"] = true
			out["value"] = encoded
			out["type"] = resultType
			return emit(cmd, out)
		},
	}
	cmd.Flags().StringVar(&fromJSON, "from", "", "the value's type, as JSON")
	cmd.Flags().StringVar(&toJSON, "to", "", "the target type, as JSON")
	_ = cmd.MarkFlagRequired("from")
	_ = cmd.MarkFlagRequired("to")
	return cmd
}

// visitRecord is one (path, value) pair seen by a walk.
func visitRecord(path cty.Path, val cty.Value) (map[string]any, error) {
	steps, err := encodePath(path)
	if err != nil {
		return nil, err
	}
	encoded, err := encodeRich(val)
	if err != nil {
		return nil, err
	}
	unmarked, _ := val.Unmark()
	ty, err := marshalResultType(unmarked.Type())
	if err != nil {
		return nil, err
	}
	return map[string]any{"path": steps, "value": encoded, "type": ty}, nil
}

func initCtyWalkCmd() *cobra.Command {
	var typeJSON string
	var pruneDepth int
	cmd := &cobra.Command{
		Use:   "walk [value-json]",
		Short: "Report the (path, value) pairs cty.Walk visits, in order",
		Long: `Walk a value and report every visit: the path, the value, and its type.

Order is the contract. Walk sees a container before its children, an object's
attributes come from an iterator, and a set element's path holds the element
itself -- none of which a second implementation can check against a reading of
the source.

--prune-depth exercises the callback's other answer. Returning false declines to
descend, and a walk that ignores it visits values the caller asked not to see.

  soup-go cty walk --type '["list","string"]' '["a","b"]'
  soup-go cty walk --type '["list","string"]' '["a"]' --prune-depth 0`,
		Args: cobra.ExactArgs(1),
		RunE: func(cmd *cobra.Command, args []string) error {
			val, err := decodeTypedArg(typeJSON, args[0])
			if err != nil {
				return emit(cmd, map[string]any{"ok": false, "error": err.Error()})
			}

			visits := make([]any, 0, 8)
			var recordErr error
			walkErr := cty.Walk(val, func(path cty.Path, v cty.Value) (bool, error) {
				record, err := visitRecord(path, v)
				if err != nil {
					recordErr = err
					return false, err
				}
				visits = append(visits, record)
				if pruneDepth >= 0 && len(path) >= pruneDepth {
					return false, nil
				}
				return true, nil
			})
			if recordErr != nil {
				return emit(cmd, map[string]any{"ok": false, "error": recordErr.Error()})
			}
			if walkErr != nil {
				return emit(cmd, map[string]any{"ok": false, "error": walkErr.Error()})
			}
			return emit(cmd, map[string]any{"ok": true, "visits": visits})
		},
	}
	typeFlag(cmd, &typeJSON)
	cmd.Flags().IntVar(&pruneDepth, "prune-depth", -1, "decline to descend once the path is this long (-1 never prunes)")
	return cmd
}

// transformOps are the named rewrites `cty transform` can apply.
//
// A transformation is a function, and a function does not travel over a command
// line, so both implementations agree on a small set of rewrites by name
// instead. Each is written to be exact about marks and about which values it
// touches, because "the same transformation" is the premise of the comparison.
var transformOps = map[string]func(cty.Value) (cty.Value, error){
	// Uppercase every known, non-null string, keeping its marks.
	"upper": func(val cty.Value) (cty.Value, error) {
		unmarked, marks := val.Unmark()
		if unmarked.Type() != cty.String || unmarked.IsNull() || !unmarked.IsKnown() {
			return val, nil
		}
		return cty.StringVal(strings.ToUpper(unmarked.AsString())).WithMarks(marks), nil
	},
	// Rewrite every unknown as a null of the same type. The same answer
	// cty.UnknownAsNull gives, reached the other way, which is worth having as
	// a cross-check on both.
	"unknown-to-null": func(val cty.Value) (cty.Value, error) {
		unmarked, marks := val.Unmark()
		if unmarked.IsKnown() {
			return val, nil
		}
		return cty.NullVal(unmarked.Type()).WithMarks(marks), nil
	},
}

func initCtyTransformCmd() *cobra.Command {
	var typeJSON, op string
	cmd := &cobra.Command{
		Use:   "transform [value-json]",
		Short: "Apply a named rewrite with cty.Transform and report the result",
		Long: `Rebuild a value bottom-up, applying one of a small set of named rewrites.

Transform visits children first, so a container is rebuilt from values that have
already been rewritten -- which is where the result's *type* comes from, and the
part a second implementation is most likely to get wrong.

Known rewrites: upper, unknown-to-null.

  soup-go cty transform --type '["list","string"]' --op upper '["a","b"]'`,
		Args: cobra.ExactArgs(1),
		RunE: func(cmd *cobra.Command, args []string) error {
			rewrite, ok := transformOps[op]
			if !ok {
				names := make([]string, 0, len(transformOps))
				for name := range transformOps {
					names = append(names, name)
				}
				sort.Strings(names)
				return fmt.Errorf("unknown op %q; known: %s", op, strings.Join(names, ", "))
			}
			val, err := decodeTypedArg(typeJSON, args[0])
			if err != nil {
				return emit(cmd, map[string]any{"ok": false, "error": err.Error()})
			}

			var result cty.Value
			var transformErr error
			if panicked := recovered(func() {
				result, transformErr = cty.Transform(val, func(_ cty.Path, v cty.Value) (cty.Value, error) {
					return rewrite(v)
				})
			}); panicked != "" {
				return emit(cmd, map[string]any{"ok": false, "panic": panicked})
			}
			if transformErr != nil {
				return emit(cmd, map[string]any{"ok": false, "error": transformErr.Error()})
			}

			encoded, err := encodeRich(result)
			if err != nil {
				return emit(cmd, map[string]any{"ok": false, "error": err.Error()})
			}
			unmarked, _ := result.Unmark()
			resultType, err := marshalResultType(unmarked.Type())
			if err != nil {
				return emit(cmd, map[string]any{"ok": false, "error": err.Error()})
			}
			return emit(cmd, map[string]any{"ok": true, "value": encoded, "type": resultType})
		},
	}
	typeFlag(cmd, &typeJSON)
	cmd.Flags().StringVar(&op, "op", "", "the rewrite to apply: upper, unknown-to-null")
	_ = cmd.MarkFlagRequired("op")
	return cmd
}

func initCtyMsgpackCmd() *cobra.Command {
	cmd := &cobra.Command{
		Use:   "msgpack",
		Short: "The cty/msgpack codec, including unknowns and refinements",
		Long: `Encode and decode values with cty/msgpack, as the Terraform wire protocol does.

` + "`wire encode`" + ` already round-trips values through this codec, but it builds
them from plain JSON and so cannot express an unknown -- which is exactly what
Terraform puts on the wire for an attribute it has not decided yet, refinements
and all. These take the rich dialect instead.`,
	}
	cmd.AddCommand(initCtyMsgpackEncodeCmd(), initCtyMsgpackDecodeCmd())
	return cmd
}

func initCtyMsgpackEncodeCmd() *cobra.Command {
	var typeJSON string
	cmd := &cobra.Command{
		Use:   "encode [value-json]",
		Short: "msgpack.Marshal a value, reported as base64",
		Args:  cobra.ExactArgs(1),
		RunE: func(cmd *cobra.Command, args []string) error {
			ty, err := parseCtyType(json.RawMessage(typeJSON))
			if err != nil {
				return emit(cmd, map[string]any{"ok": false, "error": err.Error()})
			}
			val, err := decodeRich(ty, json.RawMessage(args[0]))
			if err != nil {
				return emit(cmd, map[string]any{"ok": false, "error": err.Error()})
			}

			var encoded []byte
			var marshalErr error
			if panicked := recovered(func() { encoded, marshalErr = ctymsgpack.Marshal(val, ty) }); panicked != "" {
				return emit(cmd, map[string]any{"ok": false, "panic": panicked})
			}
			if marshalErr != nil {
				return emit(cmd, map[string]any{"ok": false, "error": marshalErr.Error()})
			}
			return emit(cmd, map[string]any{
				"ok":     true,
				"base64": base64.StdEncoding.EncodeToString(encoded),
				"hex":    hex.EncodeToString(encoded),
			})
		},
	}
	typeFlag(cmd, &typeJSON)
	return cmd
}

func initCtyMsgpackDecodeCmd() *cobra.Command {
	var typeJSON string
	cmd := &cobra.Command{
		Use:   "decode [base64]",
		Short: "msgpack.Unmarshal into a type, reported as a rich value",
		Args:  cobra.ExactArgs(1),
		RunE: func(cmd *cobra.Command, args []string) error {
			ty, err := parseCtyType(json.RawMessage(typeJSON))
			if err != nil {
				return emit(cmd, map[string]any{"ok": false, "error": err.Error()})
			}
			raw, err := base64.StdEncoding.DecodeString(args[0])
			if err != nil {
				return emit(cmd, map[string]any{"ok": false, "error": fmt.Sprintf("not base64: %s", err)})
			}

			var val cty.Value
			var unmarshalErr error
			if panicked := recovered(func() { val, unmarshalErr = ctymsgpack.Unmarshal(raw, ty) }); panicked != "" {
				return emit(cmd, map[string]any{"ok": false, "panic": panicked})
			}
			if unmarshalErr != nil {
				return emit(cmd, map[string]any{"ok": false, "error": unmarshalErr.Error()})
			}

			encoded, err := encodeRich(val)
			if err != nil {
				return emit(cmd, map[string]any{"ok": false, "error": err.Error()})
			}
			return emit(cmd, map[string]any{"ok": true, "value": encoded})
		},
	}
	typeFlag(cmd, &typeJSON)
	return cmd
}

func initCtyEqualsCmd() *cobra.Command {
	var leftTypeJSON, rightTypeJSON string
	cmd := &cobra.Command{
		Use:   "equals [left-json] [right-json]",
		Short: "Report Value.Equals and Value.RawEquals",
		Long: `Compare two values the way cty itself does, not the way the stdlib does.

` + "`cty call equal`" + ` reaches stdlib.EqualFunc, which unifies its arguments
first. This is Value.Equals: three-valued, mark-propagating, and willing to say
"not yet decided" -- the comparison a provider does when it asks whether planned
state matches prior state.

RawEquals comes along because the two answer different questions. Equals is
about the values; RawEquals is about the representations, and it is the one that
distinguishes an unknown from a null of the same type.

  soup-go cty equals --left-type '"string"' --right-type '"string"' '"a"' '{"$unknown":true}'`,
		Args: cobra.ExactArgs(2),
		RunE: func(cmd *cobra.Command, args []string) error {
			left, err := decodeTypedArg(leftTypeJSON, args[0])
			if err != nil {
				return emit(cmd, map[string]any{"ok": false, "error": fmt.Sprintf("left: %s", err)})
			}
			right, err := decodeTypedArg(rightTypeJSON, args[1])
			if err != nil {
				return emit(cmd, map[string]any{"ok": false, "error": fmt.Sprintf("right: %s", err)})
			}

			var answer cty.Value
			if panicked := recovered(func() { answer = left.Equals(right) }); panicked != "" {
				return emit(cmd, map[string]any{"ok": false, "panic": panicked})
			}

			unmarked, marks := answer.Unmark()
			described := map[string]any{"known": unmarked.IsKnown()}
			if unmarked.IsKnown() {
				described["value"] = unmarked.True()
			}
			if len(marks) > 0 {
				described["marks"] = markNames(marks)
			}

			var raw bool
			if panicked := recovered(func() { raw = left.RawEquals(right) }); panicked != "" {
				return emit(cmd, map[string]any{"ok": false, "panic": panicked})
			}
			return emit(cmd, map[string]any{"ok": true, "equals": described, "raw_equals": raw})
		},
	}
	cmd.Flags().StringVar(&leftTypeJSON, "left-type", "", "the left value's type, as JSON")
	cmd.Flags().StringVar(&rightTypeJSON, "right-type", "", "the right value's type, as JSON")
	_ = cmd.MarkFlagRequired("left-type")
	_ = cmd.MarkFlagRequired("right-type")
	return cmd
}

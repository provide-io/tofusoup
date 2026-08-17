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
//
// Every command reports go-cty's refusals and panics as data rather than
// exiting, because "go-cty will not do this" is one of the answers a parity run
// needs to record. A command that died on the first refusal would make the
// caller's comparison stop at the first interesting case.

import (
	"encoding/json"
	"fmt"
	"math"

	"github.com/spf13/cobra"
	"github.com/zclconf/go-cty/cty"
	"github.com/zclconf/go-cty/cty/ctystrings"
	ctyjson "github.com/zclconf/go-cty/cty/json"
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

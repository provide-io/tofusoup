package main

import (
	"encoding/json"
	"fmt"
	"sort"
	"strings"

	"github.com/spf13/cobra"
	"github.com/zclconf/go-cty/cty"
	"github.com/zclconf/go-cty/cty/function"
	"github.com/zclconf/go-cty/cty/function/stdlib"
	ctyjson "github.com/zclconf/go-cty/cty/json"
)

// stdlibFunctions is the oracle surface: go-cty's own standard library, keyed
// by the name pyvider.cty exports the equivalent under. go-cty has no runtime
// registry to enumerate, so this map is written out by hand and is the single
// place to extend when a new function needs comparing.
var stdlibFunctions = map[string]function.Function{
	// strings
	"upper":        stdlib.UpperFunc,
	"lower":        stdlib.LowerFunc,
	"title":        stdlib.TitleFunc,
	"trimspace":    stdlib.TrimSpaceFunc,
	"trim":         stdlib.TrimFunc,
	"trimprefix":   stdlib.TrimPrefixFunc,
	"trimsuffix":   stdlib.TrimSuffixFunc,
	"chomp":        stdlib.ChompFunc,
	"indent":       stdlib.IndentFunc,
	"join":         stdlib.JoinFunc,
	"split":        stdlib.SplitFunc,
	"replace":      stdlib.ReplaceFunc,
	"regexreplace": stdlib.RegexReplaceFunc,
	"regex":        stdlib.RegexFunc,
	"regexall":     stdlib.RegexAllFunc,
	"substr":       stdlib.SubstrFunc,
	"strrev":       stdlib.ReverseFunc,
	"format":       stdlib.FormatFunc,
	"formatlist":   stdlib.FormatListFunc,

	// collections
	"length":       stdlib.LengthFunc,
	"element":      stdlib.ElementFunc,
	"index":        stdlib.IndexFunc,
	"contains":     stdlib.ContainsFunc,
	"distinct":     stdlib.DistinctFunc,
	"chunklist":    stdlib.ChunklistFunc,
	"flatten":      stdlib.FlattenFunc,
	"keys":         stdlib.KeysFunc,
	"values":       stdlib.ValuesFunc,
	"lookup":       stdlib.LookupFunc,
	"merge":        stdlib.MergeFunc,
	"coalescelist": stdlib.CoalesceListFunc,
	"compact":      stdlib.CompactFunc,
	"concat":       stdlib.ConcatFunc,
	"range":        stdlib.RangeFunc,
	"reverselist":  stdlib.ReverseListFunc,
	"setproduct":   stdlib.SetProductFunc,
	"slice":        stdlib.SliceFunc,
	"sort":         stdlib.SortFunc,
	"zipmap":       stdlib.ZipmapFunc,
	"hasindex":     stdlib.HasIndexFunc,

	// sets
	"setunion":        stdlib.SetUnionFunc,
	"setintersection": stdlib.SetIntersectionFunc,
	"setsubtract":     stdlib.SetSubtractFunc,

	// numbers
	"abs":      stdlib.AbsoluteFunc,
	"add":      stdlib.AddFunc,
	"subtract": stdlib.SubtractFunc,
	"multiply": stdlib.MultiplyFunc,
	"divide":   stdlib.DivideFunc,
	"modulo":   stdlib.ModuloFunc,
	"negate":   stdlib.NegateFunc,
	"pow":      stdlib.PowFunc,
	"log":      stdlib.LogFunc,
	"signum":   stdlib.SignumFunc,
	"ceil":     stdlib.CeilFunc,
	"floor":    stdlib.FloorFunc,
	"int":      stdlib.IntFunc,
	"min":      stdlib.MinFunc,
	"max":      stdlib.MaxFunc,
	"parseint": stdlib.ParseIntFunc,

	// comparison and logic
	"equal":                stdlib.EqualFunc,
	"notequal":             stdlib.NotEqualFunc,
	"lessthan":             stdlib.LessThanFunc,
	"lessthanorequalto":    stdlib.LessThanOrEqualToFunc,
	"greaterthan":          stdlib.GreaterThanFunc,
	"greaterthanorequalto": stdlib.GreaterThanOrEqualToFunc,
	"and":                  stdlib.AndFunc,
	"or":                   stdlib.OrFunc,
	"not":                  stdlib.NotFunc,
	"coalesce":             stdlib.CoalesceFunc,

	// encoding and time
	"jsonencode": stdlib.JSONEncodeFunc,
	"jsondecode": stdlib.JSONDecodeFunc,
	"csvdecode":  stdlib.CSVDecodeFunc,
	"formatdate": stdlib.FormatDateFunc,
	"timeadd":    stdlib.TimeAddFunc,
}

// callArg is one argument, given as a type spec plus a JSON value so that the
// caller controls the cty type exactly rather than relying on inference.
type callArg struct {
	Type    json.RawMessage `json:"type"`
	Value   json.RawMessage `json:"value"`
	Unknown bool            `json:"unknown,omitempty"`
	Null    bool            `json:"null,omitempty"`
	Marks   []string        `json:"marks,omitempty"`
}

// callResult is deliberately explicit about the states that matter for parity:
// a value that is unknown, null or marked is a different answer from the value
// it would otherwise hold, and JSON alone cannot express the difference.
type callResult struct {
	Function string          `json:"function"`
	OK       bool            `json:"ok"`
	Error    string          `json:"error,omitempty"`
	Type     json.RawMessage `json:"type,omitempty"`
	Value    json.RawMessage `json:"value,omitempty"`
	Unknown  bool            `json:"unknown"`
	Null     bool            `json:"null"`
	Marks    []string        `json:"marks,omitempty"`
}

func decodeCallArg(raw json.RawMessage) (cty.Value, error) {
	var arg callArg
	if err := json.Unmarshal(raw, &arg); err != nil {
		return cty.NilVal, fmt.Errorf("argument is not a {type, value} object: %w", err)
	}
	if len(arg.Type) == 0 {
		return cty.NilVal, fmt.Errorf("argument is missing a type")
	}

	ty, err := parseCtyType(arg.Type)
	if err != nil {
		return cty.NilVal, fmt.Errorf("failed to parse argument type: %w", err)
	}

	var val cty.Value
	switch {
	case arg.Unknown:
		val = cty.UnknownVal(ty)
	case arg.Null:
		val = cty.NullVal(ty)
	default:
		val, err = buildCtyValueFromJSON(ty, arg.Value)
		if err != nil {
			return cty.NilVal, fmt.Errorf("failed to build argument value: %w", err)
		}
	}

	for _, name := range arg.Marks {
		val = val.Mark(name)
	}
	return val, nil
}

func describeResult(name string, result cty.Value, callErr error) callResult {
	out := callResult{Function: name}
	if callErr != nil {
		out.Error = callErr.Error()
		return out
	}
	out.OK = true

	unmarked, marks := result.UnmarkDeep()
	for m := range marks {
		if s, ok := m.(string); ok {
			out.Marks = append(out.Marks, s)
		} else {
			out.Marks = append(out.Marks, fmt.Sprintf("%v", m))
		}
	}
	sort.Strings(out.Marks)

	out.Unknown = !unmarked.IsKnown()
	if out.Unknown {
		// A null check on an unknown value panics, and the type is still the
		// useful part of the answer.
		if tyJSON, err := ctyjson.MarshalType(unmarked.Type()); err == nil {
			out.Type = tyJSON
		}
		return out
	}

	out.Null = unmarked.IsNull()
	if tyJSON, err := ctyjson.MarshalType(unmarked.Type()); err == nil {
		out.Type = tyJSON
	}
	if valJSON, err := ctyjson.Marshal(unmarked, unmarked.Type()); err == nil {
		out.Value = valJSON
	}
	return out
}

func initCtyCallCmd() *cobra.Command {
	cmd := &cobra.Command{
		Use:   "call [function] [arg-json...]",
		Short: "Call a go-cty stdlib function and report its exact result",
		Long: `Call a function from go-cty's standard library and print the result as JSON.

Exists to be an oracle: a second implementation can be compared against real
go-cty behaviour rather than against a reading of its source.

Each argument is a JSON object {"type": <type-spec>, "value": <json>}, and may
instead set "unknown": true or "null": true, or carry "marks": ["sensitive"].
The result reports unknown-ness, null-ness and marks separately from the value,
because those are exactly the distinctions a JSON value cannot carry.

  soup-go cty call upper '{"type":"string","value":"hello"}'
  soup-go cty call contains '{"type":["list","string"],"value":["a"]}' '{"type":"string","unknown":true}'
  soup-go cty call upper '{"type":"string","value":"hi","marks":["sensitive"]}'`,
		Args: cobra.MinimumNArgs(1),
		RunE: func(cmd *cobra.Command, args []string) error {
			name := args[0]
			fn, ok := stdlibFunctions[name]
			if !ok {
				known := make([]string, 0, len(stdlibFunctions))
				for k := range stdlibFunctions {
					known = append(known, k)
				}
				sort.Strings(known)
				return fmt.Errorf("unknown function %q; known: %s", name, strings.Join(known, ", "))
			}

			argVals := make([]cty.Value, 0, len(args)-1)
			for i, raw := range args[1:] {
				val, err := decodeCallArg(json.RawMessage(raw))
				if err != nil {
					return fmt.Errorf("argument %d: %w", i, err)
				}
				argVals = append(argVals, val)
			}

			// Errors are reported in the result rather than raised, so that a
			// comparison run can record "go-cty refuses this" as a finding
			// instead of dying on it.
			result, callErr := fn.Call(argVals)
			out := describeResult(name, result, callErr)

			encoded, err := json.Marshal(out)
			if err != nil {
				return fmt.Errorf("failed to encode result: %w", err)
			}
			fmt.Fprintln(cmd.OutOrStdout(), string(encoded))
			return nil
		},
	}
	return cmd
}

func initCtyFunctionsCmd() *cobra.Command {
	return &cobra.Command{
		Use:   "functions",
		Short: "List the go-cty stdlib functions available to `cty call`",
		RunE: func(cmd *cobra.Command, args []string) error {
			names := make([]string, 0, len(stdlibFunctions))
			for k := range stdlibFunctions {
				names = append(names, k)
			}
			sort.Strings(names)
			encoded, err := json.Marshal(names)
			if err != nil {
				return err
			}
			fmt.Fprintln(cmd.OutOrStdout(), string(encoded))
			return nil
		},
	}
}

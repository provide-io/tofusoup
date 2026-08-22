package main

import (
	"bytes"
	"encoding/base64"
	"encoding/json"
	"fmt"
	"io"
	"math/big"
	"os"
	"sort"
	"strconv"
	"strings"

	"github.com/spf13/cobra"
	"github.com/zclconf/go-cty/cty"
	"github.com/zclconf/go-cty/cty/function/stdlib"
	ctyjson "github.com/zclconf/go-cty/cty/json"
	"github.com/zclconf/go-cty/cty/msgpack"
)

// CTY command flags
var (
	ctyInputFormat  string
	ctyOutputFormat string
	ctyTypeJSON     string
)

// Override the convert command with real implementation
func initCtyConvertCmd() *cobra.Command {
	cmd := &cobra.Command{
		Use:   "convert [input] [output]",
		Short: "Convert CTY values between formats",
		Args:  cobra.ExactArgs(2),
		RunE: func(cmd *cobra.Command, args []string) error {
			inputPath := args[0]
			outputPath := args[1]

			// Parse the type specification
			ctyType, err := parseCtyType(json.RawMessage(ctyTypeJSON))
			if err != nil {
				return fmt.Errorf("failed to parse type: %w", err)
			}

			// Read input
			var inputData []byte
			if inputPath == "-" {
				inputData, err = io.ReadAll(os.Stdin)
				if err != nil {
					return fmt.Errorf("failed to read stdin: %w", err)
				}
			} else {
				inputData, err = os.ReadFile(inputPath)
				if err != nil {
					return fmt.Errorf("failed to read input file: %w", err)
				}
			}

			// Convert based on formats
			var value cty.Value
			switch ctyInputFormat {
			case "json":
				value, err = buildCtyValueFromJSON(ctyType, inputData)
				if err != nil {
					return fmt.Errorf("failed to parse JSON input: %w", err)
				}
			case "msgpack":
				value, err = msgpack.Unmarshal(inputData, ctyType)
				if err != nil {
					return fmt.Errorf("failed to unmarshal msgpack: %w", err)
				}
			default:
				return fmt.Errorf("unsupported input format: %s", ctyInputFormat)
			}

			// Marshal to output format
			var outputData []byte
			switch ctyOutputFormat {
			case "json":
				outputData, err = ctyjson.Marshal(value, ctyType)
				if err != nil {
					return fmt.Errorf("failed to marshal to JSON: %w", err)
				}
			case "msgpack":
				outputData, err = msgpack.Marshal(value, ctyType)
				if err != nil {
					return fmt.Errorf("failed to marshal to msgpack: %w", err)
				}
			default:
				return fmt.Errorf("unsupported output format: %s", ctyOutputFormat)
			}

			// Write output
			if outputPath == "-" {
				_, err = os.Stdout.Write(outputData)
			} else {
				err = os.WriteFile(outputPath, outputData, 0644)
			}
			if err != nil {
				return fmt.Errorf("failed to write output: %w", err)
			}

			return nil
		},
	}

	// Add flags
	cmd.Flags().StringVar(&ctyInputFormat, "input-format", "json", "Input format (json, msgpack)")
	cmd.Flags().StringVar(&ctyOutputFormat, "output-format", "json", "Output format (json, msgpack)")
	cmd.Flags().StringVar(&ctyTypeJSON, "type", "", "CTY type specification as JSON")
	cmd.MarkFlagRequired("type")

	return cmd
}

// Override the validate command with real implementation
func initCtyValidateCmd() *cobra.Command {
	cmd := &cobra.Command{
		Use:   "validate-value [value]",
		Short: "Validate a CTY value",
		Args:  cobra.ExactArgs(1),
		RunE: func(cmd *cobra.Command, args []string) error {
			valueJSON := args[0]

			// Parse the type specification
			ctyType, err := parseCtyType(json.RawMessage(ctyTypeJSON))
			if err != nil {
				return fmt.Errorf("failed to parse type: %w", err)
			}

			// Build and validate the value
			_, err = buildCtyValueFromJSON(ctyType, []byte(valueJSON))
			if err != nil {
				return fmt.Errorf("validation failed: %w", err)
			}

			fmt.Println("Validation Succeeded")
			return nil
		},
	}

	// Add flags
	cmd.Flags().StringVar(&ctyTypeJSON, "type", "", "CTY type specification as JSON")
	cmd.MarkFlagRequired("type")

	return cmd
}

// parseCtyType parses a JSON type specification into a cty.Type
func parseCtyType(data json.RawMessage) (cty.Type, error) {
	var typeStr string
	if err := json.Unmarshal(data, &typeStr); err == nil {
		switch typeStr {
		case "string":
			return cty.String, nil
		case "number":
			return cty.Number, nil
		case "bool":
			return cty.Bool, nil
		case "dynamic":
			return cty.DynamicPseudoType, nil
		case "bytes":
			// stdlib.Bytes is a capsule type, so it has no JSON spelling of its
			// own -- cty.Type.MarshalJSON refuses capsules outright, because a
			// pointer cannot be recovered from JSON. Naming it here is what
			// makes `byteslen` and `bytesslice` reachable at all; the value
			// itself travels as base64.
			return stdlib.Bytes, nil
		default:
			return cty.NilType, fmt.Errorf("unknown primitive type string: %s", typeStr)
		}
	}

	var typeList []json.RawMessage
	if err := json.Unmarshal(data, &typeList); err == nil {
		if len(typeList) < 2 {
			return cty.NilType, fmt.Errorf("type array must have at least 2 elements")
		}
		var typeKind string
		if err := json.Unmarshal(typeList[0], &typeKind); err != nil {
			return cty.NilType, err
		}
		// go-cty's own cty.Type.UnmarshalJSON requires the closing bracket right
		// after the element type for list/set/map/tuple ("unexpected extra data in
		// type description") and reads a third element -- the optional attribute
		// names -- for object only. This parser used to read the first two
		// elements and return, so a probe of a malformed type description got an
		// answer from the oracle that go-cty itself would refuse.
		maxLen := 2
		if typeKind == "object" {
			maxLen = 3
		}
		if len(typeList) > maxLen {
			return cty.NilType, fmt.Errorf("unexpected extra data in %s type description: %d elements", typeKind, len(typeList))
		}

		switch typeKind {
		case "list", "set", "map":
			elemType, err := parseCtyType(typeList[1])
			if err != nil {
				return cty.NilType, err
			}
			if typeKind == "list" {
				return cty.List(elemType), nil
			}
			if typeKind == "set" {
				return cty.Set(elemType), nil
			}
			return cty.Map(elemType), nil
		case "object":
			var attrTypesRaw map[string]json.RawMessage
			if err := json.Unmarshal(typeList[1], &attrTypesRaw); err != nil {
				return cty.NilType, err
			}
			attrTypes := make(map[string]cty.Type)
			for name, rawType := range attrTypesRaw {
				attrType, err := parseCtyType(rawType)
				if err != nil {
					return cty.NilType, err
				}
				attrTypes[name] = attrType
			}
			if len(typeList) > 2 {
				var optionals []string
				if err := json.Unmarshal(typeList[2], &optionals); err != nil {
					return cty.NilType, err
				}
				return cty.ObjectWithOptionalAttrs(attrTypes, optionals), nil
			}
			return cty.Object(attrTypes), nil
		case "tuple":
			var elemTypesRaw []json.RawMessage
			if err := json.Unmarshal(typeList[1], &elemTypesRaw); err != nil {
				return cty.NilType, err
			}
			elemTypes := make([]cty.Type, len(elemTypesRaw))
			for i, rawType := range elemTypesRaw {
				elemType, err := parseCtyType(rawType)
				if err != nil {
					return cty.NilType, err
				}
				elemTypes[i] = elemType
			}
			return cty.Tuple(elemTypes), nil
		default:
			return cty.NilType, fmt.Errorf("unknown complex type kind: %s", typeKind)
		}
	}
	return cty.NilType, fmt.Errorf("invalid type specification format")
}

// buildCtyValueFromJSON builds a cty.Value from JSON data with the given type
func buildCtyValueFromJSON(ty cty.Type, data []byte) (cty.Value, error) {
	// Handle simple JSON unmarshaling for basic types
	if ty == cty.DynamicPseudoType {
		// For dynamic types, infer the type from the JSON
		inferredType, err := ctyjson.ImpliedType(data)
		if err != nil {
			return cty.NilVal, err
		}
		return ctyjson.Unmarshal(data, inferredType)
	}

	// Decoded with UseNumber so numeric literals arrive as their original
	// digits rather than as float64. Plain json.Unmarshal rounds every number
	// through a float64, which silently lost precision above 2^53:
	// 9007199254740993 became ...992 on the way in. A harness that exists to
	// be an oracle must not quietly disagree with its own input.
	var rawValue interface{}
	dec := json.NewDecoder(bytes.NewReader(data))
	dec.UseNumber()
	if err := dec.Decode(&rawValue); err != nil {
		return cty.NilVal, err
	}

	return buildValueFromInterface(ty, rawValue, []string{})
}

// buildValueFromInterface recursively builds a cty.Value from an interface{}
func buildValueFromInterface(ty cty.Type, val interface{}, path []string) (cty.Value, error) {
	if val == nil {
		return cty.NullVal(ty), nil
	}

	// Note: go-cty does NOT support unknown values in JSON format
	// Unknown values can only be properly represented in MessagePack
	// Attempting to marshal an unknown value to JSON will result in an error:
	// "value is not known"
	// This matches Terraform's behavior exactly

	// A Bytes buffer arrives as base64, since JSON has no byte-string literal.
	if ty.Equals(stdlib.Bytes) {
		encoded, ok := val.(string)
		if !ok {
			return cty.NilVal, fmt.Errorf("expected base64 string for bytes at %s", strings.Join(path, "."))
		}
		buf, err := base64.StdEncoding.DecodeString(encoded)
		if err != nil {
			return cty.NilVal, fmt.Errorf("invalid base64 for bytes at %s: %w", strings.Join(path, "."), err)
		}
		if buf == nil {
			// BytesVal panics on a nil slice, and decoding "" can produce one.
			buf = []byte{}
		}
		return stdlib.BytesVal(buf), nil
	}

	// Handle primitive types
	switch ty {
	case cty.String:
		if s, ok := val.(string); ok {
			return cty.StringVal(s), nil
		}
		return cty.NilVal, fmt.Errorf("expected string at %s", strings.Join(path, "."))
	case cty.Number:
		switch v := val.(type) {
		case json.Number:
			bf, err := parseExactNumber(v.String())
			if err != nil {
				return cty.NilVal, fmt.Errorf("invalid number at %s: %w", strings.Join(path, "."), err)
			}
			return cty.NumberVal(bf), nil
		case float64:
			return cty.NumberFloatVal(v), nil
		case int:
			return cty.NumberIntVal(int64(v)), nil
		case int64:
			return cty.NumberIntVal(v), nil
		case string:
			bf, err := parseExactNumber(v)
			if err != nil {
				return cty.NilVal, fmt.Errorf("invalid number string at %s: %w", strings.Join(path, "."), err)
			}
			return cty.NumberVal(bf), nil
		}
		return cty.NilVal, fmt.Errorf("expected number at %s", strings.Join(path, "."))
	case cty.Bool:
		if b, ok := val.(bool); ok {
			return cty.BoolVal(b), nil
		}
		return cty.NilVal, fmt.Errorf("expected bool at %s", strings.Join(path, "."))
	}

	// Handle collection types
	if ty.IsListType() || ty.IsSetType() || ty.IsTupleType() {
		slice, ok := val.([]interface{})
		if !ok {
			return cty.NilVal, fmt.Errorf("expected array at %s", strings.Join(path, "."))
		}

		vals := make([]cty.Value, len(slice))
		for i, elem := range slice {
			var elemTy cty.Type
			if ty.IsTupleType() {
				elemTy = ty.TupleElementType(i)
			} else {
				elemTy = ty.ElementType()
			}
			elemVal, err := buildValueFromInterface(elemTy, elem, append(path, fmt.Sprintf("[%d]", i)))
			if err != nil {
				return cty.NilVal, err
			}
			vals[i] = elemVal
		}

		if ty.IsListType() {
			if len(vals) == 0 {
				return cty.ListValEmpty(ty.ElementType()), nil
			}
			return cty.ListVal(vals), nil
		}
		if ty.IsSetType() {
			if len(vals) == 0 {
				return cty.SetValEmpty(ty.ElementType()), nil
			}
			return cty.SetVal(vals), nil
		}
		return cty.TupleVal(vals), nil
	}

	// Handle map and object types
	if ty.IsMapType() || ty.IsObjectType() {
		m, ok := val.(map[string]interface{})
		if !ok {
			return cty.NilVal, fmt.Errorf("expected object at %s", strings.Join(path, "."))
		}

		vals := make(map[string]cty.Value)
		for k, v := range m {
			var elemTy cty.Type
			if ty.IsObjectType() {
				elemTy = ty.AttributeType(k)
			} else {
				elemTy = ty.ElementType()
			}
			elemVal, err := buildValueFromInterface(elemTy, v, append(path, k))
			if err != nil {
				return cty.NilVal, err
			}
			vals[k] = elemVal
		}

		if ty.IsMapType() {
			if len(vals) == 0 {
				return cty.MapValEmpty(ty.ElementType()), nil
			}
			return cty.MapVal(vals), nil
		}
		return cty.ObjectVal(vals), nil
	}

	return cty.NilVal, fmt.Errorf("cannot build value for type %s at %s", ty.FriendlyName(), strings.Join(path, "."))
}

// buildRefinedUnknown builds a refined unknown value from a `$refine` object.
//
// Every key has to be recognised, and every value has to have the shape its key
// implies. Both used to be read with a comma-ok assertion and skipped when they
// did not match, which meant a typo (`typo_prefix`) and a mis-spelled bound
// (`"number_lower_bound": "10"` rather than a pair) both produced a *bare*
// unknown and reported `ok: true`. The caller then compared its own carefully
// refined unknown against an unrefined one and read the difference as its own
// fault. An oracle asked a question it does not understand has to say so.
func buildRefinedUnknown(ty cty.Type, raw json.RawMessage) (cty.Value, error) {
	var refinements map[string]json.RawMessage
	if err := json.Unmarshal(raw, &refinements); err != nil {
		return cty.NilVal, fmt.Errorf("refinements must be an object: %w", err)
	}
	if refinements == nil {
		return cty.NilVal, fmt.Errorf("refinements must be an object")
	}

	builder := cty.UnknownVal(ty).Refine()
	seen := make(map[string]struct{}, len(refinements))
	take := func(key string) (json.RawMessage, bool) {
		field, ok := refinements[key]
		if ok {
			seen[key] = struct{}{}
		}
		return field, ok
	}

	if field, ok := take("is_known_null"); ok {
		var isNull bool
		if err := json.Unmarshal(field, &isNull); err != nil {
			return cty.NilVal, fmt.Errorf("is_known_null must be a bool: %w", err)
		}
		if isNull {
			builder = builder.Null()
		} else {
			builder = builder.NotNull()
		}
	}

	if field, ok := take("string_prefix"); ok {
		var prefix string
		if err := json.Unmarshal(field, &prefix); err != nil {
			return cty.NilVal, fmt.Errorf("string_prefix must be a string: %w", err)
		}
		// StringPrefixFull, not StringPrefix: the prefix arriving here has
		// already been through whatever trimming its sender applies, and
		// StringPrefix trims again. That double trim made the harness report a
		// shorter prefix than either implementation holds -- "hello" came back
		// as "hel" -- which reads as a divergence in the caller rather than a
		// mistake here, and is exactly the way an oracle does real damage.
		builder = builder.StringPrefixFull(prefix)
	}

	if field, ok := take("number_lower_bound"); ok {
		bound, inclusive, err := parseNumberBound("number_lower_bound", field)
		if err != nil {
			return cty.NilVal, err
		}
		builder = builder.NumberRangeLowerBound(bound, inclusive)
	}

	if field, ok := take("number_upper_bound"); ok {
		bound, inclusive, err := parseNumberBound("number_upper_bound", field)
		if err != nil {
			return cty.NilVal, err
		}
		builder = builder.NumberRangeUpperBound(bound, inclusive)
	}

	if field, ok := take("collection_length_lower_bound"); ok {
		length, err := parseLengthBound("collection_length_lower_bound", field)
		if err != nil {
			return cty.NilVal, err
		}
		builder = builder.CollectionLengthLowerBound(length)
	}

	if field, ok := take("collection_length_upper_bound"); ok {
		length, err := parseLengthBound("collection_length_upper_bound", field)
		if err != nil {
			return cty.NilVal, err
		}
		builder = builder.CollectionLengthUpperBound(length)
	}

	unread := make([]string, 0, len(refinements))
	for key := range refinements {
		if _, ok := seen[key]; !ok {
			unread = append(unread, key)
		}
	}
	if len(unread) > 0 {
		sort.Strings(unread)
		return cty.NilVal, fmt.Errorf("unknown refinement %s", strings.Join(unread, ", "))
	}

	return builder.NewValue(), nil
}

// parseNumberBound reads a `[digits, inclusive]` pair.
func parseNumberBound(key string, raw json.RawMessage) (cty.Value, bool, error) {
	var pair []json.RawMessage
	if err := json.Unmarshal(raw, &pair); err != nil {
		return cty.NilVal, false, fmt.Errorf("%s must be a [digits, inclusive] pair, got %s", key, raw)
	}
	if len(pair) != 2 {
		return cty.NilVal, false, fmt.Errorf("%s must have exactly 2 elements, got %d", key, len(pair))
	}
	var text string
	if err := json.Unmarshal(pair[0], &text); err != nil {
		return cty.NilVal, false, fmt.Errorf("%s bound must be a string of digits, got %s", key, pair[0])
	}
	var inclusive bool
	if err := json.Unmarshal(pair[1], &inclusive); err != nil {
		return cty.NilVal, false, fmt.Errorf("%s inclusiveness must be a bool, got %s", key, pair[1])
	}
	bf, err := parseBound(text)
	if err != nil {
		return cty.NilVal, false, err
	}
	return cty.NumberVal(bf), inclusive, nil
}

// parseLengthBound reads a collection length bound as an exact integer.
//
// Not through a float64, which is what `.(float64)` on a plainly-unmarshalled
// document gave it: `math.MaxInt` overflowed the conversion to int and the
// bound was dropped outright, and 2^53+1 arrived as 2^53. A length bound is
// exactly the kind of fact a differential run exists to compare, so a bound
// this harness cannot represent has to be refused rather than approximated.
func parseLengthBound(key string, raw json.RawMessage) (int, error) {
	dec := json.NewDecoder(bytes.NewReader(raw))
	dec.UseNumber()
	var decoded any
	if err := dec.Decode(&decoded); err != nil {
		return 0, fmt.Errorf("%s must be a number: %w", key, err)
	}
	num, ok := decoded.(json.Number)
	if !ok {
		return 0, fmt.Errorf("%s must be a number, got %s", key, raw)
	}
	length, err := strconv.Atoi(num.String())
	if err != nil {
		return 0, fmt.Errorf("%s must be an integer this build can hold, got %s", key, num.String())
	}
	if length < 0 {
		return 0, fmt.Errorf("%s must not be negative, got %d", key, length)
	}
	return length, nil
}

// parseBound reads a refinement bound at the same precision as every other
// number the harness accepts.
//
// `new(big.Float).SetString` starts at the default 64-bit precision, so a bound
// past 2^64 came back rounded -- 2^70 arrived as ...3400 where the caller sent
// ...3424 -- and the caller read that as its own encoder losing precision. The
// value path already used ParseFloat with 512 bits for exactly this reason;
// this is the same rule, applied where refinements are built.
func parseBound(text string) (*big.Float, error) {
	bf, err := parseExactNumber(text)
	if err != nil {
		return nil, fmt.Errorf("invalid number bound %q: %w", text, err)
	}
	return bf, nil
}

// parseExactNumber reads a number written as text, at go-cty's own precision.
//
// The single rule for every number this harness accepts as digits, whether it
// arrives as a JSON number token, as a string in a value position, or as a
// refinement bound. `new(big.Float).SetString` starts at 64 bits of mantissa,
// so the string-spelled path used to round: 2^64+1 came back as 2^64 while
// go-cty's own `cty json unmarshal` answered exactly, and a caller with an
// exact-decimal implementation read the harness's rounding as its own. 512 bits
// and round-to-nearest-even is what `cty.ParseNumberVal` uses, and is the same
// rule the bound path already adopted for the same reason.
func parseExactNumber(text string) (*big.Float, error) {
	bf, _, err := big.ParseFloat(text, 10, 512, big.ToNearestEven)
	if err != nil {
		return nil, fmt.Errorf("%q is not a number: %w", text, err)
	}
	return bf, nil
}

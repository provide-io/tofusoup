package main

import (
	"encoding/json"
	"fmt"
	"io"
	"math/big"
	"os"
	"strings"

	"github.com/spf13/cobra"
	"github.com/zclconf/go-cty/cty"
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

	// Parse the JSON to handle special cases
	var rawValue interface{}
	if err := json.Unmarshal(data, &rawValue); err != nil {
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

	// Handle primitive types
	switch ty {
	case cty.String:
		if s, ok := val.(string); ok {
			return cty.StringVal(s), nil
		}
		return cty.NilVal, fmt.Errorf("expected string at %s", strings.Join(path, "."))
	case cty.Number:
		switch v := val.(type) {
		case float64:
			return cty.NumberFloatVal(v), nil
		case int:
			return cty.NumberIntVal(int64(v)), nil
		case int64:
			return cty.NumberIntVal(v), nil
		case string:
			bf := new(big.Float)
			if _, ok := bf.SetString(v); ok {
				return cty.NumberVal(bf), nil
			}
			return cty.NilVal, fmt.Errorf("invalid number string at %s", strings.Join(path, "."))
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

// buildRefinedUnknown builds a refined unknown value from refinement data
func buildRefinedUnknown(ty cty.Type, refinementsData interface{}) (cty.Value, error) {
	refinements, ok := refinementsData.(map[string]interface{})
	if !ok {
		return cty.NilVal, fmt.Errorf("refinements must be an object")
	}

	builder := cty.UnknownVal(ty).Refine()

	if isNull, ok := refinements["is_known_null"].(bool); ok {
		if isNull {
			builder = builder.Null()
		} else {
			builder = builder.NotNull()
		}
	}

	if prefix, ok := refinements["string_prefix"].(string); ok {
		builder = builder.StringPrefix(prefix)
	}

	if lowerBound, ok := refinements["number_lower_bound"].([]interface{}); ok && len(lowerBound) >= 2 {
		numStr, _ := lowerBound[0].(string)
		inclusive, _ := lowerBound[1].(bool)
		bf := new(big.Float)
		bf.SetString(numStr)
		builder = builder.NumberRangeLowerBound(cty.NumberVal(bf), inclusive)
	}

	if upperBound, ok := refinements["number_upper_bound"].([]interface{}); ok && len(upperBound) >= 2 {
		numStr, _ := upperBound[0].(string)
		inclusive, _ := upperBound[1].(bool)
		bf := new(big.Float)
		bf.SetString(numStr)
		builder = builder.NumberRangeUpperBound(cty.NumberVal(bf), inclusive)
	}

	if lower, ok := refinements["collection_length_lower_bound"].(float64); ok {
		builder = builder.CollectionLengthLowerBound(int(lower))
	}

	if upper, ok := refinements["collection_length_upper_bound"].(float64); ok {
		builder = builder.CollectionLengthUpperBound(int(upper))
	}

	return builder.NewValue(), nil
}
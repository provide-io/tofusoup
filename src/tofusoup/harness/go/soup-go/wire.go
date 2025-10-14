package main

import (
	"encoding/base64"
	"encoding/json"
	"fmt"
	"io"
	"os"

	"github.com/spf13/cobra"
	"github.com/vmihailenco/msgpack/v5"
	"github.com/zclconf/go-cty/cty"
	ctyjson "github.com/zclconf/go-cty/cty/json"
	ctymsgpack "github.com/zclconf/go-cty/cty/msgpack"
)

// Override the encode command with real implementation
func initWireEncodeCmd() *cobra.Command {
	// Local flags for this command only
	var (
		wireInputFormat  string
		wireOutputFormat string
		wireTypeJSON     string
	)

	cmd := &cobra.Command{
		Use:   "encode [input] [output]",
		Short: "Encode data to wire format",
		Args:  cobra.RangeArgs(1, 2),
		RunE: func(cmd *cobra.Command, args []string) error {
			inputPath := args[0]
			outputPath := "-"
			if len(args) > 1 {
				outputPath = args[1]
			}

			// Read input
			var inputData []byte
			var err error
			if inputPath == "-" {
				inputData, err = io.ReadAll(os.Stdin)
			} else {
				inputData, err = os.ReadFile(inputPath)
			}
			if err != nil {
				return fmt.Errorf("failed to read input: %w", err)
			}

			var outputData []byte

			// If a type is specified, use CTY encoding
			if wireTypeJSON != "" {
				ctyType, err := parseCtyType(json.RawMessage(wireTypeJSON))
				if err != nil {
					return fmt.Errorf("failed to parse type: %w", err)
				}

				// Parse input as JSON and build CTY value
				value, err := buildCtyValueFromJSON(ctyType, inputData)
				if err != nil {
					return fmt.Errorf("failed to build value: %w", err)
				}

				// Encode to wire format
				switch wireOutputFormat {
				case "msgpack":
					outputData, err = ctymsgpack.Marshal(value, ctyType)
				case "json":
					outputData, err = ctyjson.Marshal(value, ctyType)
				default:
					return fmt.Errorf("unsupported output format: %s", wireOutputFormat)
				}
				if err != nil {
					return fmt.Errorf("failed to encode: %w", err)
				}
			} else {
				// Generic msgpack encoding without CTY type
				var data interface{}
				if err := json.Unmarshal(inputData, &data); err != nil {
					return fmt.Errorf("failed to parse JSON: %w", err)
				}

				outputData, err = msgpack.Marshal(data)
				if err != nil {
					return fmt.Errorf("failed to encode msgpack: %w", err)
				}
			}

			// Write output
			if outputPath == "-" {
				// For stdout with msgpack output, encode as base64 for safe text transmission
				if wireOutputFormat == "msgpack" {
					encoded := base64.StdEncoding.EncodeToString(outputData)
					_, err = os.Stdout.WriteString(encoded)
				} else {
					_, err = os.Stdout.Write(outputData)
				}
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
	cmd.Flags().StringVar(&wireInputFormat, "input-format", "json", "Input format (json)")
	cmd.Flags().StringVar(&wireOutputFormat, "output-format", "msgpack", "Output format (msgpack, json)")
	cmd.Flags().StringVar(&wireTypeJSON, "type", "", "Type specification as JSON (optional)")
	
	return cmd
}

// Override the decode command with real implementation
func initWireDecodeCmd() *cobra.Command {
	// Local flags for this command only
	var (
		wireInputFormat  string
		wireOutputFormat string
		wireTypeJSON     string
	)

	cmd := &cobra.Command{
		Use:   "decode [input] [output]",
		Short: "Decode data from wire format",
		Args:  cobra.RangeArgs(1, 2),
		RunE: func(cmd *cobra.Command, args []string) error {
			inputPath := args[0]
			outputPath := "-"
			if len(args) > 1 {
				outputPath = args[1]
			}

			// Read input
			var inputData []byte
			var err error
			if inputPath == "-" {
				inputData, err = io.ReadAll(os.Stdin)
			} else {
				inputData, err = os.ReadFile(inputPath)
			}
			if err != nil {
				return fmt.Errorf("failed to read input: %w", err)
			}

			// If input looks like base64 (no binary bytes), try to decode it
			// This handles the case where encode outputs base64 to stdout
			if wireInputFormat == "msgpack" && inputPath == "-" {
				// Try to decode as base64 if it looks like text
				if decoded, err := base64.StdEncoding.DecodeString(string(inputData)); err == nil {
					inputData = decoded
				}
			}

			var outputData []byte

			// If a type is specified, use CTY decoding
			if wireTypeJSON != "" {
				ctyType, err := parseCtyType(json.RawMessage(wireTypeJSON))
				if err != nil {
					return fmt.Errorf("failed to parse type: %w", err)
				}

				// Decode from wire format
				var value cty.Value
				switch wireInputFormat {
				case "msgpack":
					value, err = ctymsgpack.Unmarshal(inputData, ctyType)
				case "json":
					value, err = ctyjson.Unmarshal(inputData, ctyType)
				default:
					return fmt.Errorf("unsupported input format: %s", wireInputFormat)
				}
				if err != nil {
					return fmt.Errorf("failed to decode: %w", err)
				}

				// Encode to output format
				switch wireOutputFormat {
				case "json":
					outputData, err = ctyjson.Marshal(value, ctyType)
				case "msgpack":
					outputData, err = ctymsgpack.Marshal(value, ctyType)
				default:
					return fmt.Errorf("unsupported output format: %s", wireOutputFormat)
				}
				if err != nil {
					return fmt.Errorf("failed to encode output: %w", err)
				}
			} else {
				// Generic msgpack decoding without CTY type
				var data interface{}
				if err := msgpack.Unmarshal(inputData, &data); err != nil {
					return fmt.Errorf("failed to decode msgpack: %w", err)
				}

				outputData, err = json.MarshalIndent(data, "", "  ")
				if err != nil {
					return fmt.Errorf("failed to encode JSON: %w", err)
				}
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
	cmd.Flags().StringVar(&wireInputFormat, "input-format", "msgpack", "Input format (msgpack)")
	cmd.Flags().StringVar(&wireOutputFormat, "output-format", "json", "Output format (json)")
	cmd.Flags().StringVar(&wireTypeJSON, "type", "", "Type specification as JSON (optional)")
	
	return cmd
}
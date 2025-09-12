package main

import (
	"encoding/json"
	"fmt"
	"os"

	"github.com/hashicorp/hcl/v2"
	"github.com/hashicorp/hcl/v2/hclparse"
	"github.com/hashicorp/hcl/v2/hclsyntax"
	"github.com/spf13/cobra"
	"github.com/zclconf/go-cty/cty"
	"github.com/zclconf/go-cty/cty/function"
	ctyjson "github.com/zclconf/go-cty/cty/json"
)

// HCL output format flag
var hclOutputFormat string

// Override the parse command with real implementation
func initHclParseCmd() *cobra.Command {
	cmd := &cobra.Command{
		Use:   "parse [file]",
		Short: "Parse an HCL file",
		Args:  cobra.ExactArgs(1),
		RunE: func(cmd *cobra.Command, args []string) error {
			filename := args[0]

			// Read the file
			content, err := os.ReadFile(filename)
			if err != nil {
				return fmt.Errorf("failed to read file: %w", err)
			}

			// Parse the HCL file
			parser := hclparse.NewParser()
			file, diags := parser.ParseHCL(content, filename)
			
			if diags.HasErrors() {
				if hclOutputFormat == "diagnostic" {
					for _, diag := range diags {
						fmt.Fprintf(os.Stderr, "%s\n", diag.Error())
					}
					return fmt.Errorf("parse errors occurred")
				}
				// Return error info as JSON
				errorOutput := map[string]interface{}{
					"success": false,
					"errors":  diagnosticsToJSON(diags),
				}
				json.NewEncoder(os.Stdout).Encode(errorOutput)
				return nil
			}

			// Convert to JSON representation
			result, err := hclFileToJSON(file)
			if err != nil {
				return fmt.Errorf("failed to convert HCL to JSON: %w", err)
			}

			// Output the result
			if hclOutputFormat == "json" {
				output := map[string]interface{}{
					"success": true,
					"body":    result,
				}
				if err := json.NewEncoder(os.Stdout).Encode(output); err != nil {
					return fmt.Errorf("failed to encode JSON: %w", err)
				}
			}

			return nil
		},
	}
	
	// Add flags
	cmd.Flags().StringVar(&hclOutputFormat, "output-format", "json", "Output format (json, diagnostic)")
	
	return cmd
}

// Override the validate command with real implementation
func initHclValidateCmd() *cobra.Command {
	cmd := &cobra.Command{
		Use:   "validate [file]",
		Short: "Validate HCL syntax",
		Args:  cobra.ExactArgs(1),
		RunE: func(cmd *cobra.Command, args []string) error {
			filename := args[0]

			// Read the file
			content, err := os.ReadFile(filename)
			if err != nil {
				return fmt.Errorf("failed to read file: %w", err)
			}

			// Parse the HCL file for validation
			parser := hclparse.NewParser()
			_, diags := parser.ParseHCL(content, filename)

			result := map[string]interface{}{
				"valid": !diags.HasErrors(),
			}

			if diags.HasErrors() {
				result["errors"] = diagnosticsToJSON(diags)
			}

			// Output validation result as JSON
			if err := json.NewEncoder(os.Stdout).Encode(result); err != nil {
				return fmt.Errorf("failed to encode JSON: %w", err)
			}

			return nil
		},
	}
	
	return cmd
}

// hclFileToJSON converts an HCL file to a JSON representation
func hclFileToJSON(file *hcl.File) (interface{}, error) {
	// For now, we'll work directly with the body without partial content
	// since we're doing a general parse

	result := make(map[string]interface{})

	// Process attributes
	if body, ok := file.Body.(*hclsyntax.Body); ok {
		for name, attr := range body.Attributes {
			val, diags := attr.Expr.Value(&hcl.EvalContext{
				Variables: map[string]cty.Value{},
				Functions: map[string]function.Function{},
			})
			if !diags.HasErrors() {
				jsonVal, err := ctyjson.Marshal(val, val.Type())
				if err == nil {
					var v interface{}
					if err := json.Unmarshal(jsonVal, &v); err == nil {
						result[name] = v
					}
				}
			}
		}

		// Process blocks
		blocks := make([]map[string]interface{}, 0)
		for _, block := range body.Blocks {
			blockData := map[string]interface{}{
				"type":   block.Type,
				"labels": block.Labels,
			}
			
			// Recursively process block body
			if blockBody, err := hclBlockToJSON(block.Body); err == nil {
				blockData["body"] = blockBody
			}
			
			blocks = append(blocks, blockData)
		}
		
		if len(blocks) > 0 {
			result["blocks"] = blocks
		}
	}

	return result, nil
}

// hclBlockToJSON converts an HCL block body to JSON
func hclBlockToJSON(body hcl.Body) (interface{}, error) {
	if syntaxBody, ok := body.(*hclsyntax.Body); ok {
		result := make(map[string]interface{})
		
		// Process attributes in the block
		for name, attr := range syntaxBody.Attributes {
			val, diags := attr.Expr.Value(&hcl.EvalContext{
				Variables: map[string]cty.Value{},
				Functions: map[string]function.Function{},
			})
			if !diags.HasErrors() {
				jsonVal, err := ctyjson.Marshal(val, val.Type())
				if err == nil {
					var v interface{}
					if err := json.Unmarshal(jsonVal, &v); err == nil {
						result[name] = v
					}
				}
			}
		}
		
		// Process nested blocks
		if len(syntaxBody.Blocks) > 0 {
			blocks := make([]map[string]interface{}, 0)
			for _, block := range syntaxBody.Blocks {
				blockData := map[string]interface{}{
					"type":   block.Type,
					"labels": block.Labels,
				}
				
				if blockBody, err := hclBlockToJSON(block.Body); err == nil {
					blockData["body"] = blockBody
				}
				
				blocks = append(blocks, blockData)
			}
			result["blocks"] = blocks
		}
		
		return result, nil
	}
	
	return nil, fmt.Errorf("unsupported body type")
}

// diagnosticsToJSON converts HCL diagnostics to JSON
func diagnosticsToJSON(diags hcl.Diagnostics) []map[string]interface{} {
	result := make([]map[string]interface{}, 0, len(diags))
	for _, diag := range diags {
		severityStr := "error"
		if diag.Severity == hcl.DiagWarning {
			severityStr = "warning"
		}
		d := map[string]interface{}{
			"severity": severityStr,
			"summary":  diag.Summary,
			"detail":   diag.Detail,
		}
		if diag.Subject != nil {
			d["range"] = map[string]interface{}{
				"filename": diag.Subject.Filename,
				"start": map[string]int{
					"line":   diag.Subject.Start.Line,
					"column": diag.Subject.Start.Column,
					"byte":   diag.Subject.Start.Byte,
				},
				"end": map[string]int{
					"line":   diag.Subject.End.Line,
					"column": diag.Subject.End.Column,
					"byte":   diag.Subject.End.Byte,
				},
			}
		}
		result = append(result, d)
	}
	return result
}
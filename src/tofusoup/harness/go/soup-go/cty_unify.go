package main

import (
	"encoding/json"
	"fmt"

	"github.com/spf13/cobra"
	"github.com/zclconf/go-cty/cty"
	"github.com/zclconf/go-cty/cty/convert"
	ctyjson "github.com/zclconf/go-cty/cty/json"
)

// unifyResult reports the single type all of the given types can convert to.
//
// `Unified` is absent rather than null when there is no such type: go-cty
// signals that with cty.NilType, and a JSON `null` would be indistinguishable
// from a type that failed to marshal.
type unifyResult struct {
	Unified json.RawMessage `json:"unified,omitempty"`
	Unsafe  bool            `json:"unsafe"`
	OK      bool            `json:"ok"`
	Error   string          `json:"error,omitempty"`
}

func initCtyUnifyCmd() *cobra.Command {
	var safe bool

	cmd := &cobra.Command{
		Use:   "unify [type-json...]",
		Short: "Unify types the way go-cty's convert.UnifyUnsafe does",
		Long: `Report the single type that all of the given types can convert to.

Type unification decides the element type of a set operation, of concat, and of
any function whose result type is derived from more than one argument, so a
second implementation that unifies differently disagrees with go-cty across a
whole family of functions at once rather than in one place. It has no value
arguments and so cannot be reached through ` + "`cty call`" + `.

  soup-go cty unify '"string"' '"number"'
  soup-go cty unify '["list","string"]' '["tuple",["string","string"]]'
  soup-go cty unify --safe '"string"' '"number"'`,
		Args: cobra.MinimumNArgs(1),
		RunE: func(cmd *cobra.Command, args []string) error {
			types := make([]cty.Type, 0, len(args))
			for i, raw := range args {
				ty, err := parseCtyType(json.RawMessage(raw))
				if err != nil {
					return fmt.Errorf("type %d: %w", i, err)
				}
				types = append(types, ty)
			}

			var unified cty.Type
			if safe {
				unified, _ = convert.Unify(types)
			} else {
				unified, _ = convert.UnifyUnsafe(types)
			}

			out := unifyResult{Unsafe: !safe}
			if unified != cty.NilType {
				encoded, err := marshalResultType(unified)
				if err != nil {
					out.Error = fmt.Sprintf("unified type is not representable as JSON: %s", err)
				} else {
					out.OK = true
					out.Unified = encoded
				}
			} else {
				// Not an error: "these types have nothing in common" is an
				// answer, and the one a caller has to handle.
				out.OK = true
			}

			encoded, err := json.Marshal(out)
			if err != nil {
				return fmt.Errorf("failed to encode result: %w", err)
			}
			fmt.Fprintln(cmd.OutOrStdout(), string(encoded))
			return nil
		},
	}
	cmd.Flags().BoolVar(&safe, "safe", false, "use convert.Unify rather than convert.UnifyUnsafe")
	return cmd
}

// ctyjson is referenced by marshalResultType in cty_call.go; this keeps the
// import graph obvious to a reader of this file.
var _ = ctyjson.MarshalType

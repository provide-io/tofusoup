package main

import (
	"fmt"
	"os"
)

func main() {
	if len(os.Args) < 2 {
		fmt.Fprintln(os.Stderr, "Usage: printenv_harness_go <ENV_VAR_NAME_1> [ENV_VAR_NAME_2 ...]")
		os.Exit(1)
	}

	envVarNames := os.Args[1:]
	for _, varName := range envVarNames {
		value := os.Getenv(varName)
		// To make multiline content clearly visible and distinguishable from a path,
		// let's wrap the value in quotes and escape newlines if any.
		// However, for this initial test, a direct print is fine to see raw behavior.
		// A more robust version might use fmt.Printf("%s=%q\n", varName, value) to quote it.
		fmt.Printf("%s=%s\n", varName, value)
	}
}

// 🍲🥄📄🪄

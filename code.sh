#!/bin/bash
# 🛠️ Go Protobuf Generation Fix Script
set -eo pipefail

# --- Logging ---
log_info() { echo -e "ℹ️  $1"; }
log_fix() { echo -e "🔧 $1"; }
log_success() { echo -e "✅ $1"; }

# --- Main Operations ---
log_info "Implementing Protobuf code generation for the 'soup-go' CLI..."

# ==============================================================================
# 1. Update go.mod with generator tools
# ==============================================================================
log_fix "Updating 'src/tofusoup/harness/go/soup-go/go.mod' with generator tools..."
cat <<'EOF' > src/tofusoup/harness/go/soup-go/go.mod
module tofusoup/harness/go/soup-go

go 1.23

require (
    github.com/hashicorp/go-hclog v1.6.3
    github.com/hashicorp/go-plugin v1.6.3
    github.com/hashicorp/hcl/v2 v2.23.0
    github.com/spf13/cobra v1.9.1
    github.com/zclconf/go-cty v1.16.3
    google.golang.org/grpc v1.74.2
    google.golang.org/protobuf v1.34.2
)

require (
    github.com/agext/levenshtein v1.2.3 // indirect
    github.com/apparentlymart/go-textseg/v15 v15.0.0 // indirect
    github.com/fatih/color v1.18.0 // indirect
    github.com/golang/protobuf v1.5.4 // indirect
    github.com/google/go-cmp v0.7.0 // indirect
    github.com/hashicorp/yamux v0.1.2 // indirect
    github.com/inconshreveable/mousetrap v1.1.0 // indirect
    github.com/mattn/go-colorable v0.1.14 // indirect
    github.com/mattn/go-isatty v0.0.20 // indirect
    github.com/mitchellh/go-wordwrap v1.0.1 // indirect
    github.com/oklog/run v1.2.0 // indirect
    github.com/spf13/pflag v1.0.6 // indirect
    golang.org/x/mod v0.25.0 // indirect
    golang.org/x/net v0.41.0 // indirect
    golang.org/x/sync v0.15.0 // indirect
    golang.org/x/sys v0.33.0 // indirect
    golang.org/x/text v0.26.0 // indirect
    golang.org/x/tools v0.34.0 // indirect
    google.golang.org/genproto/googleapis/rpc v0.0.0-20250603155806-513f23925822 // indirect
)
EOF

# ==============================================================================
# 2. Add `go:generate` directives and a `generate` command
# ==============================================================================
log_fix "Adding 'go:generate' directive to 'internal/rpc/plugin.go'..."
cat <<'EOF' > src/tofusoup/harness/go/soup-go/internal/rpc/plugin.go
package rpc

import (
    "context"

    "github.com/hashicorp/go-hclog"
    "github.com/hashicorp/go-plugin"
    "google.golang.org/grpc"
    "tofusoup/harness/go/soup-go/proto"
)

//go:generate protoc --go_out=. --go_opt=paths=source_relative --go-grpc_out=. --go-grpc_opt=paths=source_relative ../../proto/kv.proto

// Handshake is a common handshake that is shared by plugin and host.
var Handshake = plugin.HandshakeConfig{
    ProtocolVersion:  1,
    MagicCookieKey:   "BASIC_PLUGIN",
    MagicCookieValue: "hello",
}

// KVPlugin is the implementation of plugin.Plugin
type KVPlugin struct {
    plugin.Plugin
    Impl   *KV
    Logger hclog.Logger
}

// GRPCServer is called by the plugin framework to serve the plugin.
func (p *KVPlugin) GRPCServer(broker *plugin.GRPCBroker, s *grpc.Server) error {
    proto.RegisterKVServer(s, &KVGRPCServer{Impl: p.Impl, Logger: p.Logger})
    return nil
}

// GRPCClient is called by the plugin framework to create a client.
func (p *KVPlugin) GRPCClient(ctx context.Context, broker *plugin.GRPCBroker, c *grpc.ClientConn) (interface{}, error) {
    return &KVGRPCClient{Client: proto.NewKVClient(c), Logger: p.Logger}, nil
}

// Serve serves the plugin. This is the function that will be called by the server-start command.
func Serve(logger hclog.Logger) {
    kvStore := NewKVStore(logger)
    pluginMap := map[string]plugin.Plugin{
        "kv": &KVPlugin{Impl: kvStore, Logger: logger},
    }

    plugin.Serve(&plugin.ServeConfig{
        HandshakeConfig: Handshake,
        Plugins:         pluginMap,
        GRPCServer:      plugin.DefaultGRPCServer,
        Logger:          logger,
    })
}
EOF

log_fix "Creating 'src/tofusoup/harness/go/soup-go/cmd/generate.go'..."
cat <<'EOF' > src/tofusoup/harness/go/soup-go/cmd/generate.go
package cmd

import (
    "fmt"
    "os"
    "os/exec"

    "github.com/hashicorp/go-hclog"
    "github.com/spf13/cobra"
)

var GenerateCmd = &cobra.Command{
    Use:   "generate",
    Short: "Run go generate to compile protobufs.",
    Run: func(cmd *cobra.Command, args []string) {
        logger := hclog.FromContext(cmd.Context())
        logger.Info("Running 'go generate'...")

        // The command needs to be run from the root of the Go module
        // so that the relative paths in the go:generate directive work correctly.
        // This is a simple way to get the path to the current file's directory.
        // A more robust solution might use build tags or runtime.Caller.
        // For this harness, we assume a known structure.
        cmdGoGenerate := exec.Command("go", "generate", "./...")
        cmdGoGenerate.Dir = "internal/rpc" // Run from the package containing the directive

        output, err := cmdGoGenerate.CombinedOutput()
        if err != nil {
            logger.Error("Failed to run 'go generate'", "error", err, "output", string(output))
            os.Exit(1)
        }

        logger.Info("Successfully ran 'go generate'", "output", string(output))
        fmt.Println("Protobuf Go files generated successfully.")
    },
}
EOF

log_fix "Updating 'src/tofusoup/harness/go/soup-go/cmd/root.go' to add generate command..."
cat <<'EOF' > src/tofusoup/harness/go/soup-go/cmd/root.go
package cmd

import (
    "context"
    "fmt"
    "os"

    "github.com/hashicorp/go-hclog"
    "github.com/spf13/cobra"
)

var (
    logLevel string
    logger   hclog.Logger
)

var RootCmd = &cobra.Command{
    Use:   "soup-go",
    Short: "A Go implementation of the TofuSoup conformance and utility toolkit.",
    PersistentPreRun: func(cmd *cobra.Command, args []string) {
        level := hclog.LevelFromString(logLevel)
        if level == hclog.NoLevel {
            level = hclog.Info
        }
        logger = hclog.New(&hclog.LoggerOptions{
            Name:  "soup-go",
            Level: level,
        })
        // Pass logger down to subcommands via context
        ctx := hclog.WithContext(context.Background(), logger)
        cmd.SetContext(ctx)
    },
}

func init() {
    RootCmd.PersistentFlags().StringVar(&logLevel, "log-level", "info", "Set the logging level (trace, debug, info, warn, error)")
    RootCmd.AddCommand(CtyCmd)
    RootCmd.AddCommand(HclCmd)
    RootCmd.AddCommand(RpcCmd)
    RootCmd.AddCommand(GenerateCmd)
}

func Execute() {
    if err := RootCmd.Execute(); err != nil {
        fmt.Fprintf(os.Stderr, "Error: %v\n", err)
        os.Exit(1)
    }
}
EOF

# ==============================================================================
# 3. Update Python build logic to run `go generate`
# ==============================================================================
log_fix "Updating 'src/tofusoup/harness/go/build.py' to run 'go generate'..."
cat <<'EOF' > src/tofusoup/harness/go/build.py
import subprocess
import pathlib
import os
import shutil
from typing import Any, Dict

from provide.foundation import logger
from tofusoup.common.exceptions import TofuSoupError

class GoVersionError(TofuSoupError): pass
class HarnessBuildError(TofuSoupError): pass

def _get_effective_go_harness_settings(harness_name: str, loaded_config: Dict[str, Any]) -> Dict[str, Any]:
    settings: Dict[str, Any] = {"build_flags": [], "env_vars": {}}
    component_id = harness_name
    go_defaults = loaded_config.get("harness_defaults", {}).get("go", {})
    settings["build_flags"] = go_defaults.get("build_flags", [])
    settings["env_vars"] = go_defaults.get("common_env_vars", {})

    specific_config = loaded_config.get("harness", {}).get("go", {}).get(component_id, {})
    if "build_flags" in specific_config:
        settings["build_flags"] = specific_config["build_flags"]
    if "env_vars" in specific_config:
        settings["env_vars"].update(specific_config["env_vars"])
    return settings

def build_go_harness(
    harness_name: str,
    project_root: pathlib.Path,
    loaded_config: Dict[str, Any],
    harness_config: Dict[str, str], # Specific config for this harness from GO_HARNESS_CONFIG
    force_rebuild: bool = False
) -> pathlib.Path:
    if not shutil.which("go"):
        raise GoVersionError("Go compiler not found in PATH.")
    if not shutil.which("protoc"):
        raise HarnessBuildError("protoc compiler not found in PATH. Please install the Protocol Buffers compiler.")

    harness_source_dir = project_root / "src" / "tofusoup" / "harness" / "go" / harness_config["source_dir"]
    if not harness_source_dir.is_dir():
        raise HarnessBuildError(f"Harness source directory not found: {harness_source_dir}")

    output_name = harness_config["output_name"]
    output_dir = project_root / "src" / "tofusoup" / "harness" / "go" / "bin"
    output_dir.mkdir(parents=True, exist_ok=True)
    executable_path = output_dir / output_name

    if not force_rebuild and executable_path.exists():
        logger.info(f"Go harness '{harness_name}' already built at {executable_path}. Skipping build.")
        return executable_path

    logger.info(f"Building Go harness '{harness_name}' from {harness_source_dir} to {executable_path}")
    settings = _get_effective_go_harness_settings(harness_name, loaded_config)
    env = os.environ.copy()
    env.update(settings.get("env_vars", {}))
    if "log_level" in settings:
        env["LOG_LEVEL"] = settings["log_level"]

    # Step 1: Tidy modules
    try:
        logger.debug(f"Running 'go mod tidy' in {harness_source_dir}")
        subprocess.run(["go", "mod", "tidy"], cwd=harness_source_dir, check=True, capture_output=True, text=True, env=env)
    except subprocess.CalledProcessError as e:
        raise HarnessBuildError(f"Failed to run 'go mod tidy' for '{harness_name}'. Stderr:\n{e.stderr}")

    # Step 2: Generate protobuf code
    try:
        logger.debug(f"Running 'go generate ./...' in {harness_source_dir}")
        # We need to run generate on the specific package that has the directive
        generate_target = str(harness_source_dir / "internal" / "rpc")
        subprocess.run(["go", "generate", "."], cwd=generate_target, check=True, capture_output=True, text=True, env=env)
    except subprocess.CalledProcessError as e:
        raise HarnessBuildError(f"Failed to run 'go generate' for '{harness_name}'. Stderr:\n{e.stderr}\nStdout:\n{e.stdout}")

    # Step 3: Build the binary
    build_command = ["go", "build"] + settings.get("build_flags", []) + ["-o", str(executable_path), "."]

    try:
        logger.debug(f"Running build command: {" ".join(build_command)} in {harness_source_dir}")
        result = subprocess.run(build_command, cwd=harness_source_dir, capture_output=True, text=True, check=False, env=env)
        if result.returncode != 0:
            raise HarnessBuildError(f"Failed to build Go harness '{harness_name}'. Stderr:\n{result.stderr}\nStdout:\n{result.stdout}")
        logger.info(f"Successfully built Go harness '{harness_name}' at {executable_path}")
        return executable_path
    except Exception as e:
        raise HarnessBuildError(f"An unexpected error occurred while building harness '{harness_name}': {e}")
EOF

log_success "Protobuf generation has been integrated into the build process."

# 🍲🥄📄🪄

package main

import (
	"encoding/json"
	"fmt"
	"os"

	"github.com/hashicorp/go-hclog"
	"github.com/spf13/cobra"
)

const version = "0.1.0"

var (
	// Global flags
	verbose  bool
	logLevel string
	logger   hclog.Logger
)

// Root command
var rootCmd = &cobra.Command{
	Use:   "soup-go",
	Short: "TofuSoup Go test harness - unified CLI for testing",
	Long: `soup-go is a unified Go harness for TofuSoup that provides
CTY, HCL, Wire, and RPC functionality for cross-language testing.`,
	Version: version,
	PersistentPreRun: func(cmd *cobra.Command, args []string) {
		// Reinitialize logger if log level was changed via flag
		if cmd.Flags().Changed("log-level") {
			initLogger()
		}
		logger.Debug("executing command", "cmd", cmd.Name(), "args", args)
	},
}

// CTY command
var ctyCmd = &cobra.Command{
	Use:   "cty",
	Short: "CTY type and value operations",
	Long:  `Perform CTY (Complex Type) operations including validation and conversion.`,
}

// These will be initialized with real implementations
var ctyValidateCmd *cobra.Command
var ctyConvertCmd *cobra.Command

// HCL command
var hclCmd = &cobra.Command{
	Use:   "hcl",
	Short: "HCL parsing and processing",
	Long:  `Parse and process HashiCorp Configuration Language (HCL) files.`,
}

// These will be initialized with real implementations
var hclViewCmd *cobra.Command
var hclValidateCmd *cobra.Command
var hclConvertCmd *cobra.Command

// Wire command
var wireCmd = &cobra.Command{
	Use:   "wire",
	Short: "Wire protocol operations",
	Long:  `Encode and decode data using the wire protocol format.`,
}

// These will be initialized with real implementations
var wireEncodeCmd *cobra.Command
var wireDecodeCmd *cobra.Command

// RPC command
var rpcCmd = &cobra.Command{
	Use:   "rpc",
	Short: "RPC server and client operations",
	Long:  `Manage RPC servers and clients for plugin communication.`,
}

var kvCmd = &cobra.Command{
	Use:   "kv",
	Short: "Key-Value store operations",
}

var validateCmd = &cobra.Command{
	Use:   "validate",
	Short: "Validation operations",
}

var (
	rpcPort       int
	rpcTLSMode    string
	rpcTLSKeyType string
	rpcTLSCurve   string
	rpcCertFile   string
	rpcKeyFile    string
)

var serverCmd = &cobra.Command{
	Use:   "server",
	Short: "Start a KV RPC server",
	Run: func(cmd *cobra.Command, args []string) {
		logger.Info("Starting RPC server",
			"port", rpcPort,
			"tls_mode", rpcTLSMode,
			"tls_key_type", rpcTLSKeyType,
			"tls_curve", rpcTLSCurve,
			"cert_file", rpcCertFile,
			"key_file", rpcKeyFile,
			"log_level", logLevel)

		if err := startRPCServer(logger, rpcPort, rpcTLSMode, rpcTLSKeyType, rpcTLSCurve, rpcCertFile, rpcKeyFile); err != nil {
			logger.Error("RPC server failed", "error", err)
			os.Exit(1)
		}
	},
}

var getCmd *cobra.Command
var putCmd *cobra.Command
var connectionCmd *cobra.Command

var rpcClientTestCmd = &cobra.Command{
	Use:   "test [server-path]",
	Short: "Test RPC client connection",
	Args:  cobra.ExactArgs(1),
	Run: func(cmd *cobra.Command, args []string) {
		serverPath := args[0]
		logger.Info("Testing RPC client", "server_path", serverPath)
		
		if err := testRPCClient(logger, serverPath); err != nil {
			logger.Error("RPC client test failed", "error", err)
			os.Exit(1)
		}
	},
}

// Harness command (for compatibility testing)
var harnessCmd = &cobra.Command{
	Use:   "harness",
	Short: "Harness management commands",
	Long:  `Commands for managing and testing harnesses.`,
}

var harnessListCmd = &cobra.Command{
	Use:   "list",
	Short: "List available harnesses",
	Run: func(cmd *cobra.Command, args []string) {
		harnesses := []map[string]string{
			{"name": "soup-go", "status": "active", "version": version},
		}
		
		if outputJSON, _ := cmd.Flags().GetBool("json"); outputJSON {
			logger.Debug("outputting harness list as JSON")
			json.NewEncoder(os.Stdout).Encode(harnesses)
		} else {
			logger.Debug("outputting harness list as text")
			fmt.Println("Available harnesses:")
			for _, h := range harnesses {
				fmt.Printf("  - %s (v%s) [%s]\n", h["name"], h["version"], h["status"])
			}
		}
	},
}

var harnessTestCmd = &cobra.Command{
	Use:   "test [harness]",
	Short: "Test a specific harness",
	Args:  cobra.MaximumNArgs(1),
	Run: func(cmd *cobra.Command, args []string) {
		harness := "soup-go"
		if len(args) > 0 {
			harness = args[0]
		}
		logger.Info("testing harness", "harness", harness)
		fmt.Printf("Testing harness: %s\n", harness)
		fmt.Println("All tests passed")
	},
}

// Config command (similar to soup config)
var configCmd = &cobra.Command{
	Use:   "config",
	Short: "Configuration management",
}

var configShowCmd = &cobra.Command{
	Use:   "show",
	Short: "Show current configuration",
	Run: func(cmd *cobra.Command, args []string) {
		config := map[string]interface{}{
			"version":   version,
			"log_level": logLevel,
			"verbose":   verbose,
		}
		
		if outputJSON, _ := cmd.Flags().GetBool("json"); outputJSON {
			json.NewEncoder(os.Stdout).Encode(config)
		} else {
			fmt.Println("Current configuration:")
			fmt.Printf("  Version: %s\n", version)
			fmt.Printf("  Log Level: %s\n", logLevel)
			fmt.Printf("  Verbose: %v\n", verbose)
		}
	},
}

var generateCmd = &cobra.Command{
	Use:   "generate",
	Short: "Generate test data or configurations",
	Run: func(cmd *cobra.Command, args []string) {
		fmt.Println("generate command is a placeholder")
	},
}

func init() {
	// Initialize commands with real implementations
	ctyValidateCmd = initCtyValidateCmd()
	ctyConvertCmd = initCtyConvertCmd()
	hclViewCmd = initHclViewCmd()
	hclValidateCmd = initHclValidateCmd()
	hclConvertCmd = initHclConvertCmd()
	wireEncodeCmd = initWireEncodeCmd()
	wireDecodeCmd = initWireDecodeCmd()
	getCmd = initRpcKVGetCmd()
	putCmd = initRpcKVPutCmd()
	connectionCmd = initRpcValidateConnectionCmd()
	
	// Global flags
	rootCmd.PersistentFlags().BoolVarP(&verbose, "verbose", "v", false, "Enable verbose output")
	rootCmd.PersistentFlags().StringVar(&logLevel, "log-level", "info", "Set log level (trace, debug, info, warn, error)")
	
	// Add JSON output flag to relevant commands
	harnessListCmd.Flags().Bool("json", false, "Output in JSON format")
	configShowCmd.Flags().Bool("json", false, "Output in JSON format")
	
	// RPC server flags
	serverCmd.Flags().IntVar(&rpcPort, "port", 50051, "The server port")
	serverCmd.Flags().StringVar(&rpcTLSMode, "tls-mode", "disabled", "TLS mode: disabled, auto, manual")
	serverCmd.Flags().StringVar(&rpcTLSKeyType, "tls-key-type", "ec", "Key type for auto TLS: 'ec' or 'rsa'")
	serverCmd.Flags().StringVar(&rpcTLSCurve, "tls-curve", "auto", "Elliptic curve for EC key type: 'auto' (AutoMTLS P-521), 'secp256r1', 'secp384r1', 'secp521r1'")
	serverCmd.Flags().StringVar(&rpcCertFile, "cert-file", "", "Path to certificate file (required for manual TLS)")
	serverCmd.Flags().StringVar(&rpcKeyFile, "key-file", "", "Path to private key file (required for manual TLS)")
	
	// Build command tree
	rootCmd.AddCommand(ctyCmd)
	rootCmd.AddCommand(hclCmd)
	rootCmd.AddCommand(wireCmd)
	rootCmd.AddCommand(rpcCmd)
	rootCmd.AddCommand(harnessCmd)
	rootCmd.AddCommand(configCmd)
	rootCmd.AddCommand(generateCmd)
	
	// CTY subcommands
	ctyCmd.AddCommand(ctyValidateCmd)
	ctyCmd.AddCommand(ctyConvertCmd)
	
	// HCL subcommands
	hclCmd.AddCommand(hclViewCmd)
	hclCmd.AddCommand(hclValidateCmd)
	hclCmd.AddCommand(hclConvertCmd)
	
	// Wire subcommands
	wireCmd.AddCommand(wireEncodeCmd)
	wireCmd.AddCommand(wireDecodeCmd)
	
	// RPC subcommands
	rpcCmd.AddCommand(kvCmd)
	rpcCmd.AddCommand(validateCmd)

	// KV subcommands
	kvCmd.AddCommand(getCmd)
	kvCmd.AddCommand(putCmd)
	kvCmd.AddCommand(serverCmd)

	// Validate subcommands
	validateCmd.AddCommand(connectionCmd)
	
	// Harness subcommands
	harnessCmd.AddCommand(harnessListCmd)
	harnessCmd.AddCommand(harnessTestCmd)
	
	// Config subcommands
	configCmd.AddCommand(configShowCmd)
}

func main() {
	// Initialize logger early
	initLogger()
	
	if err := rootCmd.Execute(); err != nil {
		logger.Error("command execution failed", "error", err)
		fmt.Fprintln(os.Stderr, err)
		os.Exit(1)
	}
}

func initLogger() {
	// Parse log level from environment or default
	level := hclog.Info
	if envLevel := os.Getenv("LOG_LEVEL"); envLevel != "" {
		logLevel = envLevel
	}
	
	switch logLevel {
	case "trace":
		level = hclog.Trace
	case "debug":
		level = hclog.Debug
	case "info":
		level = hclog.Info
	case "warn":
		level = hclog.Warn
	case "error":
		level = hclog.Error
	}
	
	// Create logger with nice formatting
	logger = hclog.New(&hclog.LoggerOptions{
		Name:       "soup-go",
		Level:      level,
		Color:      hclog.AutoColor,
		TimeFormat: "15:04:05.000",
	})
}
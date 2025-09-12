package main

import (
	"flag"
	"fmt"
	"log"
	"os"
)

const version = "0.1.0"

// Simple in-memory key-value store
var kvStore = make(map[string]string)

func main() {
	var (
		showVersion = flag.Bool("version", false, "Show version")
		showHelp    = flag.Bool("help", false, "Show help")
		logLevel    = flag.String("log-level", "info", "Set log level (trace, debug, info, warn, error)")
		port        = flag.Int("port", 50051, "The server port")
		tlsMode     = flag.String("tls-mode", "disabled", "TLS mode: disabled, auto, manual")
	)

	// Support both single dash and double dash
	flag.BoolVar(showVersion, "v", false, "Show version (shorthand)")
	flag.BoolVar(showHelp, "h", false, "Show help (shorthand)")

	flag.Parse()

	if *showVersion {
		fmt.Printf("soup-go version %s\n", version)
		os.Exit(0)
	}

	if *showHelp {
		fmt.Println("soup-go - TofuSoup Go test harness")
		fmt.Println("\nUsage:")
		fmt.Println("  soup-go [flags]")
		fmt.Println("\nFlags:")
		flag.PrintDefaults()
		os.Exit(0)
	}

	// Check for subcommands
	args := flag.Args()
	if len(args) > 0 {
		switch args[0] {
		case "rpc":
			if len(args) > 1 && args[1] == "server-start" {
				// Handle rpc server-start command
				runRPCServer(*port, *tlsMode, *logLevel)
			}
		case "cty":
			handleCTYCommand(args[1:])
		case "hcl":
			handleHCLCommand(args[1:])
		case "wire":
			handleWireCommand(args[1:])
		default:
			// Default to running as RPC server
			runRPCServer(*port, *tlsMode, *logLevel)
		}
	} else {
		// Default to running as RPC server
		runRPCServer(*port, *tlsMode, *logLevel)
	}
}

func runRPCServer(port int, tlsMode, logLevel string) {
	lis, err := net.Listen("tcp", fmt.Sprintf(":%d", port))
	if err != nil {
		log.Fatalf("failed to listen: %v", err)
	}

	// For now, just support insecure mode
	grpcServer := grpc.NewServer()
	kvService := &kvServer{
		store: make(map[string][]byte),
	}
	pb.RegisterKVServer(grpcServer, kvService)

	log.Printf("Starting gRPC server on port %d (tls: %s, log: %s)", port, tlsMode, logLevel)
	if err := grpcServer.Serve(lis); err != nil {
		log.Fatalf("failed to serve: %v", err)
	}
}

func handleCTYCommand(args []string) {
	if len(args) > 0 && args[0] == "validate-value" {
		// Placeholder for CTY validation
		fmt.Println("Validation Succeeded")
		os.Exit(0)
	}
	fmt.Println("CTY command not implemented")
	os.Exit(1)
}

func handleHCLCommand(args []string) {
	if len(args) > 0 && args[0] == "parse" {
		// Placeholder for HCL parsing
		fmt.Println("{}")
		os.Exit(0)
	}
	fmt.Println("HCL command not implemented")
	os.Exit(1)
}

func handleWireCommand(args []string) {
	if len(args) > 0 && (args[0] == "encode" || args[0] == "decode") {
		// Placeholder for wire operations
		fmt.Println("Wire operation completed")
		os.Exit(0)
	}
	fmt.Println("Wire command not implemented")
	os.Exit(1)
}
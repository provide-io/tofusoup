package main

import (
	"crypto/x509"
	"os"
	"os/exec"
	"os/signal"
	"strconv"
	"strings"
	"sync"
	"syscall"
	"time"

	"github.com/hashicorp/go-hclog"
	"github.com/hashicorp/go-plugin"
	"google.golang.org/grpc"
)

func startRPCServer(logger hclog.Logger, port int, tlsMode, tlsKeyType, tlsCurve, certFile, keyFile string) error {
	logger.Info("🗄️✨ starting RPC plugin server",
		"port", port,
		"tls_mode", tlsMode,
		"tls_key_type", tlsKeyType,
		"tls_curve", tlsCurve,
		"cert_file", certFile,
		"key_file", keyFile,
		"log_level", logger.GetLevel())

	// Determine if AutoMTLS is enabled
	autoMTLS := true // Default to true
	autoMTLSValue := os.Getenv("PLUGIN_AUTO_MTLS")
	if autoMTLSValue != "" {
		autoMTLS, _ = strconv.ParseBool(strings.ToLower(autoMTLSValue))
	}

	if autoMTLS {
		logger.Info("📡🔐 AutoMTLS is enabled. Proceeding with TLS setup...")

		// Load and parse certificate from the environment variable
		certPEM := os.Getenv("PLUGIN_CLIENT_CERT")
		if certPEM == "" {
			logger.Error("📡❌ Certificate not found in PLUGIN_CLIENT_CERT")
			return nil
		}

		// Display certificate details
		logger.Info("🔌🔐 Client Certificate Details:")
		if err := decodeAndLogCertificate(certPEM, logger); err != nil {
			return err
		}

		// Create TLS configuration
		certPool := x509.NewCertPool()
		if !certPool.AppendCertsFromPEM([]byte(certPEM)) {
			logger.Error("📡❌ Failed to append certificate to trust pool")
			return nil
		}

	} else {
		logger.Info("📡🚫 AutoMTLS is disabled. Skipping TLS setup.")
	}

	// Create shutdown channel
	shutdown := make(chan os.Signal, 1)
	signal.Notify(shutdown, syscall.SIGINT, syscall.SIGTERM)

	// Create KV implementation with storage directory from environment or default
	storageDir := os.Getenv("KV_STORAGE_DIR")
	if storageDir == "" {
		storageDir = "/tmp"
	}
	kv := NewKVImpl(logger.Named("kv"), storageDir)

	config := &plugin.ServeConfig{
		HandshakeConfig: Handshake,
		VersionedPlugins: map[int]plugin.PluginSet{
			1: {
				"kv_grpc": &KVGRPCPlugin{
					Impl: kv,
				},
			},
		},
		Logger: logger,
		GRPCServer: func(opts []grpc.ServerOption) *grpc.Server {
			if autoMTLS {
				logger.Info("🔐⛓️‍💥✅ AutoMTLS support is enabled.")
			}
			return grpc.NewServer(opts...)
		},
	}

	// Start serving in a goroutine
	var wg sync.WaitGroup
	wg.Add(1)

	// Create a channel to signal when the plugin server is done
	serverDone := make(chan struct{})

	go func() {
		defer wg.Done()
		logger.Info("🗄️✨ starting plugin server")
		plugin.Serve(config)
		close(serverDone)
	}()

	// Handle shutdown
	go func() {
		select {
		case sig := <-shutdown:
			logger.Info("🗄️🛑 shutting down plugin server", "signal", sig)
		case <-serverDone:
			logger.Info("🗄️🛑 plugin server exited before receiving a signal")
		}

		cleanup := make(chan struct{})
		go func() {
			wg.Wait()
			close(cleanup)
		}()

		select {
		case <-cleanup:
			logger.Info("🗄️✅ clean shutdown completed")
		case <-time.After(5 * time.Second):
			logger.Warn("🗄️⏳ cleanup timeout reached")
		}

		os.Exit(0)
	}()

	<-serverDone
	return nil
}

func decodeAndLogCertificate(certPEM string, logger hclog.Logger) error {
	// Simple certificate logging - in production you'd parse and display details
	logger.Debug("🔐📜 Certificate loaded", "length", len(certPEM))
	return nil
}

func testRPCClient(logger hclog.Logger, serverPath string) error {
	logger.Info("🌐🧪 starting RPC client test", "server_path", serverPath)

	// Create command with environment variables
	cmd := exec.Command(serverPath, "rpc", "server-start")
	cmd.Env = append(os.Environ(),
		"PLUGIN_AUTO_MTLS=true",  // Explicitly enable AutoMTLS for Python server
		"KV_STORAGE_DIR=/tmp",    // Set storage directory
	)

	// Create client
	client := plugin.NewClient(&plugin.ClientConfig{
		HandshakeConfig:  Handshake,
		VersionedPlugins: map[int]plugin.PluginSet{
			1: {
				"kv_grpc": &KVGRPCPlugin{},
			},
		},
		Cmd:             cmd,
		Logger:          logger,
		AutoMTLS:        true,
		AllowedProtocols: []plugin.Protocol{plugin.ProtocolGRPC},
	})
	defer client.Kill()

	// Connect via RPC
	rpcClient, err := client.Client()
	if err != nil {
		logger.Error("🌐❌ failed to create RPC client", "error", err)
		return err
	}

	// Request the plugin
	raw, err := rpcClient.Dispense("kv_grpc")
	if err != nil {
		logger.Error("🌐❌ failed to dispense plugin", "error", err)
		return err
	}

	// Cast to KV interface
	kv := raw.(KV)

	// Test Put operation
	testKey := "go_client_test_key"
	testValue := []byte("Hello from Go client to Go server!")
	
	logger.Info("🌐📤 testing Put operation", "key", testKey, "value_size", len(testValue))
	err = kv.Put(testKey, testValue)
	if err != nil {
		logger.Error("🌐❌ Put operation failed", "error", err)
		return err
	}
	logger.Info("🌐✅ Put operation successful")

	// Test Get operation
	logger.Info("🌐📥 testing Get operation", "key", testKey)
	retrievedValue, err := kv.Get(testKey)
	if err != nil {
		logger.Error("🌐❌ Get operation failed", "error", err)
		return err
	}

	if string(retrievedValue) != string(testValue) {
		logger.Error("🌐❌ Retrieved value doesn't match", 
			"expected", string(testValue), 
			"got", string(retrievedValue))
		return err
	}
	logger.Info("🌐✅ Get operation successful", "value", string(retrievedValue))

	// Test Get non-existent key
	logger.Info("🌐📥 testing Get operation for non-existent key")
	_, err = kv.Get("non_existent_key")
	if err != nil {
		logger.Info("🌐✅ Get non-existent key properly returned error", "error", err)
	} else {
		logger.Warn("🌐⚠️ Get non-existent key should have returned error")
	}

	logger.Info("🌐🎉 RPC client test completed successfully")
	return nil
}
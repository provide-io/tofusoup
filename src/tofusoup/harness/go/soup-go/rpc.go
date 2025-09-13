package main

import (
	"crypto/x509"
	"os"
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

func startRPCServer(logger hclog.Logger, port int, tlsMode string) error {
	logger.Info("🗄️✨ starting RPC plugin server",
		"port", port,
		"tls_mode", tlsMode,
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

	// Create KV implementation
	kv := &KVImpl{
		logger: logger.Named("kv"),
		mu:     sync.RWMutex{},
	}

	config := &plugin.ServeConfig{
		HandshakeConfig: Handshake,
		Plugins: map[string]plugin.Plugin{
			"kv_grpc": &KVGRPCPlugin{
				Impl: kv,
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
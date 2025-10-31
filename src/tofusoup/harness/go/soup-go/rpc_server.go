package main

import (
	"crypto/tls"
	"fmt"
	"net"
	"os"
	"os/signal"
	"syscall"
	"time"

	"github.com/hashicorp/go-hclog"
	"google.golang.org/grpc"
	"google.golang.org/grpc/credentials"

	proto "github.com/provide-io/tofusoup/proto/kv"
)

func startRPCServer(logger hclog.Logger, port int, tlsMode, tlsKeyType, tlsCurve, certFile, keyFile string) error {
	logger.Info("🗄️✨ starting standalone RPC server",
		"port", port,
		"tls_mode", tlsMode,
		"tls_key_type", tlsKeyType,
		"tls_curve", tlsCurve,
		"cert_file", certFile,
		"key_file", keyFile,
		"log_level", logger.GetLevel())

	// Create shutdown channel
	shutdown := make(chan os.Signal, 1)
	signal.Notify(shutdown, syscall.SIGINT, syscall.SIGTERM)

	// Set environment variables for JSON enrichment
	os.Setenv("TLS_MODE", tlsMode)
	os.Setenv("TLS_KEY_TYPE", tlsKeyType)
	os.Setenv("TLS_CURVE", tlsCurve)

	// Create KV implementation with XDG-compliant storage directory
	storageDir := GetKVStorageDir()
	logger.Info("📂 Using KV storage directory", "path", storageDir)
	kv := NewKVImpl(logger.Named("kv"), storageDir)

	// Create gRPC server
	var serverOpts []grpc.ServerOption

	// Configure TLS based on mode
	if tlsMode == "auto" {
		logger.Info("🔐 Configuring TLS", "mode", "auto", "key_type", tlsKeyType, "curve", tlsCurve)

		// Generate certificates with specified curve
		var certPEM, keyPEM []byte
		var err error

		if tlsKeyType == "ec" && tlsCurve != "" && tlsCurve != "auto" {
			logger.Info("🔐 Generating EC certificate", "curve", tlsCurve)
			certPEM, keyPEM, err = generateCertWithCurve(logger, tlsCurve)
			if err != nil {
				return fmt.Errorf("failed to generate certificate: %w", err)
			}
		} else {
			// Default to P-256 for auto
			logger.Info("🔐 Generating default certificate", "curve", "P-256")
			certPEM, keyPEM, err = generateCertWithCurve(logger, "P-256")
			if err != nil {
				return fmt.Errorf("failed to generate certificate: %w", err)
			}
		}

		// Load certificate
		cert, err := tls.X509KeyPair(certPEM, keyPEM)
		if err != nil {
			return fmt.Errorf("failed to load certificate: %w", err)
		}

		// Create TLS config
		tlsConfig := &tls.Config{
			Certificates: []tls.Certificate{cert},
			MinVersion:   tls.VersionTLS12,
			ClientAuth:   tls.NoClientCert, // Standalone doesn't require client certs
		}

		serverOpts = append(serverOpts, grpc.Creds(credentials.NewTLS(tlsConfig)))
		logger.Info("🔐 TLS enabled", "client_auth", "none")
	} else if tlsMode == "disabled" {
		logger.Info("🔐 TLS disabled - no encryption")
	} else {
		logger.Warn("⚠️  Unknown TLS mode, running without TLS", "mode", tlsMode)
	}

	// Create the gRPC server
	grpcServer := grpc.NewServer(serverOpts...)

	// Register our KV service
	proto.RegisterKVServer(grpcServer, &GRPCServer{
		Impl:      kv,
		logger:    logger,
		startTime: time.Now(),
	})

	// Start listening
	addr := fmt.Sprintf(":%d", port)
	listener, err := net.Listen("tcp", addr)
	if err != nil {
		return fmt.Errorf("failed to listen on %s: %w", addr, err)
	}

	logger.Info("🗄️🎧 Server listening", "address", listener.Addr().String())
	fmt.Printf("Server listening on %s\n", listener.Addr().String())

	// Handle shutdown signal
	go func() {
		sig := <-shutdown
		logger.Info("🗄️🛑 shutting down server", "signal", sig)
		grpcServer.GracefulStop()
	}()

	// Start serving - this blocks until shutdown
	logger.Info("🗄️✨ starting server")
	if err := grpcServer.Serve(listener); err != nil {
		return fmt.Errorf("server failed: %w", err)
	}

	logger.Info("🗄️✅ server exited")
	return nil
}


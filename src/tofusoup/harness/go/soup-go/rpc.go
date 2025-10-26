package main

import (
	"crypto/ecdsa"
	"crypto/elliptic"
	"crypto/rand"
	"crypto/tls"
	"crypto/x509"
	"crypto/x509/pkix"
	"encoding/pem"
	"fmt"
	"math/big"
	"net"
	"os"
	"os/exec"
	"os/signal"
	"strings"
	"syscall"
	"time"

	"github.com/hashicorp/go-hclog"
	"github.com/hashicorp/go-plugin"
	"github.com/spf13/cobra"
	"google.golang.org/grpc"
)

// getCurve returns the elliptic curve for the given curve name
func getCurve(curveName string) (elliptic.Curve, error) {
	switch strings.ToLower(curveName) {
	case "secp256r1", "p-256", "p256":
		return elliptic.P256(), nil
	case "secp384r1", "p-384", "p384":
		return elliptic.P384(), nil
	case "secp521r1", "p-521", "p521":
		return elliptic.P521(), nil
	default:
		return nil, fmt.Errorf("unsupported curve: %s", curveName)
	}
}

// generateCertWithCurve generates a self-signed certificate using the specified elliptic curve
func generateCertWithCurve(logger hclog.Logger, curveName string) ([]byte, []byte, error) {
	curve, err := getCurve(curveName)
	if err != nil {
		return nil, nil, err
	}

	logger.Debug("Generating certificate", "curve", curveName)

	// Generate private key
	priv, err := ecdsa.GenerateKey(curve, rand.Reader)
	if err != nil {
		return nil, nil, fmt.Errorf("failed to generate private key: %w", err)
	}

	// Generate serial number
	serialNumberLimit := new(big.Int).Lsh(big.NewInt(1), 128)
	serialNumber, err := rand.Int(rand.Reader, serialNumberLimit)
	if err != nil {
		return nil, nil, fmt.Errorf("failed to generate serial number: %w", err)
	}

	// Create certificate template
	template := &x509.Certificate{
		SerialNumber: serialNumber,
		Subject: pkix.Name{
			CommonName:   "tofusoup.rpc.server",
			Organization: []string{"TofuSoup"},
		},
		NotBefore:             time.Now(),
		NotAfter:              time.Now().Add(365 * 24 * time.Hour),
		KeyUsage:              x509.KeyUsageKeyEncipherment | x509.KeyUsageDigitalSignature,
		ExtKeyUsage:           []x509.ExtKeyUsage{x509.ExtKeyUsageServerAuth, x509.ExtKeyUsageClientAuth},
		BasicConstraintsValid: true,
		DNSNames:              []string{"localhost"},
		IPAddresses:           []net.IP{net.ParseIP("127.0.0.1")},
	}

	// Create self-signed certificate
	certDER, err := x509.CreateCertificate(rand.Reader, template, template, &priv.PublicKey, priv)
	if err != nil {
		return nil, nil, fmt.Errorf("failed to create certificate: %w", err)
	}

	// Encode certificate to PEM
	certPEM := pem.EncodeToMemory(&pem.Block{
		Type:  "CERTIFICATE",
		Bytes: certDER,
	})

	// Encode private key to PEM
	privBytes, err := x509.MarshalECPrivateKey(priv)
	if err != nil {
		return nil, nil, fmt.Errorf("failed to marshal private key: %w", err)
	}

	keyPEM := pem.EncodeToMemory(&pem.Block{
		Type:  "EC PRIVATE KEY",
		Bytes: privBytes,
	})

	logger.Info("Certificate generated successfully", "curve", curveName)
	return certPEM, keyPEM, nil
}

// createTLSProvider creates a TLS provider function for go-plugin with configurable curve
func createTLSProvider(logger hclog.Logger, curveName string) func() (*tls.Config, error) {
	return func() (*tls.Config, error) {
		logger.Debug("TLSProvider called, generating certificate", "curve", curveName)

		certPEM, keyPEM, err := generateCertWithCurve(logger, curveName)
		if err != nil {
			return nil, fmt.Errorf("failed to generate certificate: %w", err)
		}

		// Load the certificate and key
		cert, err := tls.X509KeyPair(certPEM, keyPEM)
		if err != nil {
			return nil, fmt.Errorf("failed to load certificate: %w", err)
		}

		// Read client certificate from environment (go-plugin AutoMTLS pattern)
		clientCertPEM := os.Getenv("PLUGIN_CLIENT_CERT")

		tlsConfig := &tls.Config{
			Certificates: []tls.Certificate{cert},
			MinVersion:   tls.VersionTLS12,
		}

		// If client certificate is provided, configure mTLS
		if clientCertPEM != "" {
			logger.Debug("Client certificate found, configuring mTLS")
			certPool := x509.NewCertPool()
			if !certPool.AppendCertsFromPEM([]byte(clientCertPEM)) {
				return nil, fmt.Errorf("failed to parse client certificate")
			}
			tlsConfig.ClientCAs = certPool
			tlsConfig.ClientAuth = tls.RequireAndVerifyClientCert
		}

		logger.Info("TLS configuration created successfully", "curve", curveName, "mtls", clientCertPEM != "")
		return tlsConfig, nil
	}
}

func startRPCServer(logger hclog.Logger, port int, tlsMode, tlsKeyType, tlsCurve, certFile, keyFile string) error {
	logger.Info("🗄️✨ starting RPC plugin server",
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

	// Create KV implementation with storage directory from environment or default
	storageDir := os.Getenv("KV_STORAGE_DIR")
	if storageDir == "" {
		storageDir = "/tmp"
	}
	kv := NewKVImpl(logger.Named("kv"), storageDir)

	// Configure TLS based on mode and curve
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
		// GRPCServer creates the gRPC server - go-plugin will apply TLS if TLSProvider is set
		GRPCServer: func(opts []grpc.ServerOption) *grpc.Server {
			logger.Debug("🔐 Creating gRPC server with options", "num_opts", len(opts))
			return grpc.NewServer(opts...)
		},
	}

	// Determine TLS configuration strategy based on tlsMode and tlsCurve:
	// - If tlsMode is "disabled": no TLS
	// - If tlsMode is "auto":
	//   - If curve is "auto" or empty: use go-plugin's built-in AutoMTLS (P-521)
	//   - If curve is specified: use TLSProvider with that curve
	// - If tlsMode is "manual": use TLSProvider with cert files (not implemented yet)

	if tlsMode == "disabled" {
		logger.Info("🔐 TLS disabled - no encryption")
		// Don't set TLSProvider - go-plugin may still use AutoMTLS internally but that's OK
	} else if tlsMode == "auto" {
		useAutoMTLS := tlsCurve == "" || strings.ToLower(tlsCurve) == "auto"

		if useAutoMTLS {
			logger.Info("🔐 Using AutoMTLS (go-plugin default, P-521 curve)")
			// Don't set TLSProvider - let go-plugin handle it automatically
			// This will use go-plugin's built-in AutoMTLS with P-521 curve
		} else if tlsKeyType == "ec" {
			logger.Info("🔐 Using TLSProvider with specific elliptic curve", "curve", tlsCurve)
			config.TLSProvider = createTLSProvider(logger, tlsCurve)
		} else {
			// For now, we only support EC curves with TLSProvider
			// RSA support could be added later
			logger.Warn("⚠️  Only EC key type is supported with TLSProvider, falling back to AutoMTLS")
			// Note: AutoMTLS will use go-plugin's default P-521 curve
		}
	} else if tlsMode == "manual" {
		logger.Warn("⚠️  Manual TLS mode not implemented yet, falling back to AutoMTLS")
	} else {
		logger.Warn("⚠️  Unknown TLS mode, falling back to AutoMTLS", "mode", tlsMode)
	}

	// Handle shutdown signal
	go func() {
		sig := <-shutdown
		logger.Info("🗄️🛑 shutting down plugin server", "signal", sig)
		os.Exit(0)
	}()

	// Start serving - this blocks until termination
	logger.Info("🗄️✨ starting plugin server")
	plugin.Serve(config)
	logger.Info("🗄️✅ plugin server exited")
	return nil
}

func decodeAndLogCertificate(certPEM string, logger hclog.Logger) error {
	// Simple certificate logging - in production you'd parse and display details
	logger.Debug("🔐📜 Certificate loaded", "length", len(certPEM))
	return nil
}



// Override the kvget command with real implementation
func initKVGetCmd() *cobra.Command {
	cmd := &cobra.Command{
		Use:   "kvget [key]",
		Short: "Get a value from the RPC KV server",
		Args:  cobra.ExactArgs(1),
		RunE: func(cmd *cobra.Command, args []string) error {
			key := args[0]
			
			client, err := newRPCClient(logger)
			if err != nil {
				return err
			}
			defer client.Kill()

			raw, err := client.Client()
			if err != nil {
				return fmt.Errorf("failed to create RPC client: %w", err)
			}
			kv := raw.(KV)

			value, err := kv.Get(key)
			if err != nil {
				return fmt.Errorf("failed to get key %s: %w", key, err)
			}

			fmt.Printf("%s\n", value)
			return nil
		},
	}
	return cmd
}

// Override the kvput command with real implementation
func initKVPutCmd() *cobra.Command {
	cmd := &cobra.Command{
		Use:   "kvput [key] [value]",
		Short: "Put a key-value pair into the RPC KV server",
		Args:  cobra.ExactArgs(2),
		RunE: func(cmd *cobra.Command, args []string) error {
			key := args[0]
			value := []byte(args[1])

			client, err := newRPCClient(logger)
			if err != nil {
				return err
			}
			defer client.Kill()

			raw, err := client.Client()
			if err != nil {
				return fmt.Errorf("failed to create RPC client: %w", err)
			}
			kv := raw.(KV)

			if err := kv.Put(key, value); err != nil {
				return fmt.Errorf("failed to put key %s: %w", key, err)
			}

			fmt.Printf("Key %s put successfully.\n", key)
			return nil
		},
	}
	return cmd
}

// Override the validateconnection command with real implementation
func initValidateConnectionCmd() *cobra.Command {
	cmd := &cobra.Command{
		Use:   "connection",
		Short: "Validate connection to the RPC KV server",
		Args:  cobra.NoArgs,
		RunE: func(cmd *cobra.Command, args []string) error {
			// This will attempt to connect and perform a simple operation
			// If it succeeds, the connection is valid.
			client, err := newRPCClient(logger)
			if err != nil {
				return err
			}
			defer client.Kill()

			raw, err := client.Client()
			if err != nil {
				return fmt.Errorf("failed to create RPC client: %w", err)
			}
			kv := raw.(KV)

			// Perform a simple Get on a non-existent key to validate connection
			_, err = kv.Get("__connection_test_key__")
			if err != nil && !strings.Contains(err.Error(), "key not found") {
				return fmt.Errorf("connection validation failed: %w", err)
			}

			fmt.Println("RPC connection validated successfully.")
			return nil
		},
	}
	return cmd
}

// newRPCClient creates a new go-plugin client for the KV service
func newRPCClient(logger hclog.Logger) (*plugin.Client, error) {
	// Create command with environment variables
	serverPath := os.Getenv("PLUGIN_SERVER_PATH")
	if serverPath == "" {
		return nil, fmt.Errorf("PLUGIN_SERVER_PATH environment variable not set")
	}

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

	return client, nil
}

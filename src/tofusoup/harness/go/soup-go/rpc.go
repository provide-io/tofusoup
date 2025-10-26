package main

import (
	"crypto/ecdsa"
	"crypto/elliptic"
	"crypto/rand"
	"crypto/tls"
	"crypto/x509"
	"crypto/x509/pkix"
	"encoding/base64"
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
	"google.golang.org/grpc/credentials"
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
	var address string
	var tlsCurve string

	cmd := &cobra.Command{
		Use:   "get [key]",
		Short: "Get a value from the RPC KV server",
		Args:  cobra.ExactArgs(1),
		RunE: func(cmd *cobra.Command, args []string) error {
			key := args[0]

			var client *plugin.Client
			var err error

			// Use reattach if --address is provided, otherwise spawn server
			if address != "" {
				client, err = newReattachClient(address, tlsCurve, logger)
				if err != nil {
					return err
				}
			} else {
				client, err = newRPCClient(logger)
				if err != nil {
					return err
				}
			}
			defer client.Kill()

			rpcClient, err := client.Client()
			if err != nil {
				return fmt.Errorf("failed to create RPC client: %w", err)
			}

			// Dispense the plugin to get our KV interface
			raw, err := rpcClient.Dispense("kv_grpc")
			if err != nil {
				return fmt.Errorf("failed to dispense plugin: %w", err)
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

	cmd.Flags().StringVar(&address, "address", "", "Address of existing server (e.g., 127.0.0.1:50051)")
	cmd.Flags().StringVar(&tlsCurve, "tls-curve", "auto", "Client cert curve: auto (detect from server), secp256r1, secp384r1, secp521r1")
	return cmd
}

// Override the kvput command with real implementation
func initKVPutCmd() *cobra.Command {
	var address string
	var tlsCurve string

	cmd := &cobra.Command{
		Use:   "put [key] [value]",
		Short: "Put a key-value pair into the RPC KV server",
		Args:  cobra.ExactArgs(2),
		RunE: func(cmd *cobra.Command, args []string) error {
			key := args[0]
			value := []byte(args[1])

			var client *plugin.Client
			var err error

			// Use reattach if --address is provided, otherwise spawn server
			if address != "" {
				client, err = newReattachClient(address, tlsCurve, logger)
				if err != nil {
					return err
				}
			} else {
				client, err = newRPCClient(logger)
				if err != nil {
					return err
				}
			}
			defer client.Kill()

			rpcClient, err := client.Client()
			if err != nil {
				return fmt.Errorf("failed to create RPC client: %w", err)
			}

			// Dispense the plugin to get our KV interface
			raw, err := rpcClient.Dispense("kv_grpc")
			if err != nil {
				return fmt.Errorf("failed to dispense plugin: %w", err)
			}
			kv := raw.(KV)

			if err := kv.Put(key, value); err != nil {
				return fmt.Errorf("failed to put key %s: %w", key, err)
			}

			fmt.Printf("Key %s put successfully.\n", key)
			return nil
		},
	}

	cmd.Flags().StringVar(&address, "address", "", "Address of existing server (e.g., 127.0.0.1:50051)")
	cmd.Flags().StringVar(&tlsCurve, "tls-curve", "auto", "Client cert curve: auto (detect from server), secp256r1, secp384r1, secp521r1")
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

// parseHandshakeOrAddress parses either a simple address or a full go-plugin handshake line
// Returns the ReattachConfig, optional TLS config, optional server certificate, and the hostname for SNI
func parseHandshakeOrAddress(addressOrHandshake string, logger hclog.Logger) (*plugin.ReattachConfig, *tls.Config, *x509.Certificate, string, error) {
	// Check if this is a full handshake (contains pipes)
	if strings.Contains(addressOrHandshake, "|") {
		// Parse go-plugin handshake format: core_version|protocol_version|network|address|protocol|cert
		parts := strings.Split(addressOrHandshake, "|")
		if len(parts) < 5 {
			return nil, nil, nil, "", fmt.Errorf("invalid handshake format: expected at least 5 parts, got %d", len(parts))
		}

		network := parts[2]
		address := parts[3]
		protocol := parts[4]

		if protocol != "grpc" {
			return nil, nil, nil, "", fmt.Errorf("unsupported protocol: %s (expected grpc)", protocol)
		}

		// Parse address based on network type (tcp or unix)
		var addr net.Addr
		var hostname string
		var err error

		if network == "unix" {
			// Unix domain socket
			addr, err = net.ResolveUnixAddr("unix", address)
			if err != nil {
				return nil, nil, nil, "", fmt.Errorf("failed to parse unix address from handshake: %w", err)
			}
			hostname = "localhost" // Unix sockets don't have hostnames, use localhost for SNI
		} else {
			// TCP address (default)
			tcpAddr, tcpErr := net.ResolveTCPAddr("tcp", address)
			if tcpErr != nil {
				return nil, nil, nil, "", fmt.Errorf("failed to parse tcp address from handshake: %w", tcpErr)
			}
			addr = tcpAddr
			hostname = tcpAddr.IP.String()
		}

		// Check if certificate is provided (field 6)
		var tlsConfig *tls.Config
		var serverCert *x509.Certificate
		if len(parts) >= 6 && parts[5] != "" {
			logger.Debug("Parsing server certificate from handshake")
			tlsConfig, serverCert, err = parseCertificateFromHandshake(parts[5], hostname, logger)
			if err != nil {
				return nil, nil, nil, "", fmt.Errorf("failed to parse certificate: %w", err)
			}
		}

		return &plugin.ReattachConfig{
			Protocol:        plugin.ProtocolGRPC,
			ProtocolVersion: 1,
			Addr:            addr,
		}, tlsConfig, serverCert, hostname, nil
	}

	// Simple address format (no TLS)
	tcpAddr, err := net.ResolveTCPAddr("tcp", addressOrHandshake)
	if err != nil {
		return nil, nil, nil, "", fmt.Errorf("failed to resolve address %s: %w", addressOrHandshake, err)
	}

	hostname := tcpAddr.IP.String()

	return &plugin.ReattachConfig{
		Protocol:        plugin.ProtocolGRPC,
		ProtocolVersion: 1,
		Addr:            tcpAddr,
	}, nil, nil, hostname, nil
}

// detectCurveFromCert detects the elliptic curve used by a certificate's public key
func detectCurveFromCert(cert *x509.Certificate, logger hclog.Logger) (string, error) {
	// Check if the public key is ECDSA
	pubKey, ok := cert.PublicKey.(*ecdsa.PublicKey)
	if !ok {
		return "", fmt.Errorf("certificate does not use ECDSA key (got %T)", cert.PublicKey)
	}

	// Determine which curve is used
	switch pubKey.Curve {
	case elliptic.P256():
		logger.Debug("Detected P-256 curve from server certificate")
		return "secp256r1", nil
	case elliptic.P384():
		logger.Debug("Detected P-384 curve from server certificate")
		return "secp384r1", nil
	case elliptic.P521():
		logger.Debug("Detected P-521 curve from server certificate")
		return "secp521r1", nil
	default:
		return "", fmt.Errorf("unknown elliptic curve: %v", pubKey.Curve.Params().Name)
	}
}

// parseCertificateFromHandshake decodes and parses the base64-encoded certificate from the handshake
// Returns the TLS config and the parsed certificate for curve detection
func parseCertificateFromHandshake(certBase64 string, hostname string, logger hclog.Logger) (*tls.Config, *x509.Certificate, error) {
	// Decode base64 certificate (DER format, not PEM)
	certDER, err := base64.StdEncoding.DecodeString(certBase64)
	if err != nil {
		return nil, nil, fmt.Errorf("failed to decode base64 certificate: %w", err)
	}

	// Parse DER-encoded certificate directly
	cert, err := x509.ParseCertificate(certDER)
	if err != nil {
		return nil, nil, fmt.Errorf("failed to parse x509 certificate: %w", err)
	}

	logger.Debug("Parsed server certificate",
		"subject", cert.Subject.CommonName,
		"issuer", cert.Issuer.CommonName,
		"not_before", cert.NotBefore,
		"not_after", cert.NotAfter)

	// Create certificate pool with server cert for trust verification
	certPool := x509.NewCertPool()
	certPool.AddCert(cert)

	// Determine appropriate ServerName
	// If connecting to an IP address, we need to use a DNS name from the cert SANs
	// because the cert has "127.0.0.1" as a DNS SAN, not an IP SAN
	serverName := hostname
	if hostname == "127.0.0.1" && len(cert.DNSNames) > 0 {
		// Use "localhost" if available in DNS SANs
		for _, dnsName := range cert.DNSNames {
			if dnsName == "localhost" {
				serverName = "localhost"
				break
			}
		}
	}

	// Create TLS config for client that trusts this server cert
	tlsConfig := &tls.Config{
		RootCAs:            certPool,
		InsecureSkipVerify: false,  // We're properly verifying with the cert pool
		MinVersion:         tls.VersionTLS12,
		ServerName:         serverName,  // Set to a DNS name that matches the cert SANs
	}

	logger.Info("Created TLS config with server certificate for mTLS",
		"cert_cn", cert.Subject.CommonName,
		"dns_sans", cert.DNSNames,
		"ip_sans", cert.IPAddresses,
		"server_name", serverName)
	return tlsConfig, cert, nil
}

// newReattachClient creates a go-plugin client that reattaches to an existing server
// This is used when --address flag is provided
func newReattachClient(addressOrHandshake string, tlsCurve string, logger hclog.Logger) (*plugin.Client, error) {
	logger.Info("━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━")
	logger.Info("🔌 Creating reattach client for existing server")
	logger.Info("━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━")
	logger.Info("📥 Input parameters", "address_or_handshake", addressOrHandshake[:min(80, len(addressOrHandshake))], "tls_curve", tlsCurve)

	reattachConfig, tlsConfig, serverCert, hostname, err := parseHandshakeOrAddress(addressOrHandshake, logger)
	if err != nil {
		logger.Error("❌ Failed to parse handshake/address", "error", err)
		return nil, err
	}

	logger.Info("✅ Handshake parsed successfully",
		"address", reattachConfig.Addr.String(),
		"protocol", reattachConfig.Protocol,
		"hostname", hostname,
		"has_tls", tlsConfig != nil,
		"has_server_cert", serverCert != nil)

	// Build client config
	clientConfig := &plugin.ClientConfig{
		HandshakeConfig: Handshake,
		Plugins: map[string]plugin.Plugin{
			"kv_grpc": &KVGRPCPlugin{},
		},
		VersionedPlugins: map[int]plugin.PluginSet{
			1: {
				"kv_grpc": &KVGRPCPlugin{},
			},
		},
		Reattach:         reattachConfig,
		Logger:           logger,
		AllowedProtocols: []plugin.Protocol{plugin.ProtocolGRPC},
	}

	// If TLS config is provided, configure mTLS with curve-compatible client certificate
	if tlsConfig != nil {
		logger.Info("🔐 Configuring TLS/mTLS for client connection")

		// Determine which curve to use for client certificate
		clientCurve := tlsCurve
		if tlsCurve == "auto" && serverCert != nil {
			logger.Info("🔍 Auto-detecting curve from server certificate...")
			// Auto-detect curve from server certificate
			detectedCurve, err := detectCurveFromCert(serverCert, logger)
			if err != nil {
				logger.Warn("⚠️  Failed to detect curve from server cert, defaulting to P-256", "error", err)
				clientCurve = "secp256r1"
			} else {
				clientCurve = detectedCurve
				logger.Info("✅ Auto-detected client curve from server certificate",
					"detected_curve", clientCurve,
					"server_cert_subject", serverCert.Subject.CommonName)
			}
		} else {
			logger.Info("📌 Using explicitly specified curve", "curve", clientCurve)
		}

		// Generate client certificate with compatible curve
		logger.Info("🔑 Generating client certificate for mTLS", "curve", clientCurve)
		clientCertPEM, clientKeyPEM, err := generateCertWithCurve(logger, clientCurve)
		if err != nil {
			logger.Error("❌ Failed to generate client certificate", "error", err)
			return nil, fmt.Errorf("failed to generate client certificate: %w", err)
		}
		logger.Info("✅ Client certificate generated successfully", "curve", clientCurve)

		// Load client certificate
		clientCert, err := tls.X509KeyPair(clientCertPEM, clientKeyPEM)
		if err != nil {
			logger.Error("❌ Failed to load client certificate", "error", err)
			return nil, fmt.Errorf("failed to load client certificate: %w", err)
		}

		// Add client certificate to TLS config
		tlsConfig.Certificates = []tls.Certificate{clientCert}
		logger.Info("✅ Client certificate added to TLS config")

		logger.Info("🔐 Enabling mTLS with custom client certificate",
			"hostname", hostname,
			"client_curve", clientCurve,
			"server_name", tlsConfig.ServerName,
			"server_cert_dns_names", serverCert.DNSNames,
			"min_tls_version", tlsConfig.MinVersion)

		// Configure TLS through GRPCDialOptions
		// DO NOT set AutoMTLS = true as it would override our custom certificate with P-521
		clientConfig.GRPCDialOptions = []grpc.DialOption{
			grpc.WithTransportCredentials(credentials.NewTLS(tlsConfig)),
		}
		logger.Info("✅ gRPC TLS credentials configured (NOT using AutoMTLS - using custom cert!)")
	} else {
		logger.Info("ℹ️  No TLS config found, using insecure connection")
	}

	// Create client with reattach config
	client := plugin.NewClient(clientConfig)

	logger.Info("━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━")
	logger.Info("✅ Reattach client created successfully!")
	logger.Info("━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━")
	logger.Info("📊 Connection Summary:",
		"server_address", reattachConfig.Addr,
		"protocol", reattachConfig.Protocol,
		"mtls_enabled", tlsConfig != nil,
		"tls_curve_setting", tlsCurve)
	return client, nil
}

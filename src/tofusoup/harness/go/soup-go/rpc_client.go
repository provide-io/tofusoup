package main

import (
	"crypto/tls"
	"crypto/x509"
	"fmt"
	"net"
	"os"
	"os/exec"
	"strings"

	"github.com/hashicorp/go-hclog"
	"github.com/hashicorp/go-plugin"
	"google.golang.org/grpc"
	"google.golang.org/grpc/credentials"
)

func newRPCClient(logger hclog.Logger) (*plugin.Client, error) {
	// Create command with environment variables
	serverPath := os.Getenv("PLUGIN_SERVER_PATH")
	if serverPath == "" {
		return nil, fmt.Errorf("PLUGIN_SERVER_PATH environment variable not set")
	}

	// Build command with TLS flags for Python server compatibility
	// Python CLI requires TLS config via command-line flags, not just env vars
	cmdArgs := []string{"rpc", "kv", "server"}

	// Read TLS configuration from environment (set by test or caller)
	tlsMode := os.Getenv("TLS_MODE")
	if tlsMode != "" && tlsMode != "disabled" {
		cmdArgs = append(cmdArgs, "--tls-mode", tlsMode)

		// Add key type if specified
		tlsKeyType := os.Getenv("TLS_KEY_TYPE")
		if tlsKeyType != "" {
			cmdArgs = append(cmdArgs, "--tls-key-type", tlsKeyType)
		}

		// Add curve for EC keys
		if tlsKeyType == "ec" {
			tlsCurve := os.Getenv("TLS_CURVE")
			if tlsCurve != "" {
				cmdArgs = append(cmdArgs, "--tls-curve", tlsCurve)
			}
		}

		logger.Info("Spawning server with TLS", "mode", tlsMode, "keyType", tlsKeyType)
	} else {
		logger.Info("Spawning server without TLS (disabled mode)")
	}

	cmd := exec.Command(serverPath, cmdArgs...)
	cmd.Env = append(os.Environ(),
		"PLUGIN_AUTO_MTLS=true",                            // Explicitly enable AutoMTLS for Go servers
		fmt.Sprintf("KV_STORAGE_DIR=%s", GetKVStorageDir()), // Set XDG-compliant storage directory
		// Add go-plugin magic cookies for Python server detection
		"PLUGIN_MAGIC_COOKIE_KEY=BASIC_PLUGIN",
		"BASIC_PLUGIN=hello",
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

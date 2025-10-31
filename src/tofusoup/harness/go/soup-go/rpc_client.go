package main

import (
	"crypto/tls"
	"crypto/x509"
	"encoding/base64"
	"encoding/pem"
	"fmt"
	"net"
	"os"
	"os/exec"
	"strings"

	"github.com/hashicorp/go-hclog"
	"github.com/hashicorp/go-plugin"
)

func newRPCClient(logger hclog.Logger) (*plugin.Client, error) {
	// Create command with environment variables
	serverPath := os.Getenv("PLUGIN_SERVER_PATH")
	if serverPath == "" {
		return nil, fmt.Errorf("PLUGIN_SERVER_PATH environment variable not set")
	}

	cmd := exec.Command(serverPath, "rpc", "kv", "server")
	cmd.Env = append(os.Environ(),
		"PLUGIN_AUTO_MTLS=true",                            // Explicitly enable AutoMTLS for Python server
		fmt.Sprintf("KV_STORAGE_DIR=%s", GetKVStorageDir()), // Set XDG-compliant storage directory
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

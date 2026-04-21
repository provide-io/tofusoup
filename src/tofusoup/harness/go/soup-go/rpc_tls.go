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
	"strings"
	"time"

	"github.com/hashicorp/go-hclog"
)

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
func decodeAndLogCertificate(certPEM string, logger hclog.Logger) error {
	// Simple certificate logging - in production you'd parse and display details
	logger.Debug("🔐📜 Certificate loaded", "length", len(certPEM))
	return nil
}

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

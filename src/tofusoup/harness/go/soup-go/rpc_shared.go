package main

import (
	"context"
	"crypto/sha256"
	"encoding/hex"
	"encoding/json"
	"fmt"
	"os"
	"sync"
	"time"

	"github.com/gofrs/flock"
	"github.com/hashicorp/go-hclog"
	"github.com/hashicorp/go-plugin"
	"google.golang.org/grpc"
	"google.golang.org/grpc/codes"
	"google.golang.org/grpc/peer"
	"google.golang.org/grpc/status"

	"github.com/provide-io/tofusoup/proto/kv"
)

// Handshake is a common handshake that is shared by plugin and host.
var Handshake = plugin.HandshakeConfig{
	ProtocolVersion:  1,
	MagicCookieKey:   "BASIC_PLUGIN",
	MagicCookieValue: "hello",
}

// getEnvOrDefault retrieves environment variable or returns default value
func getEnvOrDefault(key, defaultValue string) string {
	if value := os.Getenv(key); value != "" {
		return value
	}
	return defaultValue
}

// KV is the interface that we're exposing as a plugin.
type KV interface {
	Put(key string, value []byte) error
	Get(key string) ([]byte, error)
}

// KVGRPCPlugin is the implementation of plugin.GRPCPlugin so we can serve/consume this.
type KVGRPCPlugin struct {
	plugin.Plugin
	// Concrete implementation, written in Go.
	Impl KV
}

func (p *KVGRPCPlugin) GRPCClient(ctx context.Context, broker *plugin.GRPCBroker, c *grpc.ClientConn) (interface{}, error) {
	logger := hclog.New(&hclog.LoggerOptions{
		Name:  "🔌🌐 kv-grpc-client",
		Level: hclog.Debug,
	})

	if c == nil {
		logger.Error("🌐❌ received nil gRPC connection")
		return nil, fmt.Errorf("nil gRPC connection")
	}

	logger.Debug("🌐🔄 initializing new gRPC client connection",
		"connection_state", c.GetState().String(),
		"target", c.Target())

	grpcClient := &GRPCClient{
		client: proto.NewKVClient(c),
		logger: logger,
	}

	logger.Debug("🌐✨ GRPCClient wrapper initialized successfully",
		"client_implementation", fmt.Sprintf("%T", grpcClient))
	return grpcClient, nil
}

func (p *KVGRPCPlugin) GRPCServer(broker *plugin.GRPCBroker, s *grpc.Server) error {
	logger := hclog.New(&hclog.LoggerOptions{
		Name:  "🔌📡 kv-grpc-server",
		Level: hclog.Debug,
	})

	logger.Debug("📡🔄 initializing gRPC server registration")

	if p.Impl == nil {
		logger.Warn("📡⚠️ no implementation provided, using default implementation")
		// Use XDG-compliant cache directory
		storageDir := GetKVStorageDir()
		p.Impl = NewKVImpl(logger.Named("kv"), storageDir)
	}

	server := &GRPCServer{
		Impl:      p.Impl,
		logger:    logger,
		startTime: time.Now(),
	}

	proto.RegisterKVServer(s, server)
	logger.Info("📡✅ gRPC server registered successfully",
		"server_type", fmt.Sprintf("%T", server))
	return nil
}

// GRPCClient is an implementation of KV that talks over RPC.
type GRPCClient struct {
	client proto.KVClient
	logger hclog.Logger
}

func (m *GRPCClient) Put(key string, value []byte) error {
	m.logger.Debug("🌐📤 initiating Put request",
		"key", key,
		"value_size", len(value))

	_, err := m.client.Put(context.Background(), &proto.PutRequest{
		Key:   key,
		Value: value,
	})

	if err != nil {
		m.logger.Error("🌐❌ Put request failed",
			"key", key,
			"error", err)
		return err
	}

	m.logger.Debug("🌐✅ Put request completed successfully",
		"key", key)
	return nil
}

func (m *GRPCClient) Get(key string) ([]byte, error) {
	m.logger.Debug("🌐📥 initiating Get request", "key", key)

	resp, err := m.client.Get(context.Background(), &proto.GetRequest{
		Key: key,
	})
	if err != nil {
		m.logger.Error("🌐❌ Get request failed", "key", key, "error", err)
		return nil, err
	}

	m.logger.Debug("🌐✅ Get request completed successfully", "key", key, "value_size", len(resp.Value))
	return resp.Value, nil
}

// GRPCServer is the gRPC server that GRPCClient talks to.
type GRPCServer struct {
	proto.UnimplementedKVServer
	Impl      KV
	logger    hclog.Logger
	startTime time.Time
}

// enrichJSONWithHandshake enriches JSON values with server handshake information.
// If the value is valid JSON object, adds a 'server_handshake' field with connection metadata.
// If not JSON, returns the original bytes unchanged.
func (m *GRPCServer) enrichJSONWithHandshake(ctx context.Context, value []byte) ([]byte, error) {
	// Try to parse as JSON
	var jsonData map[string]interface{}
	if err := json.Unmarshal(value, &jsonData); err != nil {
		// Not JSON or not an object - return original
		m.logger.Debug("Value is not JSON object, storing as-is")
		return value, nil
	}

	// Get peer information from context
	peerInfo, ok := peer.FromContext(ctx)
	endpoint := "unknown"
	if ok && peerInfo.Addr != nil {
		endpoint = peerInfo.Addr.String()
	}

	// Build server handshake information with combo identification
	serverHandshake := map[string]interface{}{
		"endpoint":          endpoint,
		"protocol_version":  getEnvOrDefault("PLUGIN_PROTOCOL_VERSIONS", "1"),
		"tls_mode":          getEnvOrDefault("TLS_MODE", "unknown"),
		"timestamp":         time.Now().UTC().Format(time.RFC3339),
		"received_at":       time.Since(m.startTime).Seconds(),
		// Combo identification
		"server_language": getEnvOrDefault("SERVER_LANGUAGE", "go"),
		"client_language": getEnvOrDefault("CLIENT_LANGUAGE", "unknown"),
		"combo_id":        getEnvOrDefault("COMBO_ID", "unknown"),
	}

	// Add enhanced crypto configuration
	tlsKeyType := os.Getenv("TLS_KEY_TYPE")
	tlsKeySize := os.Getenv("TLS_KEY_SIZE")
	tlsCurve := os.Getenv("TLS_CURVE")

	if tlsKeyType != "" {
		cryptoConfig := map[string]interface{}{
			"key_type": tlsKeyType,
		}

		if tlsKeyType == "rsa" && tlsKeySize != "" {
			// Parse key size as integer
			var keySize int
			fmt.Sscanf(tlsKeySize, "%d", &keySize)
			cryptoConfig["key_size"] = keySize
		} else if tlsKeyType == "ec" && tlsCurve != "" {
			cryptoConfig["curve"] = tlsCurve
			// Map curve to key size for reference
			curveSizes := map[string]int{
				"secp256r1": 256,
				"secp384r1": 384,
				"secp521r1": 521,
			}
			if size, ok := curveSizes[tlsCurve]; ok {
				cryptoConfig["key_size"] = size
			}
		}

		serverHandshake["crypto_config"] = cryptoConfig
	}

	// Add certificate fingerprint if mTLS is enabled
	serverCertPath := os.Getenv("PLUGIN_SERVER_CERT")
	if serverCertPath != "" {
		certData, err := os.ReadFile(serverCertPath)
		if err == nil {
			hash := sha256.Sum256(certData)
			serverHandshake["cert_fingerprint"] = hex.EncodeToString(hash[:])
		} else {
			serverHandshake["cert_fingerprint"] = nil
		}
	} else {
		serverHandshake["cert_fingerprint"] = nil
	}

	// Add server handshake to JSON
	jsonData["server_handshake"] = serverHandshake

	// Marshal back to JSON
	enrichedJSON, err := json.Marshal(jsonData)
	if err != nil {
		m.logger.Warn("Failed to marshal enriched JSON, using original", "error", err)
		return value, nil
	}

	m.logger.Debug("Enriched JSON value with server handshake",
		"original_size", len(value),
		"enriched_size", len(enrichedJSON))
	return enrichedJSON, nil
}

func (m *GRPCServer) Put(ctx context.Context, req *proto.PutRequest) (*proto.Empty, error) {
	m.logger.Debug("📡📤 handling Put request",
		"key", req.Key,
		"value_size", len(req.Value))

	// Store raw value without enrichment (enrichment happens on Get)
	if err := m.Impl.Put(req.Key, req.Value); err != nil {
		m.logger.Error("📡❌ Put operation failed",
			"key", req.Key,
			"error", err)
		return nil, err
	}

	m.logger.Debug("📡✅ Put operation completed successfully",
		"key", req.Key,
		"stored_size", len(req.Value))
	return &proto.Empty{}, nil
}

func (m *GRPCServer) Get(ctx context.Context, req *proto.GetRequest) (*proto.GetResponse, error) {
	m.logger.Debug("📡📥 handling Get request",
		"key", req.Key)

	rawValue, err := m.Impl.Get(req.Key)
	if err != nil {
		// Check if this is a file not found error (key doesn't exist)
		if os.IsNotExist(err) {
			m.logger.Debug("📡📥 key not found",
				"key", req.Key)
			return nil, status.Errorf(codes.NotFound, "key not found: %s", req.Key)
		}
		m.logger.Error("📡❌ Get operation failed",
			"key", req.Key,
			"error", err)
		return nil, err
	}

	// Enrich JSON values with server handshake information on Get
	enrichedValue, err := m.enrichJSONWithHandshake(ctx, rawValue)
	if err != nil {
		m.logger.Error("📡❌ Failed to enrich value",
			"key", req.Key,
			"error", err)
		return nil, err
	}

	m.logger.Debug("📡✅ Get operation completed successfully",
		"key", req.Key,
		"raw_size", len(rawValue),
		"enriched_size", len(enrichedValue))
	return &proto.GetResponse{Value: enrichedValue}, nil
}

// KVImpl provides a simple file-based KV implementation
type KVImpl struct {
	logger     hclog.Logger
	mu         sync.RWMutex
	storageDir string
}

// NewKVImpl creates a new KVImpl with a configurable storage directory
func NewKVImpl(logger hclog.Logger, storageDir string) *KVImpl {
	if storageDir == "" {
		storageDir = GetKVStorageDir()
	}
	logger.Debug("Initializing KVImpl", "storage_dir", storageDir)
	return &KVImpl{
		logger:     logger,
		mu:         sync.RWMutex{},
		storageDir: storageDir,
	}
}

func (k *KVImpl) Put(key string, value []byte) error {
	if key == "" {
		return nil
	}

	filePath := k.storageDir + "/kv-data-" + key
	lock := flock.New(filePath)

	if err := lock.Lock(); err != nil {
		return fmt.Errorf("failed to acquire lock for key %s: %w", key, err)
	}
	defer func() {
		if err := lock.Unlock(); err != nil {
			k.logger.Error("failed to unlock file", "key", key, "error", err)
		}
	}()

	// Write the file
	if err := os.WriteFile(filePath, value, 0644); err != nil {
		return err
	}

	// fsync to ensure data is flushed to disk
	file, err := os.OpenFile(filePath, os.O_WRONLY, 0644)
	if err != nil {
		return err
	}
	defer file.Close()

	if err := file.Sync(); err != nil {
		return err
	}

	return nil
}

func (k *KVImpl) Get(key string) ([]byte, error) {
	k.mu.RLock()
	defer k.mu.RUnlock()

	if key == "" {
		return nil, nil
	}

	k.logger.Debug("🗄️📥 getting value", "key", key)
	filePath := k.storageDir + "/kv-data-" + key
	return os.ReadFile(filePath)
}
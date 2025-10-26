package main

import (
	"context"
	"fmt"
	"os"
	"sync"
	"time"

	"github.com/gofrs/flock"
	"github.com/hashicorp/go-hclog"
	"github.com/hashicorp/go-plugin"
	"google.golang.org/grpc"
	"google.golang.org/grpc/codes"
	"google.golang.org/grpc/status"

	"github.com/provide-io/tofusoup/proto/kv"
)

// Handshake is a common handshake that is shared by plugin and host.
var Handshake = plugin.HandshakeConfig{
	ProtocolVersion:  1,
	MagicCookieKey:   "BASIC_PLUGIN",
	MagicCookieValue: "hello",
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
		// Use environment variable or default to /tmp
		storageDir := os.Getenv("KV_STORAGE_DIR")
		if storageDir == "" {
			storageDir = "/tmp"
		}
		p.Impl = NewKVImpl(logger.Named("kv"), storageDir)
	}

	server := &GRPCServer{
		Impl:   p.Impl,
		logger: logger,
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
	Impl   KV
	logger hclog.Logger
}

func (m *GRPCServer) Put(ctx context.Context, req *proto.PutRequest) (*proto.Empty, error) {
	m.logger.Debug("📡📤 handling Put request",
		"key", req.Key,
		"value_size", len(req.Value))

	if err := m.Impl.Put(req.Key, req.Value); err != nil {
		m.logger.Error("📡❌ Put operation failed",
			"key", req.Key,
			"error", err)
		return nil, err
	}

	m.logger.Debug("📡✅ Put operation completed successfully",
		"key", req.Key)
	return &proto.Empty{}, nil
}

func (m *GRPCServer) Get(ctx context.Context, req *proto.GetRequest) (*proto.GetResponse, error) {
	m.logger.Debug("📡📥 handling Get request",
		"key", req.Key)

	v, err := m.Impl.Get(req.Key)
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

	m.logger.Debug("📡✅ Get operation completed successfully",
		"key", req.Key,
		"value_size", len(v))
	return &proto.GetResponse{Value: v}, nil
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
		storageDir = "/tmp"
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

	// Use a timeout for locking to prevent indefinite blocking
	ctx, cancel := context.WithTimeout(context.Background(), 10*time.Second)
	defer cancel()

	locked, err := lock.TryLockContext(ctx, 100*time.Millisecond)
	if err != nil {
		k.logger.Error("failed to acquire file lock", "key", key, "error", err)
		return fmt.Errorf("failed to acquire lock for key %s: %w", key, err)
	}
	if !locked {
		k.logger.Error("could not acquire file lock in time", "key", key)
		return fmt.Errorf("could not acquire lock for key %s in time", key)
	}
	defer lock.Unlock()

	k.logger.Debug("🗄️📤 putting value",
		"key", key,
		"value_length", len(value))

	// Write the file
	if err := os.WriteFile(filePath, value, 0644); err != nil {
		k.logger.Error("failed to write file", "key", key, "error", err)
		return err
	}

	// fsync to ensure data is flushed to disk
	file, err := os.OpenFile(filePath, os.O_WRONLY, 0644)
	if err != nil {
		k.logger.Error("failed to open file for fsync", "key", key, "error", err)
		return err
	}
	defer file.Close()

	if err := file.Sync(); err != nil {
		k.logger.Error("failed to fsync file", "key", key, "error", err)
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
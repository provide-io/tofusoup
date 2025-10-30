package main

import (
	"os"
	"path/filepath"
)

// GetCacheDir returns the XDG-compliant cache directory for tofusoup.
// Respects XDG_CACHE_HOME environment variable if set, otherwise defaults
// to ~/.cache/tofusoup
func GetCacheDir() string {
	// First check if XDG_CACHE_HOME is set
	if xdgCache := os.Getenv("XDG_CACHE_HOME"); xdgCache != "" {
		return filepath.Join(xdgCache, "tofusoup")
	}

	// Fall back to ~/.cache/tofusoup
	homeDir, err := os.UserHomeDir()
	if err != nil {
		// If we can't determine home directory, fall back to /tmp
		// This should rarely happen, but provides a safe fallback
		return "/tmp/tofusoup-cache"
	}

	return filepath.Join(homeDir, ".cache", "tofusoup")
}

// GetKVStorageDir returns the directory for KV storage.
// Checks KV_STORAGE_DIR environment variable first, then falls back
// to XDG cache directory.
func GetKVStorageDir() string {
	// First check if KV_STORAGE_DIR is explicitly set (for backward compatibility)
	if storageDir := os.Getenv("KV_STORAGE_DIR"); storageDir != "" {
		return storageDir
	}

	// Fall back to XDG cache directory
	return filepath.Join(GetCacheDir(), "kv-store")
}

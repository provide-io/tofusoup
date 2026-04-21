package main

import (
	"os"
	"path/filepath"
	"runtime"
)

// GetCacheDir returns the XDG-compliant cache directory for tofusoup.
// Priority (highest to lowest):
// 1. TOFUSOUP_CACHE_DIR environment variable (explicit override)
// 2. XDG_CACHE_HOME environment variable (XDG standard)
// 3. Platform-specific defaults (macOS, Linux, Windows)
// 4. System temp directory (last resort)
func GetCacheDir() string {
	// Check explicit override first
	if cacheDir := os.Getenv(EnvTofuSoupCacheDir); cacheDir != "" {
		return cacheDir
	}

	// Platform-specific logic
	switch runtime.GOOS {
	case "darwin":
		// macOS: ~/Library/Caches/tofusoup
		if home := os.Getenv(EnvHome); home != "" {
			return filepath.Join(home, MacOSCacheParent, MacOSCacheSubdir, AppName)
		}
	case "linux":
		// Linux: Check XDG_CACHE_HOME first
		if xdgCache := os.Getenv(EnvXDGCacheHome); xdgCache != "" {
			return filepath.Join(xdgCache, AppName)
		}
		// Fall back to ~/.cache/tofusoup (XDG default)
		if home := os.Getenv(EnvHome); home != "" {
			return filepath.Join(home, XDGCacheSubdir, AppName)
		}
	case "windows":
		// Windows: %LOCALAPPDATA%\tofusoup\cache
		if localAppData := os.Getenv(EnvLocalAppData); localAppData != "" {
			return filepath.Join(localAppData, AppName, CacheDirName)
		}
	}

	// Last resort: use system temp directory
	return filepath.Join(os.TempDir(), AppName, CacheDirName)
}

// GetKVStorageDir returns the directory for KV storage.
// Priority (highest to lowest):
// 1. KV_STORAGE_DIR environment variable (explicit override, for backward compatibility)
// 2. Subdirectory within cache directory
func GetKVStorageDir() string {
	// Check explicit override first (backward compatibility)
	if storageDir := os.Getenv(EnvKVStorageDir); storageDir != "" {
		return storageDir
	}

	// Use cache directory as base
	return filepath.Join(GetCacheDir(), KVStoreDirName)
}

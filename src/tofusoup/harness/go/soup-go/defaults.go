package main

// =================================
// Application constants
// =================================
const (
	// AppName is the application identifier used in paths
	AppName = "tofusoup"

	// CacheDirName is the cache subdirectory name
	CacheDirName = "cache"

	// KVStoreDirName is the KV storage subdirectory name
	KVStoreDirName = "kv-store"

	// HarnessesDirName is the harness binaries subdirectory name
	HarnessesDirName = "harnesses"

	// LogsDirName is the logs subdirectory name
	LogsDirName = "logs"
)

// =================================
// XDG path components (Linux standard)
// =================================
const (
	// XDGCacheSubdir is the standard XDG cache location relative to HOME
	XDGCacheSubdir = ".cache"
)

// =================================
// Environment variable names
// =================================
const (
	// EnvTofuSoupCacheDir is the explicit cache directory override
	EnvTofuSoupCacheDir = "TOFUSOUP_CACHE_DIR"

	// EnvXDGCacheHome is the XDG standard cache home directory
	EnvXDGCacheHome = "XDG_CACHE_HOME"

	// EnvKVStorageDir is the KV storage directory override
	EnvKVStorageDir = "KV_STORAGE_DIR"

	// EnvHome is the user home directory (Unix)
	EnvHome = "HOME"

	// EnvLocalAppData is the local app data directory (Windows)
	EnvLocalAppData = "LOCALAPPDATA"
)

// =================================
// Platform-specific path components
// =================================
const (
	// MacOSCacheParent is the macOS cache parent directory
	MacOSCacheParent = "Library"

	// MacOSCacheSubdir is the macOS cache subdirectory
	MacOSCacheSubdir = "Caches"
)

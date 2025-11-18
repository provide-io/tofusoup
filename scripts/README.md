# TofuSoup Scripts

This directory contains utility scripts for TofuSoup development and deployment.

## Container Management

### `workenv-container.sh`

Comprehensive Docker container management for TofuSoup workenv development.

**Usage:**
```bash
# Build container image
./scripts/workenv-container.sh build

# Start container (creates if doesn't exist)
./scripts/workenv-container.sh start

# Enter running container
./scripts/workenv-container.sh enter

# Show container status
./scripts/workenv-container.sh status

# Stop container
./scripts/workenv-container.sh stop

# Clean up everything
./scripts/workenv-container.sh clean

# Rebuild from scratch
./scripts/workenv-container.sh rebuild
```

**Features:**
- 🐳 Persistent container management (`tofusoup-workenv`)
- 🔨 Smart image building with cache options
- 🚀 Automatic container start/enter workflow
- 📊 Detailed status reporting
- 🧹 Complete cleanup capabilities
- 🎨 Colorized output with emojis

**Options:**
- `--no-cache`: Build without Docker cache
- `--shell SHELL`: Specify shell to use (default: zsh)
- `--verbose`: Enable verbose output

### `workenv-setup.sh`

Container initialization script that sets up the complete TofuSoup workenv environment.

**Usage:**
```bash
# Run setup inside container
./scripts/workenv-setup.sh
```

**What it does:**
1. 🔍 Detects platform (OS/architecture)
2. ⚡ Installs UV Python package manager
3. 🧰 Sets up TofuSoup development environment
4. ✅ Verifies workenv CLI integration
5. 📊 Shows initial tool status
6. 🔗 Creates helpful shell aliases
7. 📖 Displays usage examples

**Created Aliases:**
- `workenv` → `soup workenv`
- `tf-install` → `soup workenv terraform`
- `tofu-install` → `soup workenv tofu`
- `go-install` → `soup workenv go`
- `uv-install` → `soup workenv uv`
- `workenv-status` → `soup workenv status`
- `workenv-sync` → `soup workenv sync`

## Integration with TofuSoup CLI

The container functionality can also be accessed through the TofuSoup CLI:

```bash
# Future integration (planned)
soup workenv container start
soup workenv container enter
soup workenv container status
soup workenv container clean
```

## Migration from `/app/play.sh`

This refactored structure replaces the monolithic `/app/play.sh` with:

### Benefits
- **Modular Design**: Separate container management and setup concerns
- **Better UX**: Colorized output, emojis, clear status reporting
- **Robust Error Handling**: Comprehensive error checking and recovery
- **Documentation**: Self-documenting help and usage examples
- **Integration Ready**: Designed for TofuSoup CLI integration
- **Cross-platform**: Platform-aware setup and configuration

### Backwards Compatibility
The original `play.sh` functionality is preserved:
- `./scripts/workenv-container.sh start` replaces `./play.sh`
- Same persistent container behavior
- Enhanced with better error handling and status reporting

## Development Workflow

### First Time Setup
```bash
# Build and start container
./scripts/workenv-container.sh build
./scripts/workenv-container.sh start

# Inside container, run setup
./scripts/workenv-setup.sh

# Start installing tools
soup workenv terraform --latest
soup workenv tofu --latest
soup workenv go --latest
soup workenv uv --latest
```

### Daily Development
```bash
# Enter existing container
./scripts/workenv-container.sh enter

# Check status
workenv-status

# Install specific versions
tf-install 1.5.0
tofu-install 1.6.0
```

### Cleanup
```bash
# Stop container
./scripts/workenv-container.sh stop

# Complete cleanup
./scripts/workenv-container.sh clean
```

## Container Specifications

**Base Image:** `ubuntu:latest`

**Installed Tools:**
- Go (version configurable via ENV)
- UV Python package manager (installed by setup script)
- TofuSoup with workenv CLI
- Standard development tools (git, curl, wget, build-essential)

**Volume Mounts:**
- `/app` → TofuSoup monorepo root
- Working directory: `/app/tofusoup`

**Environment:**
- Platform-specific virtual environments (`.venv_linux_amd64`, etc.)
- Proper PATH configuration for installed tools
- Shell aliases for common operations

## Troubleshooting

**Container won't start:**
```bash
./scripts/workenv-container.sh status
./scripts/workenv-container.sh rebuild
```

**TofuSoup CLI not available:**
```bash
# Inside container
source /app/tofusoup/env.sh
# or
activate-workenv
```

**Tools not installing:**
```bash
soup workenv status
soup workenv config show
```
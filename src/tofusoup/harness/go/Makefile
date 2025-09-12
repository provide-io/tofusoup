# Makefile for TofuSoup Go Harnesses
# Builds test harnesses for conformance testing

.PHONY: all clean build soup-go go-cty go-hcl go-wire go-rpc help

# Configuration
PROJECT_ROOT ?= $(shell cd ../../../.. && pwd)
BIN_DIR ?= $(PROJECT_ROOT)/bin
BUILD_FLAGS ?= -v
GO ?= go

# Default target
all: build

# Build all harnesses
build: soup-go

# Build soup-go harness
soup-go:
	@echo "🔨 Building soup-go harness..."
	@mkdir -p $(BIN_DIR)
	@cd soup-go && $(GO) build $(BUILD_FLAGS) -o $(BIN_DIR)/soup-go .
	@echo "✅ soup-go built to $(BIN_DIR)/soup-go"

# Build go-cty harness (placeholder)
go-cty:
	@echo "🔨 Building go-cty harness..."
	@mkdir -p $(BIN_DIR)
	@echo "⚠️  go-cty not yet implemented"

# Build go-hcl harness (placeholder)
go-hcl:
	@echo "🔨 Building go-hcl harness..."
	@mkdir -p $(BIN_DIR)
	@echo "⚠️  go-hcl not yet implemented"

# Build go-wire harness (placeholder)
go-wire:
	@echo "🔨 Building go-wire harness..."
	@mkdir -p $(BIN_DIR)
	@echo "⚠️  go-wire not yet implemented"

# Build go-rpc harness (use existing)
go-rpc:
	@echo "🔨 go-rpc binary already exists at $(BIN_DIR)/go-rpc"

# Clean built binaries
clean:
	@echo "🧹 Cleaning harness binaries..."
	@rm -f $(BIN_DIR)/soup-go
	@rm -f $(BIN_DIR)/go-cty
	@rm -f $(BIN_DIR)/go-hcl
	@rm -f $(BIN_DIR)/go-wire
	@echo "✅ Harness binaries cleaned"

# Show help
help:
	@echo "TofuSoup Go Harnesses - Makefile"
	@echo ""
	@echo "Usage: make [target]"
	@echo ""
	@echo "Targets:"
	@echo "  all       Build all harnesses (default)"
	@echo "  build     Build all harnesses"
	@echo "  soup-go   Build soup-go harness"
	@echo "  go-cty    Build go-cty harness"
	@echo "  go-hcl    Build go-hcl harness"
	@echo "  go-wire   Build go-wire harness"
	@echo "  go-rpc    Build go-rpc harness"
	@echo "  clean     Remove built binaries"
	@echo "  help      Show this help message"
	@echo ""
	@echo "Environment variables:"
	@echo "  PROJECT_ROOT  Project root directory (auto-detected)"
	@echo "  BIN_DIR       Output directory for binaries (default: PROJECT_ROOT/bin)"
	@echo "  BUILD_FLAGS   Go build flags (default: -v)"
	@echo "  GO            Go compiler (default: go)"
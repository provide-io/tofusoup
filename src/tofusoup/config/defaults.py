#
# SPDX-FileCopyrightText: Copyright (c) 2025 provide.io llc. All rights reserved.
# SPDX-License-Identifier: Apache-2.0
#

"""Centralized defaults and constants for TofuSoup.

All hardcoded defaults should be defined here instead of inline in the code."""

DEFAULT_GRPC_PORT = 50051
DEFAULT_GRPC_ADDRESS = "localhost:50051"
CONNECTION_TIMEOUT = 30.0
REQUEST_TIMEOUT = 5.0

# Test configuration
TEST_TIMEOUT_SECONDS = 300
MATRIX_TIMEOUT_MINUTES = 30
MATRIX_PARALLEL_JOBS = 4
STIR_TEST_SECRET = "stir-test-secret"

# Logging
LOG_LEVELS = ["NOTSET", "TRACE", "DEBUG", "INFO", "WARNING", "ERROR", "CRITICAL"]

# Registry configuration
TERRAFORM_REGISTRY_URL = "https://registry.terraform.io"
OPENTOFU_REGISTRY_URL = "https://registry.opentofu.org"

# Cache configuration
CACHE_MAX_SIZE = 100
CACHE_TTL_SECONDS = 3600

# File defaults
DEFAULT_TFSTATE_FILE = "terraform.tfstate"
DEFAULT_OUTPUT_FORMAT = "json"

# CLI defaults
DEFAULT_REGISTRY_SOURCE = "both"
DEFAULT_TLS_MODE = "none"
DEFAULT_CLIENT_LANGUAGE = "python"

# Environment variables
ENV_TOFUSOUP_LOG_LEVEL = "TOFUSOUP_LOG_LEVEL"
ENV_TOFUSOUP_TEST_TIMEOUT = "TOFUSOUP_TEST_TIMEOUT"
ENV_TF_LOG = "TF_LOG"
ENV_TF_DATA_DIR = "TF_DATA_DIR"
ENV_WORKENV_PROFILE = "WORKENV_PROFILE"
ENV_PYVIDER_PRIVATE_STATE_SHARED_SECRET = "PYVIDER_PRIVATE_STATE_SHARED_SECRET"
ENV_KV_STORAGE_DIR = "KV_STORAGE_DIR"

# GRPC environment variables
ENV_GRPC_DEFAULT_CLIENT_CERTIFICATE_PATH = "GRPC_DEFAULT_CLIENT_CERTIFICATE_PATH"
ENV_GRPC_DEFAULT_CLIENT_PRIVATE_KEY_PATH = "GRPC_DEFAULT_CLIENT_PRIVATE_KEY_PATH"
ENV_GRPC_DEFAULT_SSL_ROOTS_FILE_PATH = "GRPC_DEFAULT_SSL_ROOTS_FILE_PATH"

# TUI configuration
TUI_SERVICE_NAME = "tofusoup-tui"
TUI_LOG_LEVEL = "DEBUG"

# Soup configuration paths
CONFIG_FILENAME = "soup.toml"
DEFAULT_CONFIG_SUBDIR = "soup"

# 🥣🔬🔚

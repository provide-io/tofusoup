#!/bin/bash
#
# env.sh - tofusoup Development Environment Setup
#
# This script sets up a clean, isolated development environment for tofusoup
# using 'uv' for high-performance virtual environment and dependency management.
#
# Usage: source ./env.sh
#

# --- Configuration ---
COLOR_BLUE='\033[0;34m'
COLOR_GREEN='\033[0;32m'
COLOR_YELLOW='\033[0;33m'
COLOR_RED='\033[0;31m'
COLOR_NC='\033[0m'

# Spinner animation for long operations
spinner() {
    local pid=$1
    local delay=0.1
    local spinstr='⠋⠙⠹⠸⠼⠴⠦⠧⠇⠏'
    while ps -p $pid > /dev/null 2>&1; do
        local temp=${spinstr#?}
        printf " [%c]  " "$spinstr"
        local spinstr=$temp${spinstr%"$temp"}
        sleep $delay
        printf "\b\b\b\b\b\b"
    done
    printf "    \b\b\b\b"
}
print_header() {
    echo -e "\n${COLOR_BLUE}--- ${1} ---${COLOR_NC}"
}

print_success() {
    echo -e "${COLOR_GREEN}✅ ${1}${COLOR_NC}"
}

print_error() {
    echo -e "${COLOR_RED}❌ ${1}${COLOR_NC}"
}

print_warning() {
    echo -e "${COLOR_YELLOW}⚠️  ${1}${COLOR_NC}"
}
# --- Cleanup Previous Environment ---
print_header "🧹 Cleaning Previous Environment"

# Remove any existing Python aliases
unalias python 2>/dev/null
unalias python3 2>/dev/null
unalias pip 2>/dev/null
unalias pip3 2>/dev/null

# Clear existing PYTHONPATH
unset PYTHONPATH

# Store original PATH for restoration if needed
ORIGINAL_PATH="${PATH}"

print_success "Cleared Python aliases and PYTHONPATH"
# --- Project Validation ---
if [ ! -f "pyproject.toml" ]; then
    print_error "No 'pyproject.toml' found in current directory"
    echo "Please run this script from the tofusoup root directory"
    return 1 2>/dev/null || exit 1
fi

PROJECT_NAME=$(basename "$(pwd)")

# --- UV Installation ---
print_header "🚀 Checking UV Package Manager"

if ! command -v uv &> /dev/null; then
    echo "Installing UV..."
    curl -LsSf https://astral.sh/uv/install.sh | sh > /tmp/uv_install.log 2>&1 &
    spinner $!
    
    UV_ENV_PATH_LOCAL="$HOME/.local/bin/env"
    UV_ENV_PATH_CARGO="$HOME/.cargo/env"
    
    if [ -f "$UV_ENV_PATH_LOCAL" ]; then
        source "$UV_ENV_PATH_LOCAL"
    elif [ -f "$UV_ENV_PATH_CARGO" ]; then
        source "$UV_ENV_PATH_CARGO"
    fi
    
    if command -v uv &> /dev/null; then
        print_success "UV installed successfully"
    else
        print_error "UV installation failed. Check /tmp/uv_install.log"
        return 1 2>/dev/null || exit 1
    fi
else
    print_success "UV already installed"
fi
# --- Platform Detection ---
TFOS=$(uname -s | tr '[:upper:]' '[:lower:]')
TFARCH=$(uname -m)
case "$TFARCH" in
    x86_64) TFARCH="amd64" ;;
    aarch64|arm64) TFARCH="arm64" ;;
esac

# Workenv directory setup
PROFILE="${TOFUSOUP_PROFILE:-default}"
if [ "$PROFILE" = "default" ]; then
    VENV_DIR="workenv/tofusoup_${TFOS}_${TFARCH}"
else
    VENV_DIR="workenv/${PROFILE}_${TFOS}_${TFARCH}"
fi

# Validate platform
if [[ "$TFOS" != "darwin" && "$TFOS" != "linux" ]]; then
    print_warning "Detected OS: $TFOS (only darwin and linux are fully tested)"
fi

# Set UV project environment early so uv commands use the correct venv
export UV_PROJECT_ENVIRONMENT="${VENV_DIR}"
# --- Virtual Environment ---
print_header "🐍 Setting Up Virtual Environment"
echo "Directory: ${VENV_DIR}"

if [ -d "${VENV_DIR}" ] && [ -f "${VENV_DIR}/bin/activate" ] && [ -f "${VENV_DIR}/bin/python" ]; then
    print_success "Virtual environment exists"
else
    echo -n "Creating virtual environment..."
    uv venv "${VENV_DIR}" > /tmp/uv_venv.log 2>&1 &
    spinner $!
    print_success "Virtual environment created"
fi

# Activate virtual environment
source "${VENV_DIR}/bin/activate"
export VIRTUAL_ENV="$(pwd)/${VENV_DIR}"
export UV_PROJECT_ENVIRONMENT="${VENV_DIR}"
# --- Dependency Installation ---
print_header "📦 Installing Dependencies"

# Create log directory
mkdir -p /tmp/tofusoup_setup

echo -n "Syncing dependencies..."
uv sync --all-groups > /tmp/tofusoup_setup/sync.log 2>&1 &
SYNC_PID=$!
spinner $SYNC_PID
wait $SYNC_PID
SYNC_EXIT_CODE=$?

if [ $SYNC_EXIT_CODE -eq 0 ]; then
    print_success "Dependencies synced"
else
    print_warning "Dependency sync failed - will install project and siblings manually"
    echo "Check /tmp/tofusoup_setup/sync.log for details"
    
    # Try to install just the project without dependencies first
    echo -n "Installing tofusoup without dependencies..."
    uv pip install --no-deps -e . > /tmp/tofusoup_setup/install_nodeps.log 2>&1 &
    INSTALL_PID=$!
    spinner $INSTALL_PID
    wait $INSTALL_PID
    if [ $? -eq 0 ]; then
        print_success "tofusoup installed (no deps)"
    else
        print_error "Failed to install tofusoup"
        return 1 2>/dev/null || exit 1
    fi
fi

echo -n "Installing tofusoup in editable mode..."
uv pip install --no-deps -e . > /tmp/tofusoup_setup/install.log 2>&1 &
spinner $!
print_success "tofusoup installed"
# --- Sibling Packages ---
print_header "🤝 Installing Sibling Packages"

PARENT_DIR=$(dirname "$(pwd)")
SIBLING_COUNT=0

# New unified siblings configuration
# Sibling with configuration
# Pattern-based sibling
for dir in "${PARENT_DIR}"/pyvider-*; do
    if [ -d "${dir}" ]; then
        SIBLING_NAME=$(basename "${dir}")
        echo -n "Installing ${SIBLING_NAME} with dependencies..."
        # If with_deps is true, first try normal install, then fallback to local-only
        uv pip install -e "${dir}" > /tmp/tofusoup_setup/${SIBLING_NAME}.log 2>&1 &
        INSTALL_PID=$!
        spinner $INSTALL_PID
        wait $INSTALL_PID
        if [ $? -ne 0 ]; then
            echo -n " Retrying with local version only..."
            uv pip install --force-reinstall --no-deps -e "${dir}" > /tmp/tofusoup_setup/${SIBLING_NAME}_local.log 2>&1 &
            INSTALL_PID=$!
            spinner $INSTALL_PID
            wait $INSTALL_PID
            if [ $? -eq 0 ]; then
                print_success "${SIBLING_NAME} installed (local, no deps)"
                print_warning "Some dependencies may be missing - check /tmp/tofusoup_setup/${SIBLING_NAME}.log"
            else
                print_error "${SIBLING_NAME} installation failed"
            fi
        else
            print_success "${SIBLING_NAME} installed"
        fi
        ((SIBLING_COUNT++))
    fi
done
# Sibling with configuration
# Explicit sibling
flavor_DIR="${PARENT_DIR}/flavor"
if [ -d "${FLAVOR_DIR}" ]; then
    echo -n "Installing flavor with dependencies..."
    uv pip install -e "${FLAVOR_DIR}" > /tmp/tofusoup_setup/flavor.log 2>&1 &
    INSTALL_PID=$!
    spinner $INSTALL_PID
    wait $INSTALL_PID
    if [ $? -ne 0 ]; then
        echo -n " Retrying with local version only..."
        uv pip install --force-reinstall --no-deps -e "${FLAVOR_DIR}" > /tmp/tofusoup_setup/flavor_local.log 2>&1 &
        INSTALL_PID=$!
        spinner $INSTALL_PID
        wait $INSTALL_PID
        if [ $? -eq 0 ]; then
            print_success "flavor installed (local, no deps)"
            print_warning "Some dependencies may be missing - check /tmp/tofusoup_setup/flavor.log"
        else
            print_error "flavor installation failed"
        fi
    else
        print_success "flavor installed"
    fi
    ((SIBLING_COUNT++))
fi
# Sibling with configuration
# Explicit sibling
wrkenv_DIR="${PARENT_DIR}/wrkenv"
if [ -d "${WRKENV_DIR}" ]; then
    echo -n "Installing wrkenv with dependencies..."
    uv pip install -e "${WRKENV_DIR}" > /tmp/tofusoup_setup/wrkenv.log 2>&1 &
    INSTALL_PID=$!
    spinner $INSTALL_PID
    wait $INSTALL_PID
    if [ $? -ne 0 ]; then
        echo -n " Retrying with local version only..."
        uv pip install --force-reinstall --no-deps -e "${WRKENV_DIR}" > /tmp/tofusoup_setup/wrkenv_local.log 2>&1 &
        INSTALL_PID=$!
        spinner $INSTALL_PID
        wait $INSTALL_PID
        if [ $? -eq 0 ]; then
            print_success "wrkenv installed (local, no deps)"
            print_warning "Some dependencies may be missing - check /tmp/tofusoup_setup/wrkenv.log"
        else
            print_error "wrkenv installation failed"
        fi
    else
        print_success "wrkenv installed"
    fi
    ((SIBLING_COUNT++))
fi


if [ $SIBLING_COUNT -eq 0 ]; then
    print_warning "No sibling packages found"
fi
# --- Environment Configuration ---
print_header "🔧 Configuring Environment"

# Set clean PYTHONPATH
export PYTHONPATH="${PWD}/src:${PWD}"
echo "PYTHONPATH: ${PYTHONPATH}"

# Clean up PATH - remove duplicates
# Ensure UV bin directories are included
UV_BIN_PATHS="$HOME/.local/bin:$HOME/.cargo/bin"
NEW_PATH="${VENV_DIR}/bin:${UV_BIN_PATHS}"
OLD_IFS="$IFS"
IFS=':'
for p in $PATH; do
    case ":$NEW_PATH:" in
        *":$p:"*) ;;
        *) NEW_PATH="$NEW_PATH:$p" ;;
    esac
done
IFS="$OLD_IFS"
export PATH="$NEW_PATH"

# --- Tool Verification ---
print_header "🔍 Verifying Installation"

echo -e "\n${COLOR_GREEN}Tool Locations & Versions:${COLOR_NC}"
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"

# Python
if command -v python &> /dev/null; then
    PYTHON_PATH=$(command -v python 2>/dev/null || which python 2>/dev/null || echo "python")
    printf "%-12s: %s\n" "Python" "$PYTHON_PATH"
    printf "%-12s  %s\n" "" "$(python --version 2>&1)"
fi

# UV
if command -v uv &> /dev/null; then
    UV_PATH=$(command -v uv 2>/dev/null || which uv 2>/dev/null || echo "uv")
    printf "%-12s: %s\n" "UV" "$UV_PATH"
    printf "%-12s  %s\n" "" "$(uv --version 2>&1)"
fi

# wrkenv
if command -v wrkenv &> /dev/null; then
    WRKENV_PATH=$(command -v wrkenv 2>/dev/null || which wrkenv 2>/dev/null || echo "wrkenv")
    printf "%-12s: %s\n" "wrkenv" "$WRKENV_PATH"
    printf "%-12s  %s\n" "" "$(wrkenv --version 2>&1 || echo 'No version info')"
fi

# ibmtf
if command -v ibmtf &> /dev/null; then
    IBMTF_PATH=$(command -v ibmtf 2>/dev/null || which ibmtf 2>/dev/null || echo "ibmtf")
    printf "%-12s: %s\n" "ibmtf" "$IBMTF_PATH"
    printf "%-12s  %s\n" "" "$(ibmtf version 2>&1 | head -1 || echo 'Not installed')"
fi

# tofu
if command -v tofu &> /dev/null; then
    TOFU_PATH=$(command -v tofu 2>/dev/null || which tofu 2>/dev/null || echo "tofu")
    printf "%-12s: %s\n" "tofu" "$TOFU_PATH"
    printf "%-12s  %s\n" "" "$(tofu version 2>&1 | head -1 || echo 'Not installed')"
fi


echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
# --- Final Summary ---
print_header "✅ Environment Ready!"

echo -e "\n${COLOR_GREEN}tofusoup development environment activated${COLOR_NC}"
echo "Virtual environment: ${VENV_DIR}"
echo "Profile: ${PROFILE}"
echo -e "\nUseful commands:"
echo "  tofusoup --help  # tofusoup CLI"
echo "  wrkenv status  # Check tool versions"
echo "  wrkenv container status  # Container status"
echo "  pytest  # Run tests"
echo "  deactivate  # Exit environment"

# --- Cleanup ---
# Remove temporary log files older than 1 day
find /tmp/tofusoup_setup -name "*.log" -mtime +1 -delete 2>/dev/null

# Return success
return 0 2>/dev/null || exit 0
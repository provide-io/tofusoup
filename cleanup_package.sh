#!/bin/bash
# cleanup_package.sh - Remove temporary/generated files for a clean package
# This script removes all non-essential files that shouldn't be in a clean source distribution

set -e  # Exit on error

echo "🧹 Cleaning up TofuSoup package..."

# Function to safely remove files/directories
safe_remove() {
    if [ -e "$1" ]; then
        echo "  Removing: $1"
        rm -rf "$1"
    fi
}

# Remove all .DS_Store files (macOS metadata)
echo "📁 Removing .DS_Store files..."
find . -name ".DS_Store" -type f -delete 2>/dev/null || true

# Remove test/debug artifacts
echo "🧪 Removing test/debug artifacts..."
safe_remove "MagicMock"
safe_remove "output"
safe_remove "soup/output/harness_runs"
safe_remove "debug_harnesses/terraform.tfstate"

# Remove all terraform.tfstate files
echo "🏗️  Removing terraform.tfstate files..."
find . -name "terraform.tfstate" -type f -delete 2>/dev/null || true
find . -name "terraform.tfstate.backup" -type f -delete 2>/dev/null || true
find . -name ".terraform.lock.hcl" -type f -delete 2>/dev/null || true

# Remove log files
echo "📝 Removing log files..."
safe_remove "conformance/rpc/server.log"
safe_remove "wrkenv.log"
find . -name "*.log" -type f -delete 2>/dev/null || true

# Remove generated test fixtures
echo "🔧 Removing generated test fixtures..."
safe_remove "tests/fixtures/generated/tfwire_compare"

# Remove Python cache directories
echo "🐍 Removing Python cache..."
find . -name "__pycache__" -type d -exec rm -rf {} + 2>/dev/null || true
find . -name "*.pyc" -type f -delete 2>/dev/null || true
find . -name "*.pyo" -type f -delete 2>/dev/null || true

# Remove pytest cache
echo "🧪 Removing pytest cache..."
safe_remove ".pytest_cache"

# Remove coverage data
echo "📊 Removing coverage data..."
safe_remove ".coverage"
safe_remove "htmlcov"
find . -name "coverage.xml" -type f -delete 2>/dev/null || true

# Remove virtual environments (if any)
echo "🌍 Removing virtual environments..."
safe_remove "venv"
safe_remove ".venv"
safe_remove "env"
safe_remove ".env"

# Remove build artifacts
echo "🏗️  Removing build artifacts..."
safe_remove "build"
safe_remove "dist"
safe_remove "*.egg-info"
find . -name "*.egg-info" -type d -exec rm -rf {} + 2>/dev/null || true

# Remove editor/IDE files
echo "💻 Removing editor/IDE files..."
safe_remove ".idea"
safe_remove ".vscode"
find . -name "*.swp" -type f -delete 2>/dev/null || true
find . -name "*.swo" -type f -delete 2>/dev/null || true
find . -name "*~" -type f -delete 2>/dev/null || true



# Remove empty directories
echo "📁 Removing empty directories..."
find . -type d -empty -delete 2>/dev/null || true

# Summary
echo ""
echo "✅ Cleanup complete!"
echo ""
echo "The following should remain:"
echo "  - Source code (src/)"
echo "  - Tests (tests/) - except generated fixtures"
echo "  - Documentation (*.md, docs/)"
echo "  - Configuration files (*.toml, *.ini, env.sh)"
echo "  - Scripts and tools (scripts/, bin/)"
echo "  - Static resources (keys/, features/, stubs/, direct/)"
echo "  - Git files (.git/, .gitignore)"
echo "  - GitHub workflows (.github/)"
echo ""
echo "Run 'git status' to see what was removed."
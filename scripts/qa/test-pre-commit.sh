#!/bin/bash
set -e

echo "🧪 Testing pre-commit configuration..."

# Function to print test status
print_status() {
    if [ $? -eq 0 ]; then
        echo "✅ $1 - PASSED"
    else
        echo "❌ $1 - FAILED"
        return 1
    fi
}

# Test 1: Check if ruff is available and configuration is valid
echo "📋 Test 1: Ruff configuration validation"
~/.local/bin/ruff check --version > /dev/null 2>&1
print_status "Ruff binary available"

~/.local/bin/ruff check src/ --dry-run > /dev/null 2>&1
print_status "Ruff configuration valid"

# Test 2: Check if YAML files are valid
echo "📋 Test 2: YAML configuration validation"
python3 -c "import yaml; yaml.safe_load(open('.pre-commit-config.yaml'))" 2>/dev/null
print_status "Pre-commit YAML valid"

python3 -c "import yaml; yaml.safe_load(open('docker-compose.yml'))" 2>/dev/null
print_status "Docker Compose YAML valid"

# Test 3: Check TOML configuration
echo "📋 Test 3: TOML configuration validation"
python3 -c "import tomllib; tomllib.load(open('pyproject.toml', 'rb'))" 2>/dev/null
print_status "pyproject.toml valid"

# Test 4: Test secrets baseline
echo "📋 Test 4: Secrets detection configuration"
if [ -f ".secrets.baseline" ]; then
    python3 -c "import json; json.load(open('.secrets.baseline'))" 2>/dev/null
    print_status "Secrets baseline valid"
else
    echo "⚠️  Secrets baseline not found (will be created on first run)"
fi

# Test 5: Check if pre-commit config has required hooks
echo "📋 Test 5: Pre-commit hooks validation"
required_hooks=("ruff" "ruff-format" "trailing-whitespace" "check-json")
for hook in "${required_hooks[@]}"; do
    if grep -q "$hook" .pre-commit-config.yaml; then
        echo "✅ Hook '$hook' configured"
    else
        echo "❌ Hook '$hook' missing"
        exit 1
    fi
done

# Test 6: Dockerfile exists for docker hooks
echo "📋 Test 6: Docker configuration"
if [ -f "Dockerfile" ]; then
    echo "✅ Dockerfile found"
else
    echo "❌ Dockerfile missing"
    exit 1
fi

echo ""
echo "🎉 All pre-commit configuration tests passed!"
echo ""
echo "Next steps:"
echo "1. Install pre-commit: pip install pre-commit (or uv add --dev pre-commit)"
echo "2. Install hooks: pre-commit install"
echo "3. Run hooks: pre-commit run --all-files"
echo ""
echo "For detailed setup instructions, see: .pre-commit-setup.md"
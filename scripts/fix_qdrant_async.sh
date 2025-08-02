#!/bin/bash

# Script to fix Qdrant adapter async issues

echo "Fixing Qdrant adapter async/sync issues..."

# Backup original file
cp src/database/qdrant_adapter.py src/database/qdrant_adapter.py.backup

# Replace with fixed version
cp src/database/qdrant_adapter_fixed.py src/database/qdrant_adapter.py

echo "✓ Qdrant adapter fixed!"
echo ""
echo "To test the fix, run:"
echo "  python scripts/test_integration_runner.py"
echo ""
echo "To revert if needed:"
echo "  cp src/database/qdrant_adapter.py.backup src/database/qdrant_adapter.py"
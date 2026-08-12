#!/usr/bin/env bash
set -euo pipefail

echo "================================================="
echo " Setting up environment for Hackathon Pipeline"
echo "================================================="

# Check Python environment
PYTHON_BIN=$(which python3 || which python)
echo "Using Python: $PYTHON_BIN"
$PYTHON_BIN --version

# Ensure output and cache directories exist
mkdir -p ./extracted ./reports ./submissions

echo "================================================="
echo " Setup complete! Ready for pipeline run."
echo "================================================="
exit 0

#!/usr/bin/env bash
set -e

echo "=== Setting up environment for Hackathon Pipeline ==="

# Check Python version
python3 --version || python --version

# Install dependencies from requirements.txt
pip install -r requirements.txt --quiet --no-index --find-links ./wheels 2>/dev/null || pip install -r requirements.txt --quiet

echo "=== Environment Setup Complete ==="

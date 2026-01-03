#!/bin/bash
# Setup script for core plugin

set -e
SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
cd "$SCRIPT_DIR"

echo "Setting up core plugin..."

# Create virtual environment
if [ ! -d ".venv" ]; then
    echo "Creating virtual environment..."
    python3 -m venv .venv
fi

# Activate and install dependencies
source .venv/bin/activate
echo "Installing dependencies..."
pip install -q -r requirements.txt

echo ""
echo "Setup complete!"
echo ""
echo "Run '/setup' in Claude Code to configure cc-plugins interactively."

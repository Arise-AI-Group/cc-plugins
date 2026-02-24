#!/bin/bash
# Setup script for unipile plugin

set -e
SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
cd "$SCRIPT_DIR"

echo "Setting up unipile plugin..."

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
echo "Configure credentials in: ~/.config/cc-plugins/.env"
echo "  UNIPILE_API_KEY=your_access_token"
echo "  UNIPILE_DSN=api27.unipile.com:15796"

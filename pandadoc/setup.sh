#!/bin/bash
# Setup script for pandadoc plugin

set -e
SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
cd "$SCRIPT_DIR"

echo "Setting up pandadoc plugin..."

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
echo "Add: PANDADOC_API_KEY=your_api_key_here"
echo ""
echo "Get your API key from: PandaDoc Settings > Integrations > API"

#!/bin/bash
# Setup script for gmail plugin

set -e
SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
cd "$SCRIPT_DIR"

echo "Setting up gmail plugin..."

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
echo "Before using, you need to set up Google OAuth credentials:"
echo "1. Go to https://console.cloud.google.com/"
echo "2. Create a project and enable Gmail API and Tasks API"
echo "3. Create OAuth 2.0 credentials (Desktop app)"
echo "4. Download the JSON file and save as: $SCRIPT_DIR/credentials.json"
echo ""
echo "On first run, you'll be prompted to authorize the app in your browser."

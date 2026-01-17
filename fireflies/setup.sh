#!/bin/bash
# Setup script for fireflies plugin

SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"

echo "Setting up Fireflies.ai plugin..."

# Create virtual environment
if [ ! -d "$SCRIPT_DIR/.venv" ]; then
    echo "Creating virtual environment..."
    python3 -m venv "$SCRIPT_DIR/.venv"
fi

# Activate and install dependencies
source "$SCRIPT_DIR/.venv/bin/activate"
echo "Installing dependencies..."
pip install -q -r "$SCRIPT_DIR/requirements.txt"

echo "Setup complete!"
echo ""
echo "To use this plugin, ensure FIREFLIES_API_KEY is set in ~/.config/cc-plugins/.env"
echo "Example: FIREFLIES_API_KEY=your-api-key-here"

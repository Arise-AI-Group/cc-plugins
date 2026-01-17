#!/bin/bash
# Setup script for loom plugin

SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"

echo "Setting up Loom plugin..."

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
echo "This plugin works with public Loom videos - no API key required."
echo ""
echo "Usage:"
echo "  ./run tool/loom_api.py transcript https://www.loom.com/share/VIDEO_ID"
echo "  ./run tool/loom_api.py comments https://www.loom.com/share/VIDEO_ID"

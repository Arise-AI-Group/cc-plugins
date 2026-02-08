#!/bin/bash
# Setup script for video-sop plugin

set -e
SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
cd "$SCRIPT_DIR"

echo "Setting up video-sop plugin..."

# Create virtual environment
if [ ! -d ".venv" ]; then
    echo "Creating virtual environment..."
    python3 -m venv .venv
fi

# Activate and install dependencies
source .venv/bin/activate
echo "Installing dependencies..."
pip install -q -r requirements.txt

# Check system dependencies
echo ""
if ! command -v ffmpeg &> /dev/null; then
    echo "WARNING: ffmpeg is required but not found."
    echo "Install with: brew install ffmpeg"
fi

if ! command -v ffprobe &> /dev/null; then
    echo "WARNING: ffprobe is required but not found."
    echo "Install with: brew install ffmpeg"
fi

echo ""
echo "Setup complete!"
echo "No API key needed — Claude Code analyzes frames directly."

#!/bin/bash
set -e
SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
cd "$SCRIPT_DIR"

echo "Setting up YouTube plugin..."

if [ ! -d ".venv" ]; then
    echo "Creating virtual environment..."
    python3 -m venv .venv
fi

source .venv/bin/activate
echo "Installing dependencies..."
pip install -q -r requirements.txt

echo ""
echo "Setup complete!"
echo ""
echo "This plugin works with public YouTube videos - no API key required."
echo ""
echo "Usage:"
echo "  ./run tool/youtube_api.py transcript https://www.youtube.com/watch?v=VIDEO_ID"
echo "  ./run tool/youtube_api.py languages https://www.youtube.com/watch?v=VIDEO_ID"

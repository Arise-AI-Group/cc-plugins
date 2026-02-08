#!/bin/bash
# Setup script for ActivityWatch plugin
set -e

SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"

echo "Setting up ActivityWatch plugin..."

# Create venv and install dependencies
if [ ! -d "$SCRIPT_DIR/.venv" ]; then
    python3 -m venv "$SCRIPT_DIR/.venv"
fi

"$SCRIPT_DIR/.venv/bin/python3" -m pip install -q -r "$SCRIPT_DIR/requirements.txt"
touch "$SCRIPT_DIR/.venv/.deps_installed"

echo "ActivityWatch plugin setup complete."
echo ""
echo "Requirements:"
echo "  - ActivityWatch must be installed and running (https://activitywatch.net)"
echo "  - Default DB location: ~/Library/Application Support/activitywatch/aw-server/peewee-sqlite.v2.db"
echo ""
echo "Optional environment variables (in ~/.config/cc-plugins/.env):"
echo "  ACTIVITYWATCH_HOST=localhost"
echo "  ACTIVITYWATCH_PORT=5600"
echo "  ACTIVITYWATCH_DB_PATH=/custom/path/to/peewee-sqlite.v2.db"

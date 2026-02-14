#!/bin/bash
# Setup script for acontext plugin
set -e

SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
ENV_FILE="$HOME/.config/cc-plugins/.env"

echo "AContext Plugin Setup"
echo "===================="
echo ""

# Check if credentials are configured
if [ -f "$ENV_FILE" ]; then
    if grep -q "ACONTEXT_API_KEY" "$ENV_FILE" && grep -q "ACONTEXT_BASE_URL" "$ENV_FILE"; then
        echo "Credentials found in $ENV_FILE"
    else
        echo "Add the following to $ENV_FILE:"
        echo ""
        echo "ACONTEXT_BASE_URL=https://acontext-api.40hero.com"
        echo "ACONTEXT_API_KEY=sk-ac-your-token-here"
        echo "ACONTEXT_DISK_ID=optional-default-disk-uuid"
    fi
else
    echo "Create $ENV_FILE with:"
    echo ""
    echo "ACONTEXT_BASE_URL=https://acontext-api.40hero.com"
    echo "ACONTEXT_API_KEY=sk-ac-your-token-here"
    echo "ACONTEXT_DISK_ID=optional-default-disk-uuid"
fi

echo ""
echo "Installing dependencies..."
cd "$SCRIPT_DIR"
./run -c "print('Dependencies installed successfully')"
echo ""
echo "Setup complete. Install with: /plugin install $SCRIPT_DIR"

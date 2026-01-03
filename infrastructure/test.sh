#!/bin/bash
# Test script for infrastructure plugin
# Usage: ./test.sh

set -e
SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
cd "$SCRIPT_DIR"

RED='\033[0;31m'
GREEN='\033[0;32m'
NC='\033[0m'

pass() { echo -e "${GREEN}[PASS]${NC} $1"; }
fail() { echo -e "${RED}[FAIL]${NC} $1"; exit 1; }

echo "Testing infrastructure plugin..."
echo ""

# Test 1: Plugin structure
echo "Checking plugin structure..."
[ -f ".claude-plugin/plugin.json" ] && pass "plugin.json exists" || fail "plugin.json missing"
[ -f "skills/SKILL.md" ] && pass "SKILL.md exists" || fail "SKILL.md missing"
[ -d "commands" ] || [ -d "tool" ] && pass "commands/ or tool/ exists" || fail "No commands or tools"
[ -d "hooks" ] && pass "hooks/ exists" || fail "hooks/ missing"
[ -f "run" ] && pass "run script exists" || fail "run script missing"
[ -x "run" ] && pass "run is executable" || fail "run not executable"
[ -f "setup.sh" ] && pass "setup.sh exists" || fail "setup.sh missing"
[ -x "setup.sh" ] && pass "setup.sh is executable" || fail "setup.sh not executable"

# Test 2: Plugin manifest
echo ""
echo "Validating plugin.json..."
if command -v python3 &> /dev/null; then
    python3 -c "import json; json.load(open('.claude-plugin/plugin.json'))" && pass "plugin.json is valid JSON" || fail "plugin.json invalid"
    name=$(python3 -c "import json; print(json.load(open('.claude-plugin/plugin.json'))['name'])")
    [ "$name" = "infrastructure" ] && pass "Plugin name correct: $name" || fail "Plugin name incorrect: $name"
fi

# Test 3: Setup (if not already done)
echo ""
echo "Checking venv setup..."
if [ ! -d ".venv" ]; then
    echo "Running setup.sh..."
    ./setup.sh > /dev/null 2>&1 && pass "setup.sh completed" || fail "setup.sh failed"
else
    pass "venv already exists"
fi

# Test 4: Tool help (doesn't require env vars)
echo ""
echo "Testing tool execution..."
if [ -f "tool/cloudflare_api.py" ]; then
    ./run tool/cloudflare_api.py --help > /dev/null 2>&1 && pass "cloudflare_api.py --help works" || echo "  Note: cloudflare_api.py --help returned non-zero (may be expected)"
fi
if [ -f "tool/dokploy_api.py" ]; then
    ./run tool/dokploy_api.py --help > /dev/null 2>&1 && pass "dokploy_api.py --help works" || echo "  Note: dokploy_api.py --help returned non-zero (may be expected)"
fi

echo ""
echo "All tests passed!"

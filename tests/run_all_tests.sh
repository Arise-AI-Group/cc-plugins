#!/bin/bash
# Run tests for all agentic plugins
# Usage: ./tests/run_all_tests.sh [plugin_name]

set -e
SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
PLUGINS_DIR="$(dirname "$SCRIPT_DIR")"

RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

passed=0
failed=0
skipped=0

run_plugin_test() {
    local plugin=$1
    local plugin_dir="$PLUGINS_DIR/$plugin"

    if [ ! -d "$plugin_dir" ]; then
        echo -e "${RED}Plugin not found: $plugin${NC}"
        return 1
    fi

    echo -e "\n${YELLOW}Testing: $plugin${NC}"
    echo "----------------------------------------"

    if [ -f "$plugin_dir/test.sh" ]; then
        if (cd "$plugin_dir" && ./test.sh); then
            echo -e "${GREEN}PASSED: $plugin${NC}"
            ((passed++))
        else
            echo -e "${RED}FAILED: $plugin${NC}"
            ((failed++))
        fi
    else
        echo -e "${YELLOW}SKIPPED: No test.sh found${NC}"
        ((skipped++))
    fi
}

# If specific plugin provided, test only that one
if [ -n "$1" ]; then
    run_plugin_test "$1"
else
    # Test all plugins
    for plugin_dir in "$PLUGINS_DIR"/agentic-*/; do
        plugin=$(basename "$plugin_dir")
        run_plugin_test "$plugin"
    done
fi

echo ""
echo "========================================"
echo -e "Results: ${GREEN}$passed passed${NC}, ${RED}$failed failed${NC}, ${YELLOW}$skipped skipped${NC}"
echo "========================================"

if [ $failed -gt 0 ]; then
    exit 1
fi

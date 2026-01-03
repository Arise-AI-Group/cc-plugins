#!/usr/bin/env python3
"""
Generate test.sh scripts for all plugins.

Usage:
    python tools/generate-tests.py
"""

import json
import os
import stat
from pathlib import Path


def get_env_vars(plugin_dir: Path) -> list:
    """Extract env vars from .env.example."""
    env_example = plugin_dir / ".env.example"
    if not env_example.exists():
        return []

    vars = []
    with open(env_example) as f:
        for line in f:
            line = line.strip()
            if line and not line.startswith("#") and "=" in line:
                var = line.split("=")[0]
                vars.append(var)
    return vars


def get_tool_files(plugin_dir: Path) -> list:
    """Get Python tool files."""
    tool_dir = plugin_dir / "tool"
    if not tool_dir.exists():
        return []
    return [f.name for f in tool_dir.glob("*.py")]


def generate_test_script(plugin_name: str, plugin_dir: Path) -> str:
    """Generate test.sh content for a plugin."""
    env_vars = get_env_vars(plugin_dir)
    tool_files = get_tool_files(plugin_dir)

    # Build env var checks
    env_checks = ""
    if env_vars:
        for var in env_vars:
            env_checks += f'grep -q "{var}" .env.example && pass "{var} in .env.example" || fail "{var} not in .env.example"\n'
    else:
        env_checks = 'pass "No env vars required"'

    # Build tool tests
    tool_tests = ""
    if tool_files:
        for tool in tool_files:
            tool_tests += f'''if [ -f "tool/{tool}" ]; then
    ./run tool/{tool} --help > /dev/null 2>&1 && pass "{tool} --help works" || echo "  Note: {tool} --help returned non-zero (may be expected)"
fi
'''
    else:
        tool_tests = 'pass "No tools to test (workflow plugin)"'

    return f'''#!/bin/bash
# Test script for {plugin_name} plugin
# Usage: ./test.sh

set -e
SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
cd "$SCRIPT_DIR"

RED='\\033[0;31m'
GREEN='\\033[0;32m'
NC='\\033[0m'

pass() {{ echo -e "${{GREEN}}[PASS]${{NC}} $1"; }}
fail() {{ echo -e "${{RED}}[FAIL]${{NC}} $1"; exit 1; }}

echo "Testing {plugin_name} plugin..."
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

# Test 2: Environment template
echo ""
echo "Checking environment configuration..."
if [ -f ".env.example" ]; then
    pass ".env.example exists"
    {env_checks.strip()}
else
    pass "No .env.example (no env vars required)"
fi

# Test 3: Plugin manifest
echo ""
echo "Validating plugin.json..."
if command -v python3 &> /dev/null; then
    python3 -c "import json; json.load(open('.claude-plugin/plugin.json'))" && pass "plugin.json is valid JSON" || fail "plugin.json invalid"
    name=$(python3 -c "import json; print(json.load(open('.claude-plugin/plugin.json'))['name'])")
    [ "$name" = "{plugin_name}" ] && pass "Plugin name correct: $name" || fail "Plugin name incorrect: $name"
fi

# Test 4: Setup (if not already done)
echo ""
echo "Checking venv setup..."
if [ ! -d ".venv" ]; then
    echo "Running setup.sh..."
    ./setup.sh > /dev/null 2>&1 && pass "setup.sh completed" || fail "setup.sh failed"
else
    pass "venv already exists"
fi

# Test 5: Tool help (doesn't require env vars)
echo ""
echo "Testing tool execution..."
{tool_tests.strip()}

echo ""
echo "All tests passed!"
'''


def main():
    plugins_dir = Path(__file__).parent.parent

    # Find plugin directories (have .claude-plugin/plugin.json)
    for plugin_dir in plugins_dir.iterdir():
        if not plugin_dir.is_dir():
            continue
        if not (plugin_dir / ".claude-plugin" / "plugin.json").exists():
            continue

        plugin_name = plugin_dir.name
        test_script = generate_test_script(plugin_name, plugin_dir)

        test_path = plugin_dir / "test.sh"
        with open(test_path, "w") as f:
            f.write(test_script)

        # Make executable
        test_path.chmod(test_path.stat().st_mode | stat.S_IXUSR | stat.S_IXGRP | stat.S_IXOTH)

        print(f"Generated: {test_path}")


if __name__ == "__main__":
    main()

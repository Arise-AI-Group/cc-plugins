#!/usr/bin/env python3
"""
Scaffold a new Claude Code plugin from scratch.

Usage:
    python tools/plugin-scaffold.py <name> [options]

Example:
    python tools/plugin-scaffold.py agentic-myservice \
        --description "My service integration" \
        --env-vars "API_KEY,API_SECRET"
"""

import argparse
import json
import os
import re
import stat
from pathlib import Path


def validate_name(name: str) -> bool:
    """Validate plugin name (lowercase, letters/numbers/hyphens, starts with letter)."""
    return bool(re.match(r"^[a-z][a-z0-9-]*$", name))


def create_plugin_manifest(name: str, description: str, output_path: Path) -> None:
    """Create .claude-plugin/plugin.json."""
    plugin_dir = output_path / ".claude-plugin"
    plugin_dir.mkdir(parents=True, exist_ok=True)

    plugin_json = {
        "name": name,
        "description": description,
        "version": "1.0.0",
        "author": {
            "name": "Your Name"
        }
    }

    with open(plugin_dir / "plugin.json", "w") as f:
        json.dump(plugin_json, f, indent=2)

    print(f"  Created .claude-plugin/plugin.json")


def create_skill(name: str, description: str, output_path: Path) -> None:
    """Create skills/SKILL.md."""
    skills_dir = output_path / "skills"
    skills_dir.mkdir(parents=True, exist_ok=True)

    python_name = name.replace("-", "_")

    skill_content = f"""---
name: {name}
description: {description}. Use when the user asks about {name} operations.
---

# {name.title().replace('-', ' ')} Operations

## Purpose

{description}

## How to Run

All operations use the Python CLI tool:

```bash
./run tool/{python_name}_api.py <action> [args]
```

## Available Actions

| Action | Description |
|--------|-------------|
| `example` | Example action - replace with real actions |

## Common Workflows

### Example Workflow

1. First step
2. Second step
3. Third step

## Edge Cases

- Document edge cases here

## Troubleshooting

- Common issues and solutions
"""

    with open(skills_dir / "SKILL.md", "w") as f:
        f.write(skill_content)

    print(f"  Created skills/SKILL.md")


def create_command(name: str, description: str, output_path: Path) -> None:
    """Create a sample command."""
    commands_dir = output_path / "commands"
    commands_dir.mkdir(parents=True, exist_ok=True)

    python_name = name.replace("-", "_")

    cmd_content = f"""---
description: {description}
---

# /{name}

{description}

## Arguments

- `$1` - Action to perform
- `$2` - Additional argument (optional)

## Available Actions

- `example` - Run example action

## Instructions

1. Parse the action from `$1`
2. Run the appropriate tool command:
   ```bash
   ./run tool/{python_name}_api.py $1 $2
   ```
3. Report results to the user
"""

    with open(commands_dir / f"{name}.md", "w") as f:
        f.write(cmd_content)

    print(f"  Created commands/{name}.md")


def create_tool(name: str, description: str, env_vars: list, output_path: Path) -> None:
    """Create tool/X_api.py and tool/config.py."""
    tool_dir = output_path / "tool"
    tool_dir.mkdir(parents=True, exist_ok=True)

    # Create config.py for credential loading
    config_content = '''"""API key loader for standalone plugin operation.

Loads credentials from ~/.config/cc-plugins/.env for remote plugin installation.
"""
import os
from pathlib import Path
from dotenv import load_dotenv

USER_ENV = Path.home() / ".config" / "cc-plugins" / ".env"

# Track if we've loaded the env file
_env_loaded = False


def get_api_key(key: str, default: str = "") -> str:
    """Get API key from environment or ~/.config/cc-plugins/.env.

    Args:
        key: Name of the environment variable (e.g., "SLACK_BOT_TOKEN")
        default: Default value if key not found

    Returns:
        The API key value or default
    """
    global _env_loaded

    # Check if already in environment
    value = os.getenv(key)
    if value:
        return value

    # Load from user's config directory (once)
    if not _env_loaded and USER_ENV.exists():
        load_dotenv(USER_ENV)
        _env_loaded = True
        value = os.getenv(key)
        if value:
            return value

    return default
'''
    config_path = tool_dir / "config.py"
    with open(config_path, "w") as f:
        f.write(config_content)
    print(f"  Created tool/config.py")

    python_name = name.replace("-", "_")

    env_checks = ""
    if env_vars:
        env_checks = "\n".join([
            f'    {var} = get_api_key("{var}")\n    if not {var}:\n        print("Error: {var} not set")\n        sys.exit(1)'
            for var in env_vars
        ])

    tool_content = f'''#!/usr/bin/env python3
"""
{name} tool

{description}

Usage:
    ./run tool/{python_name}_api.py <action> [args]

Actions:
    example     Run an example action
"""

import argparse
import os
import sys
from pathlib import Path

from .config import get_api_key


def check_env():
    """Check required environment variables."""
{env_checks if env_checks else '    pass  # No required env vars'}


def example_action(args):
    """Example action - replace with real implementation."""
    print(f"Running example action with args: {{args}}")
    print("Replace this with your actual implementation.")


def main():
    parser = argparse.ArgumentParser(description="{description}")
    parser.add_argument("action", help="Action to perform")
    parser.add_argument("args", nargs="*", help="Additional arguments")

    args = parser.parse_args()

    check_env()

    if args.action == "example":
        example_action(args.args)
    else:
        print(f"Unknown action: {{args.action}}")
        print("Available actions: example")
        sys.exit(1)


if __name__ == "__main__":
    main()
'''

    tool_path = tool_dir / f"{python_name}_api.py"
    with open(tool_path, "w") as f:
        f.write(tool_content)

    # Make executable
    tool_path.chmod(tool_path.stat().st_mode | stat.S_IXUSR | stat.S_IXGRP | stat.S_IXOTH)
    print(f"  Created tool/{python_name}_api.py")


def create_hooks(env_vars: list, output_path: Path) -> None:
    """Create hooks/hooks.json."""
    hooks_dir = output_path / "hooks"
    hooks_dir.mkdir(parents=True, exist_ok=True)

    if env_vars:
        env_check = " and ".join([f'os.getenv("{v}")' for v in env_vars])
        hooks_json = {
            "hooks": {
                "PreToolUse": [
                    {
                        "matcher": "Bash",
                        "hooks": [
                            {
                                "type": "command",
                                "command": f'python3 -c "import os; exit(0 if all([{env_check}]) else 1)"'
                            }
                        ]
                    }
                ]
            }
        }
    else:
        hooks_json = {"hooks": {}}

    with open(hooks_dir / "hooks.json", "w") as f:
        json.dump(hooks_json, f, indent=2)

    print(f"  Created hooks/hooks.json")


def create_env_example(env_vars: list, output_path: Path) -> None:
    """Create .env.example."""
    if not env_vars:
        return

    content = "# Required environment variables\n\n"
    for var in env_vars:
        content += f"{var}=\n"

    with open(output_path / ".env.example", "w") as f:
        f.write(content)

    print(f"  Created .env.example")


def create_requirements(output_path: Path) -> None:
    """Create requirements.txt."""
    content = """requests>=2.28.0
"""

    with open(output_path / "requirements.txt", "w") as f:
        f.write(content)

    print(f"  Created requirements.txt")


def create_run_script(output_path: Path) -> None:
    """Create run wrapper script."""
    content = '''#!/bin/bash
# Activate virtual environment and run Python script
SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"

if [ ! -d "$SCRIPT_DIR/.venv" ]; then
    echo "Virtual environment not found. Run ./setup.sh first."
    exit 1
fi

source "$SCRIPT_DIR/.venv/bin/activate"
python3 "$@"
'''

    run_path = output_path / "run"
    with open(run_path, "w") as f:
        f.write(content)

    run_path.chmod(run_path.stat().st_mode | stat.S_IXUSR | stat.S_IXGRP | stat.S_IXOTH)
    print(f"  Created run")


def create_setup_script(name: str, output_path: Path) -> None:
    """Create setup.sh."""
    content = f'''#!/bin/bash
# Setup script for {name} plugin

set -e
SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
cd "$SCRIPT_DIR"

echo "Setting up {name} plugin..."

# Create virtual environment
if [ ! -d ".venv" ]; then
    echo "Creating virtual environment..."
    python3 -m venv .venv
fi

# Activate and install dependencies
source .venv/bin/activate
echo "Installing dependencies..."
pip install -q -r requirements.txt

# Create .env if it doesn't exist
if [ ! -f ".env" ]; then
    if [ -f ".env.example" ]; then
        cp .env.example .env
        echo ""
        echo "Created .env from .env.example"
        echo "Please edit .env to add your credentials."
    fi
fi

echo ""
echo "Setup complete!"
echo ""
echo "To use this plugin:"
echo "  claude --plugin-dir $SCRIPT_DIR"
'''

    setup_path = output_path / "setup.sh"
    with open(setup_path, "w") as f:
        f.write(content)

    setup_path.chmod(setup_path.stat().st_mode | stat.S_IXUSR | stat.S_IXGRP | stat.S_IXOTH)
    print(f"  Created setup.sh")


def create_readme(name: str, description: str, env_vars: list, output_path: Path) -> None:
    """Create README.md."""
    python_name = name.replace("-", "_")

    env_section = "\n".join([f"- `{v}`" for v in env_vars]) if env_vars else "None required"

    content = f"""# {name}

{description}

## Installation

```bash
# Set up the plugin
./setup.sh

# Edit .env with your credentials
nano .env

# Run Claude Code with this plugin
claude --plugin-dir .
```

## Commands

- `/{name}:<action>` - Run an action

## Environment Variables

{env_section}

## Usage

### Via Slash Commands

```
/{name}:example
```

### Via CLI

```bash
./run tool/{python_name}_api.py example
./run tool/{python_name}_api.py --help
```

## Development

To add new actions:

1. Edit `tool/{python_name}_api.py` to add the action
2. Update `skills/SKILL.md` with documentation
3. Optionally add a new command in `commands/`

## License

MIT
"""

    with open(output_path / "README.md", "w") as f:
        f.write(content)

    print(f"  Created README.md")


def create_gitignore(output_path: Path) -> None:
    """Create .gitignore."""
    content = """.env
.venv/
__pycache__/
*.pyc
.DS_Store
"""

    with open(output_path / ".gitignore", "w") as f:
        f.write(content)

    print(f"  Created .gitignore")


def scaffold_plugin(name: str, description: str, env_vars: list) -> None:
    """Main scaffold function."""
    # Remove agentic- prefix if present (no longer used)
    if name.startswith("agentic-"):
        name = name.replace("agentic-", "")

    output_path = Path.cwd() / name

    if output_path.exists():
        print(f"Error: Directory already exists: {output_path}")
        return

    print(f"\nCreating plugin: {name}")
    print(f"  Output: {output_path}")
    print()

    output_path.mkdir(parents=True, exist_ok=True)

    create_plugin_manifest(name, description, output_path)
    create_skill(name, description, output_path)
    create_command(name, description, output_path)
    create_tool(name, description, env_vars, output_path)
    create_hooks(env_vars, output_path)
    create_env_example(env_vars, output_path)
    create_requirements(output_path)
    create_run_script(output_path)
    create_setup_script(name, output_path)
    create_readme(name, description, env_vars, output_path)
    create_gitignore(output_path)

    print()
    print(f"Plugin created: {output_path}")
    print()
    print("Next steps:")
    print(f"  cd {name}")
    print(f"  ./setup.sh")
    print(f"  # Edit .env with credentials")
    print(f"  # Edit tool/*.py to implement your logic")
    print(f"  claude --plugin-dir .")


def main():
    parser = argparse.ArgumentParser(
        description="Scaffold a new Claude Code plugin"
    )
    parser.add_argument(
        "name",
        help="Plugin name (e.g., agentic-myservice or just myservice)"
    )
    parser.add_argument(
        "--description", "-d",
        default="A Claude Code plugin",
        help="Plugin description"
    )
    parser.add_argument(
        "--env-vars", "-e",
        default="",
        help="Comma-separated list of required environment variables"
    )

    args = parser.parse_args()

    # Validate name
    base_name = args.name.replace("agentic-", "")
    if not validate_name(base_name):
        print("Error: Name must be lowercase, start with a letter, and contain only letters, numbers, and hyphens")
        return

    env_vars = [v.strip() for v in args.env_vars.split(",") if v.strip()]

    scaffold_plugin(args.name, args.description, env_vars)


if __name__ == "__main__":
    main()

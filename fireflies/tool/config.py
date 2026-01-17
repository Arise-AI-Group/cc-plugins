"""API key loader for standalone plugin operation.

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

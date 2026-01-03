"""Core plugin configuration."""
import os
from pathlib import Path
from dotenv import load_dotenv

# Load environment from cc-plugins config
CONFIG_DIR = Path.home() / ".config" / "cc-plugins"
ENV_FILE = CONFIG_DIR / ".env"

if ENV_FILE.exists():
    load_dotenv(ENV_FILE)

def get_config_dir() -> Path:
    """Get the cc-plugins config directory."""
    return CONFIG_DIR

def get_env_file() -> Path:
    """Get the cc-plugins .env file path."""
    return ENV_FILE

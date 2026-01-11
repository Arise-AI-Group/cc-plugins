"""Per-user task configuration.

Loads and saves user-specific settings from ~/.config/cc-plugins/tasks.json
"""
import json
from pathlib import Path
from typing import Optional

USER_CONFIG_DIR = Path.home() / ".config" / "cc-plugins"
USER_CONFIG_FILE = USER_CONFIG_DIR / "tasks.json"


def get_user_config() -> dict:
    """Load user configuration from tasks.json.

    Returns:
        dict with user configuration, empty dict if not configured
    """
    if not USER_CONFIG_FILE.exists():
        return {}

    try:
        with open(USER_CONFIG_FILE, "r") as f:
            return json.load(f)
    except (json.JSONDecodeError, IOError):
        return {}


def save_user_config(config: dict) -> None:
    """Save user configuration to tasks.json.

    Args:
        config: Configuration dictionary to save
    """
    USER_CONFIG_DIR.mkdir(parents=True, exist_ok=True)

    with open(USER_CONFIG_FILE, "w") as f:
        json.dump(config, f, indent=2)


def get_private_database_id() -> Optional[str]:
    """Get the user's private task database ID (for pages.create).

    Returns:
        Database ID string or None if not configured
    """
    config = get_user_config()
    # Support both old single-ID format and new dual-ID format
    private_db = config.get("private_task_db")
    if isinstance(private_db, dict):
        return private_db.get("database_id")
    return config.get("private_task_database_id")


def get_private_data_source_id() -> Optional[str]:
    """Get the user's private task data_source_id (for queries).

    Returns:
        Data source ID string or None if not configured
    """
    config = get_user_config()
    private_db = config.get("private_task_db")
    if isinstance(private_db, dict):
        return private_db.get("data_source_id")
    # Fallback: no data_source_id stored
    return None


def set_private_database_ids(database_id: str, data_source_id: str = None) -> None:
    """Set the user's private task database IDs.

    Args:
        database_id: Notion database ID for creating pages
        data_source_id: Notion data_source ID for queries (optional)
    """
    config = get_user_config()
    if data_source_id:
        config["private_task_db"] = {
            "database_id": database_id,
            "data_source_id": data_source_id,
        }
    else:
        config["private_task_database_id"] = database_id
    save_user_config(config)


def set_private_database_id(database_id: str) -> None:
    """Set the user's private task database ID (legacy single-ID).

    Args:
        database_id: Notion database ID for private tasks
    """
    set_private_database_ids(database_id)


def is_configured() -> bool:
    """Check if the user has configured their private task database.

    Returns:
        True if private_task_database_id is set
    """
    return get_private_database_id() is not None

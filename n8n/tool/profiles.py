"""n8n instance profile configuration.

Manages n8n profiles stored in ~/.config/cc-plugins/n8n.json for multi-instance support.
"""
import json
import os
from dataclasses import dataclass
from pathlib import Path
from typing import Dict, Optional, Tuple

from .config import get_api_key

USER_CONFIG_DIR = Path.home() / ".config" / "cc-plugins"
N8N_CONFIG_FILE = USER_CONFIG_DIR / "n8n.json"


@dataclass
class N8nProfile:
    """n8n instance profile."""

    name: str
    api_url: str
    api_key: str
    description: Optional[str] = None

    def __str__(self) -> str:
        """String representation for display."""
        desc = f" - {self.description}" if self.description else ""
        return f"{self.name}: {self.api_url}{desc}"


def get_n8n_config() -> dict:
    """Load n8n configuration from n8n.json."""
    if not N8N_CONFIG_FILE.exists():
        return {"profiles": {}, "default_profile": None}

    try:
        with open(N8N_CONFIG_FILE, "r") as f:
            return json.load(f)
    except (json.JSONDecodeError, IOError):
        return {"profiles": {}, "default_profile": None}


def save_n8n_config(config: dict) -> None:
    """Save n8n configuration to n8n.json."""
    USER_CONFIG_DIR.mkdir(parents=True, exist_ok=True)
    with open(N8N_CONFIG_FILE, "w") as f:
        json.dump(config, f, indent=2)


def list_profiles() -> Dict[str, N8nProfile]:
    """List all configured n8n profiles."""
    config = get_n8n_config()
    profiles = {}
    for name, data in config.get("profiles", {}).items():
        # Resolve API key from environment variable
        api_key = None
        if "api_key_env" in data:
            api_key = get_api_key(data["api_key_env"])
        elif "api_key" in data:
            # Direct API key (not recommended but supported)
            api_key = data["api_key"]

        profiles[name] = N8nProfile(
            name=name,
            api_url=data["api_url"].rstrip("/"),
            api_key=api_key or "",
            description=data.get("description"),
        )
    return profiles


def get_profile(name: str) -> Optional[N8nProfile]:
    """Get a specific profile by name."""
    profiles = list_profiles()
    return profiles.get(name)


def get_default_profile() -> Optional[N8nProfile]:
    """Get the default profile if configured."""
    config = get_n8n_config()
    default_name = config.get("default_profile")
    if default_name:
        return get_profile(default_name)

    # If only one profile exists, use it as default
    profiles = list_profiles()
    if len(profiles) == 1:
        return list(profiles.values())[0]

    return None


def get_default_profile_name() -> Optional[str]:
    """Get the name of the default profile."""
    config = get_n8n_config()
    default_name = config.get("default_profile")
    if default_name:
        return default_name

    # If only one profile exists, use it as default
    profiles = config.get("profiles", {})
    if len(profiles) == 1:
        return list(profiles.keys())[0]

    return None


def resolve_credentials(profile_name: Optional[str] = None) -> Tuple[str, str]:
    """
    Resolve n8n credentials based on profile or fallback to environment.

    Resolution order:
    1. If profile_name specified, use that profile
    2. If n8n.json exists with default_profile, use default
    3. If only one profile in n8n.json, use it
    4. Fall back to N8N_API_URL/N8N_API_KEY from .env

    Returns:
        Tuple of (api_url, api_key)

    Raises:
        ValueError: If no credentials can be resolved
    """
    # Try to get profile
    profile = None
    if profile_name:
        profile = get_profile(profile_name)
        if not profile:
            raise ValueError(f"Profile '{profile_name}' not found")
    else:
        profile = get_default_profile()

    if profile and profile.api_url and profile.api_key:
        return profile.api_url, profile.api_key

    # Fallback to environment variables
    api_url = get_api_key("N8N_API_URL")
    api_key = get_api_key("N8N_API_KEY")

    if api_url and api_key:
        return api_url.rstrip("/"), api_key

    # Check if we have a profile but missing credentials
    if profile:
        if not profile.api_key:
            raise ValueError(
                f"Profile '{profile.name}' has no API key. "
                f"Set the environment variable specified in api_key_env."
            )

    raise ValueError(
        "No n8n credentials configured. Either:\n"
        "1. Add a profile: ./run tool/n8n_api.py profile add <name> --url <url> --api-key-env <ENV_VAR>\n"
        "2. Set N8N_API_URL and N8N_API_KEY in ~/.config/cc-plugins/.env"
    )


def add_profile(
    name: str,
    api_url: str,
    api_key_env: Optional[str] = None,
    description: Optional[str] = None,
) -> None:
    """Add or update a profile."""
    config = get_n8n_config()
    if "profiles" not in config:
        config["profiles"] = {}

    profile_data = {
        "api_url": api_url.rstrip("/"),
    }
    if api_key_env:
        profile_data["api_key_env"] = api_key_env
    if description:
        profile_data["description"] = description

    config["profiles"][name] = profile_data
    save_n8n_config(config)


def remove_profile(name: str) -> bool:
    """Remove a profile. Returns True if removed."""
    config = get_n8n_config()
    if name in config.get("profiles", {}):
        del config["profiles"][name]
        if config.get("default_profile") == name:
            config["default_profile"] = None
        save_n8n_config(config)
        return True
    return False


def set_default_profile(name: str) -> bool:
    """Set the default profile. Returns True if successful."""
    config = get_n8n_config()
    if name in config.get("profiles", {}):
        config["default_profile"] = name
        save_n8n_config(config)
        return True
    return False


def has_multiple_profiles() -> bool:
    """Check if multiple profiles are configured."""
    config = get_n8n_config()
    return len(config.get("profiles", {})) > 1

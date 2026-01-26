"""SSH server profile configuration.

Manages SSH profiles stored in ~/.config/cc-plugins/ssh.json for multi-server support.
"""
import json
import os
from dataclasses import dataclass
from pathlib import Path
from typing import Dict, Optional

from .config import get_api_key

USER_CONFIG_DIR = Path.home() / ".config" / "cc-plugins"
SSH_CONFIG_FILE = USER_CONFIG_DIR / "ssh.json"


@dataclass
class SSHProfile:
    """SSH server profile."""

    name: str
    host: str
    user: str
    port: int = 22
    key_path: Optional[str] = None
    password: Optional[str] = None
    description: Optional[str] = None

    def to_target(self) -> str:
        """Convert to user@host:port target string."""
        if self.port == 22:
            return f"{self.user}@{self.host}"
        return f"{self.user}@{self.host}:{self.port}"


def get_ssh_config() -> dict:
    """Load SSH configuration from ssh.json."""
    if not SSH_CONFIG_FILE.exists():
        return {"profiles": {}, "default_profile": None}

    try:
        with open(SSH_CONFIG_FILE, "r") as f:
            return json.load(f)
    except (json.JSONDecodeError, IOError):
        return {"profiles": {}, "default_profile": None}


def save_ssh_config(config: dict) -> None:
    """Save SSH configuration to ssh.json."""
    USER_CONFIG_DIR.mkdir(parents=True, exist_ok=True)
    with open(SSH_CONFIG_FILE, "w") as f:
        json.dump(config, f, indent=2)


def list_profiles() -> Dict[str, SSHProfile]:
    """List all configured SSH profiles."""
    config = get_ssh_config()
    profiles = {}
    for name, data in config.get("profiles", {}).items():
        password = None
        if "password_env" in data:
            password = get_api_key(data["password_env"])

        key_path = data.get("key_path")
        if key_path:
            key_path = os.path.expanduser(key_path)

        profiles[name] = SSHProfile(
            name=name,
            host=data["host"],
            user=data["user"],
            port=data.get("port", 22),
            key_path=key_path,
            password=password,
            description=data.get("description"),
        )
    return profiles


def get_profile(name: str) -> Optional[SSHProfile]:
    """Get a specific profile by name."""
    profiles = list_profiles()
    return profiles.get(name)


def get_default_profile() -> Optional[SSHProfile]:
    """Get the default profile if configured."""
    config = get_ssh_config()
    default_name = config.get("default_profile")
    if default_name:
        return get_profile(default_name)
    return None


def add_profile(
    name: str,
    host: str,
    user: str,
    port: int = 22,
    key_path: Optional[str] = None,
    password_env: Optional[str] = None,
    description: Optional[str] = None,
) -> None:
    """Add or update a profile."""
    config = get_ssh_config()
    if "profiles" not in config:
        config["profiles"] = {}

    profile_data = {
        "host": host,
        "user": user,
        "port": port,
    }
    if key_path:
        profile_data["key_path"] = key_path
    if password_env:
        profile_data["password_env"] = password_env
    if description:
        profile_data["description"] = description

    config["profiles"][name] = profile_data
    save_ssh_config(config)


def remove_profile(name: str) -> bool:
    """Remove a profile. Returns True if removed."""
    config = get_ssh_config()
    if name in config.get("profiles", {}):
        del config["profiles"][name]
        if config.get("default_profile") == name:
            config["default_profile"] = None
        save_ssh_config(config)
        return True
    return False


def set_default_profile(name: str) -> bool:
    """Set the default profile. Returns True if successful."""
    config = get_ssh_config()
    if name in config.get("profiles", {}):
        config["default_profile"] = name
        save_ssh_config(config)
        return True
    return False

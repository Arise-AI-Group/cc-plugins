"""Style loading with multi-layer resolution support.

Supports cascading style hierarchy:
1. Plugin defaults (built-in)
2. User/business brands (~/.config/doc-gen/brands/)
3. Project overrides (.doc-gen/brand.json)
4. CLI overrides (passed at runtime)
"""

import json
import os
from pathlib import Path
from typing import Any


# Directory paths
STYLES_DIR = Path(__file__).parent.parent.parent / "styles"

# User config directory (XDG convention)
CONFIG_DIR = Path(os.environ.get("XDG_CONFIG_HOME", Path.home() / ".config")) / "doc-gen"


# Default style configuration (fallback when no style found)
DEFAULT_STYLE: dict[str, Any] = {
    "metadata": {
        "name": "default",
        "description": "Built-in default style"
    },
    "page": {
        "size": "letter",
        "margins": {"top": "1in", "right": "1in", "bottom": "1in", "left": "1in"}
    },
    "colors": {
        "primary": "#2C4A6E",
        "accent": "#E07A38",
        "text": "#333333",
        "muted": "#666666",
        "light": "#F8F9FA",
        "success": "#27AE60",
        "warning": "#E67E22",
        "danger": "#C0392B",
        "border": "#E0E0E0"
    },
    "fonts": {
        "heading": {"name": "Arial", "bold": True},
        "body": {"name": "Arial", "size": 11},
        "mono": {"name": "Courier New", "size": 10}
    },
    "styles": {
        "title": {
            "font": {"name": "Arial", "size": 24, "bold": True, "color": "primary"},
            "alignment": "center",
            "spacing": {"after": 6}
        },
        "subtitle": {
            "font": {"name": "Arial", "size": 14, "color": "muted"},
            "alignment": "center",
            "spacing": {"after": 18}
        },
        "heading1": {
            "font": {"name": "Arial", "size": 16, "bold": True, "color": "primary"},
            "spacing": {"before": 18, "after": 10}
        },
        "heading2": {
            "font": {"name": "Arial", "size": 13, "bold": True, "color": "primary"},
            "spacing": {"before": 14, "after": 8}
        },
        "heading3": {
            "font": {"name": "Arial", "size": 11, "bold": True, "color": "text"},
            "spacing": {"before": 10, "after": 6}
        },
        "body": {
            "font": {"name": "Arial", "size": 11, "color": "text"},
            "spacing": {"after": 8}
        },
        "bullet": {
            "font": {"name": "Arial", "size": 11, "color": "text"},
            "spacing": {"after": 4}
        }
    },
    "tables": {
        "default": {
            "headerRow": {
                "background": "#F0F0F0",
                "font": {"bold": True, "size": 11}
            },
            "bodyRow": {
                "font": {"size": 11}
            }
        }
    },
    "lists": {
        "bullet": {"symbol": "\u2022", "color": "text"},
        "check": {"symbol": "\u2713", "color": "success"},
        "cross": {"symbol": "\u2717", "color": "danger"},
        "dash": {"symbol": "\u2014", "color": "text"}
    },
    "contact": {}
}


def load_style(name_or_path: str | Path | None = None) -> dict[str, Any]:
    """Load a style configuration by name or file path.

    Resolution order:
    1. If None, return default style
    2. If absolute path, load directly
    3. Check styles/ for {name}.json
    4. Return default style with warning

    Args:
        name_or_path: Style name (e.g., "professional") or path to config file

    Returns:
        Style configuration dictionary
    """
    if name_or_path is None:
        return DEFAULT_STYLE.copy()

    path = Path(name_or_path)

    # If it's an absolute path or relative path that exists
    if path.is_absolute() or path.exists():
        return _load_file(path)

    # Try styles/ directory
    json_path = STYLES_DIR / f"{name_or_path}.json"
    if json_path.exists():
        return _load_file(json_path)

    # Not found - return default
    print(f"Warning: Style '{name_or_path}' not found, using default")
    return DEFAULT_STYLE.copy()


def _load_file(path: Path) -> dict[str, Any]:
    """Load a JSON style file and merge with defaults."""
    if not path.exists():
        raise FileNotFoundError(f"Style file not found: {path}")

    with open(path, "r", encoding="utf-8") as f:
        data = json.load(f)
        return _merge_with_defaults(data)


def _merge_with_defaults(style: dict[str, Any]) -> dict[str, Any]:
    """Deep merge style with defaults to fill in missing values."""
    result = {}

    for key in DEFAULT_STYLE:
        if key not in style:
            result[key] = DEFAULT_STYLE[key].copy() if isinstance(DEFAULT_STYLE[key], dict) else DEFAULT_STYLE[key]
        elif isinstance(DEFAULT_STYLE[key], dict) and isinstance(style.get(key), dict):
            # Deep merge for dict values
            result[key] = {**DEFAULT_STYLE[key], **style[key]}
        else:
            result[key] = style[key]

    # Include any extra keys from the style
    for key in style:
        if key not in result:
            result[key] = style[key]

    return result


def deep_merge(base: dict[str, Any], overlay: dict[str, Any]) -> dict[str, Any]:
    """Recursively merge overlay dict into base dict.

    - Overlay values override base values
    - Nested dicts are merged recursively
    - Lists are replaced (not concatenated)

    Args:
        base: Base dictionary
        overlay: Dictionary to merge on top

    Returns:
        New merged dictionary (does not mutate inputs)
    """
    result = base.copy()

    for key, value in overlay.items():
        if key in result and isinstance(result[key], dict) and isinstance(value, dict):
            # Recursively merge nested dicts
            result[key] = deep_merge(result[key], value)
        else:
            # Replace value
            result[key] = value

    return result


def deep_merge_all(layers: list[dict[str, Any]]) -> dict[str, Any]:
    """Merge multiple layers into a single config.

    Args:
        layers: List of config dicts, from lowest to highest priority

    Returns:
        Merged configuration
    """
    if not layers:
        return {}

    result = layers[0].copy()
    for layer in layers[1:]:
        result = deep_merge(result, layer)

    return result


def get_config_dir() -> Path:
    """Get the user config directory path.

    Returns:
        Path to ~/.config/doc-gen/ (or XDG_CONFIG_HOME/doc-gen/)
    """
    return CONFIG_DIR


def ensure_config_dir() -> Path:
    """Ensure the config directory structure exists.

    Creates:
        ~/.config/doc-gen/
        ~/.config/doc-gen/brands/
        ~/.config/doc-gen/cache/
        ~/.config/doc-gen/config.json (if missing)

    Returns:
        Path to config directory
    """
    config_dir = get_config_dir()
    brands_dir = config_dir / "brands"
    cache_dir = config_dir / "cache"
    config_file = config_dir / "config.json"

    # Create directories
    config_dir.mkdir(parents=True, exist_ok=True)
    brands_dir.mkdir(exist_ok=True)
    cache_dir.mkdir(exist_ok=True)

    # Create default config if missing
    if not config_file.exists():
        default_config = {
            "default_brand": None,
            "output_formats": ["pdf", "docx"],
            "auto_open": False
        }
        with open(config_file, "w", encoding="utf-8") as f:
            json.dump(default_config, f, indent=2)

    return config_dir


def get_global_config() -> dict[str, Any]:
    """Load the global config.json.

    Returns:
        Config dict with default_brand, output_formats, etc.
    """
    config_file = get_config_dir() / "config.json"

    if not config_file.exists():
        return {
            "default_brand": None,
            "output_formats": ["pdf", "docx"],
            "auto_open": False
        }

    with open(config_file, "r", encoding="utf-8") as f:
        return json.load(f)


def get_default_brand() -> str | None:
    """Get the default brand name from config.

    Returns:
        Brand name or None if not set
    """
    config = get_global_config()
    return config.get("default_brand")


def list_brands() -> list[dict[str, Any]]:
    """List all available brands.

    Returns:
        List of dicts with 'name', 'path', 'description'
    """
    brands_dir = get_config_dir() / "brands"
    brands = []

    if not brands_dir.exists():
        return brands

    for brand_dir in brands_dir.iterdir():
        if not brand_dir.is_dir():
            continue

        brand_file = brand_dir / "brand.json"
        if not brand_file.exists():
            continue

        try:
            with open(brand_file, "r", encoding="utf-8") as f:
                data = json.load(f)
            metadata = data.get("metadata", {})
            brands.append({
                "name": brand_dir.name,
                "path": str(brand_dir),
                "description": metadata.get("description", "")
            })
        except Exception:
            brands.append({
                "name": brand_dir.name,
                "path": str(brand_dir),
                "description": "(failed to load)"
            })

    return sorted(brands, key=lambda x: x["name"])


def load_brand_style(name: str) -> dict[str, Any] | None:
    """Load a brand style configuration.

    Args:
        name: Brand name (directory name under brands/)

    Returns:
        Style config dict or None if brand not found
    """
    brand_file = get_config_dir() / "brands" / name / "brand.json"

    if not brand_file.exists():
        return None

    with open(brand_file, "r", encoding="utf-8") as f:
        return json.load(f)


def find_project_config(start_path: Path | None = None) -> Path | None:
    """Find project-level .doc-gen/brand.json by walking up directories.

    Args:
        start_path: Starting directory (defaults to cwd)

    Returns:
        Path to brand.json or None if not found
    """
    if start_path is None:
        start_path = Path.cwd()

    current = start_path.resolve()

    # Walk up to root
    while current != current.parent:
        config_path = current / ".doc-gen" / "brand.json"
        if config_path.exists():
            return config_path
        current = current.parent

    return None


def load_project_style(project_path: Path | None = None) -> dict[str, Any] | None:
    """Load project-level style overrides.

    Searches for .doc-gen/brand.json in project_path or walks up from cwd.

    Args:
        project_path: Path to search from (defaults to cwd)

    Returns:
        Style config dict or None if not found
    """
    config_path = find_project_config(project_path)

    if config_path is None:
        return None

    with open(config_path, "r", encoding="utf-8") as f:
        return json.load(f)


def load_layered_style(
    brand: str | None = None,
    project_path: Path | None = None,
    overrides: dict[str, Any] | None = None,
    use_project_config: bool = True
) -> dict[str, Any]:
    """Load style with multi-layer resolution.

    Resolution order (lowest to highest priority):
    1. Plugin defaults
    2. User brand (if specified, or default brand)
    3. Project overrides (.doc-gen/brand.json)
    4. CLI overrides

    Args:
        brand: Brand name to use (or None for default brand)
        project_path: Path to search for project config (defaults to cwd)
        overrides: Additional overrides (e.g., from CLI flags)
        use_project_config: Whether to auto-detect project config

    Returns:
        Merged style configuration
    """
    layers = []

    # Layer 1: Plugin defaults (always)
    layers.append(DEFAULT_STYLE.copy())

    # Layer 2: User brand
    brand_name = brand or get_default_brand()
    if brand_name:
        brand_style = load_brand_style(brand_name)
        if brand_style:
            layers.append(brand_style)

    # Layer 3: Project overrides
    if use_project_config:
        project_style = load_project_style(project_path)
        if project_style:
            layers.append(project_style)

    # Layer 4: CLI overrides
    if overrides:
        layers.append(overrides)

    return deep_merge_all(layers)


def list_styles() -> list[dict[str, Any]]:
    """List all available styles with their metadata.

    Returns:
        List of dicts with 'name', 'path', and 'description'
    """
    styles = []

    if STYLES_DIR.exists():
        for json_file in STYLES_DIR.glob("*.json"):
            try:
                with open(json_file) as f:
                    data = json.load(f)
                metadata = data.get("metadata", {})
                styles.append({
                    "name": json_file.stem,
                    "path": str(json_file),
                    "description": metadata.get("description", "")
                })
            except Exception:
                styles.append({
                    "name": json_file.stem,
                    "path": str(json_file),
                    "description": "(failed to load metadata)"
                })

    return sorted(styles, key=lambda x: x["name"])

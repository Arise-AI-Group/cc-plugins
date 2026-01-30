"""Style loading with JSON (primary) and YAML (legacy) support.

Loads style configurations from the styles/ directory (JSON) or
presets/ directory (YAML) with automatic format detection.
"""

import json
from pathlib import Path
from typing import Any

import yaml


# Directory paths
STYLES_DIR = Path(__file__).parent.parent.parent / "styles"
PRESETS_DIR = Path(__file__).parent.parent.parent / "presets"  # Legacy YAML


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


def _convert_yaml_to_unified(yaml_data: dict[str, Any]) -> dict[str, Any]:
    """Convert legacy YAML preset format to unified JSON format.

    Legacy YAML format:
        colors: {primary, accent, ...}
        typography: {font_family, heading1_size (half-points), body_size, ...}
        spacing: {section_before (twips), section_after, paragraph_after}
        contact: {company, tagline, email}

    Unified JSON format:
        colors: {primary, accent, ...}
        fonts: {heading: {name, bold}, body: {name, size (points)}, ...}
        styles: {heading1: {font: {...}, spacing: {...}}, ...}
        tables: {...}
        lists: {...}
        contact: {...}
    """
    result = {
        "metadata": {
            "name": yaml_data.get("name", "converted"),
            "description": yaml_data.get("description", "Converted from YAML preset")
        },
        "page": {
            "size": "letter",
            "margins": {"top": "1in", "right": "1in", "bottom": "1in", "left": "1in"}
        },
        "colors": yaml_data.get("colors", DEFAULT_STYLE["colors"]).copy(),
        "fonts": {},
        "styles": {},
        "tables": DEFAULT_STYLE["tables"].copy(),
        "lists": DEFAULT_STYLE["lists"].copy(),
        "contact": yaml_data.get("contact", {})
    }

    # Convert typography section
    typography = yaml_data.get("typography", {})
    font_family = typography.get("font_family", "Arial")

    # Font definitions
    result["fonts"] = {
        "heading": {"name": font_family, "bold": True},
        "body": {"name": font_family, "size": typography.get("body_size", 22) / 2},  # half-points to points
        "mono": {"name": "Courier New", "size": typography.get("small_size", 18) / 2}
    }

    # Convert spacing (twips to points: 1 point = 20 twips)
    spacing = yaml_data.get("spacing", {})
    section_before = spacing.get("section_before", 400) / 20
    section_after = spacing.get("section_after", 200) / 20
    paragraph_after = spacing.get("paragraph_after", 120) / 20

    # Build styles section
    primary_color = result["colors"].get("primary", "#333333")
    text_color = result["colors"].get("text", "#333333")
    accent_color = result["colors"].get("accent", "#E07A38")

    result["styles"] = {
        "title": {
            "font": {
                "name": font_family,
                "size": typography.get("heading1_size", 28) / 2,
                "bold": True,
                "color": "primary"
            },
            "alignment": "center",
            "spacing": {"after": section_after}
        },
        "subtitle": {
            "font": {
                "name": font_family,
                "size": typography.get("heading2_size", 24) / 2,
                "color": "primary"
            },
            "alignment": "center",
            "spacing": {"after": section_after}
        },
        "heading1": {
            "font": {
                "name": font_family,
                "size": typography.get("heading1_size", 28) / 2,
                "bold": True,
                "color": "primary"
            },
            "spacing": {"before": section_before, "after": section_after}
        },
        "heading2": {
            "font": {
                "name": font_family,
                "size": typography.get("heading2_size", 24) / 2,
                "bold": True,
                "color": "primary"
            },
            "spacing": {"before": section_before * 0.75, "after": section_after}
        },
        "heading3": {
            "font": {
                "name": font_family,
                "size": typography.get("heading3_size", 20) / 2,
                "bold": True,
                "color": "accent"
            },
            "spacing": {"before": section_before * 0.5, "after": section_after}
        },
        "body": {
            "font": {
                "name": font_family,
                "size": typography.get("body_size", 22) / 2,
                "color": "text"
            },
            "spacing": {"after": paragraph_after}
        },
        "bullet": {
            "font": {
                "name": font_family,
                "size": typography.get("body_size", 22) / 2,
                "color": "text"
            },
            "spacing": {"after": paragraph_after * 0.5}
        }
    }

    # Update table header background to use primary color
    result["tables"]["default"]["headerRow"]["background"] = "primary"
    result["tables"]["default"]["headerRow"]["font"] = {"color": "#FFFFFF", "bold": True}

    return result


def load_style(name_or_path: str | Path | None = None) -> dict[str, Any]:
    """Load a style configuration by name or file path.

    Resolution order:
    1. If None, return default style
    2. If absolute path, load directly (JSON or YAML)
    3. Check styles/ for {name}.json
    4. Check presets/ for {name}.yaml (legacy, auto-converted)
    5. Return default style with warning

    Args:
        name_or_path: Style name (e.g., "professional") or path to config file

    Returns:
        Style configuration dictionary in unified format
    """
    if name_or_path is None:
        return DEFAULT_STYLE.copy()

    path = Path(name_or_path)

    # If it's an absolute path or relative path that exists
    if path.is_absolute() or path.exists():
        return _load_file(path)

    # Try styles/ directory (JSON - primary)
    json_path = STYLES_DIR / f"{name_or_path}.json"
    if json_path.exists():
        return _load_file(json_path)

    # Try presets/ directory (YAML - legacy)
    yaml_path = PRESETS_DIR / f"{name_or_path}.yaml"
    if yaml_path.exists():
        return _load_file(yaml_path)

    # Also try .yml extension
    yml_path = PRESETS_DIR / f"{name_or_path}.yml"
    if yml_path.exists():
        return _load_file(yml_path)

    # Not found - return default
    print(f"Warning: Style '{name_or_path}' not found, using default")
    return DEFAULT_STYLE.copy()


def _load_file(path: Path) -> dict[str, Any]:
    """Load a style file (JSON or YAML) and return unified format."""
    if not path.exists():
        raise FileNotFoundError(f"Style file not found: {path}")

    suffix = path.suffix.lower()

    with open(path, "r", encoding="utf-8") as f:
        if suffix == ".json":
            data = json.load(f)
            # Already in unified format
            return _merge_with_defaults(data)
        elif suffix in (".yaml", ".yml"):
            data = yaml.safe_load(f)
            # Check if it's legacy format (has 'typography' key)
            if "typography" in data or "spacing" in data:
                return _convert_yaml_to_unified(data)
            # Otherwise assume it's already unified format
            return _merge_with_defaults(data)
        else:
            raise ValueError(f"Unsupported file format: {suffix}")


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


def list_styles() -> list[dict[str, Any]]:
    """List all available styles with their metadata.

    Returns:
        List of dicts with 'name', 'path', 'format', and 'description'
    """
    styles = []

    # JSON styles (primary)
    if STYLES_DIR.exists():
        for json_file in STYLES_DIR.glob("*.json"):
            try:
                with open(json_file) as f:
                    data = json.load(f)
                metadata = data.get("metadata", {})
                styles.append({
                    "name": json_file.stem,
                    "path": str(json_file),
                    "format": "json",
                    "description": metadata.get("description", "")
                })
            except Exception:
                styles.append({
                    "name": json_file.stem,
                    "path": str(json_file),
                    "format": "json",
                    "description": "(failed to load metadata)"
                })

    # YAML presets (legacy)
    if PRESETS_DIR.exists():
        for yaml_file in PRESETS_DIR.glob("*.yaml"):
            # Skip if we already have a JSON version
            if any(s["name"] == yaml_file.stem for s in styles):
                continue
            try:
                with open(yaml_file) as f:
                    data = yaml.safe_load(f)
                styles.append({
                    "name": yaml_file.stem,
                    "path": str(yaml_file),
                    "format": "yaml (legacy)",
                    "description": data.get("description", "")
                })
            except Exception:
                styles.append({
                    "name": yaml_file.stem,
                    "path": str(yaml_file),
                    "format": "yaml (legacy)",
                    "description": "(failed to load metadata)"
                })

    return sorted(styles, key=lambda x: x["name"])

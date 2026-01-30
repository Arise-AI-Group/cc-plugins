"""Brand preset loading for document builders.

DEPRECATED: This module is deprecated. Use tool.styling instead:

    from tool.styling import load_style, StyleResolver

    # Load a style (JSON or YAML)
    style_config = load_style("professional")

    # Create resolver for the style
    resolver = StyleResolver(style_config)

    # Get colors, fonts, styles
    primary_color = resolver.resolve_color("primary")
    body_font = resolver.get_body_font()

This module is kept for backward compatibility with existing code.
"""

import warnings
from pathlib import Path
from typing import Any
import yaml

# Emit deprecation warning on import
warnings.warn(
    "tool.builder_common.presets is deprecated. Use tool.styling instead.",
    DeprecationWarning,
    stacklevel=2
)


def get_presets_dir() -> Path:
    """Get the presets directory."""
    return Path(__file__).parent.parent.parent / "presets"


def list_presets() -> list[str]:
    """List available preset names."""
    presets_dir = get_presets_dir()
    if not presets_dir.exists():
        return []
    return [f.stem for f in presets_dir.glob("*.yaml")]


def load_preset(name: str) -> dict[str, Any]:
    """Load a preset by name.

    Args:
        name: Preset name (without .yaml extension)

    Returns:
        Preset dictionary with colors, typography, spacing, contact

    Raises:
        FileNotFoundError: If preset doesn't exist
    """
    preset_path = get_presets_dir() / f"{name}.yaml"
    if not preset_path.exists():
        raise FileNotFoundError(f"Preset '{name}' not found at {preset_path}")

    with open(preset_path) as f:
        return yaml.safe_load(f)


def get_color(preset: dict[str, Any], key: str, default: str = "#333333") -> str:
    """Get a color from preset, with fallback.

    Args:
        preset: Loaded preset dictionary
        key: Color key (primary, accent, light, text, muted, success, warning)
        default: Default color if not found

    Returns:
        Hex color string
    """
    return preset.get("colors", {}).get(key, default)


def get_typography(preset: dict[str, Any], key: str, default: Any = None) -> Any:
    """Get typography setting from preset.

    Args:
        preset: Loaded preset dictionary
        key: Typography key (font_family, heading1_size, body_size, etc.)
        default: Default value if not found

    Returns:
        Typography setting value
    """
    defaults = {
        "font_family": "Arial",
        "heading1_size": 28,
        "heading2_size": 24,
        "heading3_size": 20,
        "body_size": 22,
        "small_size": 18,
    }
    return preset.get("typography", {}).get(key, defaults.get(key, default))


def get_spacing(preset: dict[str, Any], key: str, default: int = 0) -> int:
    """Get spacing setting from preset.

    Args:
        preset: Loaded preset dictionary
        key: Spacing key (section_before, section_after, paragraph_after)
        default: Default value in twips

    Returns:
        Spacing in twips
    """
    defaults = {
        "section_before": 400,
        "section_after": 200,
        "paragraph_after": 120,
    }
    return preset.get("spacing", {}).get(key, defaults.get(key, default))


def get_contact(preset: dict[str, Any], key: str, default: str = "") -> str:
    """Get contact info from preset.

    Args:
        preset: Loaded preset dictionary
        key: Contact key (company, tagline, email)
        default: Default value if not found

    Returns:
        Contact info string
    """
    return preset.get("contact", {}).get(key, default)


# Default preset values (used when no preset is loaded)
DEFAULT_PRESET: dict[str, Any] = {
    "name": "default",
    "description": "Default neutral professional style",
    "colors": {
        "primary": "#2C3E50",
        "accent": "#3498DB",
        "light": "#ECF0F1",
        "text": "#333333",
        "muted": "#7F8C8D",
        "success": "#27AE60",
        "warning": "#E67E22",
    },
    "typography": {
        "font_family": "Arial",
        "heading1_size": 28,
        "heading2_size": 24,
        "heading3_size": 20,
        "body_size": 22,
        "small_size": 18,
    },
    "spacing": {
        "section_before": 400,
        "section_after": 200,
        "paragraph_after": 120,
    },
    "contact": {
        "company": "",
        "tagline": "",
        "email": "",
    },
}

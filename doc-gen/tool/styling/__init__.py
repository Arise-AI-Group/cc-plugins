"""Unified styling module for DOCX document generation.

This module provides a unified system for loading style configurations
(JSON or YAML) and applying them to python-docx elements.

Main components:
    - loader: Load styles from JSON (primary) or YAML (legacy)
    - resolver: Resolve named colors and get element styles
    - applicators: Apply styles to runs, paragraphs, and cells

Example usage:
    from tool.styling import load_style, StyleResolver, apply_run_style

    # Load a style configuration
    config = load_style("professional")

    # Create a resolver for the style
    resolver = StyleResolver(config)

    # Resolve a named color
    color = resolver.resolve_color("primary")

    # Get font configuration for an element
    font_config = resolver.get_font_config("heading1")

    # Apply styles to a run
    apply_run_style(run, font_config, resolver)
"""

from .loader import (
    load_style,
    list_styles,
    DEFAULT_STYLE,
    STYLES_DIR,
    PRESETS_DIR,
)

from .resolver import StyleResolver

from .applicators import (
    apply_run_style,
    apply_paragraph_style,
    apply_element_style,
    apply_cell_style,
    apply_table_header_style,
    apply_table_body_style,
    set_cell_background,
    set_cell_borders,
    get_alignment,
    ALIGNMENTS,
)

__all__ = [
    # Loader
    "load_style",
    "list_styles",
    "DEFAULT_STYLE",
    "STYLES_DIR",
    "PRESETS_DIR",
    # Resolver
    "StyleResolver",
    # Applicators
    "apply_run_style",
    "apply_paragraph_style",
    "apply_element_style",
    "apply_cell_style",
    "apply_table_header_style",
    "apply_table_body_style",
    "set_cell_background",
    "set_cell_borders",
    "get_alignment",
    "ALIGNMENTS",
]

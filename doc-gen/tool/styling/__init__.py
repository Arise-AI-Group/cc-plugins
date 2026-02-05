"""Unified styling module for DOCX document generation.

This module provides a unified system for loading style configurations
with multi-layer resolution (defaults < brand < project < CLI).

Main components:
    - loader: Load and merge styles from multiple sources
    - resolver: Resolve named colors and get element styles
    - applicators: Apply styles to runs, paragraphs, and cells

Example usage:
    from tool.styling import load_layered_style, StyleResolver, apply_run_style

    # Load style with multi-layer resolution
    config = load_layered_style(brand="40hero")

    # Or load a simple single-file style
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
    # Single-file loading
    load_style,
    list_styles,
    DEFAULT_STYLE,
    STYLES_DIR,
    # Multi-layer loading
    load_layered_style,
    deep_merge,
    deep_merge_all,
    # Brand management
    list_brands,
    load_brand_style,
    get_default_brand,
    # Project config
    find_project_config,
    load_project_style,
    # Config utilities
    get_config_dir,
    ensure_config_dir,
    get_global_config,
    CONFIG_DIR,
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
    # Single-file loading
    "load_style",
    "list_styles",
    "DEFAULT_STYLE",
    "STYLES_DIR",
    # Multi-layer loading
    "load_layered_style",
    "deep_merge",
    "deep_merge_all",
    # Brand management
    "list_brands",
    "load_brand_style",
    "get_default_brand",
    # Project config
    "find_project_config",
    "load_project_style",
    # Config utilities
    "get_config_dir",
    "ensure_config_dir",
    "get_global_config",
    "CONFIG_DIR",
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

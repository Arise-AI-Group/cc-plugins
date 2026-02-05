#!/usr/bin/env python3
"""DOCX Builder CLI - Programmatic document construction tool.

Stateless CLI for building professional DOCX documents element by element.
Each command operates on a document file path, enabling Claude to construct
documents with full control over formatting and layout.

Supports multi-layer styling:
- Plugin defaults (built-in)
- User brands (~/.config/doc-gen/brands/)
- Project overrides (.doc-gen/brand.json)
- CLI overrides (--color-*, --font-*)

Usage:
    # Create with brand
    ./run tool/docx_builder/cli.py create output.docx --brand 40hero

    # Create with CLI overrides
    ./run tool/docx_builder/cli.py create output.docx --brand 40hero --color-primary "#FF0000"

    # Legacy: create with preset (still supported)
    ./run tool/docx_builder/cli.py create output.docx --preset 40hero

    # Add content
    ./run tool/docx_builder/cli.py add-heading output.docx "PROPOSAL" --level 1
    ./run tool/docx_builder/cli.py add-paragraph output.docx "Introduction text..."
    ./run tool/docx_builder/cli.py add-bullet-list output.docx --items '["Item 1", "Item 2"]'
    ./run tool/docx_builder/cli.py add-table output.docx --data '[["A","B"],["1","2"]]' --header-row

    # List brands
    ./run tool/docx_builder/cli.py list-brands
"""

import argparse
import json
import sys
from pathlib import Path


def json_output(data: dict, output_format: str = "json") -> None:
    """Output result in specified format."""
    if output_format == "json":
        print(json.dumps(data, indent=2))
    else:
        # Text format - simple key: value pairs
        for key, value in data.items():
            print(f"{key}: {value}")


def build_overrides_from_args(args) -> dict | None:
    """Build overrides dict from CLI args.

    Args:
        args: Parsed argparse namespace

    Returns:
        Overrides dict or None if no overrides specified
    """
    overrides = {}

    # Color overrides
    colors = {}
    for color_name in ["primary", "accent", "text", "muted", "success", "danger", "border"]:
        arg_name = f"color_{color_name}"
        value = getattr(args, arg_name, None)
        if value:
            colors[color_name] = value

    if colors:
        overrides["colors"] = colors

    # Font overrides
    fonts = {}
    if getattr(args, "font_heading", None):
        fonts["heading"] = {"name": args.font_heading}
    if getattr(args, "font_body", None):
        fonts["body"] = {"name": args.font_body}

    if fonts:
        overrides["fonts"] = fonts

    return overrides if overrides else None


def cmd_create(args) -> dict:
    """Create a new document."""
    from .core import create_document

    margins = None
    if args.margins:
        margins = json.loads(args.margins)

    # Build overrides from CLI flags
    overrides = build_overrides_from_args(args)

    return create_document(
        output_path=args.path,
        preset=args.preset,
        brand=args.brand,
        page_size=args.page_size,
        margins=margins,
        overrides=overrides,
        use_project_config=not getattr(args, "no_project_config", False),
    )


def cmd_info(args) -> dict:
    """Get document info."""
    from .core import get_document_metadata

    return get_document_metadata(args.path)


def cmd_finalize(args) -> dict:
    """Finalize document."""
    from .core import finalize_document

    return finalize_document(args.path, cleanup_metadata=args.cleanup)


def cmd_add_heading(args) -> dict:
    """Add a heading."""
    from .content import add_heading

    return add_heading(
        doc_path=args.path,
        text=args.text,
        level=args.level,
        color=args.color,
        font=args.font,
        alignment=args.alignment,
        spacing_before=args.spacing_before,
        spacing_after=args.spacing_after,
    )


def cmd_add_paragraph(args) -> dict:
    """Add a paragraph."""
    from .content import add_paragraph

    return add_paragraph(
        doc_path=args.path,
        text=args.text,
        bold=args.bold,
        italic=args.italic,
        color=args.color,
        font=args.font,
        font_size=args.font_size,
        alignment=args.alignment,
        spacing_after=args.spacing_after,
    )


def cmd_add_bullet_list(args) -> dict:
    """Add a bullet list."""
    from .content import add_bullet_list

    items = json.loads(args.items)
    return add_bullet_list(
        doc_path=args.path,
        items=items,
        style=args.style,
        color=args.color,
        font=args.font,
        font_size=args.font_size,
    )


def cmd_add_numbered_list(args) -> dict:
    """Add a numbered list."""
    from .content import add_numbered_list

    items = json.loads(args.items)
    return add_numbered_list(
        doc_path=args.path,
        items=items,
        start=args.start,
        color=args.color,
        font=args.font,
        font_size=args.font_size,
    )


def cmd_add_table(args) -> dict:
    """Add a table."""
    from .tables import add_table

    data = json.loads(args.data)
    column_widths = json.loads(args.column_widths) if args.column_widths else None
    style = json.loads(args.style) if args.style else None

    return add_table(
        doc_path=args.path,
        data=data,
        header_row=args.header_row,
        column_widths=column_widths,
        style=style,
    )


def cmd_list_brands(args) -> dict:
    """List available brands."""
    from ..styling import list_brands, get_global_config

    brands = list_brands()
    default_brand = get_global_config().get("default_brand")

    # Mark default brand
    for brand in brands:
        brand["is_default"] = brand["name"] == default_brand

    return {
        "success": True,
        "brands": brands,
        "default_brand": default_brand,
        "count": len(brands)
    }


def cmd_setup_header_footer(args) -> dict:
    """Set up header and/or footer for a document."""
    from .content import setup_header_footer
    from .core import load_document

    # Load document to get style config
    _, metadata = load_document(args.path)
    style_config = metadata.get("style_config", metadata.get("preset_data", {}))

    header_config = None
    footer_config = None

    if args.from_brand:
        # Use config from brand
        header_config = style_config.get("header")
        footer_config = style_config.get("footer")
    else:
        # Build from CLI args
        if not args.no_header and args.header_text:
            header_config = {
                "enabled": True,
                "text": args.header_text,
                "position": args.header_position,
            }
        elif args.no_header:
            header_config = {"enabled": False}

        if not args.no_footer:
            footer_config = {
                "enabled": True,
                "text": args.footer_text or "Page {{ page }}",
                "position": args.footer_position,
            }
        elif args.no_footer:
            footer_config = {"enabled": False}

    return setup_header_footer(
        doc_path=args.path,
        header_config=header_config,
        footer_config=footer_config,
    )


def main():
    parser = argparse.ArgumentParser(
        description="DOCX Builder - Programmatic document construction",
        formatter_class=argparse.RawDescriptionHelpFormatter,
    )
    parser.add_argument(
        "--output-format", "-f",
        choices=["json", "text"],
        default="json",
        help="Output format (default: json)",
    )

    subparsers = parser.add_subparsers(dest="command", help="Commands")

    # create command
    create_parser = subparsers.add_parser("create", help="Create new document")
    create_parser.add_argument("path", help="Output path for document")
    create_parser.add_argument("--brand", "-b", help="Brand name from ~/.config/doc-gen/brands/")
    create_parser.add_argument("--preset", "-p", help="Legacy preset name (superseded by --brand)")
    create_parser.add_argument("--page-size", default="letter", choices=["letter", "a4"])
    create_parser.add_argument("--margins", help='JSON margins: {"top": 1, "right": 1, ...}')
    create_parser.add_argument("--no-project-config", action="store_true",
                               help="Disable auto-detection of .doc-gen/brand.json")
    # Color overrides
    create_parser.add_argument("--color-primary", help="Primary color (hex, e.g., #1E3A5F)")
    create_parser.add_argument("--color-accent", help="Accent color (hex)")
    create_parser.add_argument("--color-text", help="Text color (hex)")
    create_parser.add_argument("--color-muted", help="Muted/secondary text color (hex)")
    create_parser.add_argument("--color-success", help="Success color (hex)")
    create_parser.add_argument("--color-danger", help="Danger/error color (hex)")
    create_parser.add_argument("--color-border", help="Border color (hex)")
    # Font overrides
    create_parser.add_argument("--font-heading", help="Heading font family")
    create_parser.add_argument("--font-body", help="Body font family")
    create_parser.set_defaults(func=cmd_create)

    # info command
    info_parser = subparsers.add_parser("info", help="Get document info")
    info_parser.add_argument("path", help="Document path")
    info_parser.set_defaults(func=cmd_info)

    # finalize command
    finalize_parser = subparsers.add_parser("finalize", help="Finalize document")
    finalize_parser.add_argument("path", help="Document path")
    finalize_parser.add_argument("--cleanup", action="store_true", help="Remove metadata file")
    finalize_parser.set_defaults(func=cmd_finalize)

    # add-heading command
    heading_parser = subparsers.add_parser("add-heading", help="Add heading")
    heading_parser.add_argument("path", help="Document path")
    heading_parser.add_argument("text", help="Heading text")
    heading_parser.add_argument("--level", "-l", type=int, default=1, choices=[1, 2, 3])
    heading_parser.add_argument("--color", "-c", help="Hex color (e.g., #1E3A5F)")
    heading_parser.add_argument("--font", help="Font name")
    heading_parser.add_argument("--alignment", "-a", default="left",
                                 choices=["left", "center", "right", "justify"])
    heading_parser.add_argument("--spacing-before", type=int, help="Spacing before (twips)")
    heading_parser.add_argument("--spacing-after", type=int, help="Spacing after (twips)")
    heading_parser.set_defaults(func=cmd_add_heading)

    # add-paragraph command
    para_parser = subparsers.add_parser("add-paragraph", help="Add paragraph")
    para_parser.add_argument("path", help="Document path")
    para_parser.add_argument("text", help="Paragraph text")
    para_parser.add_argument("--bold", "-b", action="store_true")
    para_parser.add_argument("--italic", "-i", action="store_true")
    para_parser.add_argument("--color", "-c", help="Hex color")
    para_parser.add_argument("--font", help="Font name")
    para_parser.add_argument("--font-size", type=int, help="Size in half-points (22 = 11pt)")
    para_parser.add_argument("--alignment", "-a", default="left",
                              choices=["left", "center", "right", "justify"])
    para_parser.add_argument("--spacing-after", type=int, help="Spacing after (twips)")
    para_parser.set_defaults(func=cmd_add_paragraph)

    # add-bullet-list command
    bullet_parser = subparsers.add_parser("add-bullet-list", help="Add bullet list")
    bullet_parser.add_argument("path", help="Document path")
    bullet_parser.add_argument("--items", required=True, help='JSON array: ["item1", "item2"]')
    bullet_parser.add_argument("--style", default="bullet",
                                choices=["bullet", "checkmark", "dash", "x"])
    bullet_parser.add_argument("--color", "-c", help="Hex color")
    bullet_parser.add_argument("--font", help="Font name")
    bullet_parser.add_argument("--font-size", type=int, help="Size in half-points")
    bullet_parser.set_defaults(func=cmd_add_bullet_list)

    # add-numbered-list command
    num_parser = subparsers.add_parser("add-numbered-list", help="Add numbered list")
    num_parser.add_argument("path", help="Document path")
    num_parser.add_argument("--items", required=True, help='JSON array: ["item1", "item2"]')
    num_parser.add_argument("--start", type=int, default=1, help="Starting number")
    num_parser.add_argument("--color", "-c", help="Hex color")
    num_parser.add_argument("--font", help="Font name")
    num_parser.add_argument("--font-size", type=int, help="Size in half-points")
    num_parser.set_defaults(func=cmd_add_numbered_list)

    # add-table command
    table_parser = subparsers.add_parser("add-table", help="Add table")
    table_parser.add_argument("path", help="Document path")
    table_parser.add_argument("--data", required=True, help='JSON 2D array: [["a","b"],["1","2"]]')
    table_parser.add_argument("--header-row", action="store_true", help="Style first row as header")
    table_parser.add_argument("--column-widths", help="JSON array of widths in inches")
    table_parser.add_argument("--style", help='JSON style: {"header_bg": "#1E3A5F", ...}')
    table_parser.set_defaults(func=cmd_add_table)

    # list-brands command
    brands_parser = subparsers.add_parser("list-brands", help="List available brands")
    brands_parser.set_defaults(func=cmd_list_brands)

    # setup-header-footer command
    hf_parser = subparsers.add_parser("setup-header-footer",
                                       help="Configure document header and footer")
    hf_parser.add_argument("path", help="Document path")
    hf_parser.add_argument("--header-text", help="Header text (supports {{ variables }})")
    hf_parser.add_argument("--header-position", choices=["left", "center", "right"],
                           default="right", help="Header alignment")
    hf_parser.add_argument("--no-header", action="store_true", help="Disable header")
    hf_parser.add_argument("--footer-text", help="Footer text (supports {{ page }})")
    hf_parser.add_argument("--footer-position", choices=["left", "center", "right"],
                           default="center", help="Footer alignment")
    hf_parser.add_argument("--no-footer", action="store_true", help="Disable footer")
    hf_parser.add_argument("--from-brand", action="store_true",
                           help="Use header/footer config from document's brand")
    hf_parser.set_defaults(func=cmd_setup_header_footer)

    args = parser.parse_args()

    if not args.command:
        parser.print_help()
        sys.exit(1)

    try:
        result = args.func(args)
        json_output(result, args.output_format)
        sys.exit(0 if result.get("success", True) else 1)
    except FileNotFoundError as e:
        json_output({"success": False, "error": str(e)}, args.output_format)
        sys.exit(1)
    except json.JSONDecodeError as e:
        json_output({"success": False, "error": f"Invalid JSON: {e}"}, args.output_format)
        sys.exit(1)
    except Exception as e:
        json_output({"success": False, "error": str(e)}, args.output_format)
        sys.exit(1)


if __name__ == "__main__":
    main()

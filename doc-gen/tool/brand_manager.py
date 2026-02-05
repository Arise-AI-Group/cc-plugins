#!/usr/bin/env python3
"""Brand management for doc-gen styling system.

Provides CRUD operations for managing brands stored in ~/.config/doc-gen/brands/.

Each brand is a directory containing:
- brand.json: Style configuration
- reference.docx: Original reference document (optional)
- assets/: Logo and other assets (optional)

Usage:
    ./run tool/brand_manager.py list
    ./run tool/brand_manager.py create mybrand
    ./run tool/brand_manager.py show mybrand
    ./run tool/brand_manager.py set-default mybrand
    ./run tool/brand_manager.py delete mybrand
    ./run tool/brand_manager.py copy source dest
"""

import argparse
import json
import shutil
import sys
from pathlib import Path
from typing import Any

# Add parent to path for imports
sys.path.insert(0, str(Path(__file__).parent))

from styling.loader import (
    ensure_config_dir,
    get_config_dir,
    get_global_config,
    list_brands,
    load_brand_style,
    DEFAULT_STYLE,
)


def json_output(data: dict, output_format: str = "json") -> None:
    """Output result in specified format."""
    if output_format == "json":
        print(json.dumps(data, indent=2))
    else:
        # Text format
        if "brands" in data:
            for brand in data["brands"]:
                print(f"{brand['name']}: {brand.get('description', '')}")
        elif "error" in data:
            print(f"Error: {data['error']}")
        else:
            for key, value in data.items():
                if isinstance(value, dict):
                    print(f"{key}:")
                    for k, v in value.items():
                        print(f"  {k}: {v}")
                else:
                    print(f"{key}: {value}")


def get_default_brand_template() -> dict[str, Any]:
    """Get a clean default brand template.

    Returns:
        Brand config suitable for brand.json
    """
    return {
        "metadata": {
            "name": "",
            "description": ""
        },
        "colors": DEFAULT_STYLE["colors"].copy(),
        "fonts": DEFAULT_STYLE["fonts"].copy(),
        "styles": DEFAULT_STYLE["styles"].copy(),
        "tables": DEFAULT_STYLE["tables"].copy(),
        "lists": DEFAULT_STYLE["lists"].copy(),
        "contact": {
            "company": "",
            "company_short": "",
            "tagline": "",
            "name": "",
            "email": "",
            "phone": "",
            "website": ""
        },
        "header": {
            "enabled": False,
            "text": "",
            "position": "right",
            "font_size": 10,
            "color": "muted"
        },
        "footer": {
            "enabled": True,
            "text": "Page {{ page }}",
            "position": "center",
            "font_size": 9,
            "color": "muted"
        },
        "assets": {
            "logo": None,
            "logo_width": "1.5in"
        },
        "page": DEFAULT_STYLE["page"].copy()
    }


def cmd_list(args) -> dict:
    """List all available brands."""
    ensure_config_dir()
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


def cmd_create(args) -> dict:
    """Create a new brand."""
    ensure_config_dir()
    brand_dir = get_config_dir() / "brands" / args.name
    brand_file = brand_dir / "brand.json"

    if brand_dir.exists():
        return {
            "success": False,
            "error": f"Brand '{args.name}' already exists"
        }

    # Create brand directory
    brand_dir.mkdir(parents=True)
    (brand_dir / "assets").mkdir()

    # Load from source: DOCX extraction, JSON file, or default template
    source_type = "template"
    if getattr(args, "from_docx", None):
        from style_extractor import extract_styles_from_docx
        docx_path = Path(args.from_docx)
        if not docx_path.exists():
            shutil.rmtree(brand_dir)  # Clean up
            return {
                "success": False,
                "error": f"DOCX file not found: {args.from_docx}"
            }
        # Extract styles from DOCX
        brand_config = extract_styles_from_docx(docx_path)
        # Copy reference DOCX to brand directory
        shutil.copy(docx_path, brand_dir / "reference.docx")
        source_type = "docx"
    elif args.from_json:
        from_path = Path(args.from_json)
        if not from_path.exists():
            shutil.rmtree(brand_dir)  # Clean up
            return {
                "success": False,
                "error": f"Source file not found: {args.from_json}"
            }
        with open(from_path, "r", encoding="utf-8") as f:
            brand_config = json.load(f)
        source_type = "json"
    else:
        brand_config = get_default_brand_template()

    # Set metadata
    brand_config.setdefault("metadata", {})
    brand_config["metadata"]["name"] = args.name
    if args.description:
        brand_config["metadata"]["description"] = args.description

    # Write brand.json
    with open(brand_file, "w", encoding="utf-8") as f:
        json.dump(brand_config, f, indent=2)

    return {
        "success": True,
        "operation": "create",
        "name": args.name,
        "path": str(brand_dir),
        "source_type": source_type,
        "message": f"Created brand '{args.name}' from {source_type}"
    }


def cmd_show(args) -> dict:
    """Show brand details."""
    brand_config = load_brand_style(args.name)

    if brand_config is None:
        return {
            "success": False,
            "error": f"Brand '{args.name}' not found"
        }

    brand_dir = get_config_dir() / "brands" / args.name
    default_brand = get_global_config().get("default_brand")

    return {
        "success": True,
        "name": args.name,
        "path": str(brand_dir),
        "is_default": args.name == default_brand,
        "config": brand_config
    }


def cmd_set_default(args) -> dict:
    """Set the default brand."""
    # Verify brand exists
    brand_config = load_brand_style(args.name)
    if brand_config is None:
        return {
            "success": False,
            "error": f"Brand '{args.name}' not found"
        }

    # Update config.json
    config_file = get_config_dir() / "config.json"
    config = get_global_config()
    config["default_brand"] = args.name

    with open(config_file, "w", encoding="utf-8") as f:
        json.dump(config, f, indent=2)

    return {
        "success": True,
        "operation": "set-default",
        "name": args.name,
        "message": f"Set '{args.name}' as default brand"
    }


def cmd_delete(args) -> dict:
    """Delete a brand."""
    brand_dir = get_config_dir() / "brands" / args.name

    if not brand_dir.exists():
        return {
            "success": False,
            "error": f"Brand '{args.name}' not found"
        }

    # Check if it's the default
    config = get_global_config()
    was_default = config.get("default_brand") == args.name

    # Remove directory
    shutil.rmtree(brand_dir)

    # Clear default if needed
    if was_default:
        config["default_brand"] = None
        config_file = get_config_dir() / "config.json"
        with open(config_file, "w", encoding="utf-8") as f:
            json.dump(config, f, indent=2)

    return {
        "success": True,
        "operation": "delete",
        "name": args.name,
        "was_default": was_default,
        "message": f"Deleted brand '{args.name}'"
    }


def cmd_copy(args) -> dict:
    """Copy an existing brand to create a new one."""
    source_dir = get_config_dir() / "brands" / args.source
    dest_dir = get_config_dir() / "brands" / args.dest

    if not source_dir.exists():
        return {
            "success": False,
            "error": f"Source brand '{args.source}' not found"
        }

    if dest_dir.exists():
        return {
            "success": False,
            "error": f"Destination brand '{args.dest}' already exists"
        }

    # Copy entire directory
    shutil.copytree(source_dir, dest_dir)

    # Update metadata in the copy
    brand_file = dest_dir / "brand.json"
    with open(brand_file, "r", encoding="utf-8") as f:
        brand_config = json.load(f)

    brand_config.setdefault("metadata", {})
    brand_config["metadata"]["name"] = args.dest
    brand_config["metadata"]["description"] = f"Copy of {args.source}"

    with open(brand_file, "w", encoding="utf-8") as f:
        json.dump(brand_config, f, indent=2)

    return {
        "success": True,
        "operation": "copy",
        "source": args.source,
        "dest": args.dest,
        "path": str(dest_dir),
        "message": f"Copied '{args.source}' to '{args.dest}'"
    }


def cmd_init(args) -> dict:
    """Initialize the config directory structure."""
    config_dir = ensure_config_dir()

    return {
        "success": True,
        "operation": "init",
        "config_dir": str(config_dir),
        "brands_dir": str(config_dir / "brands"),
        "message": "Initialized doc-gen configuration"
    }


def main():
    parser = argparse.ArgumentParser(
        description="Brand management for doc-gen styling",
        formatter_class=argparse.RawDescriptionHelpFormatter,
    )
    parser.add_argument(
        "--output-format", "-f",
        choices=["json", "text"],
        default="json",
        help="Output format (default: json)",
    )

    subparsers = parser.add_subparsers(dest="command", help="Commands")

    # list command
    list_parser = subparsers.add_parser("list", help="List all brands")
    list_parser.set_defaults(func=cmd_list)

    # create command
    create_parser = subparsers.add_parser("create", help="Create a new brand")
    create_parser.add_argument("name", help="Brand name")
    create_parser.add_argument("--from-docx", help="Extract styles from reference DOCX file")
    create_parser.add_argument("--from-json", help="Initialize from JSON file")
    create_parser.add_argument("--description", "-d", help="Brand description")
    create_parser.set_defaults(func=cmd_create)

    # show command
    show_parser = subparsers.add_parser("show", help="Show brand details")
    show_parser.add_argument("name", help="Brand name")
    show_parser.set_defaults(func=cmd_show)

    # set-default command
    default_parser = subparsers.add_parser("set-default", help="Set default brand")
    default_parser.add_argument("name", help="Brand name")
    default_parser.set_defaults(func=cmd_set_default)

    # delete command
    delete_parser = subparsers.add_parser("delete", help="Delete a brand")
    delete_parser.add_argument("name", help="Brand name")
    delete_parser.set_defaults(func=cmd_delete)

    # copy command
    copy_parser = subparsers.add_parser("copy", help="Copy a brand")
    copy_parser.add_argument("source", help="Source brand name")
    copy_parser.add_argument("dest", help="Destination brand name")
    copy_parser.set_defaults(func=cmd_copy)

    # init command
    init_parser = subparsers.add_parser("init", help="Initialize config directory")
    init_parser.set_defaults(func=cmd_init)

    args = parser.parse_args()

    if not args.command:
        parser.print_help()
        sys.exit(1)

    try:
        result = args.func(args)
        json_output(result, args.output_format)
        sys.exit(0 if result.get("success", True) else 1)
    except Exception as e:
        json_output({"success": False, "error": str(e)}, args.output_format)
        sys.exit(1)


if __name__ == "__main__":
    main()

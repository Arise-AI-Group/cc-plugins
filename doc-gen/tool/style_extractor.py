#!/usr/bin/env python3
"""Extract styling information from reference DOCX documents.

Parses DOCX XML to extract:
- Font families and sizes from styles.xml
- Colors from document.xml
- Header/footer text and formatting

Usage:
    ./run tool/style_extractor.py extract reference.docx
    ./run tool/style_extractor.py extract reference.docx --output brand.json
"""

import argparse
import json
import re
import sys
import tempfile
from collections import Counter
from pathlib import Path
from typing import Any

from lxml import etree

# Add parent to path for imports
sys.path.insert(0, str(Path(__file__).parent))

from office import NAMESPACES
from office.unpack import unpack_docx


def parse_styles_xml(xml_path: Path) -> dict[str, Any]:
    """Parse word/styles.xml to extract font and style information.

    Args:
        xml_path: Path to styles.xml file

    Returns:
        Dict with fonts and styles information
    """
    tree = etree.parse(str(xml_path))
    root = tree.getroot()

    result = {
        "fonts": {},
        "styles": {},
    }

    # Find default font from docDefaults
    doc_defaults = root.find('.//w:docDefaults', NAMESPACES)
    if doc_defaults is not None:
        rpr_default = doc_defaults.find('.//w:rPrDefault/w:rPr', NAMESPACES)
        if rpr_default is not None:
            font = _extract_font_from_rpr(rpr_default)
            if font.get("name"):
                result["fonts"]["body"] = font

    # Find Normal style (base paragraph style)
    normal_style = root.find('.//w:style[@w:styleId="Normal"]', NAMESPACES)
    if normal_style is not None:
        rpr = normal_style.find('w:rPr', NAMESPACES)
        if rpr is not None:
            font = _extract_font_from_rpr(rpr)
            if font:
                result["fonts"]["body"] = {**result["fonts"].get("body", {}), **font}

    # Find heading styles
    for i in range(1, 4):
        style_id = f"Heading{i}"
        heading_style = root.find(f'.//w:style[@w:styleId="{style_id}"]', NAMESPACES)
        if heading_style is not None:
            rpr = heading_style.find('w:rPr', NAMESPACES)
            ppr = heading_style.find('w:pPr', NAMESPACES)

            style_info = {"font": {}}

            if rpr is not None:
                style_info["font"] = _extract_font_from_rpr(rpr)

            if ppr is not None:
                # Extract spacing
                spacing = ppr.find('w:spacing', NAMESPACES)
                if spacing is not None:
                    before = spacing.get('{%s}before' % NAMESPACES['w'])
                    after = spacing.get('{%s}after' % NAMESPACES['w'])
                    if before or after:
                        style_info["spacing"] = {}
                        if before:
                            # Convert twips to points (20 twips = 1 point)
                            style_info["spacing"]["before"] = int(before) / 20
                        if after:
                            style_info["spacing"]["after"] = int(after) / 20

                # Extract alignment
                jc = ppr.find('w:jc', NAMESPACES)
                if jc is not None:
                    alignment = jc.get('{%s}val' % NAMESPACES['w'])
                    if alignment:
                        style_info["alignment"] = alignment

            result["styles"][f"heading{i}"] = style_info

            # Also populate fonts.heading from first heading
            if i == 1 and style_info.get("font"):
                result["fonts"]["heading"] = style_info["font"]

    return result


def _extract_font_from_rpr(rpr: etree._Element) -> dict[str, Any]:
    """Extract font properties from a w:rPr element.

    Args:
        rpr: lxml element for run properties

    Returns:
        Font dict with name, size, bold, italic, color
    """
    font = {}

    # Font name
    fonts_elem = rpr.find('w:rFonts', NAMESPACES)
    if fonts_elem is not None:
        # Try different font attributes in order of preference
        for attr in ['ascii', 'hAnsi', 'cs', 'eastAsia']:
            name = fonts_elem.get('{%s}%s' % (NAMESPACES['w'], attr))
            if name:
                font["name"] = name
                break

    # Font size (in half-points)
    sz = rpr.find('w:sz', NAMESPACES)
    if sz is not None:
        val = sz.get('{%s}val' % NAMESPACES['w'])
        if val:
            # Convert half-points to points
            font["size"] = int(val) / 2

    # Bold
    b = rpr.find('w:b', NAMESPACES)
    if b is not None:
        val = b.get('{%s}val' % NAMESPACES['w'])
        font["bold"] = val != "0" if val else True

    # Italic
    i = rpr.find('w:i', NAMESPACES)
    if i is not None:
        val = i.get('{%s}val' % NAMESPACES['w'])
        font["italic"] = val != "0" if val else True

    # Color
    color = rpr.find('w:color', NAMESPACES)
    if color is not None:
        val = color.get('{%s}val' % NAMESPACES['w'])
        if val and val != "auto":
            font["color"] = f"#{val}"

    return font


def parse_header_footer_xml(xml_path: Path, part_type: str) -> dict[str, Any]:
    """Parse header or footer XML to extract text and formatting.

    Args:
        xml_path: Path to header1.xml or footer1.xml
        part_type: "header" or "footer"

    Returns:
        Dict with enabled, text, position, color, font_size
    """
    tree = etree.parse(str(xml_path))
    root = tree.getroot()

    result = {
        "enabled": True,
        "text": "",
        "position": "center",
    }

    # Find all paragraphs
    paragraphs = root.findall('.//w:p', NAMESPACES)

    texts = []
    alignment = None

    for para in paragraphs:
        # Get alignment
        ppr = para.find('w:pPr', NAMESPACES)
        if ppr is not None:
            jc = ppr.find('w:jc', NAMESPACES)
            if jc is not None:
                alignment = jc.get('{%s}val' % NAMESPACES['w'])

        # Get text content
        for run in para.findall('.//w:r', NAMESPACES):
            # Handle regular text
            t = run.find('w:t', NAMESPACES)
            if t is not None and t.text:
                texts.append(t.text)

            # Handle page number field
            fld_char = run.find('.//w:fldChar', NAMESPACES)
            if fld_char is not None:
                fld_type = fld_char.get('{%s}fldCharType' % NAMESPACES['w'])
                if fld_type == "begin":
                    texts.append("{{ page }}")

            # Handle simple field for page number
            instr = run.find('.//w:instrText', NAMESPACES)
            if instr is not None and instr.text and "PAGE" in instr.text.upper():
                texts.append("{{ page }}")

    # Set text
    result["text"] = "".join(texts).strip()

    # Set position based on alignment
    if alignment:
        alignment_map = {
            "left": "left",
            "center": "center",
            "right": "right",
            "both": "justify",
        }
        result["position"] = alignment_map.get(alignment, "center")

    return {part_type: result}


def extract_color_palette(xml_path: Path) -> list[str]:
    """Extract colors used in document.xml.

    Args:
        xml_path: Path to document.xml

    Returns:
        List of hex color strings (most frequent first)
    """
    tree = etree.parse(str(xml_path))
    root = tree.getroot()

    colors = []

    # Find all color elements
    for color_elem in root.findall('.//w:color', NAMESPACES):
        val = color_elem.get('{%s}val' % NAMESPACES['w'])
        if val and val != "auto" and len(val) == 6:
            colors.append(f"#{val.upper()}")

    # Find highlight colors
    for highlight in root.findall('.//w:highlight', NAMESPACES):
        val = highlight.get('{%s}val' % NAMESPACES['w'])
        # Named colors - we'll skip these for now
        pass

    # Find shading colors (backgrounds)
    for shd in root.findall('.//w:shd', NAMESPACES):
        fill = shd.get('{%s}fill' % NAMESPACES['w'])
        if fill and fill != "auto" and len(fill) == 6:
            colors.append(f"#{fill.upper()}")

    # Count and sort by frequency
    counter = Counter(colors)
    return [color for color, _ in counter.most_common()]


def classify_colors(colors: list[str]) -> dict[str, str]:
    """Classify extracted colors into semantic categories.

    Uses heuristics based on color properties:
    - Darkest saturated color → primary
    - Bright/warm saturated color → accent
    - Dark neutral → text
    - Light neutral → muted

    Args:
        colors: List of hex colors (most frequent first)

    Returns:
        Dict mapping semantic names to hex colors
    """
    if not colors:
        return {}

    result = {}

    def hex_to_rgb(hex_color: str) -> tuple[int, int, int]:
        hex_color = hex_color.lstrip("#")
        return (
            int(hex_color[0:2], 16),
            int(hex_color[2:4], 16),
            int(hex_color[4:6], 16),
        )

    def get_luminance(rgb: tuple[int, int, int]) -> float:
        r, g, b = [x / 255.0 for x in rgb]
        return 0.299 * r + 0.587 * g + 0.114 * b

    def get_saturation(rgb: tuple[int, int, int]) -> float:
        r, g, b = [x / 255.0 for x in rgb]
        max_c = max(r, g, b)
        min_c = min(r, g, b)
        if max_c == 0:
            return 0
        return (max_c - min_c) / max_c

    # Analyze colors
    analyzed = []
    for color in colors:
        rgb = hex_to_rgb(color)
        analyzed.append({
            "color": color,
            "rgb": rgb,
            "luminance": get_luminance(rgb),
            "saturation": get_saturation(rgb),
        })

    # Find primary (darkish, saturated)
    saturated = [c for c in analyzed if c["saturation"] > 0.3]
    if saturated:
        # Prefer darker saturated colors for primary
        saturated.sort(key=lambda x: x["luminance"])
        result["primary"] = saturated[0]["color"]

        # Look for accent (brighter or different hue)
        if len(saturated) > 1:
            # Pick the most different from primary
            primary_rgb = saturated[0]["rgb"]
            best_accent = None
            best_diff = 0
            for c in saturated[1:]:
                diff = sum(abs(a - b) for a, b in zip(primary_rgb, c["rgb"]))
                if diff > best_diff:
                    best_diff = diff
                    best_accent = c["color"]
            if best_accent:
                result["accent"] = best_accent

    # Find text color (dark, low saturation)
    dark_neutrals = [c for c in analyzed if c["luminance"] < 0.4 and c["saturation"] < 0.3]
    if dark_neutrals:
        dark_neutrals.sort(key=lambda x: x["luminance"])
        result["text"] = dark_neutrals[0]["color"]

    # Find muted color (medium luminance, low saturation)
    muted = [c for c in analyzed if 0.3 < c["luminance"] < 0.7 and c["saturation"] < 0.3]
    if muted:
        muted.sort(key=lambda x: x["luminance"])
        result["muted"] = muted[len(muted) // 2]["color"]

    return result


def extract_styles_from_docx(docx_path: Path) -> dict[str, Any]:
    """Extract brand settings from a reference DOCX.

    Args:
        docx_path: Path to reference DOCX file

    Returns:
        Brand config dict compatible with brand.json schema
    """
    import zipfile

    with tempfile.TemporaryDirectory() as temp_dir:
        temp_path = Path(temp_dir)

        # Extract DOCX using zipfile directly (simpler than unpack_docx for read-only)
        with zipfile.ZipFile(docx_path, 'r') as zf:
            zf.extractall(temp_path)

        brand = {
            "metadata": {
                "name": docx_path.stem,
                "description": f"Extracted from {docx_path.name}",
                "source_document": str(docx_path),
            },
            "colors": {},
            "fonts": {},
            "styles": {},
        }

        # Parse styles.xml
        styles_path = temp_path / "word" / "styles.xml"
        if styles_path.exists():
            styles_info = parse_styles_xml(styles_path)
            if styles_info.get("fonts"):
                brand["fonts"] = styles_info["fonts"]
            if styles_info.get("styles"):
                brand["styles"] = styles_info["styles"]

        # Parse header
        header_path = temp_path / "word" / "header1.xml"
        if header_path.exists():
            header_info = parse_header_footer_xml(header_path, "header")
            brand.update(header_info)

        # Parse footer
        footer_path = temp_path / "word" / "footer1.xml"
        if footer_path.exists():
            footer_info = parse_header_footer_xml(footer_path, "footer")
            brand.update(footer_info)

        # Extract and classify colors from document
        doc_path = temp_path / "word" / "document.xml"
        if doc_path.exists():
            colors = extract_color_palette(doc_path)
            classified = classify_colors(colors)
            if classified:
                brand["colors"] = classified
            brand["_extracted_colors"] = colors[:10]  # Keep raw colors for review

        return brand


def cmd_extract(args) -> dict:
    """Extract styles from a DOCX file."""
    docx_path = Path(args.docx)

    if not docx_path.exists():
        return {
            "success": False,
            "error": f"File not found: {args.docx}"
        }

    brand = extract_styles_from_docx(docx_path)

    # Save to file if output specified
    if args.output:
        output_path = Path(args.output)
        with open(output_path, "w", encoding="utf-8") as f:
            json.dump(brand, f, indent=2)
        return {
            "success": True,
            "operation": "extract",
            "source": str(docx_path),
            "output": str(output_path),
            "brand": brand,
        }

    return {
        "success": True,
        "operation": "extract",
        "source": str(docx_path),
        "brand": brand,
    }


def main():
    parser = argparse.ArgumentParser(
        description="Extract styling from reference DOCX files",
        formatter_class=argparse.RawDescriptionHelpFormatter,
    )
    parser.add_argument(
        "--output-format", "-f",
        choices=["json", "text"],
        default="json",
        help="Output format (default: json)",
    )

    subparsers = parser.add_subparsers(dest="command", help="Commands")

    # extract command
    extract_parser = subparsers.add_parser("extract", help="Extract styles from DOCX")
    extract_parser.add_argument("docx", help="Path to reference DOCX file")
    extract_parser.add_argument("--output", "-o", help="Output file path (optional)")
    extract_parser.set_defaults(func=cmd_extract)

    args = parser.parse_args()

    if not args.command:
        parser.print_help()
        sys.exit(1)

    try:
        result = args.func(args)

        if args.output_format == "json":
            print(json.dumps(result, indent=2))
        else:
            if result.get("success"):
                print(f"Source: {result.get('source')}")
                if result.get("output"):
                    print(f"Output: {result.get('output')}")
                brand = result.get("brand", {})
                print(f"\nFonts: {brand.get('fonts', {})}")
                print(f"Colors: {brand.get('colors', {})}")
                if brand.get("header"):
                    print(f"Header: {brand.get('header')}")
                if brand.get("footer"):
                    print(f"Footer: {brand.get('footer')}")
            else:
                print(f"Error: {result.get('error')}")

        sys.exit(0 if result.get("success", True) else 1)

    except Exception as e:
        print(json.dumps({"success": False, "error": str(e)}, indent=2))
        sys.exit(1)


if __name__ == "__main__":
    main()

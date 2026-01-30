"""Content elements for DOCX builder: headings, paragraphs, and lists."""

import re
from pathlib import Path
from typing import Any

from docx.shared import Pt

from .core import load_document, save_document
from ..styling import StyleResolver, apply_run_style, get_alignment


def _parse_markdown_text(text: str) -> list[tuple[str, dict]]:
    """Parse simple markdown formatting (bold, italic) into segments.

    Args:
        text: Text with optional **bold** and *italic* markers

    Returns:
        List of (text, {bold: bool, italic: bool}) tuples
    """
    segments = []
    # Pattern to match **bold**, *italic*, or plain text
    pattern = r"(\*\*[^*]+\*\*|\*[^*]+\*|[^*]+)"

    for match in re.finditer(pattern, text):
        segment = match.group(0)
        if segment.startswith("**") and segment.endswith("**"):
            segments.append((segment[2:-2], {"bold": True, "italic": False}))
        elif segment.startswith("*") and segment.endswith("*"):
            segments.append((segment[1:-1], {"bold": False, "italic": True}))
        else:
            segments.append((segment, {"bold": False, "italic": False}))

    return segments


def add_heading(
    doc_path: str | Path,
    text: str,
    level: int = 1,
    color: str | None = None,
    font: str | None = None,
    alignment: str = "left",
    spacing_before: float | None = None,
    spacing_after: float | None = None,
) -> dict[str, Any]:
    """Add a heading to the document.

    Args:
        doc_path: Path to the DOCX file
        text: Heading text
        level: Heading level (1-3)
        color: Optional hex color (e.g., "#1E3A5F") or named color ("primary")
        font: Optional font name
        alignment: "left", "center", "right", or "justify"
        spacing_before: Optional spacing before in points
        spacing_after: Optional spacing after in points

    Returns:
        Dict with status
    """
    doc, metadata = load_document(doc_path)
    style_config = metadata.get("style_config", metadata.get("preset_data", {}))
    resolver = StyleResolver(style_config)

    # Determine element name for style lookup
    element_name = f"heading{level}" if level > 1 else "title"
    element_style = resolver.get_element_style(element_name)
    font_config = element_style.get("font", {}).copy()

    # Apply overrides
    if font:
        font_config["name"] = font
    if color:
        font_config["color"] = color

    # Create paragraph and add text
    para = doc.add_paragraph()

    # Parse text for markdown formatting
    segments = _parse_markdown_text(text)
    for seg_text, formatting in segments:
        run = para.add_run(seg_text)

        # Build font config for this run
        run_font_config = font_config.copy()
        # Headings are always bold (unless formatting overrides)
        run_font_config["bold"] = run_font_config.get("bold", True) or formatting.get("bold", False)
        run_font_config["italic"] = formatting.get("italic", False)

        apply_run_style(run, run_font_config, resolver)

    # Set alignment
    style_alignment = element_style.get("alignment", alignment)
    para.alignment = get_alignment(style_alignment)

    # Set spacing
    pf = para.paragraph_format
    if spacing_before is not None:
        pf.space_before = Pt(spacing_before)
    else:
        pf.space_before = resolver.get_spacing(element_name, "before")

    if spacing_after is not None:
        pf.space_after = Pt(spacing_after)
    else:
        pf.space_after = resolver.get_spacing(element_name, "after")

    save_document(doc, doc_path)

    return {"success": True, "element": "heading", "level": level, "text": text[:50]}


def add_paragraph(
    doc_path: str | Path,
    text: str,
    bold: bool = False,
    italic: bool = False,
    color: str | None = None,
    font: str | None = None,
    font_size: float | None = None,
    alignment: str = "left",
    spacing_after: float | None = None,
) -> dict[str, Any]:
    """Add a paragraph to the document.

    Args:
        doc_path: Path to the DOCX file
        text: Paragraph text (supports **bold** and *italic* markdown)
        bold: Make entire paragraph bold
        italic: Make entire paragraph italic
        color: Optional hex color or named color
        font: Optional font name
        font_size: Optional font size in points
        alignment: "left", "center", "right", or "justify"
        spacing_after: Optional spacing after in points

    Returns:
        Dict with status
    """
    doc, metadata = load_document(doc_path)
    style_config = metadata.get("style_config", metadata.get("preset_data", {}))
    resolver = StyleResolver(style_config)

    # Get body style
    element_style = resolver.get_element_style("body")
    font_config = element_style.get("font", {}).copy()

    # Apply overrides
    if font:
        font_config["name"] = font
    if font_size is not None:
        font_config["size"] = font_size
    if color:
        font_config["color"] = color

    para = doc.add_paragraph()

    # Parse text for markdown formatting
    segments = _parse_markdown_text(text)
    for seg_text, formatting in segments:
        run = para.add_run(seg_text)

        # Build font config for this run
        run_font_config = font_config.copy()
        run_font_config["bold"] = bold or formatting.get("bold", False)
        run_font_config["italic"] = italic or formatting.get("italic", False)

        apply_run_style(run, run_font_config, resolver)

    # Set alignment
    para.alignment = get_alignment(alignment)

    # Set spacing
    pf = para.paragraph_format
    if spacing_after is not None:
        pf.space_after = Pt(spacing_after)
    else:
        pf.space_after = resolver.get_spacing("body", "after")

    save_document(doc, doc_path)

    return {"success": True, "element": "paragraph", "text": text[:50]}


def add_bullet_list(
    doc_path: str | Path,
    items: list[str],
    style: str = "bullet",
    color: str | None = None,
    font: str | None = None,
    font_size: float | None = None,
) -> dict[str, Any]:
    """Add a bullet list to the document.

    Args:
        doc_path: Path to the DOCX file
        items: List of items (each can contain **bold** markdown)
        style: "bullet", "check", "cross", or "dash"
        color: Optional hex color or named color
        font: Optional font name
        font_size: Optional font size in points

    Returns:
        Dict with status
    """
    doc, metadata = load_document(doc_path)
    style_config = metadata.get("style_config", metadata.get("preset_data", {}))
    resolver = StyleResolver(style_config)

    # Get bullet style and list config
    element_style = resolver.get_element_style("bullet")
    font_config = element_style.get("font", {}).copy()
    list_config = resolver.get_list_config(style)

    # Get bullet symbol and color
    bullet_char = list_config.get("symbol", "\u2022")
    bullet_color = list_config.get("color", "text")

    # Apply overrides
    if font:
        font_config["name"] = font
    if font_size is not None:
        font_config["size"] = font_size
    if color:
        font_config["color"] = color

    for item_text in items:
        para = doc.add_paragraph()

        # Add bullet character with its color
        bullet_run = para.add_run(f"{bullet_char} ")
        bullet_font_config = font_config.copy()
        bullet_font_config["color"] = bullet_color
        bullet_font_config["bold"] = True
        apply_run_style(bullet_run, bullet_font_config, resolver)

        # Parse and add item text
        segments = _parse_markdown_text(item_text)
        for seg_text, formatting in segments:
            run = para.add_run(seg_text)

            run_font_config = font_config.copy()
            run_font_config["bold"] = formatting.get("bold", False)
            run_font_config["italic"] = formatting.get("italic", False)

            apply_run_style(run, run_font_config, resolver)

        # Set indentation for list appearance
        pf = para.paragraph_format
        pf.left_indent = Pt(20)
        pf.space_after = resolver.get_spacing("bullet", "after", 4)

    save_document(doc, doc_path)

    return {"success": True, "element": "bullet_list", "count": len(items)}


def add_numbered_list(
    doc_path: str | Path,
    items: list[str],
    start: int = 1,
    color: str | None = None,
    font: str | None = None,
    font_size: float | None = None,
) -> dict[str, Any]:
    """Add a numbered list to the document.

    Args:
        doc_path: Path to the DOCX file
        items: List of items (each can contain **bold** markdown)
        start: Starting number
        color: Optional hex color or named color
        font: Optional font name
        font_size: Optional font size in points

    Returns:
        Dict with status
    """
    doc, metadata = load_document(doc_path)
    style_config = metadata.get("style_config", metadata.get("preset_data", {}))
    resolver = StyleResolver(style_config)

    # Get bullet style (used for numbered lists too)
    element_style = resolver.get_element_style("bullet")
    font_config = element_style.get("font", {}).copy()

    # Apply overrides
    if font:
        font_config["name"] = font
    if font_size is not None:
        font_config["size"] = font_size
    if color:
        font_config["color"] = color

    for i, item_text in enumerate(items, start=start):
        para = doc.add_paragraph()

        # Add number
        num_run = para.add_run(f"{i}. ")
        num_font_config = font_config.copy()
        num_font_config["bold"] = True
        apply_run_style(num_run, num_font_config, resolver)

        # Parse and add item text
        segments = _parse_markdown_text(item_text)
        for seg_text, formatting in segments:
            run = para.add_run(seg_text)

            run_font_config = font_config.copy()
            run_font_config["bold"] = formatting.get("bold", False)
            run_font_config["italic"] = formatting.get("italic", False)

            apply_run_style(run, run_font_config, resolver)

        # Set indentation
        pf = para.paragraph_format
        pf.left_indent = Pt(20)
        pf.space_after = resolver.get_spacing("bullet", "after", 4)

    save_document(doc, doc_path)

    return {"success": True, "element": "numbered_list", "count": len(items)}

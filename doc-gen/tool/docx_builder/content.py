"""Content elements for DOCX builder: headings, paragraphs, and lists."""

from pathlib import Path
from typing import Any

from docx.shared import Pt, RGBColor, Twips
from docx.enum.text import WD_ALIGN_PARAGRAPH
from docx.oxml.ns import qn
from docx.oxml import OxmlElement

from .core import load_document, save_document
from ..builder_common.presets import get_color, get_typography, get_spacing


def _parse_color(color_str: str) -> RGBColor:
    """Parse hex color string to RGBColor."""
    color_str = color_str.lstrip("#")
    return RGBColor(
        int(color_str[0:2], 16),
        int(color_str[2:4], 16),
        int(color_str[4:6], 16),
    )


def _get_alignment(alignment: str) -> int:
    """Convert alignment string to WD_ALIGN_PARAGRAPH constant."""
    alignments = {
        "left": WD_ALIGN_PARAGRAPH.LEFT,
        "center": WD_ALIGN_PARAGRAPH.CENTER,
        "right": WD_ALIGN_PARAGRAPH.RIGHT,
        "justify": WD_ALIGN_PARAGRAPH.JUSTIFY,
    }
    return alignments.get(alignment.lower(), WD_ALIGN_PARAGRAPH.LEFT)


def _parse_markdown_text(text: str) -> list[tuple[str, dict]]:
    """Parse simple markdown formatting (bold, italic) into segments.

    Args:
        text: Text with optional **bold** and *italic* markers

    Returns:
        List of (text, {bold: bool, italic: bool}) tuples
    """
    import re

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
    spacing_before: int | None = None,
    spacing_after: int | None = None,
) -> dict[str, Any]:
    """Add a heading to the document.

    Args:
        doc_path: Path to the DOCX file
        text: Heading text
        level: Heading level (1-3)
        color: Optional hex color (e.g., "#1E3A5F")
        font: Optional font name
        alignment: "left", "center", "right", or "justify"
        spacing_before: Optional spacing before in twips
        spacing_after: Optional spacing after in twips

    Returns:
        Dict with status
    """
    doc, metadata = load_document(doc_path)
    preset = metadata.get("preset_data", {})

    # Create paragraph and add text
    para = doc.add_paragraph()

    # Parse text for markdown formatting
    segments = _parse_markdown_text(text)
    for seg_text, formatting in segments:
        run = para.add_run(seg_text)
        run.bold = formatting.get("bold", False) or True  # Headings are always bold
        run.italic = formatting.get("italic", False)

        # Set font
        font_name = font or get_typography(preset, "font_family")
        run.font.name = font_name
        run._element.rPr.rFonts.set(qn("w:eastAsia"), font_name)

        # Set size based on level
        size_key = f"heading{level}_size"
        size = get_typography(preset, size_key, 28 - (level - 1) * 4)
        run.font.size = Pt(size / 2)  # Convert half-points to points

        # Set color
        if color:
            run.font.color.rgb = _parse_color(color)
        else:
            primary = get_color(preset, "primary")
            run.font.color.rgb = _parse_color(primary)

    # Set alignment
    para.alignment = _get_alignment(alignment)

    # Set spacing
    pf = para.paragraph_format
    if spacing_before is not None:
        pf.space_before = Twips(spacing_before)
    else:
        pf.space_before = Twips(get_spacing(preset, "section_before"))

    if spacing_after is not None:
        pf.space_after = Twips(spacing_after)
    else:
        pf.space_after = Twips(get_spacing(preset, "section_after"))

    save_document(doc, doc_path)

    return {"success": True, "element": "heading", "level": level, "text": text[:50]}


def add_paragraph(
    doc_path: str | Path,
    text: str,
    bold: bool = False,
    italic: bool = False,
    color: str | None = None,
    font: str | None = None,
    font_size: int | None = None,
    alignment: str = "left",
    spacing_after: int | None = None,
) -> dict[str, Any]:
    """Add a paragraph to the document.

    Args:
        doc_path: Path to the DOCX file
        text: Paragraph text (supports **bold** and *italic* markdown)
        bold: Make entire paragraph bold
        italic: Make entire paragraph italic
        color: Optional hex color
        font: Optional font name
        font_size: Optional font size in half-points (e.g., 22 for 11pt)
        alignment: "left", "center", "right", or "justify"
        spacing_after: Optional spacing after in twips

    Returns:
        Dict with status
    """
    doc, metadata = load_document(doc_path)
    preset = metadata.get("preset_data", {})

    para = doc.add_paragraph()

    # Parse text for markdown formatting
    segments = _parse_markdown_text(text)
    for seg_text, formatting in segments:
        run = para.add_run(seg_text)

        # Apply formatting
        run.bold = bold or formatting.get("bold", False)
        run.italic = italic or formatting.get("italic", False)

        # Set font
        font_name = font or get_typography(preset, "font_family")
        run.font.name = font_name
        run._element.rPr.rFonts.set(qn("w:eastAsia"), font_name)

        # Set size
        size = font_size or get_typography(preset, "body_size")
        run.font.size = Pt(size / 2)

        # Set color
        if color:
            run.font.color.rgb = _parse_color(color)
        else:
            text_color = get_color(preset, "text")
            run.font.color.rgb = _parse_color(text_color)

    # Set alignment
    para.alignment = _get_alignment(alignment)

    # Set spacing
    pf = para.paragraph_format
    if spacing_after is not None:
        pf.space_after = Twips(spacing_after)
    else:
        pf.space_after = Twips(get_spacing(preset, "paragraph_after"))

    save_document(doc, doc_path)

    return {"success": True, "element": "paragraph", "text": text[:50]}


def add_bullet_list(
    doc_path: str | Path,
    items: list[str],
    style: str = "bullet",
    color: str | None = None,
    font: str | None = None,
    font_size: int | None = None,
) -> dict[str, Any]:
    """Add a bullet list to the document.

    Args:
        doc_path: Path to the DOCX file
        items: List of items (each can contain **bold** markdown)
        style: "bullet", "checkmark", or "dash"
        color: Optional hex color
        font: Optional font name
        font_size: Optional font size in half-points

    Returns:
        Dict with status
    """
    doc, metadata = load_document(doc_path)
    preset = metadata.get("preset_data", {})

    # Bullet characters for different styles
    bullets = {
        "bullet": "\u2022",    # •
        "checkmark": "\u2713", # ✓
        "dash": "\u2014",      # —
        "x": "\u2717",         # ✗
    }
    bullet_char = bullets.get(style, bullets["bullet"])

    for item_text in items:
        para = doc.add_paragraph()

        # Add bullet character
        bullet_run = para.add_run(f"{bullet_char} ")
        font_name = font or get_typography(preset, "font_family")
        bullet_run.font.name = font_name
        size = font_size or get_typography(preset, "body_size")
        bullet_run.font.size = Pt(size / 2)

        # Parse and add item text
        segments = _parse_markdown_text(item_text)
        for seg_text, formatting in segments:
            run = para.add_run(seg_text)
            run.bold = formatting.get("bold", False)
            run.italic = formatting.get("italic", False)
            run.font.name = font_name
            run._element.rPr.rFonts.set(qn("w:eastAsia"), font_name)
            run.font.size = Pt(size / 2)

            if color:
                run.font.color.rgb = _parse_color(color)
            else:
                text_color = get_color(preset, "text")
                run.font.color.rgb = _parse_color(text_color)

        # Set indentation for list appearance
        pf = para.paragraph_format
        pf.left_indent = Pt(20)
        pf.space_after = Twips(80)

    save_document(doc, doc_path)

    return {"success": True, "element": "bullet_list", "count": len(items)}


def add_numbered_list(
    doc_path: str | Path,
    items: list[str],
    start: int = 1,
    color: str | None = None,
    font: str | None = None,
    font_size: int | None = None,
) -> dict[str, Any]:
    """Add a numbered list to the document.

    Args:
        doc_path: Path to the DOCX file
        items: List of items (each can contain **bold** markdown)
        start: Starting number
        color: Optional hex color
        font: Optional font name
        font_size: Optional font size in half-points

    Returns:
        Dict with status
    """
    doc, metadata = load_document(doc_path)
    preset = metadata.get("preset_data", {})

    for i, item_text in enumerate(items, start=start):
        para = doc.add_paragraph()

        # Add number
        num_run = para.add_run(f"{i}. ")
        font_name = font or get_typography(preset, "font_family")
        num_run.font.name = font_name
        size = font_size or get_typography(preset, "body_size")
        num_run.font.size = Pt(size / 2)

        # Parse and add item text
        segments = _parse_markdown_text(item_text)
        for seg_text, formatting in segments:
            run = para.add_run(seg_text)
            run.bold = formatting.get("bold", False)
            run.italic = formatting.get("italic", False)
            run.font.name = font_name
            run._element.rPr.rFonts.set(qn("w:eastAsia"), font_name)
            run.font.size = Pt(size / 2)

            if color:
                run.font.color.rgb = _parse_color(color)
            else:
                text_color = get_color(preset, "text")
                run.font.color.rgb = _parse_color(text_color)

        # Set indentation
        pf = para.paragraph_format
        pf.left_indent = Pt(20)
        pf.space_after = Twips(80)

    save_document(doc, doc_path)

    return {"success": True, "element": "numbered_list", "count": len(items)}

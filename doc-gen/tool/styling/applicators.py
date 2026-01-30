"""Apply styles to python-docx elements.

Provides functions to apply font, paragraph, and cell styles to
python-docx elements using a StyleResolver.
"""

from typing import Any

from docx.shared import Pt, Inches
from docx.text.paragraph import Paragraph
from docx.text.run import Run
from docx.table import _Cell
from docx.enum.text import WD_ALIGN_PARAGRAPH
from docx.oxml.ns import qn
from docx.oxml import OxmlElement

from .resolver import StyleResolver


# Alignment mapping
ALIGNMENTS = {
    "left": WD_ALIGN_PARAGRAPH.LEFT,
    "center": WD_ALIGN_PARAGRAPH.CENTER,
    "right": WD_ALIGN_PARAGRAPH.RIGHT,
    "justify": WD_ALIGN_PARAGRAPH.JUSTIFY,
}


def apply_run_style(
    run: Run,
    font_config: dict[str, Any],
    resolver: StyleResolver
) -> None:
    """Apply font styling to a text run.

    Args:
        run: The python-docx Run object
        font_config: Font configuration dict with name, size, bold, italic, color, etc.
        resolver: StyleResolver for resolving color references
    """
    if not font_config:
        return

    # Font name
    if "name" in font_config:
        run.font.name = font_config["name"]
        # Also set for East Asian fonts to ensure consistency
        rPr = run._element.get_or_add_rPr()
        rFonts = rPr.get_or_add_rFonts()
        rFonts.set(qn("w:eastAsia"), font_config["name"])

    # Font size
    if "size" in font_config:
        run.font.size = Pt(font_config["size"])

    # Bold
    if "bold" in font_config:
        run.font.bold = font_config["bold"]

    # Italic
    if "italic" in font_config:
        run.font.italic = font_config["italic"]

    # Underline
    if "underline" in font_config:
        run.font.underline = font_config["underline"]

    # Color
    if "color" in font_config:
        run.font.color.rgb = resolver.resolve_color(font_config["color"])

    # All caps
    if font_config.get("allCaps"):
        run.font.all_caps = True


def apply_paragraph_style(
    paragraph: Paragraph,
    style_config: dict[str, Any],
    resolver: StyleResolver
) -> None:
    """Apply paragraph formatting.

    Args:
        paragraph: The python-docx Paragraph object
        style_config: Style configuration dict with alignment, spacing, indent, etc.
        resolver: StyleResolver for resolving values
    """
    if not style_config:
        return

    # Alignment
    if "alignment" in style_config:
        alignment = style_config["alignment"]
        if alignment in ALIGNMENTS:
            paragraph.alignment = ALIGNMENTS[alignment]

    # Spacing
    if "spacing" in style_config:
        spacing = style_config["spacing"]
        pf = paragraph.paragraph_format

        if "before" in spacing:
            pf.space_before = Pt(spacing["before"])
        if "after" in spacing:
            pf.space_after = Pt(spacing["after"])

    # Indentation
    if "indent" in style_config:
        indent = style_config["indent"]
        pf = paragraph.paragraph_format

        if "left" in indent:
            value = indent["left"]
            if isinstance(value, str) and "in" in value:
                pf.left_indent = Inches(float(value.replace("in", "")))
            else:
                pf.left_indent = Pt(value)

        if "right" in indent:
            value = indent["right"]
            if isinstance(value, str) and "in" in value:
                pf.right_indent = Inches(float(value.replace("in", "")))
            else:
                pf.right_indent = Pt(value)

        if "firstLine" in indent:
            value = indent["firstLine"]
            if isinstance(value, str) and "in" in value:
                pf.first_line_indent = Inches(float(value.replace("in", "")))
            else:
                pf.first_line_indent = Pt(value)


def apply_element_style(
    paragraph: Paragraph,
    run: Run,
    element: str,
    resolver: StyleResolver,
    font_overrides: dict[str, Any] | None = None
) -> None:
    """Apply complete element styling (font + paragraph).

    Convenience function that applies both font and paragraph styles
    for a named element.

    Args:
        paragraph: The python-docx Paragraph object
        run: The python-docx Run object
        element: Element name (title, heading1, body, etc.)
        resolver: StyleResolver instance
        font_overrides: Optional dict to override font settings
    """
    style = resolver.get_element_style(element)
    font_config = style.get("font", {}).copy()

    # Apply any overrides
    if font_overrides:
        font_config.update(font_overrides)

    apply_run_style(run, font_config, resolver)
    apply_paragraph_style(paragraph, style, resolver)


def set_cell_background(cell: _Cell, color_hex: str) -> None:
    """Set table cell background color.

    Args:
        cell: The python-docx _Cell object
        color_hex: Hex color string without # (e.g., "1E3A5F")
    """
    shading = OxmlElement("w:shd")
    shading.set(qn("w:fill"), color_hex.lstrip("#"))
    cell._tc.get_or_add_tcPr().append(shading)


def set_cell_borders(
    cell: _Cell,
    color_hex: str = "000000",
    width: int = 4
) -> None:
    """Set table cell borders.

    Args:
        cell: The python-docx _Cell object
        color_hex: Border color as hex without # (e.g., "CCCCCC")
        width: Border width in eighths of a point (4 = 0.5pt)
    """
    tc = cell._tc
    tcPr = tc.get_or_add_tcPr()
    tcBorders = OxmlElement("w:tcBorders")

    for edge in ("top", "left", "bottom", "right"):
        edge_el = OxmlElement(f"w:{edge}")
        edge_el.set(qn("w:val"), "single")
        edge_el.set(qn("w:sz"), str(width))
        edge_el.set(qn("w:color"), color_hex.lstrip("#"))
        tcBorders.append(edge_el)

    tcPr.append(tcBorders)


def apply_cell_style(
    cell: _Cell,
    cell_config: dict[str, Any],
    resolver: StyleResolver
) -> None:
    """Apply styling to a table cell.

    Args:
        cell: The python-docx _Cell object
        cell_config: Cell configuration dict with background, font, etc.
        resolver: StyleResolver for resolving color references
    """
    # Background color
    if "background" in cell_config:
        bg_hex = resolver.resolve_color_hex(cell_config["background"])
        set_cell_background(cell, bg_hex)

    # Apply font styling to cell content
    font_config = cell_config.get("font", {})
    if font_config:
        for paragraph in cell.paragraphs:
            for run in paragraph.runs:
                apply_run_style(run, font_config, resolver)


def apply_table_header_style(
    cell: _Cell,
    resolver: StyleResolver,
    table_style: str = "default"
) -> None:
    """Apply header row styling to a table cell.

    Args:
        cell: The python-docx _Cell object
        resolver: StyleResolver instance
        table_style: Table style name
    """
    table_config = resolver.get_table_style(table_style)
    header_config = table_config.get("headerRow", {})
    apply_cell_style(cell, header_config, resolver)


def apply_table_body_style(
    cell: _Cell,
    resolver: StyleResolver,
    table_style: str = "default"
) -> None:
    """Apply body row styling to a table cell.

    Args:
        cell: The python-docx _Cell object
        resolver: StyleResolver instance
        table_style: Table style name
    """
    table_config = resolver.get_table_style(table_style)
    body_config = table_config.get("bodyRow", {})
    apply_cell_style(cell, body_config, resolver)


def get_alignment(alignment: str) -> int:
    """Convert alignment string to WD_ALIGN_PARAGRAPH constant.

    Args:
        alignment: "left", "center", "right", or "justify"

    Returns:
        WD_ALIGN_PARAGRAPH constant
    """
    return ALIGNMENTS.get(alignment.lower(), WD_ALIGN_PARAGRAPH.LEFT)

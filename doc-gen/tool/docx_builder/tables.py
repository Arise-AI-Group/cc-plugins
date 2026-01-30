"""Table support for DOCX builder with professional styling."""

from pathlib import Path
from typing import Any

from docx.shared import Pt, Inches
from docx.enum.table import WD_TABLE_ALIGNMENT
from docx.oxml.ns import nsdecls
from docx.oxml import parse_xml

from .core import load_document, save_document
from ..styling import StyleResolver, apply_run_style, set_cell_background, set_cell_borders


def _set_cell_width(cell, width_inches: float):
    """Set cell width."""
    cell.width = Inches(width_inches)


def add_table(
    doc_path: str | Path,
    data: list[list[str]],
    header_row: bool = True,
    column_widths: list[float] | None = None,
    style: dict[str, Any] | None = None,
    table_style: str = "default",
) -> dict[str, Any]:
    """Add a table to the document with professional styling.

    Args:
        doc_path: Path to the DOCX file
        data: 2D array of cell content [[row1], [row2], ...]
        header_row: If True, first row is styled as header
        column_widths: Optional list of column widths in inches
        style: Optional style dict with overrides:
            - header_bg: Header background color (hex or named)
            - header_color: Header text color (hex or named)
            - border_color: Border color (hex or named)
            - alternating_rows: Enable alternating row colors (default: False)
            - alternating_color: Color for alternating rows
            - total_row: If True, style last row as total (default: False)
        table_style: Name of table style from style config (default: "default")

    Returns:
        Dict with status and table info
    """
    doc, metadata = load_document(doc_path)
    style_config = metadata.get("style_config", metadata.get("preset_data", {}))
    resolver = StyleResolver(style_config)

    if not data:
        return {"success": False, "error": "No data provided"}

    # Get table style configuration
    table_config = resolver.get_table_style(table_style)
    header_config = table_config.get("headerRow", {})
    body_config = table_config.get("bodyRow", {})

    # Build effective style with defaults from style config and user overrides
    effective_style = {
        "header_bg": header_config.get("background", "primary"),
        "header_color": header_config.get("font", {}).get("color", "#FFFFFF"),
        "border_color": resolver.colors.get("border", "#CCCCCC"),
        "alternating_rows": False,
        "alternating_color": resolver.colors.get("light", "#F5F5F5"),
        "total_row": False,
    }
    if style:
        effective_style.update(style)

    # Create table
    num_rows = len(data)
    num_cols = len(data[0]) if data else 0
    table = doc.add_table(rows=num_rows, cols=num_cols)

    # Set table width to full page width
    table.alignment = WD_TABLE_ALIGNMENT.CENTER
    table.autofit = False

    # Get font settings from body style
    body_font = resolver.get_body_font()
    font_name = body_font.get("name", "Arial")
    font_size = body_font.get("size", 11)

    # Calculate column widths
    if column_widths:
        widths = column_widths
    else:
        # Default: equal widths totaling ~6.5 inches (letter page with 1" margins)
        total_width = 6.5
        widths = [total_width / num_cols] * num_cols

    # Fill table
    for row_idx, row_data in enumerate(data):
        row = table.rows[row_idx]

        # Determine row styling
        is_header = header_row and row_idx == 0
        is_total = effective_style["total_row"] and row_idx == num_rows - 1
        is_alternating = (
            effective_style["alternating_rows"]
            and not is_header
            and not is_total
            and row_idx % 2 == 0
        )

        for col_idx, cell_text in enumerate(row_data):
            if col_idx >= num_cols:
                break

            cell = row.cells[col_idx]

            # Set cell width
            if col_idx < len(widths):
                _set_cell_width(cell, widths[col_idx])

            # Clear default paragraph and add text
            cell.text = ""
            para = cell.paragraphs[0]
            run = para.add_run(str(cell_text))

            # Build font config for this cell
            font_config = {
                "name": font_name,
                "size": font_size,
            }

            # Style based on row type
            if is_header or is_total:
                font_config["bold"] = True
                font_config["color"] = effective_style["header_color"]
                bg_hex = resolver.resolve_color_hex(effective_style["header_bg"])
                set_cell_background(cell, bg_hex)
            elif is_alternating:
                font_config["color"] = "text"
                bg_hex = resolver.resolve_color_hex(effective_style["alternating_color"])
                set_cell_background(cell, bg_hex)
            else:
                font_config["color"] = "text"

            apply_run_style(run, font_config, resolver)

            # Set borders
            border_hex = resolver.resolve_color_hex(effective_style["border_color"])
            set_cell_borders(cell, border_hex)

            # Set cell padding
            tc = cell._tc
            tcPr = tc.get_or_add_tcPr()
            tcMar = parse_xml(
                f'''<w:tcMar {nsdecls("w")}>
                    <w:top w:w="80" w:type="dxa"/>
                    <w:left w:w="120" w:type="dxa"/>
                    <w:bottom w:w="80" w:type="dxa"/>
                    <w:right w:w="120" w:type="dxa"/>
                </w:tcMar>'''
            )
            tcPr.append(tcMar)

    save_document(doc, doc_path)

    return {
        "success": True,
        "element": "table",
        "rows": num_rows,
        "columns": num_cols,
        "header_row": header_row,
    }


def add_simple_table(
    doc_path: str | Path,
    data: list[list[str]],
    borders: bool = True,
) -> dict[str, Any]:
    """Add a simple table without special styling.

    Args:
        doc_path: Path to the DOCX file
        data: 2D array of cell content
        borders: Whether to show borders

    Returns:
        Dict with status
    """
    doc, metadata = load_document(doc_path)
    style_config = metadata.get("style_config", metadata.get("preset_data", {}))
    resolver = StyleResolver(style_config)

    if not data:
        return {"success": False, "error": "No data provided"}

    num_rows = len(data)
    num_cols = len(data[0]) if data else 0
    table = doc.add_table(rows=num_rows, cols=num_cols)

    body_font = resolver.get_body_font()
    font_name = body_font.get("name", "Arial")
    font_size = body_font.get("size", 11)

    for row_idx, row_data in enumerate(data):
        row = table.rows[row_idx]
        for col_idx, cell_text in enumerate(row_data):
            if col_idx >= num_cols:
                break
            cell = row.cells[col_idx]
            cell.text = ""
            para = cell.paragraphs[0]
            run = para.add_run(str(cell_text))

            font_config = {"name": font_name, "size": font_size}
            apply_run_style(run, font_config, resolver)

            if borders:
                border_hex = resolver.resolve_color_hex("border", "CCCCCC")
                set_cell_borders(cell, border_hex)

    save_document(doc, doc_path)

    return {"success": True, "element": "simple_table", "rows": num_rows, "columns": num_cols}

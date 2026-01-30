#!/usr/bin/env python3
"""Fill non-fillable PDF forms using text annotations.

This tool adds FreeText annotations to PDFs, allowing you to "fill" forms
that don't have actual form fields. Supports both PDF and image coordinate
systems with automatic conversion.

Usage:
    ./run tool/forms/fill_annotations.py input.pdf fields.json -o filled.pdf

Input JSON format (fields.json):
    {
      "pages": [
        {"page_number": 1, "pdf_width": 612, "pdf_height": 792}
      ],
      "form_fields": [
        {
          "page_number": 1,
          "description": "Last name entry field",
          "field_label": "Last Name",
          "label_bounding_box": [43, 63, 87, 73],
          "entry_bounding_box": [92, 63, 260, 79],
          "entry_text": {"text": "Smith", "font_size": 10}
        }
      ]
    }

Note: Use "pdf_width"/"pdf_height" for PDF coordinates (y=0 at top).
      Use "image_width"/"image_height" for image coordinates (auto-converted).
"""

import argparse
import json
import sys
from pathlib import Path

from pypdf import PdfReader, PdfWriter
from pypdf.annotations import FreeText
from pypdf.generic import ArrayObject, FloatObject, NameObject


def convert_image_to_pdf_coords(
    box: list,
    image_width: float,
    image_height: float,
    pdf_width: float,
    pdf_height: float
) -> list:
    """Convert image coordinates to PDF coordinates.

    Image: y=0 at top, increases downward
    PDF: y=0 at bottom, increases upward

    Args:
        box: [x0, top, x1, bottom] in image coordinates
        image_width: Width of the image
        image_height: Height of the image
        pdf_width: Width of the PDF page
        pdf_height: Height of the PDF page

    Returns:
        [left, bottom, right, top] in PDF coordinates
    """
    x_scale = pdf_width / image_width
    y_scale = pdf_height / image_height

    x0 = box[0] * x_scale
    x1 = box[2] * x_scale

    # Flip Y coordinates
    # image top -> pdf bottom calculation
    top_pdf = pdf_height - (box[1] * y_scale)
    bottom_pdf = pdf_height - (box[3] * y_scale)

    return [x0, bottom_pdf, x1, top_pdf]


def add_text_annotation(
    writer: PdfWriter,
    page_index: int,
    rect: list,
    text: str,
    font_size: int = 10,
    font_color: str = "000000"
):
    """Add a FreeText annotation to a page.

    Args:
        writer: PdfWriter instance
        page_index: 0-based page index
        rect: [left, bottom, right, top] in PDF coordinates
        text: Text to display
        font_size: Font size in points
        font_color: Hex color string (default: black)
    """
    # Create FreeText annotation
    annotation = FreeText(
        text=text,
        rect=rect,
        font_size=f"{font_size}pt",
        font_color=font_color,
        border_color=None
    )

    writer.add_annotation(page_index, annotation)


def fill_annotations(
    pdf_path: str,
    fields_data: dict,
    output_path: str
) -> dict:
    """Fill a PDF with text annotations.

    Args:
        pdf_path: Path to the input PDF
        fields_data: dict with pages and form_fields
        output_path: Path for the output PDF

    Returns:
        dict with status and details
    """
    reader = PdfReader(pdf_path)
    writer = PdfWriter()

    # Copy all pages
    for page in reader.pages:
        writer.add_page(page)

    # Build page dimension lookup
    page_dims = {}
    for page_info in fields_data.get("pages", []):
        page_num = page_info["page_number"]

        # Determine coordinate system
        if "image_width" in page_info:
            # Image coordinates - need PDF dimensions for conversion
            pdf_page = reader.pages[page_num - 1]
            page_dims[page_num] = {
                "image_width": page_info["image_width"],
                "image_height": page_info["image_height"],
                "pdf_width": float(pdf_page.mediabox.width),
                "pdf_height": float(pdf_page.mediabox.height),
                "is_image_coords": True
            }
        else:
            # PDF coordinates
            page_dims[page_num] = {
                "pdf_width": page_info.get("pdf_width", 612),
                "pdf_height": page_info.get("pdf_height", 792),
                "is_image_coords": False
            }

    # Process fields
    filled_count = 0
    errors = []

    for field in fields_data.get("form_fields", []):
        page_num = field.get("page_number", 1)
        entry_text = field.get("entry_text", {})
        text = entry_text.get("text", "")
        font_size = entry_text.get("font_size", 10)

        if not text:
            continue

        entry_box = field.get("entry_bounding_box")
        if not entry_box:
            errors.append(f"Missing entry_bounding_box for field: {field.get('field_label', 'unknown')}")
            continue

        # Get page dimensions
        dims = page_dims.get(page_num)
        if not dims:
            # Try to get from PDF directly
            if page_num <= len(reader.pages):
                pdf_page = reader.pages[page_num - 1]
                dims = {
                    "pdf_width": float(pdf_page.mediabox.width),
                    "pdf_height": float(pdf_page.mediabox.height),
                    "is_image_coords": False
                }
            else:
                errors.append(f"Page {page_num} not found in PDF")
                continue

        # Convert coordinates if needed
        if dims.get("is_image_coords"):
            rect = convert_image_to_pdf_coords(
                entry_box,
                dims["image_width"],
                dims["image_height"],
                dims["pdf_width"],
                dims["pdf_height"]
            )
        else:
            # PDF coordinates are already correct format
            rect = entry_box

        try:
            add_text_annotation(
                writer,
                page_num - 1,  # 0-based index
                rect,
                text,
                font_size
            )
            filled_count += 1
        except Exception as e:
            errors.append(f"Failed to add annotation for {field.get('field_label', 'unknown')}: {e}")

    # Write output
    with open(output_path, "wb") as f:
        writer.write(f)

    return {
        "filled": filled_count,
        "errors": errors if errors else None
    }


def main():
    parser = argparse.ArgumentParser(
        description="Fill non-fillable PDF forms using text annotations"
    )
    parser.add_argument("input", help="Input PDF file")
    parser.add_argument("fields", help="JSON file with field definitions")
    parser.add_argument(
        "-o", "--output",
        required=True,
        help="Output PDF file"
    )
    parser.add_argument(
        "--output-format",
        choices=["json", "text"],
        default="json",
        help="Output format (default: json)"
    )

    args = parser.parse_args()

    # Validate inputs
    if not Path(args.input).exists():
        result = {
            "status": "error",
            "operation": "fill_annotations",
            "error": f"PDF file not found: {args.input}"
        }
        print(json.dumps(result, indent=2))
        sys.exit(1)

    if not Path(args.fields).exists():
        result = {
            "status": "error",
            "operation": "fill_annotations",
            "error": f"Fields file not found: {args.fields}"
        }
        print(json.dumps(result, indent=2))
        sys.exit(1)

    try:
        # Load fields
        with open(args.fields) as f:
            fields_data = json.load(f)

        # Fill form
        fill_result = fill_annotations(args.input, fields_data, args.output)

        if fill_result.get("errors"):
            result = {
                "status": "partial" if fill_result["filled"] > 0 else "error",
                "operation": "fill_annotations",
                "input": args.input,
                "output": args.output,
                "fields_filled": fill_result["filled"],
                "errors": fill_result["errors"]
            }
        else:
            result = {
                "status": "success",
                "operation": "fill_annotations",
                "input": args.input,
                "output": args.output,
                "fields_filled": fill_result["filled"]
            }

        if args.output_format == "text":
            print(f"Added {fill_result['filled']} annotation(s)")
            if fill_result.get("errors"):
                for err in fill_result["errors"]:
                    print(f"  Warning: {err}")
            print(f"Output: {args.output}")
        else:
            print(json.dumps(result, indent=2))

        if result["status"] == "error":
            sys.exit(1)

    except json.JSONDecodeError as e:
        result = {
            "status": "error",
            "operation": "fill_annotations",
            "error": f"Invalid JSON in fields file: {e}"
        }
        print(json.dumps(result, indent=2))
        sys.exit(1)
    except Exception as e:
        result = {
            "status": "error",
            "operation": "fill_annotations",
            "error": str(e)
        }
        print(json.dumps(result, indent=2))
        sys.exit(1)


if __name__ == "__main__":
    main()

#!/usr/bin/env python3
"""Extract form field metadata from a fillable PDF.

Usage:
    ./run tool/forms/extract_fields.py input.pdf -o fields.json

Output JSON format:
    [
      {
        "field_id": "last_name",
        "page": 1,
        "rect": [left, bottom, right, top],
        "type": "text"
      },
      {
        "field_id": "checkbox1",
        "page": 1,
        "type": "checkbox",
        "checked_value": "/On",
        "unchecked_value": "/Off"
      },
      {
        "field_id": "gender",
        "page": 1,
        "type": "radio_group",
        "radio_options": [
          {"value": "/Male", "rect": [100, 200, 120, 220]},
          {"value": "/Female", "rect": [100, 180, 120, 200]}
        ]
      },
      {
        "field_id": "country",
        "page": 1,
        "type": "choice",
        "choice_options": [
          {"value": "US", "text": "United States"},
          {"value": "CA", "text": "Canada"}
        ]
      }
    ]
"""

import argparse
import json
import sys
from pathlib import Path

from pypdf import PdfReader
from pypdf.generic import ArrayObject, NameObject


def get_field_type(field) -> str:
    """Determine the type of a form field."""
    ft = field.get("/FT")
    if ft is None:
        return "unknown"

    ft_str = str(ft)

    if ft_str == "/Tx":
        return "text"
    elif ft_str == "/Btn":
        # Check if it's a checkbox or radio button
        flags = field.get("/Ff", 0)
        if isinstance(flags, int) and (flags & (1 << 15)):  # Radio flag
            return "radio_group"
        return "checkbox"
    elif ft_str == "/Ch":
        return "choice"
    elif ft_str == "/Sig":
        return "signature"

    return "unknown"


def get_field_rect(field, reader) -> list:
    """Get the bounding rectangle of a field."""
    # Try to get rect from widget annotation
    if "/Rect" in field:
        rect = field["/Rect"]
        if isinstance(rect, ArrayObject):
            return [float(x) for x in rect]

    # Try Kids
    if "/Kids" in field:
        kids = field["/Kids"]
        if kids and len(kids) > 0:
            kid = kids[0].get_object()
            if "/Rect" in kid:
                rect = kid["/Rect"]
                if isinstance(rect, ArrayObject):
                    return [float(x) for x in rect]

    return None


def get_field_page(field, reader) -> int:
    """Get the page number of a field (1-based)."""
    # Try to get page from widget annotation
    if "/P" in field:
        page_ref = field["/P"]
        for i, page in enumerate(reader.pages):
            if page.indirect_reference == page_ref:
                return i + 1

    # Check Kids
    if "/Kids" in field:
        kids = field["/Kids"]
        if kids and len(kids) > 0:
            kid = kids[0].get_object()
            if "/P" in kid:
                page_ref = kid["/P"]
                for i, page in enumerate(reader.pages):
                    if page.indirect_reference == page_ref:
                        return i + 1

    # Default to page 1 if we can't determine
    return 1


def extract_checkbox_values(field) -> tuple:
    """Extract checked and unchecked values for a checkbox."""
    checked_value = "/On"
    unchecked_value = "/Off"

    # Look in the appearance states
    if "/AP" in field:
        ap = field["/AP"]
        if "/N" in ap:
            normal = ap["/N"]
            if isinstance(normal, dict):
                for key in normal.keys():
                    if key != "/Off":
                        checked_value = str(key)

    # Also check Kids
    if "/Kids" in field:
        for kid_ref in field["/Kids"]:
            kid = kid_ref.get_object()
            if "/AP" in kid:
                ap = kid["/AP"]
                if "/N" in ap:
                    normal = ap["/N"]
                    if isinstance(normal, dict):
                        for key in normal.keys():
                            if key != "/Off":
                                checked_value = str(key)

    return checked_value, unchecked_value


def extract_radio_options(field, reader) -> list:
    """Extract radio button options."""
    options = []

    if "/Kids" in field:
        for kid_ref in field["/Kids"]:
            kid = kid_ref.get_object()
            value = None
            rect = None

            # Get the value from appearance states
            if "/AP" in kid:
                ap = kid["/AP"]
                if "/N" in ap:
                    normal = ap["/N"]
                    if isinstance(normal, dict):
                        for key in normal.keys():
                            if key != "/Off":
                                value = str(key)

            # Get rectangle
            if "/Rect" in kid:
                rect_arr = kid["/Rect"]
                if isinstance(rect_arr, ArrayObject):
                    rect = [float(x) for x in rect_arr]

            if value:
                option = {"value": value}
                if rect:
                    option["rect"] = rect
                options.append(option)

    return options


def extract_choice_options(field) -> list:
    """Extract choice/dropdown options."""
    options = []

    if "/Opt" in field:
        opt = field["/Opt"]
        for item in opt:
            if isinstance(item, ArrayObject) and len(item) >= 2:
                options.append({
                    "value": str(item[0]),
                    "text": str(item[1])
                })
            else:
                text = str(item)
                options.append({
                    "value": text,
                    "text": text
                })

    return options


def extract_fields(pdf_path: str) -> list:
    """Extract all form field metadata from a PDF.

    Args:
        pdf_path: Path to the PDF file

    Returns:
        List of field dictionaries
    """
    reader = PdfReader(pdf_path)
    fields_dict = reader.get_fields()

    if not fields_dict:
        return []

    fields = []

    for field_name, field in fields_dict.items():
        field_type = get_field_type(field)

        field_info = {
            "field_id": field_name,
            "page": get_field_page(field, reader),
            "type": field_type
        }

        rect = get_field_rect(field, reader)
        if rect:
            field_info["rect"] = rect

        if field_type == "checkbox":
            checked, unchecked = extract_checkbox_values(field)
            field_info["checked_value"] = checked
            field_info["unchecked_value"] = unchecked

        elif field_type == "radio_group":
            field_info["radio_options"] = extract_radio_options(field, reader)

        elif field_type == "choice":
            field_info["choice_options"] = extract_choice_options(field)

        fields.append(field_info)

    # Sort by page, then by vertical position (top to bottom)
    fields.sort(key=lambda f: (f["page"], -(f.get("rect", [0, 0, 0, 0])[1] or 0)))

    return fields


def main():
    parser = argparse.ArgumentParser(
        description="Extract form field metadata from a fillable PDF"
    )
    parser.add_argument("input", help="Input PDF file")
    parser.add_argument(
        "-o", "--output",
        help="Output JSON file (default: stdout)"
    )
    parser.add_argument(
        "--output-format",
        choices=["json", "text"],
        default="json",
        help="Output format (default: json)"
    )

    args = parser.parse_args()

    if not Path(args.input).exists():
        result = {
            "status": "error",
            "operation": "extract_fields",
            "error": f"File not found: {args.input}"
        }
        print(json.dumps(result, indent=2))
        sys.exit(1)

    try:
        fields = extract_fields(args.input)

        if args.output:
            with open(args.output, "w") as f:
                json.dump(fields, f, indent=2)
            result = {
                "status": "success",
                "operation": "extract_fields",
                "input": args.input,
                "output": args.output,
                "field_count": len(fields)
            }
            print(json.dumps(result, indent=2))
        else:
            if args.output_format == "text":
                print(f"Found {len(fields)} field(s):")
                for field in fields:
                    print(f"  - {field['field_id']} ({field['type']}) on page {field['page']}")
            else:
                print(json.dumps(fields, indent=2))

    except Exception as e:
        result = {
            "status": "error",
            "operation": "extract_fields",
            "error": str(e)
        }
        print(json.dumps(result, indent=2))
        sys.exit(1)


if __name__ == "__main__":
    main()

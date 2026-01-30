#!/usr/bin/env python3
"""Validate bounding boxes in a fields.json file.

Checks for:
- Intersecting bounding boxes (would cause overlapping text)
- Entry boxes that are too small for the specified font size
- Invalid or missing coordinates

Usage:
    ./run tool/forms/check_bounding_boxes.py fields.json

Output:
    {"status": "success", "valid": true, "warnings": [], "errors": []}
"""

import argparse
import json
import sys
from pathlib import Path


def boxes_intersect(box1: list, box2: list) -> bool:
    """Check if two bounding boxes intersect.

    Args:
        box1, box2: [x0, top, x1, bottom] coordinates

    Returns:
        True if boxes overlap
    """
    # Boxes are [x0, top, x1, bottom]
    # No intersection if one is completely to the side or above/below
    if box1[2] <= box2[0]:  # box1 is left of box2
        return False
    if box2[2] <= box1[0]:  # box2 is left of box1
        return False
    if box1[3] <= box2[1]:  # box1 is above box2
        return False
    if box2[3] <= box1[1]:  # box2 is above box1
        return False
    return True


def check_box_size(box: list, font_size: int) -> tuple:
    """Check if a bounding box is large enough for the font size.

    Args:
        box: [x0, top, x1, bottom] coordinates
        font_size: Font size in points

    Returns:
        (is_valid, message)
    """
    width = abs(box[2] - box[0])
    height = abs(box[3] - box[1])

    # Minimum height should be roughly 1.2x font size
    min_height = font_size * 1.2

    if height < min_height:
        return (False, f"Box height ({height:.1f}) is too small for font size {font_size}")

    # Width check - at least font_size wide
    if width < font_size:
        return (False, f"Box width ({width:.1f}) is too narrow for font size {font_size}")

    return (True, None)


def validate_box(box: list, field_name: str) -> list:
    """Validate a single bounding box.

    Args:
        box: Bounding box coordinates
        field_name: Name of the field for error messages

    Returns:
        List of error messages
    """
    errors = []

    if not box:
        errors.append(f"{field_name}: Missing bounding box")
        return errors

    if not isinstance(box, list) or len(box) != 4:
        errors.append(f"{field_name}: Bounding box must be [x0, top, x1, bottom]")
        return errors

    try:
        coords = [float(x) for x in box]
    except (TypeError, ValueError):
        errors.append(f"{field_name}: Bounding box contains non-numeric values")
        return errors

    # Check for negative coordinates
    if any(c < 0 for c in coords):
        errors.append(f"{field_name}: Bounding box contains negative coordinates")

    # Check that x1 > x0 and bottom > top (or top > bottom depending on coord system)
    if coords[2] <= coords[0]:
        errors.append(f"{field_name}: x1 must be greater than x0")

    return errors


def check_bounding_boxes(fields_data: dict) -> dict:
    """Validate all bounding boxes in a fields.json structure.

    Args:
        fields_data: dict with pages and form_fields

    Returns:
        dict with valid (bool), warnings, and errors
    """
    errors = []
    warnings = []

    fields = fields_data.get("form_fields", [])

    # Group fields by page
    fields_by_page = {}
    for i, field in enumerate(fields):
        page = field.get("page_number", 1)
        if page not in fields_by_page:
            fields_by_page[page] = []
        fields_by_page[page].append((i, field))

    # Validate each field
    for i, field in enumerate(fields):
        field_label = field.get("field_label", f"field_{i}")

        # Validate entry bounding box
        entry_box = field.get("entry_bounding_box")
        box_errors = validate_box(entry_box, f"{field_label} entry_bounding_box")
        errors.extend(box_errors)

        # Validate label bounding box if present
        label_box = field.get("label_bounding_box")
        if label_box:
            box_errors = validate_box(label_box, f"{field_label} label_bounding_box")
            errors.extend(box_errors)

        # Check box size
        if entry_box and len(entry_box) == 4:
            entry_text = field.get("entry_text", {})
            font_size = entry_text.get("font_size", 10)
            is_valid, msg = check_box_size(entry_box, font_size)
            if not is_valid:
                warnings.append(f"{field_label}: {msg}")

    # Check for intersecting entry boxes on same page
    for page, page_fields in fields_by_page.items():
        for i, (idx1, field1) in enumerate(page_fields):
            box1 = field1.get("entry_bounding_box")
            if not box1 or len(box1) != 4:
                continue

            for idx2, field2 in page_fields[i + 1:]:
                box2 = field2.get("entry_bounding_box")
                if not box2 or len(box2) != 4:
                    continue

                if boxes_intersect(box1, box2):
                    label1 = field1.get("field_label", f"field_{idx1}")
                    label2 = field2.get("field_label", f"field_{idx2}")
                    errors.append(
                        f"Page {page}: '{label1}' and '{label2}' entry boxes intersect"
                    )

    return {
        "valid": len(errors) == 0,
        "warnings": warnings,
        "errors": errors
    }


def main():
    parser = argparse.ArgumentParser(
        description="Validate bounding boxes in a fields.json file"
    )
    parser.add_argument("fields", help="JSON file with field definitions")
    parser.add_argument(
        "--output-format",
        choices=["json", "text"],
        default="json",
        help="Output format (default: json)"
    )

    args = parser.parse_args()

    if not Path(args.fields).exists():
        result = {
            "status": "error",
            "operation": "check_bounding_boxes",
            "error": f"File not found: {args.fields}"
        }
        print(json.dumps(result, indent=2))
        sys.exit(1)

    try:
        with open(args.fields) as f:
            fields_data = json.load(f)

        check_result = check_bounding_boxes(fields_data)

        result = {
            "status": "success",
            "operation": "check_bounding_boxes",
            "input": args.fields,
            **check_result
        }

        if args.output_format == "text":
            if check_result["valid"]:
                print("✓ All bounding boxes are valid")
            else:
                print("✗ Validation failed")

            if check_result["errors"]:
                print("\nErrors:")
                for err in check_result["errors"]:
                    print(f"  ✗ {err}")

            if check_result["warnings"]:
                print("\nWarnings:")
                for warn in check_result["warnings"]:
                    print(f"  ⚠ {warn}")
        else:
            print(json.dumps(result, indent=2))

        if not check_result["valid"]:
            sys.exit(1)

    except json.JSONDecodeError as e:
        result = {
            "status": "error",
            "operation": "check_bounding_boxes",
            "error": f"Invalid JSON: {e}"
        }
        print(json.dumps(result, indent=2))
        sys.exit(1)
    except Exception as e:
        result = {
            "status": "error",
            "operation": "check_bounding_boxes",
            "error": str(e)
        }
        print(json.dumps(result, indent=2))
        sys.exit(1)


if __name__ == "__main__":
    main()

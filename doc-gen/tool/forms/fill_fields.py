#!/usr/bin/env python3
"""Fill fillable PDF form fields.

Usage:
    ./run tool/forms/fill_fields.py input.pdf values.json -o filled.pdf

Input JSON format (values.json):
    [
      {
        "field_id": "last_name",
        "value": "Simpson"
      },
      {
        "field_id": "checkbox1",
        "value": "/On"
      }
    ]
"""

import argparse
import json
import sys
from pathlib import Path

from pypdf import PdfReader, PdfWriter


def fill_fields(pdf_path: str, values: list, output_path: str) -> dict:
    """Fill fillable PDF form fields.

    Args:
        pdf_path: Path to the input PDF
        values: List of dicts with field_id and value
        output_path: Path for the filled PDF

    Returns:
        dict with status and details
    """
    reader = PdfReader(pdf_path)
    writer = PdfWriter()

    # Copy all pages to writer
    for page in reader.pages:
        writer.add_page(page)

    # Get existing fields to validate
    existing_fields = reader.get_fields()
    if not existing_fields:
        return {
            "filled": 0,
            "errors": ["PDF has no fillable fields"]
        }

    # Create field value mapping
    field_values = {}
    errors = []

    for item in values:
        field_id = item.get("field_id")
        value = item.get("value")

        if not field_id:
            errors.append(f"Missing field_id in value entry: {item}")
            continue

        if field_id not in existing_fields:
            errors.append(f"Field not found: {field_id}")
            continue

        field_values[field_id] = value

    # Fill the fields
    if field_values:
        writer.update_page_form_field_values(
            writer.pages[0],
            field_values
        )

    # Write output
    with open(output_path, "wb") as f:
        writer.write(f)

    return {
        "filled": len(field_values),
        "errors": errors if errors else None
    }


def main():
    parser = argparse.ArgumentParser(
        description="Fill fillable PDF form fields"
    )
    parser.add_argument("input", help="Input PDF file")
    parser.add_argument("values", help="JSON file with field values")
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
            "operation": "fill_fields",
            "error": f"PDF file not found: {args.input}"
        }
        print(json.dumps(result, indent=2))
        sys.exit(1)

    if not Path(args.values).exists():
        result = {
            "status": "error",
            "operation": "fill_fields",
            "error": f"Values file not found: {args.values}"
        }
        print(json.dumps(result, indent=2))
        sys.exit(1)

    try:
        # Load values
        with open(args.values) as f:
            values = json.load(f)

        if not isinstance(values, list):
            result = {
                "status": "error",
                "operation": "fill_fields",
                "error": "Values file must contain a JSON array"
            }
            print(json.dumps(result, indent=2))
            sys.exit(1)

        # Fill fields
        fill_result = fill_fields(args.input, values, args.output)

        if fill_result.get("errors"):
            result = {
                "status": "partial" if fill_result["filled"] > 0 else "error",
                "operation": "fill_fields",
                "input": args.input,
                "output": args.output,
                "fields_filled": fill_result["filled"],
                "errors": fill_result["errors"]
            }
        else:
            result = {
                "status": "success",
                "operation": "fill_fields",
                "input": args.input,
                "output": args.output,
                "fields_filled": fill_result["filled"]
            }

        if args.output_format == "text":
            print(f"Filled {fill_result['filled']} field(s)")
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
            "operation": "fill_fields",
            "error": f"Invalid JSON in values file: {e}"
        }
        print(json.dumps(result, indent=2))
        sys.exit(1)
    except Exception as e:
        result = {
            "status": "error",
            "operation": "fill_fields",
            "error": str(e)
        }
        print(json.dumps(result, indent=2))
        sys.exit(1)


if __name__ == "__main__":
    main()

#!/usr/bin/env python3
"""Check if a PDF has fillable form fields.

Usage:
    ./run tool/forms/check_fillable.py input.pdf

Output:
    {"status": "success", "has_fields": true, "field_count": 5}
"""

import argparse
import json
import sys
from pathlib import Path

from pypdf import PdfReader


def check_fillable(pdf_path: str) -> dict:
    """Check if PDF has fillable form fields.

    Args:
        pdf_path: Path to the PDF file

    Returns:
        dict with has_fields (bool) and field_count (int)
    """
    reader = PdfReader(pdf_path)

    # Check for AcroForm
    if reader.get_fields() is None:
        return {"has_fields": False, "field_count": 0}

    fields = reader.get_fields()
    field_count = len(fields) if fields else 0

    return {
        "has_fields": field_count > 0,
        "field_count": field_count
    }


def main():
    parser = argparse.ArgumentParser(
        description="Check if a PDF has fillable form fields"
    )
    parser.add_argument("input", help="Input PDF file")
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
            "operation": "check_fillable",
            "error": f"File not found: {args.input}"
        }
        print(json.dumps(result, indent=2))
        sys.exit(1)

    try:
        check_result = check_fillable(args.input)
        result = {
            "status": "success",
            "operation": "check_fillable",
            "input": args.input,
            **check_result
        }

        if args.output_format == "text":
            if check_result["has_fields"]:
                print(f"PDF has {check_result['field_count']} fillable field(s)")
            else:
                print("PDF has no fillable fields")
        else:
            print(json.dumps(result, indent=2))

    except Exception as e:
        result = {
            "status": "error",
            "operation": "check_fillable",
            "error": str(e)
        }
        print(json.dumps(result, indent=2))
        sys.exit(1)


if __name__ == "__main__":
    main()

#!/usr/bin/env python3
"""Extract form structure from non-fillable PDFs.

This tool extracts text labels, lines, and checkbox-like elements with their
exact PDF coordinates. Use this to identify field positions before filling
with annotations.

Usage:
    ./run tool/forms/extract_structure.py input.pdf -o structure.json

Output JSON format:
    {
      "pages": [
        {
          "page_number": 1,
          "pdf_width": 612,
          "pdf_height": 792,
          "labels": [
            {"text": "Last Name", "x0": 43, "top": 63, "x1": 87, "bottom": 73}
          ],
          "lines": [
            {"x0": 40, "y": 100, "x1": 300}
          ],
          "checkboxes": [
            {"x0": 100, "top": 150, "x1": 110, "bottom": 160, "center_x": 105, "center_y": 155}
          ],
          "row_boundaries": [
            {"top": 50, "bottom": 70}
          ]
        }
      ]
    }
"""

import argparse
import json
import sys
from pathlib import Path

import pdfplumber


def extract_structure(pdf_path: str) -> dict:
    """Extract form structure from a PDF.

    Args:
        pdf_path: Path to the PDF file

    Returns:
        dict with pages containing labels, lines, checkboxes, and row_boundaries
    """
    pages_data = []

    with pdfplumber.open(pdf_path) as pdf:
        for page_num, page in enumerate(pdf.pages, start=1):
            page_width = float(page.width)
            page_height = float(page.height)

            page_data = {
                "page_number": page_num,
                "pdf_width": page_width,
                "pdf_height": page_height,
                "labels": [],
                "lines": [],
                "checkboxes": [],
                "row_boundaries": []
            }

            # Extract text elements with positions
            chars = page.chars
            words = page.extract_words(
                keep_blank_chars=False,
                x_tolerance=3,
                y_tolerance=3
            )

            for word in words:
                page_data["labels"].append({
                    "text": word["text"],
                    "x0": round(float(word["x0"]), 2),
                    "top": round(float(word["top"]), 2),
                    "x1": round(float(word["x1"]), 2),
                    "bottom": round(float(word["bottom"]), 2)
                })

            # Extract lines (potential underlines or borders)
            if page.lines:
                for line in page.lines:
                    # Only horizontal lines (form field indicators)
                    if abs(line["y0"] - line["y1"]) < 2:
                        page_data["lines"].append({
                            "x0": round(float(line["x0"]), 2),
                            "y": round(float(line["y0"]), 2),
                            "x1": round(float(line["x1"]), 2)
                        })

            # Extract rectangles (potential checkboxes)
            if page.rects:
                for rect in page.rects:
                    width = float(rect["x1"]) - float(rect["x0"])
                    height = float(rect["y1"]) - float(rect["y0"])

                    # Small squares are likely checkboxes (5-20 pts)
                    if 5 <= width <= 20 and 5 <= height <= 20:
                        if abs(width - height) < 3:  # Square-ish
                            center_x = (float(rect["x0"]) + float(rect["x1"])) / 2
                            center_y = (float(rect["top"]) + float(rect["bottom"])) / 2

                            page_data["checkboxes"].append({
                                "x0": round(float(rect["x0"]), 2),
                                "top": round(float(rect["top"]), 2),
                                "x1": round(float(rect["x1"]), 2),
                                "bottom": round(float(rect["bottom"]), 2),
                                "center_x": round(center_x, 2),
                                "center_y": round(center_y, 2)
                            })

            # Calculate row boundaries from horizontal lines
            h_lines = sorted([l["y"] for l in page_data["lines"]])
            if len(h_lines) >= 2:
                for i in range(len(h_lines) - 1):
                    page_data["row_boundaries"].append({
                        "top": round(h_lines[i], 2),
                        "bottom": round(h_lines[i + 1], 2)
                    })

            pages_data.append(page_data)

    return {"pages": pages_data}


def main():
    parser = argparse.ArgumentParser(
        description="Extract form structure from non-fillable PDFs"
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
            "operation": "extract_structure",
            "error": f"File not found: {args.input}"
        }
        print(json.dumps(result, indent=2))
        sys.exit(1)

    try:
        structure = extract_structure(args.input)

        if args.output:
            with open(args.output, "w") as f:
                json.dump(structure, f, indent=2)
            result = {
                "status": "success",
                "operation": "extract_structure",
                "input": args.input,
                "output": args.output,
                "pages": len(structure["pages"]),
                "total_labels": sum(len(p["labels"]) for p in structure["pages"]),
                "total_checkboxes": sum(len(p["checkboxes"]) for p in structure["pages"])
            }
            print(json.dumps(result, indent=2))
        else:
            if args.output_format == "text":
                for page in structure["pages"]:
                    print(f"Page {page['page_number']} ({page['pdf_width']}x{page['pdf_height']})")
                    print(f"  Labels: {len(page['labels'])}")
                    print(f"  Lines: {len(page['lines'])}")
                    print(f"  Checkboxes: {len(page['checkboxes'])}")
            else:
                print(json.dumps(structure, indent=2))

    except Exception as e:
        result = {
            "status": "error",
            "operation": "extract_structure",
            "error": str(e)
        }
        print(json.dumps(result, indent=2))
        sys.exit(1)


if __name__ == "__main__":
    main()

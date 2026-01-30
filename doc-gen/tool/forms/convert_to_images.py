#!/usr/bin/env python3
"""Convert PDF pages to images.

Usage:
    ./run tool/forms/convert_to_images.py input.pdf output_dir/
    ./run tool/forms/convert_to_images.py input.pdf output_dir/ --scale 2.0
    ./run tool/forms/convert_to_images.py input.pdf output_dir/ --pages 1-3

Output:
    Creates page_1.png, page_2.png, etc. in the output directory.
"""

import argparse
import json
import sys
from pathlib import Path

try:
    import pypdfium2 as pdfium
    HAS_PYPDFIUM = True
except ImportError:
    HAS_PYPDFIUM = False


def parse_page_range(page_spec: str, total_pages: int) -> list:
    """Parse page range specification like '1-3,5,7-10'.

    Args:
        page_spec: Page specification string
        total_pages: Total number of pages in document

    Returns:
        List of 0-based page indices
    """
    pages = []

    for part in page_spec.split(","):
        part = part.strip()
        if "-" in part:
            start, end = part.split("-", 1)
            start = int(start) if start else 1
            end = int(end) if end else total_pages
            pages.extend(range(start - 1, min(end, total_pages)))
        else:
            page_num = int(part) - 1
            if 0 <= page_num < total_pages:
                pages.append(page_num)

    return sorted(set(pages))


def convert_to_images(
    pdf_path: str,
    output_dir: str,
    scale: float = 1.5,
    pages: list = None,
    format: str = "png"
) -> dict:
    """Convert PDF pages to images.

    Args:
        pdf_path: Path to the PDF file
        output_dir: Directory for output images
        scale: Rendering scale factor (default 1.5)
        pages: List of 0-based page indices (default: all)
        format: Image format (png or jpg)

    Returns:
        dict with status and list of created files
    """
    if not HAS_PYPDFIUM:
        raise ImportError(
            "pypdfium2 is required for PDF to image conversion. "
            "Install with: pip install pypdfium2"
        )

    output_path = Path(output_dir)
    output_path.mkdir(parents=True, exist_ok=True)

    pdf = pdfium.PdfDocument(pdf_path)
    total_pages = len(pdf)

    if pages is None:
        pages = list(range(total_pages))

    created_files = []
    image_dimensions = []

    for page_idx in pages:
        if page_idx >= total_pages:
            continue

        page = pdf[page_idx]
        bitmap = page.render(scale=scale, rotation=0)
        img = bitmap.to_pil()

        # Store dimensions for reference
        image_dimensions.append({
            "page": page_idx + 1,
            "width": img.width,
            "height": img.height
        })

        # Save image
        ext = "jpg" if format == "jpg" else "png"
        filename = f"page_{page_idx + 1}.{ext}"
        filepath = output_path / filename

        if format == "jpg":
            img.save(filepath, "JPEG", quality=90)
        else:
            img.save(filepath, "PNG")

        created_files.append(str(filepath))

    return {
        "total_pages": total_pages,
        "converted": len(created_files),
        "files": created_files,
        "dimensions": image_dimensions,
        "scale": scale
    }


def main():
    parser = argparse.ArgumentParser(
        description="Convert PDF pages to images"
    )
    parser.add_argument("input", help="Input PDF file")
    parser.add_argument("output_dir", help="Output directory for images")
    parser.add_argument(
        "--scale",
        type=float,
        default=1.5,
        help="Rendering scale factor (default: 1.5)"
    )
    parser.add_argument(
        "--pages",
        help="Page range to convert (e.g., '1-3,5,7-10')"
    )
    parser.add_argument(
        "--format",
        choices=["png", "jpg"],
        default="png",
        help="Image format (default: png)"
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
            "operation": "convert_to_images",
            "error": f"File not found: {args.input}"
        }
        print(json.dumps(result, indent=2))
        sys.exit(1)

    try:
        # Parse page range if provided
        pages = None
        if args.pages:
            # We need to peek at the PDF to get total pages
            if HAS_PYPDFIUM:
                pdf = pdfium.PdfDocument(args.input)
                total_pages = len(pdf)
                pages = parse_page_range(args.pages, total_pages)

        convert_result = convert_to_images(
            args.input,
            args.output_dir,
            scale=args.scale,
            pages=pages,
            format=args.format
        )

        result = {
            "status": "success",
            "operation": "convert_to_images",
            "input": args.input,
            "output_dir": args.output_dir,
            **convert_result
        }

        if args.output_format == "text":
            print(f"Converted {convert_result['converted']} page(s) to images")
            print(f"Scale: {convert_result['scale']}x")
            print(f"Output directory: {args.output_dir}")
            for f in convert_result["files"]:
                print(f"  - {f}")
        else:
            print(json.dumps(result, indent=2))

    except ImportError as e:
        result = {
            "status": "error",
            "operation": "convert_to_images",
            "error": str(e)
        }
        print(json.dumps(result, indent=2))
        sys.exit(1)
    except Exception as e:
        result = {
            "status": "error",
            "operation": "convert_to_images",
            "error": str(e)
        }
        print(json.dumps(result, indent=2))
        sys.exit(1)


if __name__ == "__main__":
    main()

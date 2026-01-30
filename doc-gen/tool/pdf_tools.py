#!/usr/bin/env python3
"""PDF processing tools.

Provides commands for common PDF operations:
- merge: Combine multiple PDFs
- split: Extract pages from PDF
- extract-text: Extract text content
- extract-tables: Extract tables to CSV/JSON
- rotate: Rotate pages
- metadata: Get/set PDF metadata

Usage:
    ./run tool/pdf_tools.py merge file1.pdf file2.pdf -o merged.pdf
    ./run tool/pdf_tools.py split input.pdf -o output_dir/
    ./run tool/pdf_tools.py extract-text document.pdf
    ./run tool/pdf_tools.py extract-tables document.pdf --format csv
    ./run tool/pdf_tools.py rotate input.pdf -o rotated.pdf --angle 90
    ./run tool/pdf_tools.py metadata document.pdf
"""

import argparse
import csv
import io
import json
import sys
from pathlib import Path

try:
    from pypdf import PdfReader, PdfWriter
    HAS_PYPDF = True
except ImportError:
    HAS_PYPDF = False

try:
    import pdfplumber
    HAS_PDFPLUMBER = True
except ImportError:
    HAS_PDFPLUMBER = False


def require_pypdf():
    """Check that pypdf is available."""
    if not HAS_PYPDF:
        raise RuntimeError("pypdf is not installed. Install it with: pip install pypdf")


def require_pdfplumber():
    """Check that pdfplumber is available."""
    if not HAS_PDFPLUMBER:
        raise RuntimeError("pdfplumber is not installed. Install it with: pip install pdfplumber")


def merge_pdfs(input_files: list, output_path: str) -> dict:
    """Merge multiple PDFs into one.

    Args:
        input_files: List of PDF file paths
        output_path: Output PDF path

    Returns:
        Dict with operation results
    """
    require_pypdf()

    writer = PdfWriter()
    total_pages = 0

    for pdf_file in input_files:
        pdf_path = Path(pdf_file)
        if not pdf_path.exists():
            raise FileNotFoundError(f"PDF file not found: {pdf_path}")

        reader = PdfReader(str(pdf_path))
        for page in reader.pages:
            writer.add_page(page)
            total_pages += 1

    output_path = Path(output_path)
    output_path.parent.mkdir(parents=True, exist_ok=True)

    with open(output_path, 'wb') as output:
        writer.write(output)

    return {
        'status': 'success',
        'operation': 'merge',
        'input_files': input_files,
        'output': str(output_path),
        'total_pages': total_pages,
    }


def split_pdf(input_path: str, output_dir: str, pages: str = None) -> dict:
    """Split a PDF into individual pages or page ranges.

    Args:
        input_path: Path to input PDF
        output_dir: Directory for output files
        pages: Optional page specification (e.g., "1-3,5,7-9")

    Returns:
        Dict with operation results
    """
    require_pypdf()

    input_path = Path(input_path)
    if not input_path.exists():
        raise FileNotFoundError(f"PDF file not found: {input_path}")

    output_dir = Path(output_dir)
    output_dir.mkdir(parents=True, exist_ok=True)

    reader = PdfReader(str(input_path))
    total_pages = len(reader.pages)

    # Parse page specification
    if pages:
        page_numbers = parse_page_spec(pages, total_pages)
    else:
        page_numbers = list(range(total_pages))

    output_files = []
    for i, page_num in enumerate(page_numbers):
        writer = PdfWriter()
        writer.add_page(reader.pages[page_num])

        output_file = output_dir / f"page_{page_num + 1:03d}.pdf"
        with open(output_file, 'wb') as output:
            writer.write(output)
        output_files.append(str(output_file))

    return {
        'status': 'success',
        'operation': 'split',
        'input': str(input_path),
        'output_dir': str(output_dir),
        'pages_extracted': len(output_files),
        'output_files': output_files,
    }


def parse_page_spec(spec: str, total_pages: int) -> list:
    """Parse page specification like "1-3,5,7-9" into list of 0-indexed page numbers."""
    pages = []
    for part in spec.split(','):
        part = part.strip()
        if '-' in part:
            start, end = part.split('-', 1)
            start = int(start) - 1
            end = int(end) - 1
            pages.extend(range(max(0, start), min(total_pages, end + 1)))
        else:
            page = int(part) - 1
            if 0 <= page < total_pages:
                pages.append(page)
    return sorted(set(pages))


def extract_text(input_path: str, pages: str = None) -> dict:
    """Extract text from PDF.

    Uses pdfplumber for better layout preservation if available,
    falls back to pypdf otherwise.

    Args:
        input_path: Path to PDF file
        pages: Optional page specification

    Returns:
        Dict with extracted text
    """
    input_path = Path(input_path)
    if not input_path.exists():
        raise FileNotFoundError(f"PDF file not found: {input_path}")

    text_parts = []

    if HAS_PDFPLUMBER:
        with pdfplumber.open(str(input_path)) as pdf:
            total_pages = len(pdf.pages)
            page_numbers = parse_page_spec(pages, total_pages) if pages else range(total_pages)

            for page_num in page_numbers:
                page_text = pdf.pages[page_num].extract_text() or ''
                text_parts.append(f"--- Page {page_num + 1} ---\n{page_text}")
    elif HAS_PYPDF:
        reader = PdfReader(str(input_path))
        total_pages = len(reader.pages)
        page_numbers = parse_page_spec(pages, total_pages) if pages else range(total_pages)

        for page_num in page_numbers:
            page_text = reader.pages[page_num].extract_text() or ''
            text_parts.append(f"--- Page {page_num + 1} ---\n{page_text}")
    else:
        raise RuntimeError("Neither pdfplumber nor pypdf is installed")

    return {
        'status': 'success',
        'operation': 'extract_text',
        'input': str(input_path),
        'pages_processed': len(text_parts),
        'text': '\n\n'.join(text_parts),
    }


def extract_tables(input_path: str, output_format: str = 'json',
                   output_path: str = None, pages: str = None) -> dict:
    """Extract tables from PDF.

    Args:
        input_path: Path to PDF file
        output_format: Output format (json, csv)
        output_path: Optional output file path
        pages: Optional page specification

    Returns:
        Dict with extracted tables
    """
    require_pdfplumber()

    input_path = Path(input_path)
    if not input_path.exists():
        raise FileNotFoundError(f"PDF file not found: {input_path}")

    all_tables = []

    with pdfplumber.open(str(input_path)) as pdf:
        total_pages = len(pdf.pages)
        page_numbers = parse_page_spec(pages, total_pages) if pages else range(total_pages)

        for page_num in page_numbers:
            tables = pdf.pages[page_num].extract_tables()
            for i, table in enumerate(tables):
                if table:  # Skip empty tables
                    all_tables.append({
                        'page': page_num + 1,
                        'table_index': i + 1,
                        'rows': table,
                    })

    result = {
        'status': 'success',
        'operation': 'extract_tables',
        'input': str(input_path),
        'tables_found': len(all_tables),
    }

    if output_format == 'csv' and output_path:
        # Write each table to a separate CSV
        output_path = Path(output_path)
        output_path.mkdir(parents=True, exist_ok=True)

        csv_files = []
        for table in all_tables:
            csv_file = output_path / f"table_p{table['page']}_t{table['table_index']}.csv"
            with open(csv_file, 'w', newline='') as f:
                writer = csv.writer(f)
                for row in table['rows']:
                    writer.writerow(row)
            csv_files.append(str(csv_file))

        result['output_files'] = csv_files
    else:
        result['tables'] = all_tables

    return result


def rotate_pages(input_path: str, output_path: str, angle: int = 90,
                 pages: str = None) -> dict:
    """Rotate pages in a PDF.

    Args:
        input_path: Path to input PDF
        output_path: Path for output PDF
        angle: Rotation angle (90, 180, 270)
        pages: Optional page specification (rotate only these pages)

    Returns:
        Dict with operation results
    """
    require_pypdf()

    input_path = Path(input_path)
    if not input_path.exists():
        raise FileNotFoundError(f"PDF file not found: {input_path}")

    if angle not in (90, 180, 270, -90, -180, -270):
        raise ValueError(f"Invalid rotation angle: {angle}. Use 90, 180, or 270.")

    reader = PdfReader(str(input_path))
    writer = PdfWriter()

    total_pages = len(reader.pages)
    pages_to_rotate = set(parse_page_spec(pages, total_pages)) if pages else set(range(total_pages))

    rotated_count = 0
    for i, page in enumerate(reader.pages):
        if i in pages_to_rotate:
            page.rotate(angle)
            rotated_count += 1
        writer.add_page(page)

    output_path = Path(output_path)
    output_path.parent.mkdir(parents=True, exist_ok=True)

    with open(output_path, 'wb') as output:
        writer.write(output)

    return {
        'status': 'success',
        'operation': 'rotate',
        'input': str(input_path),
        'output': str(output_path),
        'angle': angle,
        'pages_rotated': rotated_count,
    }


def get_metadata(input_path: str) -> dict:
    """Get PDF metadata.

    Args:
        input_path: Path to PDF file

    Returns:
        Dict with metadata
    """
    require_pypdf()

    input_path = Path(input_path)
    if not input_path.exists():
        raise FileNotFoundError(f"PDF file not found: {input_path}")

    reader = PdfReader(str(input_path))
    meta = reader.metadata or {}

    return {
        'status': 'success',
        'operation': 'metadata',
        'input': str(input_path),
        'pages': len(reader.pages),
        'metadata': {
            'title': meta.get('/Title', meta.get('title', '')),
            'author': meta.get('/Author', meta.get('author', '')),
            'subject': meta.get('/Subject', meta.get('subject', '')),
            'creator': meta.get('/Creator', meta.get('creator', '')),
            'producer': meta.get('/Producer', meta.get('producer', '')),
            'creation_date': str(meta.get('/CreationDate', meta.get('creation_date', ''))),
            'modification_date': str(meta.get('/ModDate', meta.get('modification_date', ''))),
        }
    }


def main():
    parser = argparse.ArgumentParser(
        description='PDF processing tools',
        formatter_class=argparse.RawDescriptionHelpFormatter,
    )

    subparsers = parser.add_subparsers(dest='command', help='Command to run')

    # merge command
    merge_parser = subparsers.add_parser('merge', help='Merge multiple PDFs')
    merge_parser.add_argument('files', nargs='+', help='PDF files to merge')
    merge_parser.add_argument('-o', '--output', required=True, help='Output PDF path')

    # split command
    split_parser = subparsers.add_parser('split', help='Split PDF into pages')
    split_parser.add_argument('pdf', help='Input PDF file')
    split_parser.add_argument('-o', '--output', required=True, help='Output directory')
    split_parser.add_argument('-p', '--pages', help='Pages to extract (e.g., "1-3,5,7-9")')

    # extract-text command
    text_parser = subparsers.add_parser('extract-text', help='Extract text from PDF')
    text_parser.add_argument('pdf', help='Input PDF file')
    text_parser.add_argument('-p', '--pages', help='Pages to extract (e.g., "1-3,5")')

    # extract-tables command
    tables_parser = subparsers.add_parser('extract-tables', help='Extract tables from PDF')
    tables_parser.add_argument('pdf', help='Input PDF file')
    tables_parser.add_argument('-f', '--format', default='json',
                               choices=['json', 'csv'],
                               help='Output format (default: json)')
    tables_parser.add_argument('-o', '--output', help='Output path (directory for CSV)')
    tables_parser.add_argument('-p', '--pages', help='Pages to process (e.g., "1-3,5")')

    # rotate command
    rotate_parser = subparsers.add_parser('rotate', help='Rotate PDF pages')
    rotate_parser.add_argument('pdf', help='Input PDF file')
    rotate_parser.add_argument('-o', '--output', required=True, help='Output PDF path')
    rotate_parser.add_argument('-a', '--angle', type=int, default=90,
                               choices=[90, 180, 270, -90, -180, -270],
                               help='Rotation angle (default: 90)')
    rotate_parser.add_argument('-p', '--pages', help='Pages to rotate (e.g., "1-3,5")')

    # metadata command
    meta_parser = subparsers.add_parser('metadata', help='Get PDF metadata')
    meta_parser.add_argument('pdf', help='Input PDF file')

    # Global options
    parser.add_argument('--output-format', default='json',
                        choices=['json', 'text'],
                        help='Output format (default: json)')

    args = parser.parse_args()

    if not args.command:
        parser.print_help()
        sys.exit(1)

    try:
        if args.command == 'merge':
            result = merge_pdfs(args.files, args.output)
        elif args.command == 'split':
            result = split_pdf(args.pdf, args.output, args.pages)
        elif args.command == 'extract-text':
            result = extract_text(args.pdf, args.pages)
        elif args.command == 'extract-tables':
            result = extract_tables(args.pdf, args.format, args.output, args.pages)
        elif args.command == 'rotate':
            result = rotate_pages(args.pdf, args.output, args.angle, args.pages)
        elif args.command == 'metadata':
            result = get_metadata(args.pdf)
        else:
            parser.print_help()
            sys.exit(1)

        if args.output_format == 'json':
            print(json.dumps(result, indent=2))
        else:
            if 'text' in result:
                print(result['text'])
            elif 'tables' in result:
                for table in result['tables']:
                    print(f"\n=== Page {table['page']}, Table {table['table_index']} ===")
                    for row in table['rows']:
                        print('\t'.join(str(cell) for cell in row))
            else:
                print(f"Operation: {result['operation']}")
                for key, value in result.items():
                    if key not in ('status', 'operation'):
                        print(f"{key}: {value}")

    except Exception as e:
        error_result = {
            'status': 'error',
            'operation': args.command,
            'error': str(e)
        }
        print(json.dumps(error_result, indent=2), file=sys.stderr)
        sys.exit(1)


if __name__ == '__main__':
    main()

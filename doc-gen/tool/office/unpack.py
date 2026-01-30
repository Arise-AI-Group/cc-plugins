#!/usr/bin/env python3
"""Unpack DOCX to editable XML structure.

Extracts a DOCX file (which is a ZIP archive) to a directory, with options for:
- Pretty-printing XML for readability
- Merging adjacent runs with identical formatting
- Converting smart quotes to XML entities for safe editing

Usage:
    ./run tool/office/unpack.py document.docx unpacked/
    ./run tool/office/unpack.py document.docx unpacked/ --merge-runs false
"""

import argparse
import json
import os
import re
import sys
import zipfile
from pathlib import Path

from lxml import etree

# Add parent to path for imports
sys.path.insert(0, str(Path(__file__).parent.parent))
from office import NAMESPACES, SMART_QUOTES


def smart_quotes_to_entities(text: str) -> str:
    """Convert smart quote characters to XML entities."""
    for char, entity in SMART_QUOTES.items():
        text = text.replace(char, entity)
    return text


def get_run_properties_key(run: etree._Element) -> str:
    """Get a hashable key representing run properties for merging comparison.

    Two runs can be merged if they have identical formatting (rPr contents).
    """
    rPr = run.find('w:rPr', NAMESPACES)
    if rPr is None:
        return ''
    # Serialize the rPr element for comparison (excluding whitespace differences)
    return etree.tostring(rPr, method='c14n').decode('utf-8')


def merge_adjacent_runs(root: etree._Element) -> int:
    """Merge adjacent w:r elements with identical formatting.

    This simplifies the XML structure, making manual edits easier.
    Returns the number of runs merged.
    """
    merged_count = 0

    # Find all paragraphs
    for para in root.iter('{%s}p' % NAMESPACES['w']):
        children = list(para)
        i = 0

        while i < len(children) - 1:
            current = children[i]
            next_elem = children[i + 1]

            # Check if both are runs
            if (current.tag == '{%s}r' % NAMESPACES['w'] and
                next_elem.tag == '{%s}r' % NAMESPACES['w']):

                # Check if formatting matches
                if get_run_properties_key(current) == get_run_properties_key(next_elem):
                    # Get text elements
                    current_text = current.find('w:t', NAMESPACES)
                    next_text = next_elem.find('w:t', NAMESPACES)

                    # Only merge if both have simple text content (no complex children)
                    current_children = [c.tag for c in current if c.tag != '{%s}rPr' % NAMESPACES['w']]
                    next_children = [c.tag for c in next_elem if c.tag != '{%s}rPr' % NAMESPACES['w']]

                    if (current_children == ['{%s}t' % NAMESPACES['w']] and
                        next_children == ['{%s}t' % NAMESPACES['w']] and
                        current_text is not None and next_text is not None):

                        # Merge text
                        current_text.text = (current_text.text or '') + (next_text.text or '')

                        # Preserve xml:space if either had it
                        if next_text.get('{http://www.w3.org/XML/1998/namespace}space') == 'preserve':
                            current_text.set('{http://www.w3.org/XML/1998/namespace}space', 'preserve')

                        # Remove the merged run
                        para.remove(next_elem)
                        children = list(para)  # Refresh list
                        merged_count += 1
                        continue

            i += 1

    return merged_count


def pretty_print_xml(xml_bytes: bytes) -> bytes:
    """Pretty-print XML with proper indentation."""
    try:
        parser = etree.XMLParser(remove_blank_text=True)
        root = etree.fromstring(xml_bytes, parser)
        return etree.tostring(root, pretty_print=True, xml_declaration=True, encoding='UTF-8')
    except etree.XMLSyntaxError:
        # If parsing fails, return original
        return xml_bytes


def unpack_docx(docx_path: str, output_dir: str, merge_runs: bool = True) -> dict:
    """Unpack a DOCX file to a directory structure.

    Args:
        docx_path: Path to the DOCX file
        output_dir: Directory to extract to
        merge_runs: Whether to merge adjacent runs with identical formatting

    Returns:
        Dict with operation results
    """
    docx_path = Path(docx_path)
    output_dir = Path(output_dir)

    if not docx_path.exists():
        raise FileNotFoundError(f"DOCX file not found: {docx_path}")

    # Create output directory
    output_dir.mkdir(parents=True, exist_ok=True)

    extracted_files = []
    xml_files = []
    merged_runs = 0

    with zipfile.ZipFile(docx_path, 'r') as zf:
        for item in zf.namelist():
            # Read file content
            content = zf.read(item)

            # Determine output path
            out_path = output_dir / item
            out_path.parent.mkdir(parents=True, exist_ok=True)

            # Process XML files
            if item.endswith('.xml') or item.endswith('.rels'):
                xml_files.append(item)

                # Pretty-print XML
                content = pretty_print_xml(content)

                # Convert smart quotes to entities
                text_content = content.decode('utf-8')
                text_content = smart_quotes_to_entities(text_content)

                # Merge runs in document.xml
                if merge_runs and item == 'word/document.xml':
                    try:
                        root = etree.fromstring(text_content.encode('utf-8'))
                        merged_runs = merge_adjacent_runs(root)
                        text_content = etree.tostring(root, pretty_print=True,
                                                       xml_declaration=True,
                                                       encoding='UTF-8').decode('utf-8')
                    except etree.XMLSyntaxError:
                        pass  # Keep original if parsing fails

                content = text_content.encode('utf-8')

            # Write file
            out_path.write_bytes(content)
            extracted_files.append(item)

    return {
        'status': 'success',
        'operation': 'unpack',
        'input': str(docx_path),
        'output_dir': str(output_dir),
        'files_count': len(extracted_files),
        'xml_files': xml_files,
        'merged_runs': merged_runs,
    }


def main():
    parser = argparse.ArgumentParser(
        description='Unpack DOCX to editable XML structure',
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  ./run tool/office/unpack.py document.docx unpacked/
  ./run tool/office/unpack.py document.docx unpacked/ --merge-runs false
        """
    )
    parser.add_argument('docx', help='Path to DOCX file')
    parser.add_argument('output_dir', help='Output directory for unpacked files')
    parser.add_argument('--merge-runs', type=str, default='true',
                        choices=['true', 'false'],
                        help='Merge adjacent runs with identical formatting (default: true)')
    parser.add_argument('--output-format', default='json',
                        choices=['json', 'text'],
                        help='Output format (default: json)')

    args = parser.parse_args()

    try:
        merge_runs = args.merge_runs.lower() == 'true'
        result = unpack_docx(args.docx, args.output_dir, merge_runs=merge_runs)

        if args.output_format == 'json':
            print(json.dumps(result, indent=2))
        else:
            print(f"Unpacked {result['files_count']} files to {result['output_dir']}")
            if result['merged_runs'] > 0:
                print(f"Merged {result['merged_runs']} adjacent runs")

    except Exception as e:
        error_result = {
            'status': 'error',
            'operation': 'unpack',
            'error': str(e)
        }
        print(json.dumps(error_result, indent=2), file=sys.stderr)
        sys.exit(1)


if __name__ == '__main__':
    main()

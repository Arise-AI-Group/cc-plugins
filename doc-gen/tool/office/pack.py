#!/usr/bin/env python3
"""Pack XML directory back into DOCX.

Repackages an unpacked DOCX directory back into a valid DOCX file, with:
- XML validation and auto-repair
- Whitespace preservation handling
- DurableId correction
- Optional reference to original file for content types

Usage:
    ./run tool/office/pack.py unpacked/ output.docx --original input.docx
    ./run tool/office/pack.py unpacked/ output.docx --validate false
"""

import argparse
import json
import os
import random
import re
import sys
import zipfile
from pathlib import Path

from lxml import etree

# Add parent to path for imports
sys.path.insert(0, str(Path(__file__).parent.parent))
from office import NAMESPACES


# Maximum valid durableId value (2^31 - 1)
MAX_DURABLE_ID = 0x7FFFFFFF


def generate_durable_id() -> int:
    """Generate a valid durableId (positive 32-bit integer)."""
    return random.randint(1, MAX_DURABLE_ID)


def fix_durable_ids(root: etree._Element) -> int:
    """Fix durableId values that are too large.

    Word requires durableId to be a positive 32-bit signed integer.
    Returns count of fixed IDs.
    """
    fixed = 0

    # Look for durableId attributes in various namespaces
    for ns_prefix in ['w15', 'w14']:
        ns = NAMESPACES.get(ns_prefix, '')
        if not ns:
            continue

        # Find elements with durableId attribute
        for elem in root.iter():
            attr_name = '{%s}durableId' % ns
            if attr_name in elem.attrib:
                try:
                    current_id = int(elem.attrib[attr_name])
                    if current_id > MAX_DURABLE_ID or current_id < 0:
                        elem.attrib[attr_name] = str(generate_durable_id())
                        fixed += 1
                except ValueError:
                    # Non-numeric, regenerate
                    elem.attrib[attr_name] = str(generate_durable_id())
                    fixed += 1

    return fixed


def fix_whitespace_preservation(root: etree._Element) -> int:
    """Add xml:space="preserve" to w:t elements with leading/trailing whitespace.

    Returns count of fixed elements.
    """
    fixed = 0
    xml_space = '{http://www.w3.org/XML/1998/namespace}space'

    for t_elem in root.iter('{%s}t' % NAMESPACES['w']):
        text = t_elem.text or ''
        if text and (text[0].isspace() or text[-1].isspace()):
            if t_elem.get(xml_space) != 'preserve':
                t_elem.set(xml_space, 'preserve')
                fixed += 1

    # Also check delText elements
    for t_elem in root.iter('{%s}delText' % NAMESPACES['w']):
        text = t_elem.text or ''
        if text and (text[0].isspace() or text[-1].isspace()):
            if t_elem.get(xml_space) != 'preserve':
                t_elem.set(xml_space, 'preserve')
                fixed += 1

    return fixed


def validate_xml_structure(xml_content: bytes, filename: str) -> list:
    """Basic XML validation.

    Returns list of error messages (empty if valid).
    """
    errors = []
    try:
        etree.fromstring(xml_content)
    except etree.XMLSyntaxError as e:
        errors.append(f"{filename}: {str(e)}")
    return errors


def condense_xml(xml_content: bytes) -> bytes:
    """Remove pretty-printing whitespace from XML.

    This reduces file size and avoids potential whitespace issues.
    """
    try:
        parser = etree.XMLParser(remove_blank_text=True)
        root = etree.fromstring(xml_content, parser)
        return etree.tostring(root, xml_declaration=True, encoding='UTF-8')
    except etree.XMLSyntaxError:
        return xml_content


def process_xml_file(content: bytes, filename: str, validate: bool) -> tuple:
    """Process an XML file with validation and auto-repair.

    Returns (processed_content, repairs_made, errors).
    """
    repairs = []
    errors = []

    if validate:
        errors = validate_xml_structure(content, filename)
        if errors:
            return content, repairs, errors

    try:
        root = etree.fromstring(content)

        # Apply auto-repairs
        durable_fixes = fix_durable_ids(root)
        if durable_fixes:
            repairs.append(f"Fixed {durable_fixes} durableId value(s)")

        whitespace_fixes = fix_whitespace_preservation(root)
        if whitespace_fixes:
            repairs.append(f"Added xml:space='preserve' to {whitespace_fixes} element(s)")

        # Condense and serialize
        content = etree.tostring(root, xml_declaration=True, encoding='UTF-8')
        content = condense_xml(content)

    except etree.XMLSyntaxError as e:
        if validate:
            errors.append(f"{filename}: {str(e)}")

    return content, repairs, errors


def pack_docx(input_dir: str, output_path: str, original_path: str = None,
              validate: bool = True) -> dict:
    """Pack a directory back into a DOCX file.

    Args:
        input_dir: Directory containing unpacked DOCX structure
        output_path: Path for output DOCX file
        original_path: Optional path to original DOCX for reference
        validate: Whether to validate XML structure

    Returns:
        Dict with operation results
    """
    input_dir = Path(input_dir)
    output_path = Path(output_path)

    if not input_dir.exists():
        raise FileNotFoundError(f"Input directory not found: {input_dir}")

    # Collect files to pack
    files_to_pack = []
    for root, dirs, files in os.walk(input_dir):
        for file in files:
            full_path = Path(root) / file
            rel_path = full_path.relative_to(input_dir)
            files_to_pack.append((full_path, str(rel_path).replace(os.sep, '/')))

    if not files_to_pack:
        raise ValueError(f"No files found in {input_dir}")

    # Check for required files
    rel_paths = [f[1] for f in files_to_pack]
    if '[Content_Types].xml' not in rel_paths:
        raise ValueError("Missing [Content_Types].xml - not a valid DOCX structure")

    all_repairs = []
    all_errors = []

    # Create output directory if needed
    output_path.parent.mkdir(parents=True, exist_ok=True)

    # Create DOCX (ZIP with specific compression)
    with zipfile.ZipFile(output_path, 'w', zipfile.ZIP_DEFLATED) as zf:
        for full_path, rel_path in files_to_pack:
            content = full_path.read_bytes()

            # Process XML files
            if rel_path.endswith('.xml') or rel_path.endswith('.rels'):
                content, repairs, errors = process_xml_file(content, rel_path, validate)
                if repairs:
                    all_repairs.extend([f"{rel_path}: {r}" for r in repairs])
                if errors:
                    all_errors.extend(errors)

            zf.writestr(rel_path, content)

    result = {
        'status': 'success' if not all_errors else 'warning',
        'operation': 'pack',
        'input_dir': str(input_dir),
        'output': str(output_path),
        'files_count': len(files_to_pack),
    }

    if all_repairs:
        result['repairs'] = all_repairs

    if all_errors:
        result['status'] = 'error'
        result['errors'] = all_errors

    return result


def main():
    parser = argparse.ArgumentParser(
        description='Pack XML directory back into DOCX',
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  ./run tool/office/pack.py unpacked/ output.docx
  ./run tool/office/pack.py unpacked/ output.docx --original input.docx
  ./run tool/office/pack.py unpacked/ output.docx --validate false

Auto-repairs:
  - durableId values >= 0x7FFFFFFF are regenerated
  - Missing xml:space="preserve" added to w:t with whitespace
        """
    )
    parser.add_argument('input_dir', help='Directory containing unpacked DOCX')
    parser.add_argument('output', help='Output DOCX file path')
    parser.add_argument('--original', help='Original DOCX file for reference (unused, for compatibility)')
    parser.add_argument('--validate', type=str, default='true',
                        choices=['true', 'false'],
                        help='Validate XML structure (default: true)')
    parser.add_argument('--output-format', default='json',
                        choices=['json', 'text'],
                        help='Output format (default: json)')

    args = parser.parse_args()

    try:
        validate = args.validate.lower() == 'true'
        result = pack_docx(args.input_dir, args.output,
                          original_path=args.original, validate=validate)

        if args.output_format == 'json':
            print(json.dumps(result, indent=2))
        else:
            print(f"Packed {result['files_count']} files to {result['output']}")
            if 'repairs' in result:
                print("Repairs made:")
                for repair in result['repairs']:
                    print(f"  - {repair}")
            if 'errors' in result:
                print("Errors:")
                for error in result['errors']:
                    print(f"  - {error}")

        if result['status'] == 'error':
            sys.exit(1)

    except Exception as e:
        error_result = {
            'status': 'error',
            'operation': 'pack',
            'error': str(e)
        }
        print(json.dumps(error_result, indent=2), file=sys.stderr)
        sys.exit(1)


if __name__ == '__main__':
    main()

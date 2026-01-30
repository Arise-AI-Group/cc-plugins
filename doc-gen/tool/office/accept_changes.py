#!/usr/bin/env python3
"""Accept all tracked changes in an unpacked DOCX.

Processes the XML to accept all tracked changes:
- Removes all w:del elements (deletions disappear)
- Unwraps w:ins elements (keeps content, removes insertion markers)
- Handles paragraph mark deletions
- Processes document.xml, headers, footers

Usage:
    ./run tool/office/accept_changes.py unpacked/
"""

import argparse
import json
import sys
from pathlib import Path

from lxml import etree

# Add parent to path for imports
sys.path.insert(0, str(Path(__file__).parent.parent))
from office import NAMESPACES


def remove_deletions(root: etree._Element) -> int:
    """Remove all w:del elements from the document.

    Returns count of deletions removed.
    """
    removed = 0
    w_ns = NAMESPACES['w']

    # Find all w:del elements
    del_elements = root.findall('.//{%s}del' % w_ns)

    for del_elem in del_elements:
        parent = del_elem.getparent()
        if parent is not None:
            parent.remove(del_elem)
            removed += 1

    # Also handle paragraph mark deletions (w:del inside w:pPr/w:rPr)
    for rPr in root.findall('.//{%s}rPr' % w_ns):
        del_marker = rPr.find('{%s}del' % w_ns)
        if del_marker is not None:
            rPr.remove(del_marker)
            removed += 1

    return removed


def unwrap_insertions(root: etree._Element) -> int:
    """Unwrap all w:ins elements, keeping their content.

    Returns count of insertions unwrapped.
    """
    unwrapped = 0
    w_ns = NAMESPACES['w']

    # Process insertions - need to handle carefully to preserve order
    while True:
        ins_elements = root.findall('.//{%s}ins' % w_ns)
        if not ins_elements:
            break

        for ins_elem in ins_elements:
            parent = ins_elem.getparent()
            if parent is None:
                continue

            # Get position in parent
            index = list(parent).index(ins_elem)

            # Move all children to parent at the same position
            children = list(ins_elem)
            for i, child in enumerate(children):
                ins_elem.remove(child)
                parent.insert(index + i, child)

            # Remove the now-empty ins element
            parent.remove(ins_elem)
            unwrapped += 1

        # Check if we made progress (avoid infinite loop)
        new_ins = root.findall('.//{%s}ins' % w_ns)
        if len(new_ins) >= len(ins_elements):
            break

    return unwrapped


def remove_move_markers(root: etree._Element) -> int:
    """Remove move-from and move-to markers.

    These are used for tracking moved content.
    Returns count of markers removed.
    """
    removed = 0
    w_ns = NAMESPACES['w']

    # Remove moveFrom markers (treat as deletions - remove content)
    for elem in root.findall('.//{%s}moveFrom' % w_ns):
        parent = elem.getparent()
        if parent is not None:
            parent.remove(elem)
            removed += 1

    # Unwrap moveTo markers (keep content)
    while True:
        move_to_elements = root.findall('.//{%s}moveTo' % w_ns)
        if not move_to_elements:
            break

        for move_elem in move_to_elements:
            parent = move_elem.getparent()
            if parent is None:
                continue

            index = list(parent).index(move_elem)
            children = list(move_elem)
            for i, child in enumerate(children):
                move_elem.remove(child)
                parent.insert(index + i, child)
            parent.remove(move_elem)
            removed += 1

        new_moves = root.findall('.//{%s}moveTo' % w_ns)
        if len(new_moves) >= len(move_to_elements):
            break

    # Remove moveFromRangeStart/End and moveToRangeStart/End
    for tag in ['moveFromRangeStart', 'moveFromRangeEnd',
                'moveToRangeStart', 'moveToRangeEnd']:
        for elem in root.findall('.//{%s}%s' % (w_ns, tag)):
            parent = elem.getparent()
            if parent is not None:
                parent.remove(elem)
                removed += 1

    return removed


def remove_custom_xml_markers(root: etree._Element) -> int:
    """Remove customXmlInsRangeStart/End and customXmlDelRangeStart/End.

    Returns count of markers removed.
    """
    removed = 0
    w_ns = NAMESPACES['w']

    for tag in ['customXmlInsRangeStart', 'customXmlInsRangeEnd',
                'customXmlDelRangeStart', 'customXmlDelRangeEnd']:
        for elem in root.findall('.//{%s}%s' % (w_ns, tag)):
            parent = elem.getparent()
            if parent is not None:
                parent.remove(elem)
                removed += 1

    return removed


def process_xml_file(file_path: Path) -> dict:
    """Process a single XML file to accept tracked changes.

    Returns dict with counts of changes made.
    """
    content = file_path.read_bytes()

    try:
        root = etree.fromstring(content)
    except etree.XMLSyntaxError as e:
        return {'error': str(e)}

    deletions = remove_deletions(root)
    insertions = unwrap_insertions(root)
    moves = remove_move_markers(root)
    custom_xml = remove_custom_xml_markers(root)

    total = deletions + insertions + moves + custom_xml

    if total > 0:
        # Write back
        new_content = etree.tostring(root, pretty_print=True,
                                      xml_declaration=True, encoding='UTF-8')
        file_path.write_bytes(new_content)

    return {
        'deletions_removed': deletions,
        'insertions_unwrapped': insertions,
        'moves_processed': moves,
        'custom_xml_markers': custom_xml,
        'total_changes': total
    }


def accept_changes(unpacked_dir: str) -> dict:
    """Accept all tracked changes in an unpacked DOCX directory.

    Args:
        unpacked_dir: Path to unpacked DOCX directory

    Returns:
        Dict with operation results
    """
    unpacked_dir = Path(unpacked_dir)

    if not unpacked_dir.exists():
        raise FileNotFoundError(f"Directory not found: {unpacked_dir}")

    word_dir = unpacked_dir / 'word'
    if not word_dir.exists():
        raise ValueError(f"Not a valid DOCX structure: missing word/ directory")

    # Files that may contain tracked changes
    files_to_process = [
        word_dir / 'document.xml',
    ]

    # Add headers and footers
    for f in word_dir.glob('header*.xml'):
        files_to_process.append(f)
    for f in word_dir.glob('footer*.xml'):
        files_to_process.append(f)

    # Add footnotes and endnotes
    for name in ['footnotes.xml', 'endnotes.xml']:
        if (word_dir / name).exists():
            files_to_process.append(word_dir / name)

    results = {}
    total_changes = 0

    for file_path in files_to_process:
        if file_path.exists():
            rel_path = str(file_path.relative_to(unpacked_dir))
            result = process_xml_file(file_path)
            if 'error' not in result and result['total_changes'] > 0:
                results[rel_path] = result
                total_changes += result['total_changes']

    return {
        'status': 'success',
        'operation': 'accept_changes',
        'input_dir': str(unpacked_dir),
        'files_processed': len([f for f in files_to_process if f.exists()]),
        'total_changes': total_changes,
        'details': results
    }


def main():
    parser = argparse.ArgumentParser(
        description='Accept all tracked changes in an unpacked DOCX',
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  ./run tool/office/accept_changes.py unpacked/

This modifies the XML files in place. The changes include:
  - Removing all deletions (w:del elements)
  - Unwrapping all insertions (keeping w:ins content)
  - Processing move markers
  - Removing custom XML change markers
        """
    )
    parser.add_argument('unpacked_dir', help='Path to unpacked DOCX directory')
    parser.add_argument('--output-format', default='json',
                        choices=['json', 'text'],
                        help='Output format (default: json)')

    args = parser.parse_args()

    try:
        result = accept_changes(args.unpacked_dir)

        if args.output_format == 'json':
            print(json.dumps(result, indent=2))
        else:
            print(f"Accepted {result['total_changes']} tracked changes")
            for file_path, details in result.get('details', {}).items():
                print(f"  {file_path}:")
                print(f"    - {details['deletions_removed']} deletions removed")
                print(f"    - {details['insertions_unwrapped']} insertions accepted")

    except Exception as e:
        error_result = {
            'status': 'error',
            'operation': 'accept_changes',
            'error': str(e)
        }
        print(json.dumps(error_result, indent=2), file=sys.stderr)
        sys.exit(1)


if __name__ == '__main__':
    main()

#!/usr/bin/env python3
"""Add comments to unpacked DOCX.

Creates/updates comments.xml with new comments. After running this,
you still need to add comment markers to document.xml.

Usage:
    ./run tool/office/comment.py unpacked/ 0 "Comment text"
    ./run tool/office/comment.py unpacked/ 1 "Reply" --parent 0
    ./run tool/office/comment.py unpacked/ 0 "Text" --author "Custom Author"
"""

import argparse
import json
import sys
from datetime import datetime, timezone
from pathlib import Path

from lxml import etree

# Add parent to path for imports
sys.path.insert(0, str(Path(__file__).parent.parent))
from office import NAMESPACES


# XML template for comments.xml if it doesn't exist
COMMENTS_XML_TEMPLATE = """<?xml version="1.0" encoding="UTF-8" standalone="yes"?>
<w:comments xmlns:w="http://schemas.openxmlformats.org/wordprocessingml/2006/main"
            xmlns:w14="http://schemas.microsoft.com/office/word/2010/wordml"
            xmlns:w15="http://schemas.microsoft.com/office/word/2012/wordml">
</w:comments>"""

# Template for commentsExtended.xml (for threaded comments)
COMMENTS_EXTENDED_TEMPLATE = """<?xml version="1.0" encoding="UTF-8" standalone="yes"?>
<w15:commentsEx xmlns:w15="http://schemas.microsoft.com/office/word/2012/wordml">
</w15:commentsEx>"""

# Relationship types
COMMENTS_REL_TYPE = "http://schemas.openxmlformats.org/officeDocument/2006/relationships/comments"
COMMENTS_EXTENDED_REL_TYPE = "http://schemas.microsoft.com/office/2011/relationships/commentsExtended"


def get_iso_timestamp() -> str:
    """Get current timestamp in ISO format for Word."""
    return datetime.now(timezone.utc).strftime('%Y-%m-%dT%H:%M:%SZ')


def ensure_comments_file(word_dir: Path) -> etree._Element:
    """Ensure comments.xml exists and return its root element."""
    comments_path = word_dir / 'comments.xml'

    if comments_path.exists():
        return etree.parse(str(comments_path)).getroot()
    else:
        # Create new comments.xml
        root = etree.fromstring(COMMENTS_XML_TEMPLATE.encode())
        return root


def ensure_comments_extended_file(word_dir: Path) -> etree._Element:
    """Ensure commentsExtended.xml exists and return its root element."""
    extended_path = word_dir / 'commentsExtended.xml'

    if extended_path.exists():
        return etree.parse(str(extended_path)).getroot()
    else:
        root = etree.fromstring(COMMENTS_EXTENDED_TEMPLATE.encode())
        return root


def add_comment_relationship(word_dir: Path, comment_type: str = 'comments') -> str:
    """Add relationship for comments.xml if not present. Returns rId."""
    rels_path = word_dir / '_rels' / 'document.xml.rels'

    if not rels_path.exists():
        raise FileNotFoundError("document.xml.rels not found")

    tree = etree.parse(str(rels_path))
    root = tree.getroot()

    # Namespace for relationships
    rel_ns = "http://schemas.openxmlformats.org/package/2006/relationships"

    if comment_type == 'comments':
        target = 'comments.xml'
        rel_type = COMMENTS_REL_TYPE
    else:
        target = 'commentsExtended.xml'
        rel_type = COMMENTS_EXTENDED_REL_TYPE

    # Check if relationship already exists
    for rel in root.findall('{%s}Relationship' % rel_ns):
        if rel.get('Target') == target:
            return rel.get('Id')

    # Find next available rId
    existing_ids = [rel.get('Id') for rel in root.findall('{%s}Relationship' % rel_ns)]
    next_id = 1
    while f'rId{next_id}' in existing_ids:
        next_id += 1

    new_rid = f'rId{next_id}'

    # Add relationship
    new_rel = etree.SubElement(root, '{%s}Relationship' % rel_ns)
    new_rel.set('Id', new_rid)
    new_rel.set('Type', rel_type)
    new_rel.set('Target', target)

    # Save
    tree.write(str(rels_path), xml_declaration=True, encoding='UTF-8')

    return new_rid


def add_content_type(unpacked_dir: Path, extension: str = None, part_name: str = None,
                     content_type: str = None) -> None:
    """Add content type to [Content_Types].xml if not present."""
    ct_path = unpacked_dir / '[Content_Types].xml'

    if not ct_path.exists():
        raise FileNotFoundError("[Content_Types].xml not found")

    tree = etree.parse(str(ct_path))
    root = tree.getroot()

    ct_ns = "http://schemas.openxmlformats.org/package/2006/content-types"

    if part_name:
        # Check if override exists
        for override in root.findall('{%s}Override' % ct_ns):
            if override.get('PartName') == part_name:
                return

        # Add override
        new_override = etree.SubElement(root, '{%s}Override' % ct_ns)
        new_override.set('PartName', part_name)
        new_override.set('ContentType', content_type)

    tree.write(str(ct_path), xml_declaration=True, encoding='UTF-8')


def create_comment_element(comment_id: int, author: str, text: str,
                           initials: str = None) -> etree._Element:
    """Create a w:comment element."""
    w_ns = NAMESPACES['w']

    # Build comment structure
    comment = etree.Element('{%s}comment' % w_ns)
    comment.set('{%s}id' % w_ns, str(comment_id))
    comment.set('{%s}author' % w_ns, author)
    comment.set('{%s}date' % w_ns, get_iso_timestamp())
    if initials:
        comment.set('{%s}initials' % w_ns, initials)

    # Add paragraph with text
    para = etree.SubElement(comment, '{%s}p' % w_ns)

    # Add run with text
    run = etree.SubElement(para, '{%s}r' % w_ns)
    t = etree.SubElement(run, '{%s}t' % w_ns)
    t.text = text

    return comment


def create_comment_extended(comment_id: int, parent_id: int = None) -> etree._Element:
    """Create a w15:commentEx element for threading."""
    w15_ns = NAMESPACES['w15']

    comment_ex = etree.Element('{%s}commentEx' % w15_ns)
    comment_ex.set('{%s}paraId' % w15_ns, format(comment_id, '08X'))

    if parent_id is not None:
        comment_ex.set('{%s}paraIdParent' % w15_ns, format(parent_id, '08X'))

    # Mark as done = false (comment is active)
    comment_ex.set('{%s}done' % w15_ns, '0')

    return comment_ex


def add_comment(unpacked_dir: str, comment_id: int, text: str,
                author: str = "Claude", parent_id: int = None,
                initials: str = None) -> dict:
    """Add a comment to an unpacked DOCX.

    Args:
        unpacked_dir: Path to unpacked DOCX directory
        comment_id: Unique ID for this comment
        text: Comment text (should be pre-escaped if contains XML entities)
        author: Comment author name
        parent_id: ID of parent comment if this is a reply
        initials: Author initials (optional)

    Returns:
        Dict with operation results
    """
    unpacked_dir = Path(unpacked_dir)
    word_dir = unpacked_dir / 'word'

    if not word_dir.exists():
        raise ValueError(f"Not a valid DOCX structure: missing word/ directory")

    # Ensure comments.xml exists and get root
    comments_root = ensure_comments_file(word_dir)

    # Create comment element
    comment_elem = create_comment_element(comment_id, author, text, initials)

    # Add to comments
    comments_root.append(comment_elem)

    # Save comments.xml
    comments_path = word_dir / 'comments.xml'
    etree.ElementTree(comments_root).write(
        str(comments_path), pretty_print=True,
        xml_declaration=True, encoding='UTF-8'
    )

    # Add relationship if needed
    add_comment_relationship(word_dir, 'comments')

    # Add content type
    add_content_type(
        unpacked_dir,
        part_name='/word/comments.xml',
        content_type='application/vnd.openxmlformats-officedocument.wordprocessingml.comments+xml'
    )

    # Handle threaded comments (replies)
    if parent_id is not None:
        extended_root = ensure_comments_extended_file(word_dir)
        comment_ex = create_comment_extended(comment_id, parent_id)
        extended_root.append(comment_ex)

        extended_path = word_dir / 'commentsExtended.xml'
        etree.ElementTree(extended_root).write(
            str(extended_path), pretty_print=True,
            xml_declaration=True, encoding='UTF-8'
        )

        add_comment_relationship(word_dir, 'extended')
        add_content_type(
            unpacked_dir,
            part_name='/word/commentsExtended.xml',
            content_type='application/vnd.openxmlformats-officedocument.wordprocessingml.commentsExtended+xml'
        )

    result = {
        'status': 'success',
        'operation': 'add_comment',
        'comment_id': comment_id,
        'author': author,
        'text': text[:50] + ('...' if len(text) > 50 else ''),
    }

    if parent_id is not None:
        result['parent_id'] = parent_id
        result['is_reply'] = True

    result['next_step'] = (
        "Add markers to document.xml:\n"
        f"  <w:commentRangeStart w:id=\"{comment_id}\"/>\n"
        f"  ... content to comment on ...\n"
        f"  <w:commentRangeEnd w:id=\"{comment_id}\"/>\n"
        f"  <w:r><w:rPr><w:rStyle w:val=\"CommentReference\"/></w:rPr>"
        f"<w:commentReference w:id=\"{comment_id}\"/></w:r>"
    )

    return result


def main():
    parser = argparse.ArgumentParser(
        description='Add comments to unpacked DOCX',
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  ./run tool/office/comment.py unpacked/ 0 "This needs revision"
  ./run tool/office/comment.py unpacked/ 1 "I agree" --parent 0
  ./run tool/office/comment.py unpacked/ 2 "Fixed" --author "Jane Doe"

After adding a comment, you must add markers to document.xml:
  <w:commentRangeStart w:id="0"/>
  ... content to comment on ...
  <w:commentRangeEnd w:id="0"/>
  <w:r><w:rPr><w:rStyle w:val="CommentReference"/></w:rPr><w:commentReference w:id="0"/></w:r>

For replies, nest the markers inside the parent's range.
        """
    )
    parser.add_argument('unpacked_dir', help='Path to unpacked DOCX directory')
    parser.add_argument('comment_id', type=int, help='Unique comment ID (integer)')
    parser.add_argument('text', help='Comment text')
    parser.add_argument('--author', default='Claude', help='Comment author (default: Claude)')
    parser.add_argument('--parent', type=int, help='Parent comment ID for replies')
    parser.add_argument('--initials', help='Author initials')
    parser.add_argument('--output-format', default='json',
                        choices=['json', 'text'],
                        help='Output format (default: json)')

    args = parser.parse_args()

    try:
        result = add_comment(
            args.unpacked_dir,
            args.comment_id,
            args.text,
            author=args.author,
            parent_id=args.parent,
            initials=args.initials
        )

        if args.output_format == 'json':
            print(json.dumps(result, indent=2))
        else:
            print(f"Added comment {result['comment_id']} by {result['author']}")
            if result.get('is_reply'):
                print(f"  (reply to comment {result['parent_id']})")
            print(f"\n{result['next_step']}")

    except Exception as e:
        error_result = {
            'status': 'error',
            'operation': 'add_comment',
            'error': str(e)
        }
        print(json.dumps(error_result, indent=2), file=sys.stderr)
        sys.exit(1)


if __name__ == '__main__':
    main()

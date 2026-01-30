"""Office document manipulation utilities.

This package provides tools for working with Office Open XML documents:
- unpack.py: Extract DOCX to editable XML structure
- pack.py: Repackage XML back to DOCX with validation
- accept_changes.py: Accept all tracked changes via XML manipulation
- comment.py: Add/manage comments in documents
"""

# OOXML namespaces used across modules
NAMESPACES = {
    'w': 'http://schemas.openxmlformats.org/wordprocessingml/2006/main',
    'w14': 'http://schemas.microsoft.com/office/word/2010/wordml',
    'w15': 'http://schemas.microsoft.com/office/word/2012/wordml',
    'r': 'http://schemas.openxmlformats.org/officeDocument/2006/relationships',
    'a': 'http://schemas.openxmlformats.org/drawingml/2006/main',
    'wp': 'http://schemas.openxmlformats.org/drawingml/2006/wordprocessingDrawing',
    'pic': 'http://schemas.openxmlformats.org/drawingml/2006/picture',
    'mc': 'http://schemas.openxmlformats.org/markup-compatibility/2006',
    'cp': 'http://schemas.openxmlformats.org/package/2006/metadata/core-properties',
    'dc': 'http://purl.org/dc/elements/1.1/',
    'dcterms': 'http://purl.org/dc/terms/',
}

# Smart quote character mappings for XML entity conversion
SMART_QUOTES = {
    '\u2018': '&#x2018;',  # Left single quote
    '\u2019': '&#x2019;',  # Right single quote / apostrophe
    '\u201C': '&#x201C;',  # Left double quote
    '\u201D': '&#x201D;',  # Right double quote
    '\u2014': '&#x2014;',  # Em dash
    '\u2013': '&#x2013;',  # En dash
    '\u2026': '&#x2026;',  # Ellipsis
}

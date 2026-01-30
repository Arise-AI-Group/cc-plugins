"""DOCX document builder for programmatic document construction.

This module provides low-level building blocks for creating professional
Word documents. Each function operates on a document file path, enabling
stateless CLI operation.
"""

from .core import create_document, load_document, save_document, get_document_metadata
from .content import add_heading, add_paragraph, add_bullet_list, add_numbered_list
from .tables import add_table, add_simple_table

__all__ = [
    "create_document",
    "load_document",
    "save_document",
    "get_document_metadata",
    "add_heading",
    "add_paragraph",
    "add_bullet_list",
    "add_numbered_list",
    "add_table",
    "add_simple_table",
]

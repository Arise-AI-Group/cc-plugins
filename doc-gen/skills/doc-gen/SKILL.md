---
name: doc-gen
description: This skill should be used when the user asks to "create a document", "generate PDF", "edit DOCX", "add tracked changes", "extract text from PDF", "merge PDFs", "add comments to document", "convert markdown to Word". Comprehensive document generation, editing, and processing for DOCX and PDF files.
---

# Document Generation & Processing

## Overview

This plugin provides three core capabilities:

1. **Document Generation** - Create PDFs and DOCX from HTML/Markdown
2. **DOCX Editing** - Edit existing DOCX files via XML manipulation
3. **PDF Processing** - Extract, merge, split, and analyze PDFs

## Quick Reference

| Task | Tool | Command |
|------|------|---------|
| HTML to PDF | doc_gen.py | `./run tool/doc_gen.py pdf input.html -o output.pdf` |
| Markdown to DOCX | doc_gen.py | `./run tool/doc_gen.py docx input.md -o output.docx` |
| Extract text from DOCX | docx_tools.py | `./run tool/docx_tools.py extract doc.docx` |
| Accept tracked changes | docx_tools.py | `./run tool/docx_tools.py accept-changes in.docx out.docx` |
| DOCX to PDF | docx_tools.py | `./run tool/docx_tools.py to-pdf doc.docx` |
| Unpack DOCX for editing | unpack.py | `./run tool/office/unpack.py doc.docx unpacked/` |
| Repack DOCX after editing | pack.py | `./run tool/office/pack.py unpacked/ output.docx` |
| Add comment to DOCX | comment.py | `./run tool/office/comment.py unpacked/ 0 "Comment text"` |
| Merge PDFs | pdf_tools.py | `./run tool/pdf_tools.py merge f1.pdf f2.pdf -o out.pdf` |
| Split PDF | pdf_tools.py | `./run tool/pdf_tools.py split doc.pdf -o pages/` |
| Extract PDF text | pdf_tools.py | `./run tool/pdf_tools.py extract-text doc.pdf` |
| Extract PDF tables | pdf_tools.py | `./run tool/pdf_tools.py extract-tables doc.pdf` |

---

## Document Generation

Generate professional documents from HTML or Markdown using templates and styles.

### HTML to PDF

```bash
./run tool/doc_gen.py pdf template.html -o output.pdf --style report
```

Built-in styles: `quote`, `report`, `invoice`

### Markdown to DOCX

```bash
./run tool/doc_gen.py docx content.md -o output.docx
```

### With Template Variables

```bash
./run tool/doc_gen.py pdf template.html -o output.pdf \
  --var "client_name=Acme Corp" \
  --var "date=2025-01-30"
```

Templates use Jinja2 syntax: `{{ client_name }}`

---

## DOCX Editing

Edit existing DOCX files using the unpack/edit/pack workflow. This enables tracked changes, comments, and precise formatting control.

### Workflow

1. **Unpack**: Extract DOCX to XML
   ```bash
   ./run tool/office/unpack.py document.docx unpacked/
   ```

2. **Edit**: Modify XML files in `unpacked/word/`
   - Use the Edit tool for string replacements
   - See `references/docx-editing.md` for tracked changes patterns
   - See `references/docx-xml-reference.md` for XML structure

3. **Repack**: Create new DOCX
   ```bash
   ./run tool/office/pack.py unpacked/ output.docx
   ```

### Quick Operations

**Accept all tracked changes:**
```bash
./run tool/docx_tools.py accept-changes input.docx clean.docx
```

**Extract text:**
```bash
./run tool/docx_tools.py extract document.docx
```

**Add a comment:**
```bash
./run tool/office/comment.py unpacked/ 0 "This needs revision" --author "Claude"
```
Then add markers to document.xml (see `references/docx-editing.md`).

---

## PDF Processing

Process PDF files: merge, split, extract content, and analyze.

### Merge PDFs

```bash
./run tool/pdf_tools.py merge file1.pdf file2.pdf file3.pdf -o combined.pdf
```

### Split PDF

```bash
# All pages to individual files
./run tool/pdf_tools.py split document.pdf -o pages/

# Specific pages
./run tool/pdf_tools.py split document.pdf -o pages/ --pages "1-3,5,7-10"
```

### Extract Text

```bash
./run tool/pdf_tools.py extract-text document.pdf
./run tool/pdf_tools.py extract-text document.pdf --pages "1-5"
```

### Extract Tables

```bash
# Get tables as JSON
./run tool/pdf_tools.py extract-tables document.pdf

# Export to CSV files
./run tool/pdf_tools.py extract-tables document.pdf --format csv -o tables/
```

### Rotate Pages

```bash
./run tool/pdf_tools.py rotate document.pdf -o rotated.pdf --angle 90
./run tool/pdf_tools.py rotate document.pdf -o rotated.pdf --angle 180 --pages "2,4"
```

### Get Metadata

```bash
./run tool/pdf_tools.py metadata document.pdf
```

---

## Reference Documentation

For detailed procedures and XML patterns:

- **[docx-editing.md](references/docx-editing.md)** - Tracked changes, comments, unpack/pack workflow
- **[docx-xml-reference.md](references/docx-xml-reference.md)** - OOXML structure, element patterns, schema compliance
- **[pdf-operations.md](references/pdf-operations.md)** - Advanced PDF processing, Python library usage

---

## Dependencies

- **pandoc** - Markdown/DOCX conversion (external)
- **weasyprint** - HTML to PDF rendering
- **lxml** - XML processing for DOCX editing
- **pypdf** - PDF manipulation
- **pdfplumber** - PDF text/table extraction

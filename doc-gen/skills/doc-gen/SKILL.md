---
name: doc-gen
description: This skill should be used when the user asks to "create a document", "generate PDF", "edit DOCX", "add tracked changes", "extract text from PDF", "merge PDFs", "add comments to document", "convert markdown to Word", "fill PDF form", "check if PDF is fillable", "extract form fields". Comprehensive document generation, editing, and processing for DOCX and PDF files.
---

# Document Generation & Processing

## Overview

This plugin provides four core capabilities:

1. **Document Generation** - Create PDFs and DOCX from HTML/Markdown
2. **DOCX Editing** - Edit existing DOCX files via XML manipulation
3. **PDF Processing** - Extract, merge, split, and analyze PDFs
4. **PDF Form Filling** - Fill both fillable and non-fillable PDF forms

## Quick Reference

| Task | Tool | Command |
|------|------|---------|
| Create styled DOCX | docx_builder | `./run tool/docx_builder/cli.py create doc.docx --preset professional` |
| Add heading | docx_builder | `./run tool/docx_builder/cli.py add-heading doc.docx "Title" --level 1` |
| Add paragraph | docx_builder | `./run tool/docx_builder/cli.py add-paragraph doc.docx "Text..."` |
| Add table | docx_builder | `./run tool/docx_builder/cli.py add-table doc.docx --data '[["A","B"],["1","2"]]'` |
| HTML to PDF | doc_gen.py | `./run tool/doc_gen.py pdf input.html -o output.pdf` |
| Markdown to DOCX (basic) | doc_gen.py | `./run tool/doc_gen.py docx input.md -o output.docx` |
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
| Check if PDF is fillable | check_fillable.py | `./run tool/forms/check_fillable.py doc.pdf` |
| Extract form fields | extract_fields.py | `./run tool/forms/extract_fields.py doc.pdf -o fields.json` |
| Fill fillable PDF | fill_fields.py | `./run tool/forms/fill_fields.py doc.pdf values.json -o filled.pdf` |
| PDF to images | convert_to_images.py | `./run tool/forms/convert_to_images.py doc.pdf images/` |
| Extract form structure | extract_structure.py | `./run tool/forms/extract_structure.py doc.pdf -o structure.json` |
| Fill with annotations | fill_annotations.py | `./run tool/forms/fill_annotations.py doc.pdf fields.json -o filled.pdf` |

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

## Styled DOCX Builder

Build professional DOCX documents programmatically with full styling control. Uses a unified style system with JSON presets.

### Built-in Styles

| Style | Description |
|-------|-------------|
| `default` | Clean, minimal styling |
| `professional` | Business documents with blue headers |
| `proposal` | Quote/proposal with accent highlights |
| `40hero` | 4.0 Hero Industrial branding |

### Workflow

1. **Create document with style:**
   ```bash
   ./run tool/docx_builder/cli.py create output.docx --preset professional
   ```

2. **Add content elements:**
   ```bash
   ./run tool/docx_builder/cli.py add-heading output.docx "Document Title" --level 1
   ./run tool/docx_builder/cli.py add-paragraph output.docx "Introduction paragraph text..."
   ./run tool/docx_builder/cli.py add-bullet-list output.docx --items '["Item 1", "Item 2"]'
   ./run tool/docx_builder/cli.py add-table output.docx --data '[["Header A", "Header B"], ["Row 1", "Data"]]'
   ```

3. **Finalize (optional):**
   ```bash
   ./run tool/docx_builder/cli.py finalize output.docx --cleanup-metadata
   ```

### Style Overrides

Override style settings per-element:

```bash
# Custom color on heading
./run tool/docx_builder/cli.py add-heading doc.docx "Title" --color "#E07A38"

# Custom font
./run tool/docx_builder/cli.py add-paragraph doc.docx "Text" --font "Calibri" --font-size 12
```

### Creating Custom Styles

Copy and modify an existing style:

```bash
cp styles/professional.json styles/my-brand.json
# Edit colors, fonts, spacing in my-brand.json
./run tool/docx_builder/cli.py create doc.docx --preset my-brand
```

For full style configuration schema, see **[docx-style-config.md](references/docx-style-config.md)**.

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

## PDF Form Filling

Fill both fillable PDF forms (with AcroForm fields) and non-fillable forms (using annotations).

### Step 1: Check if PDF is Fillable

```bash
./run tool/forms/check_fillable.py form.pdf
```

If `has_fields: true`, use the **Fillable PDF** workflow. Otherwise, use the **Non-Fillable PDF** workflow.

### Fillable PDF Workflow

1. **Extract field info:**
   ```bash
   ./run tool/forms/extract_fields.py form.pdf -o field_info.json
   ```

2. **Create values file** (`values.json`):
   ```json
   [
     {"field_id": "last_name", "value": "Smith"},
     {"field_id": "checkbox1", "value": "/On"}
   ]
   ```

3. **Fill the form:**
   ```bash
   ./run tool/forms/fill_fields.py form.pdf values.json -o filled.pdf
   ```

### Non-Fillable PDF Workflow

1. **Try structure extraction first:**
   ```bash
   ./run tool/forms/extract_structure.py form.pdf -o structure.json
   ```

2. **Convert to images for visual analysis:**
   ```bash
   ./run tool/forms/convert_to_images.py form.pdf images/ --scale 1.5
   ```

3. **Create fields.json** with entry positions (see `references/pdf-forms.md` for format).

4. **Validate bounding boxes:**
   ```bash
   ./run tool/forms/check_bounding_boxes.py fields.json
   ```

5. **Fill with annotations:**
   ```bash
   ./run tool/forms/fill_annotations.py form.pdf fields.json -o filled.pdf
   ```

For complete workflow details, see **[pdf-forms.md](references/pdf-forms.md)**.

---

## Reference Documentation

For detailed procedures and patterns:

- **[docx-style-config.md](references/docx-style-config.md)** - JSON style configuration schema for docx_builder
- **[docx-editing.md](references/docx-editing.md)** - Tracked changes, comments, unpack/pack workflow
- **[docx-xml-reference.md](references/docx-xml-reference.md)** - OOXML structure, element patterns, schema compliance
- **[pdf-operations.md](references/pdf-operations.md)** - Advanced PDF processing, Python library usage
- **[pdf-forms.md](references/pdf-forms.md)** - PDF form filling workflows for fillable and non-fillable PDFs

---

## Dependencies

All dependencies are pure Python (pip-installable, no external binaries):

- **weasyprint** - HTML to PDF rendering
- **python-docx** - DOCX creation and parsing
- **mammoth** - DOCX to HTML conversion
- **mistune** - Markdown parsing
- **lxml** - XML processing for DOCX editing
- **pypdf** - PDF manipulation
- **pdfplumber** - PDF text/table extraction
- **pypdfium2** - PDF rendering to images

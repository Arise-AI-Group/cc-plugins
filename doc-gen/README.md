# doc-gen

Comprehensive document generation, editing, and processing plugin for Claude Code.

## Features

### Document Generation
- **HTML to PDF** - High-quality PDF generation with WeasyPrint
- **Markdown to DOCX** - Word document creation with Pandoc
- **Jinja2 Templates** - Variable substitution for dynamic documents
- **Pre-built Stylesheets** - Professional styles for quotes, reports, invoices

### DOCX Editing
- **Unpack/Edit/Pack Workflow** - Edit DOCX files via XML manipulation
- **Tracked Changes** - Add insertions and deletions with author attribution
- **Comments** - Add comments and threaded replies
- **Accept Changes** - Accept all tracked changes programmatically

### PDF Processing
- **Merge** - Combine multiple PDFs
- **Split** - Extract pages to individual files
- **Extract Text** - Get text content with layout preservation
- **Extract Tables** - Export tables to JSON or CSV
- **Rotate** - Rotate pages by 90/180/270 degrees
- **Metadata** - Read PDF metadata

## Prerequisites

### System Dependencies

**Pandoc** (required for DOCX conversion):

```bash
# macOS
brew install pandoc

# Ubuntu/Debian
sudo apt install pandoc
```

**WeasyPrint dependencies** (for HTML to PDF):

```bash
# macOS
brew install pango libffi

# Ubuntu/Debian
sudo apt install libpango-1.0-0 libpangocairo-1.0-0
```

## Installation

```bash
./setup.sh
```

## Quick Reference

| Task | Command |
|------|---------|
| HTML to PDF | `./run tool/doc_gen.py pdf input.html -o output.pdf` |
| Markdown to DOCX | `./run tool/doc_gen.py docx input.md -o output.docx` |
| Extract DOCX text | `./run tool/docx_tools.py extract doc.docx` |
| Accept tracked changes | `./run tool/docx_tools.py accept-changes in.docx out.docx` |
| Unpack DOCX for editing | `./run tool/office/unpack.py doc.docx unpacked/` |
| Repack DOCX | `./run tool/office/pack.py unpacked/ output.docx` |
| Add comment | `./run tool/office/comment.py unpacked/ 0 "Comment text"` |
| Merge PDFs | `./run tool/pdf_tools.py merge f1.pdf f2.pdf -o out.pdf` |
| Split PDF | `./run tool/pdf_tools.py split doc.pdf -o pages/` |
| Extract PDF text | `./run tool/pdf_tools.py extract-text doc.pdf` |
| Extract tables | `./run tool/pdf_tools.py extract-tables doc.pdf` |

## Usage Examples

### Document Generation

```bash
# HTML to PDF with style
./run tool/doc_gen.py pdf quote.html --style quote -o quote.pdf

# Markdown to DOCX
./run tool/doc_gen.py docx document.md -o document.docx

# With template variables
./run tool/doc_gen.py pdf template.html -o output.pdf \
  --var client_name="Acme Corp" \
  --var date="January 30, 2025"
```

### DOCX Editing

```bash
# Unpack for editing
./run tool/office/unpack.py document.docx unpacked/

# Edit XML files in unpacked/word/ using the Edit tool
# Then repack
./run tool/office/pack.py unpacked/ edited.docx

# Or accept all tracked changes in one command
./run tool/docx_tools.py accept-changes input.docx clean.docx
```

### PDF Processing

```bash
# Merge multiple PDFs
./run tool/pdf_tools.py merge file1.pdf file2.pdf file3.pdf -o combined.pdf

# Split into individual pages
./run tool/pdf_tools.py split document.pdf -o pages/

# Extract specific pages
./run tool/pdf_tools.py split document.pdf -o pages/ --pages "1-3,5,7-10"

# Extract text
./run tool/pdf_tools.py extract-text document.pdf

# Extract tables to CSV
./run tool/pdf_tools.py extract-tables document.pdf --format csv -o tables/

# Rotate pages
./run tool/pdf_tools.py rotate document.pdf -o rotated.pdf --angle 90
```

## Built-in Styles

| Style | Use Case |
|-------|----------|
| `quote` | Professional quotes and proposals |
| `report` | Business reports and documentation |
| `invoice` | Invoices with pricing tables |

## Output Format

All commands output JSON:

```json
{
  "status": "success",
  "operation": "merge",
  "output": "/path/to/output.pdf"
}
```

## Documentation

See the skill documentation for detailed reference:
- `skills/doc-gen/SKILL.md` - Overview and quick reference
- `skills/doc-gen/references/docx-editing.md` - Tracked changes and comments
- `skills/doc-gen/references/docx-xml-reference.md` - OOXML structure
- `skills/doc-gen/references/pdf-operations.md` - PDF library usage

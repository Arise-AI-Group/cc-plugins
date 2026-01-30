---
name: doc-gen
description: This skill should be used when the user asks to "convert HTML to PDF", "generate PDF from HTML", "create Word doc from markdown", "convert markdown to docx", "export HTML as Word", "create styled PDF", "generate quote PDF", "make invoice PDF". Converts documents using WeasyPrint (HTML to PDF) and Pandoc (Markdown to DOCX) with Jinja2 templating and pre-built stylesheets.
---

# Document Generation

## When to Use

**Trigger phrases:**
- "Convert this HTML to PDF"
- "Generate a PDF from this template"
- "Create a Word doc from markdown"
- "Make a styled PDF quote"
- "Export this as DOCX"
- "Generate invoice PDF"

Use this skill when:
- Converting styled HTML to print-ready PDF (quotes, reports, invoices)
- Converting Markdown to Word documents
- Generating documents from templates with variable substitution
- Creating professional documents with consistent styling

## Execution Method

Always use Python: `tool/doc_gen.py`

## Quick Reference

| Task | Command |
|------|---------|
| HTML to PDF | `./run tool/doc_gen.py pdf input.html -o output.pdf` |
| HTML to PDF with style | `./run tool/doc_gen.py pdf input.html --style quote -o output.pdf` |
| Markdown to DOCX | `./run tool/doc_gen.py docx input.md -o output.docx` |
| Markdown to PDF | `./run tool/doc_gen.py pdf input.md -o output.pdf` |
| With variables | `./run tool/doc_gen.py pdf template.html -o out.pdf --var client="Acme"` |
| List styles | `./run tool/doc_gen.py styles` |

## PDF Generation (WeasyPrint)

WeasyPrint converts HTML+CSS to high-quality PDF. Best for styled documents.

### Basic HTML to PDF

```bash
./run tool/doc_gen.py pdf document.html -o document.pdf
```

### With Built-in Styles

Three pre-built stylesheets available:
- `quote` - Professional quotes/proposals with blue accents
- `report` - Clean business reports with serif fonts
- `invoice` - Invoice layout with pricing tables

```bash
./run tool/doc_gen.py pdf quote.html --style quote -o quote.pdf
./run tool/doc_gen.py pdf report.html --style report -o report.pdf
./run tool/doc_gen.py pdf invoice.html --style invoice -o invoice.pdf
```

### With Custom CSS

```bash
./run tool/doc_gen.py pdf document.html --css custom.css -o document.pdf
```

## DOCX Generation (Pandoc)

Pandoc converts Markdown or HTML to Word documents.

### Markdown to DOCX

```bash
./run tool/doc_gen.py docx document.md -o document.docx
```

### HTML to DOCX

```bash
./run tool/doc_gen.py docx document.html -o document.docx
```

## Template Variables (Jinja2)

Templates support `{{ variable }}` substitution.

### Single Variables

```bash
./run tool/doc_gen.py pdf template.html -o output.pdf \
  --var client_name="Acme Corp" \
  --var date="January 29, 2026" \
  --var total="$5,000"
```

### Variables from JSON File

Create a JSON file with variables:

```json
{
  "client_name": "Acme Corp",
  "client_email": "contact@acme.com",
  "quote_number": "Q-2026-001",
  "line_items": [
    {"description": "Phase 1", "amount": "$2,500"},
    {"description": "Phase 2", "amount": "$2,500"}
  ],
  "total": "$5,000"
}
```

Then reference it:

```bash
./run tool/doc_gen.py pdf template.html -o output.pdf --vars data.json
```

### Available Example Template

The plugin includes a quote template at `templates/quote.html` with these variables:
- `company_name`, `company_address`, `company_email`, `company_phone`
- `client_name`, `client_company`, `client_email`
- `quote_number`, `date`, `valid_until`
- `project_description`, `deliverables` (list)
- `line_items` (list of {description, amount}), `total`

## When to Use Each Tool

| Format | Tool | Best For |
|--------|------|----------|
| HTML to PDF | WeasyPrint | Styled documents, precise layout, print-ready |
| Markdown to PDF | Pandoc | Simple documents, academic papers |
| Markdown to DOCX | Pandoc | Editable documents, collaboration |
| HTML to DOCX | Pandoc | Converting web content to Word |

## System Requirements

- **WeasyPrint**: Installed via pip (may need system libs: `brew install pango` on macOS)
- **Pandoc**: Install separately (`brew install pandoc` or `apt install pandoc`)

Run `./setup.sh` to check dependencies.

## Output Format

All commands output JSON to stdout:

```json
{
  "status": "success",
  "output": "/path/to/output.pdf",
  "format": "pdf",
  "engine": "weasyprint"
}
```

Errors return:

```json
{
  "status": "error",
  "error": "Error message"
}
```

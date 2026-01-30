# doc-gen

Document generation plugin for Claude Code using WeasyPrint and Pandoc.

## Features

- **HTML to PDF** - High-quality PDF generation with WeasyPrint
- **Markdown to DOCX** - Word document creation with Pandoc
- **Markdown to PDF** - Simple PDF generation with Pandoc
- **Jinja2 Templates** - Variable substitution (`{{client_name}}`, `{{date}}`)
- **Pre-built Stylesheets** - Professional styles for quotes, reports, invoices

## Prerequisites

### System Dependencies

**Pandoc** (required for DOCX and Markdown-to-PDF):

```bash
# macOS
brew install pandoc

# Ubuntu/Debian
sudo apt install pandoc

# Windows
choco install pandoc
```

**WeasyPrint** (installed via pip, but may need system libraries):

```bash
# macOS - if you encounter issues
brew install pango libffi

# Ubuntu/Debian
sudo apt install libpango-1.0-0 libpangocairo-1.0-0
```

## Installation

```bash
# Run setup to check dependencies and install Python packages
./setup.sh
```

## Usage

### HTML to PDF

```bash
# Basic conversion
./run tool/doc_gen.py pdf document.html -o document.pdf

# With built-in style
./run tool/doc_gen.py pdf quote.html --style quote -o quote.pdf

# With custom CSS
./run tool/doc_gen.py pdf document.html --css custom.css -o document.pdf
```

### Markdown to DOCX

```bash
./run tool/doc_gen.py docx document.md -o document.docx
```

### Markdown to PDF

```bash
./run tool/doc_gen.py pdf document.md -o document.pdf
```

### With Template Variables

```bash
# Single variables
./run tool/doc_gen.py pdf template.html -o output.pdf \
  --var client_name="Acme Corp" \
  --var date="January 29, 2026"

# From JSON file
./run tool/doc_gen.py pdf template.html -o output.pdf --vars data.json
```

### List Available Styles

```bash
./run tool/doc_gen.py styles
```

## Built-in Styles

| Style | Use Case |
|-------|----------|
| `quote` | Professional quotes and proposals |
| `report` | Business reports and documentation |
| `invoice` | Invoices with pricing tables |

## Template Variables

Templates use Jinja2 syntax. Example:

```html
<h1>Quote for {{ client_name }}</h1>
<p>Date: {{ date }}</p>
<p>Total: {{ total }}</p>
```

Pass variables via CLI:

```bash
./run tool/doc_gen.py pdf template.html -o out.pdf \
  --var client_name="Acme" \
  --var date="2026-01-29" \
  --var total="$5,000"
```

Or via JSON file:

```json
{
  "client_name": "Acme Corp",
  "date": "2026-01-29",
  "total": "$5,000"
}
```

```bash
./run tool/doc_gen.py pdf template.html -o out.pdf --vars data.json
```

## Example Template

See `templates/quote.html` for a complete quote template with:
- Company and client information
- Project overview
- Line items table
- Terms and conditions

## Output Format

All commands output JSON:

```json
{
  "status": "success",
  "output": "/path/to/output.pdf",
  "format": "pdf",
  "engine": "weasyprint"
}
```

## Troubleshooting

### WeasyPrint Installation Issues

If WeasyPrint fails to install, ensure you have the required system libraries:

```bash
# macOS
brew install pango cairo libffi gdk-pixbuf

# Ubuntu/Debian
sudo apt install python3-cffi python3-brotli libpango-1.0-0 libpangocairo-1.0-0
```

### Pandoc Not Found

Install Pandoc from https://pandoc.org/installing.html or use your package manager.

### PDF Generation Fails

- Check that the input HTML is valid
- Ensure CSS doesn't have syntax errors
- For complex layouts, test in a browser first

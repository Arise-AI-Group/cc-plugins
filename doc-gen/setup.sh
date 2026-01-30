#!/bin/bash
set -e
SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
cd "$SCRIPT_DIR"

echo "Setting up doc-gen plugin..."
echo ""

# Check for system dependencies
echo "Checking system dependencies..."

# Check for Pandoc
if command -v pandoc &> /dev/null; then
    PANDOC_VERSION=$(pandoc --version | head -n1)
    echo "  [OK] $PANDOC_VERSION"
else
    echo "  [MISSING] Pandoc not found"
    echo ""
    echo "  Install Pandoc:"
    echo "    macOS:  brew install pandoc"
    echo "    Ubuntu: sudo apt install pandoc"
    echo "    Or visit: https://pandoc.org/installing.html"
    echo ""
fi

# Check for WeasyPrint (will be installed via pip, but check for system deps)
if command -v weasyprint &> /dev/null; then
    echo "  [OK] WeasyPrint CLI available"
else
    echo "  [INFO] WeasyPrint will be installed via pip"
    echo "         If you encounter issues, install system dependencies:"
    echo "         macOS:  brew install pango libffi"
    echo "         Ubuntu: sudo apt install libpango-1.0-0 libpangocairo-1.0-0"
fi

echo ""

# Set up Python venv
if [ ! -d ".venv" ]; then
    echo "Creating virtual environment..."
    python3 -m venv .venv
fi

source .venv/bin/activate
echo "Installing Python dependencies..."
pip install -q -r requirements.txt

echo ""
echo "Setup complete!"
echo ""
echo "Usage:"
echo "  # HTML to PDF"
echo "  ./run tool/doc_gen.py pdf input.html -o output.pdf"
echo ""
echo "  # Markdown to DOCX"
echo "  ./run tool/doc_gen.py docx input.md -o output.docx"
echo ""
echo "  # With template variables"
echo "  ./run tool/doc_gen.py pdf template.html -o output.pdf --var client='Acme Corp'"

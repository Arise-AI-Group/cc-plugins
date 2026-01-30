#!/usr/bin/env python3
"""Document generation CLI using WeasyPrint and Pandoc.

Converts HTML/Markdown to PDF and DOCX with Jinja2 templating support.

CLI Usage:
    # HTML to PDF (WeasyPrint)
    ./run tool/doc_gen.py pdf input.html -o output.pdf
    ./run tool/doc_gen.py pdf input.html --style quote -o output.pdf
    ./run tool/doc_gen.py pdf input.html --css custom.css -o output.pdf

    # With Jinja2 template variables
    ./run tool/doc_gen.py pdf template.html -o output.pdf --var client="Acme Corp"
    ./run tool/doc_gen.py pdf template.html -o output.pdf --vars data.json

    # Markdown to DOCX (Pandoc)
    ./run tool/doc_gen.py docx input.md -o output.docx

    # Markdown to PDF (Pandoc)
    ./run tool/doc_gen.py pdf input.md -o output.pdf --engine pandoc

Module Usage:
    from tool.doc_gen import DocGenerator

    gen = DocGenerator()
    gen.html_to_pdf("input.html", "output.pdf", style="quote")
    gen.markdown_to_docx("input.md", "output.docx")
"""

import argparse
import json
import os
import subprocess
import sys
from pathlib import Path
from typing import Any

from jinja2 import Environment, FileSystemLoader, BaseLoader


class DocGenError(Exception):
    """Base exception for document generation errors."""
    pass


class DependencyError(DocGenError):
    """Raised when a required dependency is missing."""
    pass


class TemplateError(DocGenError):
    """Raised when template processing fails."""
    pass


class ConversionError(DocGenError):
    """Raised when document conversion fails."""
    pass


def get_plugin_dir() -> Path:
    """Get the plugin directory (parent of tool/)."""
    return Path(__file__).parent.parent


def get_styles_dir() -> Path:
    """Get the styles directory."""
    return get_plugin_dir() / "styles"


def get_templates_dir() -> Path:
    """Get the templates directory."""
    return get_plugin_dir() / "templates"


class DocGenerator:
    """Document generator using WeasyPrint and Pandoc."""

    def __init__(self):
        self.styles_dir = get_styles_dir()
        self.templates_dir = get_templates_dir()

    def _check_weasyprint(self) -> None:
        """Check if WeasyPrint is available."""
        try:
            import weasyprint  # noqa: F401
        except ImportError:
            raise DependencyError(
                "WeasyPrint not installed. Run: pip install weasyprint"
            )

    def _check_pandoc(self) -> None:
        """Check if Pandoc is available."""
        try:
            result = subprocess.run(
                ["pandoc", "--version"],
                capture_output=True,
                text=True
            )
            if result.returncode != 0:
                raise DependencyError("Pandoc not working properly")
        except FileNotFoundError:
            raise DependencyError(
                "Pandoc not installed. Install with:\n"
                "  macOS:  brew install pandoc\n"
                "  Ubuntu: sudo apt install pandoc"
            )

    def _render_template(
        self,
        content: str,
        variables: dict[str, Any],
        base_path: Path | None = None
    ) -> str:
        """Render Jinja2 template with variables.

        Args:
            content: Template content string
            variables: Dictionary of template variables
            base_path: Base path for template includes (optional)

        Returns:
            Rendered template string
        """
        if not variables:
            return content

        try:
            if base_path:
                env = Environment(loader=FileSystemLoader(str(base_path)))
                template = env.from_string(content)
            else:
                env = Environment(loader=BaseLoader())
                template = env.from_string(content)

            return template.render(**variables)
        except Exception as e:
            raise TemplateError(f"Template rendering failed: {e}")

    def _get_style_css(self, style_name: str) -> str | None:
        """Get CSS content for a built-in style.

        Args:
            style_name: Name of the style (e.g., 'quote', 'report', 'invoice')

        Returns:
            CSS content string or None if style not found
        """
        style_file = self.styles_dir / f"{style_name}.css"
        if style_file.exists():
            return style_file.read_text()
        return None

    def html_to_pdf(
        self,
        input_path: str | Path,
        output_path: str | Path,
        css_path: str | Path | None = None,
        style: str | None = None,
        variables: dict[str, Any] | None = None
    ) -> Path:
        """Convert HTML to PDF using WeasyPrint.

        Args:
            input_path: Path to input HTML file
            output_path: Path for output PDF file
            css_path: Optional path to custom CSS file
            style: Optional built-in style name (quote, report, invoice)
            variables: Optional Jinja2 template variables

        Returns:
            Path to the created PDF file
        """
        self._check_weasyprint()
        from weasyprint import HTML, CSS

        input_path = Path(input_path)
        output_path = Path(output_path)

        if not input_path.exists():
            raise ConversionError(f"Input file not found: {input_path}")

        # Read and optionally render template
        content = input_path.read_text()
        if variables:
            content = self._render_template(
                content, variables, input_path.parent
            )

        # Build stylesheets list
        stylesheets = []

        # Add built-in style if specified
        if style:
            style_css = self._get_style_css(style)
            if style_css:
                stylesheets.append(CSS(string=style_css))
            else:
                print(f"Warning: Style '{style}' not found, skipping", file=sys.stderr)

        # Add custom CSS if specified
        if css_path:
            css_path = Path(css_path)
            if css_path.exists():
                stylesheets.append(CSS(filename=str(css_path)))
            else:
                raise ConversionError(f"CSS file not found: {css_path}")

        # Create PDF
        html = HTML(string=content, base_url=str(input_path.parent))
        html.write_pdf(
            str(output_path),
            stylesheets=stylesheets if stylesheets else None
        )

        return output_path

    def markdown_to_pdf(
        self,
        input_path: str | Path,
        output_path: str | Path,
        variables: dict[str, Any] | None = None
    ) -> Path:
        """Convert Markdown to PDF using Pandoc.

        Args:
            input_path: Path to input Markdown file
            output_path: Path for output PDF file
            variables: Optional Jinja2 template variables

        Returns:
            Path to the created PDF file
        """
        self._check_pandoc()

        input_path = Path(input_path)
        output_path = Path(output_path)

        if not input_path.exists():
            raise ConversionError(f"Input file not found: {input_path}")

        # Read and optionally render template
        content = input_path.read_text()
        if variables:
            content = self._render_template(
                content, variables, input_path.parent
            )

        # Write to temp file if template was rendered
        if variables:
            import tempfile
            with tempfile.NamedTemporaryFile(
                mode='w', suffix='.md', delete=False
            ) as f:
                f.write(content)
                temp_input = f.name
        else:
            temp_input = str(input_path)

        try:
            result = subprocess.run(
                [
                    "pandoc",
                    temp_input,
                    "-o", str(output_path),
                    "--pdf-engine=xelatex"
                ],
                capture_output=True,
                text=True
            )

            if result.returncode != 0:
                # Try without xelatex (fallback to pdflatex)
                result = subprocess.run(
                    ["pandoc", temp_input, "-o", str(output_path)],
                    capture_output=True,
                    text=True
                )
                if result.returncode != 0:
                    raise ConversionError(
                        f"Pandoc conversion failed: {result.stderr}"
                    )
        finally:
            if variables and temp_input != str(input_path):
                os.unlink(temp_input)

        return output_path

    def markdown_to_docx(
        self,
        input_path: str | Path,
        output_path: str | Path,
        variables: dict[str, Any] | None = None
    ) -> Path:
        """Convert Markdown to DOCX using Pandoc.

        Args:
            input_path: Path to input Markdown file
            output_path: Path for output DOCX file
            variables: Optional Jinja2 template variables

        Returns:
            Path to the created DOCX file
        """
        self._check_pandoc()

        input_path = Path(input_path)
        output_path = Path(output_path)

        if not input_path.exists():
            raise ConversionError(f"Input file not found: {input_path}")

        # Read and optionally render template
        content = input_path.read_text()
        if variables:
            content = self._render_template(
                content, variables, input_path.parent
            )

        # Write to temp file if template was rendered
        if variables:
            import tempfile
            with tempfile.NamedTemporaryFile(
                mode='w', suffix='.md', delete=False
            ) as f:
                f.write(content)
                temp_input = f.name
        else:
            temp_input = str(input_path)

        try:
            result = subprocess.run(
                ["pandoc", temp_input, "-o", str(output_path)],
                capture_output=True,
                text=True
            )

            if result.returncode != 0:
                raise ConversionError(
                    f"Pandoc conversion failed: {result.stderr}"
                )
        finally:
            if variables and temp_input != str(input_path):
                os.unlink(temp_input)

        return output_path

    def html_to_docx(
        self,
        input_path: str | Path,
        output_path: str | Path,
        variables: dict[str, Any] | None = None
    ) -> Path:
        """Convert HTML to DOCX using Pandoc.

        Args:
            input_path: Path to input HTML file
            output_path: Path for output DOCX file
            variables: Optional Jinja2 template variables

        Returns:
            Path to the created DOCX file
        """
        self._check_pandoc()

        input_path = Path(input_path)
        output_path = Path(output_path)

        if not input_path.exists():
            raise ConversionError(f"Input file not found: {input_path}")

        # Read and optionally render template
        content = input_path.read_text()
        if variables:
            content = self._render_template(
                content, variables, input_path.parent
            )

        # Write to temp file if template was rendered
        if variables:
            import tempfile
            with tempfile.NamedTemporaryFile(
                mode='w', suffix='.html', delete=False
            ) as f:
                f.write(content)
                temp_input = f.name
        else:
            temp_input = str(input_path)

        try:
            result = subprocess.run(
                ["pandoc", temp_input, "-o", str(output_path)],
                capture_output=True,
                text=True
            )

            if result.returncode != 0:
                raise ConversionError(
                    f"Pandoc conversion failed: {result.stderr}"
                )
        finally:
            if variables and temp_input != str(input_path):
                os.unlink(temp_input)

        return output_path

    def list_styles(self) -> list[str]:
        """List available built-in styles.

        Returns:
            List of style names
        """
        if not self.styles_dir.exists():
            return []
        return [f.stem for f in self.styles_dir.glob("*.css")]


def parse_var(var_str: str) -> tuple[str, str]:
    """Parse a variable string like 'key=value'.

    Args:
        var_str: String in format 'key=value'

    Returns:
        Tuple of (key, value)
    """
    if '=' not in var_str:
        raise ValueError(f"Invalid variable format: {var_str} (expected key=value)")
    key, value = var_str.split('=', 1)
    return key.strip(), value.strip()


def build_parser() -> argparse.ArgumentParser:
    """Build the argument parser."""
    parser = argparse.ArgumentParser(
        prog="doc_gen",
        description="Document generation using WeasyPrint and Pandoc",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  # HTML to PDF with WeasyPrint
  ./run tool/doc_gen.py pdf input.html -o output.pdf
  ./run tool/doc_gen.py pdf input.html --style quote -o output.pdf

  # With template variables
  ./run tool/doc_gen.py pdf template.html -o out.pdf --var client="Acme"
  ./run tool/doc_gen.py pdf template.html -o out.pdf --vars data.json

  # Markdown to DOCX with Pandoc
  ./run tool/doc_gen.py docx input.md -o output.docx

  # Markdown to PDF with Pandoc
  ./run tool/doc_gen.py pdf input.md -o output.pdf --engine pandoc

  # List available styles
  ./run tool/doc_gen.py styles
"""
    )

    subparsers = parser.add_subparsers(dest="command", help="Available commands")

    # PDF command
    pdf_parser = subparsers.add_parser("pdf", help="Generate PDF from HTML or Markdown")
    pdf_parser.add_argument("input", help="Input file (HTML or Markdown)")
    pdf_parser.add_argument("-o", "--output", required=True, help="Output PDF file")
    pdf_parser.add_argument("--style", help="Built-in style (quote, report, invoice)")
    pdf_parser.add_argument("--css", help="Custom CSS file path")
    pdf_parser.add_argument(
        "--engine",
        choices=["weasyprint", "pandoc"],
        default="weasyprint",
        help="PDF engine (default: weasyprint for HTML, pandoc for Markdown)"
    )
    pdf_parser.add_argument(
        "--var",
        action="append",
        dest="vars",
        help="Template variable (key=value), can be repeated"
    )
    pdf_parser.add_argument(
        "--vars",
        dest="vars_file",
        help="JSON file with template variables"
    )

    # DOCX command
    docx_parser = subparsers.add_parser("docx", help="Generate DOCX from HTML or Markdown")
    docx_parser.add_argument("input", help="Input file (HTML or Markdown)")
    docx_parser.add_argument("-o", "--output", required=True, help="Output DOCX file")
    docx_parser.add_argument(
        "--var",
        action="append",
        dest="vars",
        help="Template variable (key=value), can be repeated"
    )
    docx_parser.add_argument(
        "--vars",
        dest="vars_file",
        help="JSON file with template variables"
    )

    # Styles command
    subparsers.add_parser("styles", help="List available built-in styles")

    return parser


def collect_variables(args) -> dict[str, Any]:
    """Collect template variables from CLI args and JSON file.

    Args:
        args: Parsed arguments with vars and vars_file attributes

    Returns:
        Dictionary of template variables
    """
    variables = {}

    # Load from JSON file first
    if hasattr(args, 'vars_file') and args.vars_file:
        vars_path = Path(args.vars_file)
        if not vars_path.exists():
            raise ValueError(f"Variables file not found: {vars_path}")
        with open(vars_path) as f:
            variables.update(json.load(f))

    # Override with CLI variables
    if hasattr(args, 'vars') and args.vars:
        for var_str in args.vars:
            key, value = parse_var(var_str)
            variables[key] = value

    return variables


def main():
    """Main CLI entry point."""
    parser = build_parser()
    args = parser.parse_args()

    if not args.command:
        parser.print_help()
        sys.exit(1)

    gen = DocGenerator()

    try:
        if args.command == "styles":
            styles = gen.list_styles()
            if styles:
                print("Available styles:")
                for style in styles:
                    print(f"  - {style}")
            else:
                print("No built-in styles found")
            return

        # Collect template variables
        variables = collect_variables(args)

        input_path = Path(args.input)
        output_path = Path(args.output)

        # Determine file type
        input_ext = input_path.suffix.lower()
        is_html = input_ext in ['.html', '.htm']
        is_markdown = input_ext in ['.md', '.markdown']

        if args.command == "pdf":
            # Determine engine based on input type if not specified
            engine = args.engine
            if is_markdown and engine == "weasyprint":
                engine = "pandoc"  # Default to pandoc for markdown

            if engine == "weasyprint":
                result = gen.html_to_pdf(
                    input_path,
                    output_path,
                    css_path=args.css,
                    style=args.style,
                    variables=variables
                )
            else:
                result = gen.markdown_to_pdf(
                    input_path,
                    output_path,
                    variables=variables
                )

            print(json.dumps({
                "status": "success",
                "output": str(result),
                "format": "pdf",
                "engine": engine
            }, indent=2))

        elif args.command == "docx":
            if is_html:
                result = gen.html_to_docx(
                    input_path,
                    output_path,
                    variables=variables
                )
            else:
                result = gen.markdown_to_docx(
                    input_path,
                    output_path,
                    variables=variables
                )

            print(json.dumps({
                "status": "success",
                "output": str(result),
                "format": "docx"
            }, indent=2))

    except (DocGenError, ValueError) as e:
        print(json.dumps({
            "status": "error",
            "error": str(e)
        }, indent=2), file=sys.stderr)
        sys.exit(1)


if __name__ == "__main__":
    main()

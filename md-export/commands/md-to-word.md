# Markdown to Word
> Convert a Markdown file to a Word document (.docx).

## Variables
markdown_path: $1
output_path: $2

## Instructions
- Convert the markdown file to a Word document
- Mermaid diagrams are rendered as embedded PNG images
- Callout boxes get dotted borders with background shading
- If no output path specified, outputs to same directory as input

## Run
```bash
# Default output (same directory)
./run tools/md_to_docx.py "$markdown_path"

# Custom output path
./run tools/md_to_docx.py "$markdown_path" --output "$output_path"
```

## Report
- Confirm the document was created
- Report the output file path
- Note any diagrams that were rendered

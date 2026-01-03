# Markdown to Google Doc
> Convert a Markdown file to a Google Doc.

## Variables
markdown_path: $1
folder_id: $2

## Instructions
- Convert the markdown file to a Google Doc
- If folder_id provided, create in that Drive folder
- ASCII templates are converted to bullet lists
- Flowcharts are preserved as code blocks

## Run
```bash
# Default (root of Drive)
./run tools/md_to_gdoc.py "$markdown_path"

# With target folder
./run tools/md_to_gdoc.py "$markdown_path" --folder-id "$folder_id"

# Directory mode (recursive)
./run tools/md_to_gdoc.py "path/to/directory/"
```

## Report
- Confirm the document was created
- Report the Google Doc URL
- Note the document title

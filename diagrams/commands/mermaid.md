# Mermaid

Generate Mermaid diagram code from JSON input.

## Variables

- `input_file`: $1
- `output_file`: $2

## Instructions

- Input must be a valid JSON file with diagram schema
- Output defaults to `diagrams/{input_name}.md`
- Use `--raw` flag for raw Mermaid syntax without markdown fencing

## Run

```bash
./run tool/generate_mermaid.py "$input_file" --output "${output_file:-diagrams/output.md}"
```

## Report

- Show the generated Mermaid code
- Confirm file was saved

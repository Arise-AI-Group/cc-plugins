# Draw.io

Generate a Draw.io diagram from JSON input.

## Variables

- `input_file`: $1
- `output_file`: $2

## Instructions

- Input must be a valid JSON file with diagram schema
- Output defaults to `diagrams/{input_name}.drawio`

## Run

```bash
./run tool/generate_drawio.py "$input_file" --output "${output_file:-diagrams/output.drawio}"
```

## Report

- Confirm file was created
- Report canvas size and element count

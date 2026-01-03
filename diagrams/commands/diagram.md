# Diagram

Generate a diagram from description or JSON input.

## Variables

- `input`: $ARGUMENTS

## Instructions

1. If input is a file path ending in `.json`, use as structured input
2. If input is natural language, convert to structured JSON format first
3. Default format is Draw.io (`.drawio`)
4. Refer to `runbook/generate_diagram.md` for detailed guidance

## Process

### For JSON Input
```bash
./run tool/generate_drawio.py "$input" --output "diagrams/output.drawio"
```

### For Natural Language
1. Parse the description to identify nodes, connections, and groups
2. Generate JSON matching the schema in the runbook
3. Pass to the appropriate tool

## Report

- Confirm diagram was generated
- Report the output file path
- Describe the diagram structure (nodes, connections, groups)

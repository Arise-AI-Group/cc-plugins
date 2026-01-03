# Extract SOP
> Extract a structured SOP from a transcript.

## Variables
transcript_path: $1
topic: $2

## Instructions
- If no topic provided, first list available topics with `--list-topics`
- Extract the SOP for the specified topic
- Output is saved as `{filename}_sop.md` in the same directory

## Run
```bash
# If topic is empty, list topics first
./run tools/extract_sop.py "$transcript_path" --list-topics

# With topic specified
./run tools/extract_sop.py "$transcript_path" --topic "$topic"
```

## Report
- Confirm the SOP was extracted
- Report the output file path
- Summarize the SOP structure (sections, completeness)

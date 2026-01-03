#!/usr/bin/env python3
"""
Migrate ASCII flowcharts in Markdown files to Mermaid diagrams.

Uses GPT-4 to convert ASCII art flowcharts to equivalent Mermaid syntax.

Usage:
    # Preview changes (dry run)
    ./run tool/migrate_ascii_to_mermaid.py path/to/sops/ --dry-run

    # Apply changes (creates backups)
    ./run tool/migrate_ascii_to_mermaid.py path/to/sops/ --apply

    # Single file
    ./run tool/migrate_ascii_to_mermaid.py path/to/file.md --apply

Requirements:
    - OPENAI_API_KEY in .env
"""

import sys
import os
import re
import json
import argparse
import shutil
from pathlib import Path
from datetime import datetime
from typing import List, Dict, Any, Optional, Tuple

from openai import OpenAI

from .config import get_api_key

# Ensure OPENAI_API_KEY is available in environment for OpenAI client
if not os.getenv('OPENAI_API_KEY'):
    _key = get_api_key("OPENAI_API_KEY")
    if _key:
        os.environ['OPENAI_API_KEY'] = _key

# ASCII flowchart detection patterns
FLOW_CHARS = r'[▼▲→←↓↑]'
BRANCH_PATTERN = r'[/\\]\s+[/\\]'
BOX_CHARS = r'[┌┐└┘│═─╔╗╚╝║├┤┬┴┼┃┏┓┗┛]'


def is_ascii_flowchart(content: str) -> bool:
    """Check if content is an ASCII flowchart (not just a box template)."""
    has_flow = bool(re.search(FLOW_CHARS, content) or re.search(BRANCH_PATTERN, content))
    return has_flow


def find_ascii_flowcharts(md_content: str) -> List[Tuple[int, int, str]]:
    """Find all ASCII flowcharts in markdown content.

    Returns list of (start_pos, end_pos, content) tuples.
    """
    flowcharts = []

    # Find all code blocks
    pattern = r'```\s*\n(.*?)```'
    for match in re.finditer(pattern, md_content, re.DOTALL):
        content = match.group(1)
        if is_ascii_flowchart(content):
            flowcharts.append((match.start(), match.end(), content.strip()))

    return flowcharts


def convert_to_mermaid(ascii_content: str, client: OpenAI) -> Optional[str]:
    """Convert ASCII flowchart to Mermaid using GPT-4."""
    prompt = f"""Convert this ASCII flowchart to Mermaid syntax.

ASCII Flowchart:
```
{ascii_content}
```

Requirements:
1. Use `graph TD` for top-down flowcharts
2. Use `graph LR` for left-right flowcharts
3. Preserve all decision points, actions, and flow
4. Use appropriate shapes:
   - [Text] for rectangles (actions)
   - {{Text}} for diamonds (decisions)
   - ([Text]) for rounded rectangles (start/end)
5. Use -->|label| for labeled arrows
6. Keep text concise but meaningful

Return ONLY the Mermaid code, no explanation or markdown fencing."""

    try:
        response = client.chat.completions.create(
            model="gpt-4o",
            messages=[
                {"role": "system", "content": "You are a technical documentation expert. Convert ASCII diagrams to Mermaid syntax accurately."},
                {"role": "user", "content": prompt}
            ],
            temperature=0.2,
            max_tokens=1000
        )

        mermaid_code = response.choices[0].message.content.strip()

        # Remove any markdown fencing if present
        mermaid_code = re.sub(r'^```mermaid\s*\n?', '', mermaid_code)
        mermaid_code = re.sub(r'\n?```$', '', mermaid_code)

        return mermaid_code

    except Exception as e:
        print(f"  Error converting: {e}", file=sys.stderr)
        return None


def process_file(
    file_path: Path,
    client: OpenAI,
    dry_run: bool = True,
    backup_dir: Optional[Path] = None
) -> Dict[str, Any]:
    """Process a single markdown file.

    Returns dict with results.
    """
    print(f"\nProcessing: {file_path}", file=sys.stderr)

    with open(file_path, 'r', encoding='utf-8') as f:
        content = f.read()

    flowcharts = find_ascii_flowcharts(content)

    if not flowcharts:
        print("  No ASCII flowcharts found", file=sys.stderr)
        return {
            'file': str(file_path),
            'flowcharts_found': 0,
            'converted': 0,
            'status': 'skipped'
        }

    print(f"  Found {len(flowcharts)} ASCII flowchart(s)", file=sys.stderr)

    conversions = []
    new_content = content
    offset = 0  # Track position changes as we replace

    for start, end, ascii_content in flowcharts:
        print(f"  Converting flowchart at position {start}...", file=sys.stderr)

        if dry_run:
            # In dry run, just show what would be converted
            print("    [DRY RUN] Would convert:", file=sys.stderr)
            preview = ascii_content[:100].replace('\n', '\\n')
            print(f"    {preview}...", file=sys.stderr)
            conversions.append({
                'position': start,
                'original_preview': preview,
                'status': 'would_convert'
            })
        else:
            # Actually convert
            mermaid = convert_to_mermaid(ascii_content, client)

            if mermaid:
                # Replace the code block
                old_block = f"```\n{ascii_content}\n```"
                new_block = f"```mermaid\n{mermaid}\n```"

                # Adjust positions for previous replacements
                adj_start = start + offset
                adj_end = end + offset

                new_content = new_content[:adj_start] + new_block + new_content[adj_end:]
                offset += len(new_block) - (end - start)

                print(f"    Converted to Mermaid ({len(mermaid)} chars)", file=sys.stderr)
                conversions.append({
                    'position': start,
                    'mermaid_preview': mermaid[:100],
                    'status': 'converted'
                })
            else:
                print("    Failed to convert", file=sys.stderr)
                conversions.append({
                    'position': start,
                    'status': 'failed'
                })

    # Apply changes if not dry run
    if not dry_run and any(c['status'] == 'converted' for c in conversions):
        # Create backup
        if backup_dir:
            backup_path = backup_dir / f"{file_path.stem}_{datetime.now().strftime('%Y%m%d_%H%M%S')}.md"
            shutil.copy(file_path, backup_path)
            print(f"  Backup created: {backup_path}", file=sys.stderr)

        # Write updated content
        with open(file_path, 'w', encoding='utf-8') as f:
            f.write(new_content)
        print(f"  File updated: {file_path}", file=sys.stderr)

    converted_count = sum(1 for c in conversions if c['status'] == 'converted')

    return {
        'file': str(file_path),
        'flowcharts_found': len(flowcharts),
        'converted': converted_count,
        'conversions': conversions,
        'status': 'dry_run' if dry_run else 'applied'
    }


def process_directory(
    dir_path: Path,
    client: OpenAI,
    dry_run: bool = True
) -> List[Dict[str, Any]]:
    """Process all markdown files in a directory."""
    results = []

    # Create backup directory
    backup_dir = None
    if not dry_run:
        backup_dir = dir_path / '.backups'
        backup_dir.mkdir(exist_ok=True)

    md_files = sorted(dir_path.rglob('*.md'))

    if not md_files:
        print(f"No markdown files found in {dir_path}", file=sys.stderr)
        return results

    print(f"Found {len(md_files)} markdown file(s)", file=sys.stderr)

    for md_path in md_files:
        # Skip backup files
        if '.backups' in str(md_path):
            continue

        try:
            result = process_file(md_path, client, dry_run, backup_dir)
            results.append(result)
        except Exception as e:
            print(f"  Error: {e}", file=sys.stderr)
            results.append({
                'file': str(md_path),
                'error': str(e)
            })

    return results


def main():
    parser = argparse.ArgumentParser(
        description='Migrate ASCII flowcharts to Mermaid diagrams'
    )
    parser.add_argument(
        'path',
        help='Path to Markdown file or directory'
    )
    parser.add_argument(
        '--dry-run', '-n',
        action='store_true',
        default=True,
        help='Preview changes without applying (default)'
    )
    parser.add_argument(
        '--apply',
        action='store_true',
        help='Apply changes (creates backups)'
    )

    args = parser.parse_args()

    # Check for API key
    if not os.getenv('OPENAI_API_KEY'):
        print("Error: OPENAI_API_KEY not found in environment", file=sys.stderr)
        sys.exit(1)

    client = OpenAI()

    path = Path(args.path)
    dry_run = not args.apply

    if not path.exists():
        print(f"Error: Path not found: {path}", file=sys.stderr)
        sys.exit(1)

    if dry_run:
        print("=== DRY RUN MODE (use --apply to make changes) ===", file=sys.stderr)
    else:
        print("=== APPLY MODE (creating backups) ===", file=sys.stderr)

    if path.is_file():
        if path.suffix != '.md':
            print(f"Error: Not a markdown file: {path}", file=sys.stderr)
            sys.exit(1)

        backup_dir = path.parent / '.backups'
        if not dry_run:
            backup_dir.mkdir(exist_ok=True)

        result = process_file(path, client, dry_run, backup_dir if not dry_run else None)
        print(json.dumps(result, indent=2))
    else:
        results = process_directory(path, client, dry_run)

        # Summary
        total_found = sum(r.get('flowcharts_found', 0) for r in results)
        total_converted = sum(r.get('converted', 0) for r in results)

        print(f"\n=== Summary ===", file=sys.stderr)
        print(f"Files processed: {len(results)}", file=sys.stderr)
        print(f"Flowcharts found: {total_found}", file=sys.stderr)
        print(f"Flowcharts converted: {total_converted}", file=sys.stderr)

        print(json.dumps(results, indent=2))


if __name__ == '__main__':
    main()

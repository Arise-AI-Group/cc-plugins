#!/usr/bin/env python3
"""
Convert Markdown files to formatted Google Docs.

Uses Google Drive API's native markdown conversion for proper formatting
of tables, headers, lists, and code blocks.

Features:
- Native markdown to Google Docs conversion via Drive API
- Emoji conversion for checkmarks (✓ → ✅, ☐ → ⬜)
- Mirrors folder structure in Google Drive
- Handles duplicate names with revision suffixes

Usage:
    # Single file
    ./run tool/md_to_gdoc.py path/to/file.md

    # Directory (recursive)
    ./run tool/md_to_gdoc.py path/to/directory/

    # With options
    ./run tool/md_to_gdoc.py path/to/file.md --folder-id 1ABC123xyz
    ./run tool/md_to_gdoc.py path/to/file.md --dry-run
"""

import sys
import os
import re
import json
import argparse
from pathlib import Path

# Google API imports
from google.auth.transport.requests import Request
from google.oauth2.credentials import Credentials
from google_auth_oauthlib.flow import InstalledAppFlow
from googleapiclient.discovery import build
from googleapiclient.http import MediaInMemoryUpload

from .config import get_api_key

# Google API scopes
SCOPES = [
    "https://www.googleapis.com/auth/drive.file"
]


def convert_ascii_boxes(content: str) -> str:
    """Convert ASCII box templates to clean sections, but preserve flowcharts.

    Detects code blocks containing box-drawing characters and:
    - TEMPLATES (rules boxes, quick ref cards): Convert to bullet lists
    - FLOWCHARTS (contain arrows/branching): Preserve as code blocks

    Handles:
    - ✓ items → bullet list with ✅ emoji
    - • items → standard bullet list
    - Lines ending in : → bold sub-headers (if short)
    - ALL CAPS statements → bold taglines
    - Other lines → bullet points (prevents paragraph collapse)
    """
    # Box-drawing characters to detect
    box_chars = r'[┌┐└┘│═─╔╗╚╝║├┤┬┴┼┃┏┓┗┛]'

    # Flowchart indicators - arrows and branching
    flow_chars = r'[▼▲→←↓↑]'
    branch_pattern = r'[/\\]\s+[/\\]'  # Branching like /   \

    # Pattern: code block containing box-drawing characters
    code_block_pattern = r'```\n(.*?)```'

    def process_block(match):
        block_content = match.group(1)

        # Not an ASCII box - return unchanged
        if not re.search(box_chars, block_content):
            return match.group(0)

        # FLOWCHART: Has arrows or branching - preserve as code block
        if re.search(flow_chars, block_content) or re.search(branch_pattern, block_content):
            return match.group(0)

        # TEMPLATE: Convert to clean section
        lines = block_content.split('\n')
        output_lines = []
        title = None

        for line in lines:
            # Remove box-drawing characters
            clean = re.sub(box_chars, '', line).strip()

            # Skip empty lines from box borders
            if not clean:
                continue

            # First non-empty line is the title
            if title is None:
                title = clean
                continue

            # Detect item types and format appropriately
            if clean.startswith('✓') or clean.startswith('✔'):
                # Checkmark item → bullet with emoji
                item_text = clean.lstrip('✓✔ ').strip()
                output_lines.append(f'- ✅ {item_text}')
            elif clean.startswith('•'):
                # Bullet item → standard bullet
                item_text = clean.lstrip('• ').strip()
                output_lines.append(f'- {item_text}')
            elif clean.endswith(':') and len(clean) < 40:
                # Sub-header (e.g., "PHONE CALLS ONLY FOR:")
                output_lines.append(f'\n**{clean}**')
            elif clean.isupper() and len(clean) > 10 and ':' not in clean:
                # All-caps statement (tagline) → bold
                output_lines.append(f'\n**{clean}**')
            else:
                # DEFAULT: bullet point (prevents paragraph collapse in Google Docs)
                output_lines.append(f'- {clean}')

        # Build result with page break
        if title:
            result = f'\n\n---\n\n## 📋 {title}\n\n'
            result += '\n'.join(output_lines) + '\n'
            return result
        elif output_lines:
            return '\n\n---\n\n' + '\n'.join(output_lines) + '\n'
        else:
            return ''

    return re.sub(code_block_pattern, process_block, content, flags=re.DOTALL)


def add_section_breaks(content: str) -> str:
    """Add horizontal rules before ## headings for cleaner page breaks.

    Google Docs can awkwardly split sections, leaving headers orphaned at the
    bottom of a page. Adding --- before major sections encourages natural breaks.
    """
    lines = content.split('\n')
    result = []

    for i, line in enumerate(lines):
        # Check if this is a ## heading
        if line.startswith('## '):
            # Look back to see if previous non-empty line is ---
            has_break = False
            for j in range(i - 1, -1, -1):
                if lines[j].strip():
                    if lines[j].strip() == '---':
                        has_break = True
                    break

            if not has_break:
                result.append('---')
                result.append('')

        result.append(line)

    return '\n'.join(result)


def preprocess_markdown(content: str) -> str:
    """Pre-process markdown before Drive API conversion.

    Applies:
    - ASCII box conversion (templates, quick reference cards → printable sections)
    - Section breaks before ## headings for cleaner page breaks
    - Emoji conversions for checkmarks and other symbols
    """
    # Convert ASCII boxes first (before other transformations)
    content = convert_ascii_boxes(content)

    # Add section breaks for cleaner page breaks
    content = add_section_breaks(content)

    # Markdown checkbox syntax → emojis
    content = re.sub(r'- \[x\]', '- ✅', content)
    content = re.sub(r'- \[X\]', '- ✅', content)
    content = re.sub(r'- \[ \]', '- ⬜', content)

    # Unicode checkmark characters → emojis
    content = content.replace('✓', '✅')
    content = content.replace('✔', '✅')
    content = content.replace('☑', '✅')
    content = content.replace('☒', '✅')
    content = content.replace('☐', '⬜')
    content = content.replace('✗', '❌')

    # Common emoji-like patterns
    content = content.replace(':white_check_mark:', '✅')
    content = content.replace(':x:', '❌')

    return content


def extract_title(content: str, file_path: Path) -> str:
    """Extract document title from markdown content."""
    # Look for # heading at start
    lines = content.split('\n')
    for line in lines:
        line = line.strip()
        if line.startswith('# '):
            return line[2:].strip()
        elif line and not line.startswith('**'):
            # Skip metadata lines, stop at first non-metadata content
            break

    # Fallback to filename
    return file_path.stem.replace('-', ' ').replace('_', ' ').title()


class DriveManager:
    """Manage Google Drive folders and files."""

    def __init__(self, drive_service):
        self.drive_service = drive_service
        self._folder_cache = {}

    def convert_markdown_to_doc(self, content: str, title: str, folder_id: str = None) -> dict:
        """Convert markdown to Google Doc using Drive API native conversion.

        Args:
            content: Markdown content (will be preprocessed)
            title: Document title
            folder_id: Optional parent folder ID

        Returns:
            dict with 'id' and 'webViewLink'
        """
        # Pre-process for emojis
        content = preprocess_markdown(content)

        # Create media upload with markdown mime type
        media = MediaInMemoryUpload(
            content.encode('utf-8'),
            mimetype='text/markdown',
            resumable=True
        )

        # File metadata - target is Google Docs
        file_metadata = {
            'name': title,
            'mimeType': 'application/vnd.google-apps.document'
        }

        if folder_id and folder_id != 'root':
            file_metadata['parents'] = [folder_id]

        # Upload and convert
        file = self.drive_service.files().create(
            body=file_metadata,
            media_body=media,
            fields='id, webViewLink'
        ).execute()

        return file

    def ensure_folder_structure(self, local_path: Path, base_folder_id: str = None) -> str:
        """Create folder structure mirroring local path. Returns target folder ID."""
        if base_folder_id is None:
            base_folder_id = 'root'

        # Get path parts relative to project (e.g., plotter-mechanics/sops/new)
        parts = local_path.parent.parts

        # Find index of a known root folder or use full path
        try:
            # Look for common root folders
            for root in ['plotter-mechanix', 'execution', 'directives']:
                if root in parts:
                    idx = parts.index(root)
                    parts = parts[idx:]
                    break
        except ValueError:
            pass

        current_folder_id = base_folder_id

        for part in parts:
            # Transform folder name
            display_name = self._transform_folder_name(part)
            cache_key = f"{current_folder_id}/{display_name}"

            if cache_key in self._folder_cache:
                current_folder_id = self._folder_cache[cache_key]
            else:
                folder_id = self._find_or_create_folder(display_name, current_folder_id)
                self._folder_cache[cache_key] = folder_id
                current_folder_id = folder_id

        return current_folder_id

    def _transform_folder_name(self, slug: str) -> str:
        """Transform slug to display name."""
        # Special cases
        special = {
            'sops': 'SOPs',
            'api': 'API',
        }
        if slug.lower() in special:
            return special[slug.lower()]

        # General transformation: kebab-case to Title Case
        return slug.replace('-', ' ').replace('_', ' ').title()

    def _find_or_create_folder(self, name: str, parent_id: str) -> str:
        """Find existing folder or create new one."""
        # Search for existing folder
        query = f"name = '{name}' and '{parent_id}' in parents and mimeType = 'application/vnd.google-apps.folder' and trashed = false"

        results = self.drive_service.files().list(
            q=query,
            spaces='drive',
            fields='files(id, name)'
        ).execute()

        files = results.get('files', [])
        if files:
            return files[0]['id']

        # Create new folder
        file_metadata = {
            'name': name,
            'mimeType': 'application/vnd.google-apps.folder',
            'parents': [parent_id]
        }

        folder = self.drive_service.files().create(
            body=file_metadata,
            fields='id'
        ).execute()

        return folder.get('id')

    def get_unique_name(self, title: str, folder_id: str) -> str:
        """Get unique document name, adding revision suffix if needed."""
        # Search for existing documents with this name
        escaped_title = title.replace("'", "\\'")
        query = f"name contains '{escaped_title}' and '{folder_id}' in parents and mimeType = 'application/vnd.google-apps.document' and trashed = false"

        results = self.drive_service.files().list(
            q=query,
            spaces='drive',
            fields='files(name)'
        ).execute()

        existing_names = {f['name'] for f in results.get('files', [])}

        if title not in existing_names:
            return title

        # Find highest revision
        max_rev = 1
        pattern = re.compile(rf'^{re.escape(title)}_r(\d+)$')

        for name in existing_names:
            match = pattern.match(name)
            if match:
                rev = int(match.group(1))
                max_rev = max(max_rev, rev)

        return f"{title}_r{max_rev + 1}"


def get_google_credentials():
    """Get Google API credentials (follows existing pattern)."""
    creds = None

    if os.path.exists("token.json"):
        try:
            creds = Credentials.from_authorized_user_file("token.json", SCOPES)
        except Exception:
            creds = None

    if not creds or not creds.valid:
        if creds and creds.expired and creds.refresh_token:
            try:
                creds.refresh(Request())
            except Exception:
                creds = None

        if not creds:
            if not os.path.exists("credentials.json"):
                print("Error: credentials.json not found.", file=sys.stderr)
                print("Please set up Google OAuth credentials first.", file=sys.stderr)
                sys.exit(1)

            print("Initiating Google OAuth flow...", file=sys.stderr)
            flow = InstalledAppFlow.from_client_secrets_file("credentials.json", SCOPES)
            creds = flow.run_local_server(port=8080)

        with open("token.json", "w") as token:
            token.write(creds.to_json())

    return creds


def process_file(file_path: Path, folder_id: str = None, dry_run: bool = False,
                 no_folders: bool = False) -> dict:
    """Process a single markdown file."""
    print(f"Processing: {file_path}", file=sys.stderr)

    # Read markdown content
    with open(file_path, "r", encoding="utf-8") as f:
        content = f.read()

    # Extract title
    title = extract_title(content, file_path)
    print(f"  Title: {title}", file=sys.stderr)

    if dry_run:
        print(f"  [DRY RUN] Would create: {title}", file=sys.stderr)
        return {
            "title": title,
            "file": str(file_path),
            "dry_run": True
        }

    # Get credentials and build service
    creds = get_google_credentials()
    drive_service = build('drive', 'v3', credentials=creds)

    drive_manager = DriveManager(drive_service)

    # Determine target folder
    target_folder_id = folder_id or 'root'

    if not no_folders and folder_id is None:
        # Create folder structure mirroring local path
        target_folder_id = drive_manager.ensure_folder_structure(file_path)

    # Get unique document name
    doc_title = drive_manager.get_unique_name(title, target_folder_id)

    # Convert markdown to Google Doc
    result = drive_manager.convert_markdown_to_doc(content, doc_title, target_folder_id)

    doc_url = result.get('webViewLink', f"https://docs.google.com/document/d/{result['id']}/edit")
    print(f"  Created: {doc_title}", file=sys.stderr)
    print(f"  URL: {doc_url}", file=sys.stderr)

    return {
        "doc_id": result['id'],
        "url": doc_url,
        "title": doc_title
    }


def process_directory(dir_path: Path, folder_id: str = None, dry_run: bool = False,
                      no_folders: bool = False) -> list:
    """Process all markdown files in a directory."""
    results = []

    # Find all .md files
    md_files = sorted(dir_path.rglob("*.md"))

    if not md_files:
        print(f"No markdown files found in {dir_path}", file=sys.stderr)
        return results

    print(f"Found {len(md_files)} markdown file(s)", file=sys.stderr)

    for file_path in md_files:
        try:
            result = process_file(file_path, folder_id, dry_run, no_folders)
            results.append(result)
        except Exception as e:
            print(f"  Error: {e}", file=sys.stderr)
            results.append({
                "file": str(file_path),
                "error": str(e)
            })

    return results


def main():
    parser = argparse.ArgumentParser(
        description="Convert Markdown files to formatted Google Docs"
    )
    parser.add_argument(
        "path",
        help="Path to Markdown file or directory"
    )
    parser.add_argument(
        "--folder-id", "-f",
        help="Google Drive folder ID for output (default: create folder structure)"
    )
    parser.add_argument(
        "--dry-run", "-n",
        action="store_true",
        help="Parse and show what would be created without creating"
    )
    parser.add_argument(
        "--no-folders",
        action="store_true",
        help="Don't create folder structure, put all docs in target folder"
    )

    args = parser.parse_args()

    path = Path(args.path)

    if not path.exists():
        print(f"Error: Path not found: {path}", file=sys.stderr)
        sys.exit(1)

    if path.is_file():
        if not path.suffix == '.md':
            print(f"Error: Not a markdown file: {path}", file=sys.stderr)
            sys.exit(1)
        result = process_file(path, args.folder_id, args.dry_run, args.no_folders)
        print(json.dumps(result, indent=2))
    else:
        results = process_directory(path, args.folder_id, args.dry_run, args.no_folders)
        print(json.dumps(results, indent=2))


if __name__ == "__main__":
    main()

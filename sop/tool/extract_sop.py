#!/usr/bin/env python3
"""
Extract structured SOPs from transcripts using GPT-4.

Features:
- Topic detection: Identify potential SOP topics in a transcript
- Selective extraction: Extract a specific topic as a structured SOP
- Dual output: Markdown file (internal) + Google Doc (client-facing)

Usage:
    # List topics found in transcript
    ./run tool/extract_sop.py "path/to/transcript.txt" --list-topics

    # Extract specific SOP
    ./run tool/extract_sop.py "path/to/transcript.txt" --topic "laminator setup"

    # Extract with custom title
    ./run tool/extract_sop.py "path/to/transcript.txt" --topic "laminator setup" --title "Laminator Setup Guide"

    # Skip Google Doc creation (Markdown only)
    ./run tool/extract_sop.py "path/to/transcript.txt" --topic "laminator setup" --no-gdoc
"""

import sys
import os
import argparse
import json
from datetime import datetime
from pathlib import Path
from openai import OpenAI

# Google Docs imports
from google.auth.transport.requests import Request
from google.oauth2.credentials import Credentials
from google_auth_oauthlib.flow import InstalledAppFlow
from googleapiclient.discovery import build
from googleapiclient.errors import HttpError

from .config import get_api_key

# Google API scopes
SCOPES = [
    "https://www.googleapis.com/auth/documents",
    "https://www.googleapis.com/auth/drive.file"
]


def get_google_credentials():
    """Get Google API credentials (follows existing pattern from copy_slides_template.py)."""
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
                print("Warning: credentials.json not found. Google Doc creation will be skipped.", file=sys.stderr)
                return None

            print("Initiating Google OAuth flow...", file=sys.stderr)
            flow = InstalledAppFlow.from_client_secrets_file("credentials.json", SCOPES)
            creds = flow.run_local_server(port=8080)

        with open("token.json", "w") as token:
            token.write(creds.to_json())

    return creds


def list_topics(client: OpenAI, transcript: str) -> list[dict]:
    """
    Analyze transcript and identify potential SOP topics.

    Returns:
        List of topic dictionaries with 'topic', 'description', and 'confidence'
    """
    prompt = """Analyze this transcript and identify distinct procedures, processes, or tasks that could be turned into Standard Operating Procedures (SOPs).

For each potential SOP topic found, provide:
1. A concise topic name
2. A brief description of what the procedure covers
3. A confidence level (high/medium/low) based on how complete the instructions are in the transcript

Focus on actionable, step-by-step procedures. Ignore casual conversation, greetings, or off-topic discussion.

Return your response as a JSON array with this structure:
[
    {
        "topic": "Topic Name",
        "description": "Brief description of what this procedure covers",
        "confidence": "high|medium|low",
        "approximate_location": "beginning|middle|end of transcript"
    }
]

If no clear SOP topics are found, return an empty array: []

TRANSCRIPT:
"""

    response = client.chat.completions.create(
        model="gpt-4o",
        messages=[
            {"role": "system", "content": "You are an expert at analyzing conversations and extracting procedural knowledge. You identify teachable processes that can be documented as SOPs."},
            {"role": "user", "content": prompt + transcript}
        ],
        response_format={"type": "json_object"},
        temperature=0.3
    )

    try:
        result = json.loads(response.choices[0].message.content)
        # Handle both array and object with 'topics' key
        if isinstance(result, list):
            return result
        elif isinstance(result, dict) and 'topics' in result:
            return result['topics']
        else:
            return []
    except json.JSONDecodeError:
        print("Warning: Could not parse topic list response.", file=sys.stderr)
        return []


def extract_sop(client: OpenAI, transcript: str, topic: str, title: str = None) -> dict:
    """
    Extract a structured SOP for a specific topic from the transcript.

    Returns:
        Dictionary with 'markdown' and 'plain' versions of the SOP
    """
    sop_title = title or topic.title()

    prompt = f"""Extract a complete Standard Operating Procedure (SOP) for the following topic from this transcript.

TOPIC TO EXTRACT: {topic}

Create a professional, actionable SOP that someone could follow to complete this task.

IMPORTANT GUIDELINES:
- Focus ONLY on the specified topic, ignore unrelated conversation
- If multiple speakers are present, identify the expert/instructor and extract their knowledge
- Include specific details, measurements, settings, and tips mentioned
- Note any warnings, common mistakes, or troubleshooting advice
- If steps are unclear or incomplete in the transcript, note this

Return your response as JSON with this structure:
{{
    "title": "{sop_title}",
    "expert_name": "Name if mentioned, otherwise null",
    "overview": {{
        "purpose": "Why this procedure exists",
        "audience": "Who should use this SOP",
        "time_estimate": "Estimated time if mentioned, otherwise null",
        "equipment_materials": ["List", "of", "required", "items"]
    }},
    "prerequisites": ["What must be ready before starting"],
    "steps": [
        {{
            "step_number": 1,
            "title": "Step Title",
            "instructions": "Detailed instructions for this step",
            "tips": ["Optional expert tips for this step"],
            "warnings": ["Optional warnings or cautions"]
        }}
    ],
    "troubleshooting": [
        {{
            "issue": "Common problem",
            "solution": "How to fix it"
        }}
    ],
    "expert_notes": ["Key insights or tips that don't fit elsewhere"],
    "completeness": "complete|partial|minimal",
    "completeness_notes": "Any notes about missing information"
}}

TRANSCRIPT:
"""

    response = client.chat.completions.create(
        model="gpt-4o",
        messages=[
            {"role": "system", "content": "You are an expert technical writer who creates clear, actionable Standard Operating Procedures from expert knowledge. You extract procedural information from conversations and structure it professionally."},
            {"role": "user", "content": prompt + transcript}
        ],
        response_format={"type": "json_object"},
        temperature=0.2
    )

    try:
        return json.loads(response.choices[0].message.content)
    except json.JSONDecodeError:
        print("Error: Could not parse SOP response.", file=sys.stderr)
        sys.exit(1)


def sop_to_markdown(sop: dict, source_file: str, include_metadata: bool = True) -> str:
    """Convert SOP dictionary to Markdown format."""
    lines = []

    # Title
    lines.append(f"# {sop['title']} - Standard Operating Procedure")
    lines.append("")

    # Metadata (for internal version)
    if include_metadata:
        lines.append(f"**Source**: {source_file} | **Extracted**: {datetime.now().strftime('%Y-%m-%d')}")
        if sop.get('expert_name'):
            lines.append(f"**Expert**: {sop['expert_name']}")
        lines.append("")

    # Overview
    lines.append("## Overview")
    overview = sop.get('overview', {})
    if overview.get('purpose'):
        lines.append(f"- **Purpose**: {overview['purpose']}")
    if overview.get('audience'):
        lines.append(f"- **Audience**: {overview['audience']}")
    if overview.get('time_estimate'):
        lines.append(f"- **Time estimate**: {overview['time_estimate']}")
    if overview.get('equipment_materials'):
        lines.append(f"- **Equipment/Materials needed**:")
        for item in overview['equipment_materials']:
            lines.append(f"  - {item}")
    lines.append("")

    # Prerequisites
    if sop.get('prerequisites'):
        lines.append("## Prerequisites")
        for prereq in sop['prerequisites']:
            lines.append(f"- {prereq}")
        lines.append("")

    # Procedure
    lines.append("## Procedure")
    lines.append("")
    for step in sop.get('steps', []):
        lines.append(f"### Step {step['step_number']}: {step['title']}")
        lines.append(step['instructions'])

        if step.get('tips'):
            for tip in step['tips']:
                lines.append(f"> *Expert tip: {tip}*")

        if step.get('warnings'):
            for warning in step['warnings']:
                lines.append(f"> **Warning**: {warning}")

        lines.append("")

    # Troubleshooting
    if sop.get('troubleshooting'):
        lines.append("## Troubleshooting")
        lines.append("")
        lines.append("| Issue | Solution |")
        lines.append("|-------|----------|")
        for item in sop['troubleshooting']:
            lines.append(f"| {item['issue']} | {item['solution']} |")
        lines.append("")

    # Expert Notes
    if sop.get('expert_notes'):
        lines.append("## Expert Notes")
        for note in sop['expert_notes']:
            lines.append(f"- {note}")
        lines.append("")

    # Completeness note
    if include_metadata:
        lines.append("---")
        completeness = sop.get('completeness', 'unknown')
        lines.append(f"*Generated from audio transcription. Completeness: {completeness}.*")
        if sop.get('completeness_notes'):
            lines.append(f"*Note: {sop['completeness_notes']}*")

    return "\n".join(lines)


def create_formatted_google_doc(sop: dict) -> str:
    """
    Create a professionally formatted Google Doc from the SOP data.

    Returns:
        URL of the created document
    """
    creds = get_google_credentials()
    if not creds:
        return None

    try:
        docs_service = build('docs', 'v1', credentials=creds)

        # Create empty document
        doc = docs_service.documents().create(body={'title': sop['title']}).execute()
        doc_id = doc.get('documentId')

        # Build the document content and formatting requests
        requests = []
        current_index = 1

        def add_text(text: str, bold: bool = False, italic: bool = False,
                     font_size: int = 11, heading: str = None, bullet: bool = False,
                     color: dict = None, space_after: int = 0) -> int:
            """Helper to add text with formatting. Returns new index."""
            nonlocal current_index, requests

            # Insert the text
            requests.append({
                'insertText': {
                    'location': {'index': current_index},
                    'text': text + '\n'
                }
            })

            text_length = len(text)
            end_index = current_index + text_length

            # Apply paragraph style (heading)
            if heading:
                requests.append({
                    'updateParagraphStyle': {
                        'range': {'startIndex': current_index, 'endIndex': end_index + 1},
                        'paragraphStyle': {'namedStyleType': heading},
                        'fields': 'namedStyleType'
                    }
                })

            # Apply text formatting
            text_style = {}
            if bold:
                text_style['bold'] = True
            if italic:
                text_style['italic'] = True
            if font_size != 11:
                text_style['fontSize'] = {'magnitude': font_size, 'unit': 'PT'}
            if color:
                text_style['foregroundColor'] = {'color': {'rgbColor': color}}

            if text_style:
                requests.append({
                    'updateTextStyle': {
                        'range': {'startIndex': current_index, 'endIndex': end_index},
                        'textStyle': text_style,
                        'fields': ','.join(text_style.keys())
                    }
                })

            # Apply bullet if needed
            if bullet:
                requests.append({
                    'createParagraphBullets': {
                        'range': {'startIndex': current_index, 'endIndex': end_index + 1},
                        'bulletPreset': 'BULLET_DISC_CIRCLE_SQUARE'
                    }
                })

            # Add spacing after paragraph
            if space_after > 0:
                requests.append({
                    'updateParagraphStyle': {
                        'range': {'startIndex': current_index, 'endIndex': end_index + 1},
                        'paragraphStyle': {'spaceBelow': {'magnitude': space_after, 'unit': 'PT'}},
                        'fields': 'spaceBelow'
                    }
                })

            current_index = end_index + 1  # +1 for newline
            return current_index

        # === TITLE ===
        add_text(sop['title'], heading='TITLE', space_after=12)

        # === OVERVIEW SECTION ===
        add_text('Overview', heading='HEADING_1', space_after=6)

        overview = sop.get('overview', {})
        if overview.get('purpose'):
            add_text(f"Purpose: {overview['purpose']}", bullet=True)
        if overview.get('audience'):
            add_text(f"Audience: {overview['audience']}", bullet=True)
        if overview.get('time_estimate'):
            add_text(f"Time Estimate: {overview['time_estimate']}", bullet=True)

        # Equipment/Materials
        if overview.get('equipment_materials'):
            add_text('Equipment & Materials Needed:', bold=True, space_after=4)
            for item in overview['equipment_materials']:
                add_text(item, bullet=True)

        # === PREREQUISITES ===
        if sop.get('prerequisites'):
            add_text('Prerequisites', heading='HEADING_1', space_after=6)
            for prereq in sop['prerequisites']:
                add_text(prereq, bullet=True)

        # === PROCEDURE ===
        add_text('Procedure', heading='HEADING_1', space_after=6)

        for step in sop.get('steps', []):
            # Step heading
            add_text(f"Step {step['step_number']}: {step['title']}", heading='HEADING_2', space_after=4)

            # Instructions
            add_text(step['instructions'], space_after=6)

            # Tips (in italic, with a different color)
            if step.get('tips'):
                for tip in step['tips']:
                    add_text(f"💡 Tip: {tip}", italic=True,
                             color={'red': 0.13, 'green': 0.55, 'blue': 0.13}, space_after=4)

            # Warnings (in bold, red-ish)
            if step.get('warnings'):
                for warning in step['warnings']:
                    add_text(f"⚠️ Warning: {warning}", bold=True,
                             color={'red': 0.8, 'green': 0.2, 'blue': 0.2}, space_after=4)

        # === TROUBLESHOOTING ===
        if sop.get('troubleshooting'):
            add_text('Troubleshooting', heading='HEADING_1', space_after=6)

            for item in sop['troubleshooting']:
                add_text(f"Issue: {item['issue']}", bold=True)
                add_text(f"Solution: {item['solution']}", space_after=8)

        # === EXPERT NOTES ===
        if sop.get('expert_notes'):
            add_text('Expert Notes', heading='HEADING_1', space_after=6)
            for note in sop['expert_notes']:
                add_text(note, bullet=True)

        # Execute all the requests
        if requests:
            docs_service.documents().batchUpdate(
                documentId=doc_id,
                body={'requests': requests}
            ).execute()

        doc_url = f"https://docs.google.com/document/d/{doc_id}/edit"
        return doc_url

    except HttpError as err:
        print(f"Google API error: {err}", file=sys.stderr)
        return None


def main():
    parser = argparse.ArgumentParser(
        description="Extract SOPs from transcripts using GPT-4"
    )
    parser.add_argument(
        "transcript_file",
        help="Path to the transcript file"
    )
    parser.add_argument(
        "--list-topics",
        action="store_true",
        help="List potential SOP topics found in the transcript"
    )
    parser.add_argument(
        "--topic", "-t",
        help="Topic to extract as an SOP"
    )
    parser.add_argument(
        "--title",
        help="Custom title for the SOP (default: topic name)"
    )
    parser.add_argument(
        "--no-gdoc",
        action="store_true",
        help="Skip Google Doc creation (Markdown only)"
    )
    parser.add_argument(
        "--output", "-o",
        help="Custom output path for the Markdown file"
    )

    args = parser.parse_args()

    # Validate input
    if not os.path.exists(args.transcript_file):
        print(f"Error: File not found: {args.transcript_file}", file=sys.stderr)
        sys.exit(1)

    if not args.list_topics and not args.topic:
        print("Error: Must specify either --list-topics or --topic", file=sys.stderr)
        sys.exit(1)

    # Check for API key
    api_key = os.getenv("OPENAI_API_KEY")
    if not api_key:
        print("Error: OPENAI_API_KEY not found in environment.", file=sys.stderr)
        sys.exit(1)

    client = OpenAI(api_key=api_key)

    # Read transcript
    with open(args.transcript_file, "r", encoding="utf-8") as f:
        transcript = f.read()

    print(f"Loaded transcript: {len(transcript):,} characters", file=sys.stderr)

    if args.list_topics:
        # List topics mode
        print("Analyzing transcript for potential SOP topics...", file=sys.stderr)
        topics = list_topics(client, transcript)

        if not topics:
            print("\nNo clear SOP topics found in the transcript.")
            return

        print(f"\nFound {len(topics)} potential SOP topic(s):\n")
        for i, topic in enumerate(topics, 1):
            print(f"{i}. {topic['topic']}")
            print(f"   Description: {topic['description']}")
            print(f"   Confidence: {topic['confidence']}")
            if topic.get('approximate_location'):
                print(f"   Location: {topic['approximate_location']}")
            print()

        print("To extract an SOP, run:")
        print(f'  ./run execution/extract_sop.py "{args.transcript_file}" --topic "<topic name>"')

    else:
        # Extract SOP mode
        print(f"Extracting SOP for topic: {args.topic}", file=sys.stderr)

        sop = extract_sop(client, transcript, args.topic, args.title)

        # Generate Markdown (internal version with metadata)
        markdown_internal = sop_to_markdown(sop, Path(args.transcript_file).name, include_metadata=True)

        # Generate Markdown (client version without metadata)
        markdown_client = sop_to_markdown(sop, Path(args.transcript_file).name, include_metadata=False)

        # Determine output path
        if args.output:
            output_path = args.output
        else:
            input_path = Path(args.transcript_file)
            # Remove _transcript suffix if present
            stem = input_path.stem
            if stem.endswith('_transcript'):
                stem = stem[:-11]
            output_path = str(input_path.parent / f"{stem}_sop.md")

        # Save Markdown file
        with open(output_path, "w", encoding="utf-8") as f:
            f.write(markdown_internal)

        print(f"\nMarkdown SOP saved to: {output_path}", file=sys.stderr)

        # Create Google Doc
        if not args.no_gdoc:
            print("Creating Google Doc...", file=sys.stderr)
            doc_url = create_formatted_google_doc(sop)

            if doc_url:
                print(f"Google Doc created: {doc_url}", file=sys.stderr)
            else:
                print("Google Doc creation skipped or failed.", file=sys.stderr)

        # Print completeness info
        completeness = sop.get('completeness', 'unknown')
        print(f"\nSOP Completeness: {completeness}", file=sys.stderr)
        if sop.get('completeness_notes'):
            print(f"Note: {sop['completeness_notes']}", file=sys.stderr)

        # Output the markdown path for easy piping
        print(output_path)


if __name__ == "__main__":
    main()

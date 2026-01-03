#!/usr/bin/env python3
"""
Copy a Google Slides template and replace text placeholders with proposal data.

Usage:
    echo '<proposal_json>' | python copy_slides_template.py <template_id>
    # or
    python copy_slides_template.py <template_id> < proposal.json

Arguments:
    template_id: Google Slides presentation ID (from URL)

Output:
    URL of the new presentation printed to stdout
"""

import sys
import json
import os.path
from google.auth.transport.requests import Request
from google.oauth2.credentials import Credentials
from google.oauth2 import service_account
from google_auth_oauthlib.flow import InstalledAppFlow
from googleapiclient.discovery import build
from googleapiclient.errors import HttpError

# Scopes needed for Drive (copy) and Slides (edit)
SCOPES = [
    "https://www.googleapis.com/auth/drive",
    "https://www.googleapis.com/auth/presentations"
]
SERVICE_ACCOUNT_FILE = 'service_account.json'


def get_credentials():
    """
    Gets valid user credentials.
    Priority:
    1. Service Account (if service_account.json exists)
    2. OAuth 2.0 (token.json or credentials.json)
    """
    creds = None

    # 1. Try Service Account
    if os.path.exists(SERVICE_ACCOUNT_FILE):
        try:
            print(f"Found {SERVICE_ACCOUNT_FILE}, attempting Service Account authentication...", file=sys.stderr)
            creds = service_account.Credentials.from_service_account_file(
                SERVICE_ACCOUNT_FILE, scopes=SCOPES)
            return creds
        except Exception as e:
            print(f"Service Account auth failed: {e}. Falling back to OAuth...", file=sys.stderr)

    # 2. Fallback to OAuth 2.0
    if os.path.exists("token.json"):
        try:
            creds = Credentials.from_authorized_user_file("token.json", SCOPES)
        except Exception:
            creds = None

    # If there are no (valid) credentials available, let the user log in.
    if not creds or not creds.valid:
        if creds and creds.expired and creds.refresh_token:
            try:
                creds.refresh(Request())
            except Exception:
                creds = None

        if not creds:
            if not os.path.exists("credentials.json"):
                print("Error: neither service_account.json nor credentials.json found.", file=sys.stderr)
                print("Please provide one of them to authenticate.", file=sys.stderr)
                sys.exit(1)

            print("Initiating OAuth 2.0 flow...", file=sys.stderr)
            flow = InstalledAppFlow.from_client_secrets_file(
                "credentials.json", SCOPES
            )
            creds = flow.run_local_server(port=8080)

        # Save the credentials for the next run
        with open("token.json", "w") as token:
            token.write(creds.to_json())

    return creds


def copy_template(drive_service, template_id: str, new_title: str) -> str:
    """
    Copy a Google Slides template to a new presentation.

    Returns:
        The ID of the new presentation
    """
    copy_body = {
        'name': new_title
    }

    copied_file = drive_service.files().copy(
        fileId=template_id,
        body=copy_body
    ).execute()

    return copied_file.get('id')


def replace_text_in_slides(slides_service, presentation_id: str, replacements: dict):
    """
    Replace placeholder text in the presentation.

    Placeholders in the template should be formatted as {{field_name}}
    e.g., {{proposal_title}}, {{overview}}, etc.
    """
    requests = []

    for field, value in replacements.items():
        # Create replacement request for {{field_name}} format
        requests.append({
            'replaceAllText': {
                'containsText': {
                    'text': '{{' + field + '}}',
                    'matchCase': False
                },
                'replaceText': str(value)
            }
        })

    if requests:
        slides_service.presentations().batchUpdate(
            presentationId=presentation_id,
            body={'requests': requests}
        ).execute()


def main():
    if len(sys.argv) != 2:
        print("Usage: echo '<json>' | python copy_slides_template.py <template_id>", file=sys.stderr)
        print("Example: echo '{...}' | python copy_slides_template.py 1ANPY3KX5c-G4ZFzsD5dMN3qACKYf8ZXlE7755KqCjF0", file=sys.stderr)
        sys.exit(1)

    template_id = sys.argv[1]

    # Read proposal JSON from stdin
    try:
        input_text = sys.stdin.read().strip()
        if not input_text:
            print("Error: No input provided. Pipe proposal JSON to stdin.", file=sys.stderr)
            sys.exit(1)

        proposal = json.loads(input_text)
    except json.JSONDecodeError as e:
        print(f"Error: Invalid JSON - {e}", file=sys.stderr)
        sys.exit(1)

    # Get the title for the new presentation
    new_title = proposal.get('proposal_title', 'Untitled Proposal')

    print(f"Copying template to: {new_title}", file=sys.stderr)

    # Authenticate
    creds = get_credentials()

    try:
        # Build services
        drive_service = build('drive', 'v3', credentials=creds)
        slides_service = build('slides', 'v1', credentials=creds)

        # Step 1: Copy the template
        new_presentation_id = copy_template(drive_service, template_id, new_title)
        print(f"Created new presentation: {new_presentation_id}", file=sys.stderr)

        # Step 2: Replace text placeholders
        replace_text_in_slides(slides_service, new_presentation_id, proposal)
        print("Replaced all text placeholders", file=sys.stderr)

        # Output the URL
        presentation_url = f"https://docs.google.com/presentation/d/{new_presentation_id}/edit"
        print(presentation_url)

    except HttpError as err:
        print(f"Google API error: {err}", file=sys.stderr)
        sys.exit(1)


if __name__ == "__main__":
    main()

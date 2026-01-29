"""Google OAuth helper for Gmail and Tasks API authentication.

Handles OAuth 2.0 flow with automatic token refresh and service account fallback.
Token is stored in token.json in the plugin directory.
"""
import os
import sys
from pathlib import Path
from typing import List, Optional

from google.auth.transport.requests import Request
from google.oauth2.credentials import Credentials
from google.oauth2 import service_account
from google_auth_oauthlib.flow import InstalledAppFlow
from googleapiclient.discovery import build


# Default scopes for Gmail and Tasks
GMAIL_SCOPES = [
    'https://www.googleapis.com/auth/gmail.readonly',
    'https://www.googleapis.com/auth/gmail.modify',
    'https://www.googleapis.com/auth/gmail.compose',
    'https://www.googleapis.com/auth/gmail.labels',
]

TASKS_SCOPES = [
    'https://www.googleapis.com/auth/tasks',
]

ALL_SCOPES = GMAIL_SCOPES + TASKS_SCOPES


def get_plugin_dir() -> Path:
    """Get the plugin directory (where credentials are stored)."""
    return Path(__file__).parent.parent


def get_google_credentials(
    scopes: List[str] = None,
    credentials_path: str = None,
    token_path: str = None,
    service_account_path: str = None
) -> Credentials:
    """
    Get Google API credentials.

    Priority:
    1. Service Account (if service_account.json exists) - for headless automation
    2. OAuth 2.0 (token.json or credentials.json) - for interactive use

    Args:
        scopes: List of API scopes required (default: ALL_SCOPES)
        credentials_path: Path to OAuth client credentials (default: credentials.json)
        token_path: Path to saved tokens (default: token.json)
        service_account_path: Path to service account JSON (default: service_account.json)

    Returns:
        google.oauth2.credentials.Credentials

    Raises:
        FileNotFoundError: If credentials.json not found
        Exception: If authentication fails
    """
    plugin_dir = get_plugin_dir()
    scopes = scopes or ALL_SCOPES
    credentials_path = credentials_path or str(plugin_dir / 'credentials.json')
    token_path = token_path or str(plugin_dir / 'token.json')
    service_account_path = service_account_path or str(plugin_dir / 'service_account.json')

    creds = None

    # 1. Try Service Account (useful for automation/headless)
    if os.path.exists(service_account_path):
        try:
            print("Using service account authentication...", file=sys.stderr)
            creds = service_account.Credentials.from_service_account_file(
                service_account_path, scopes=scopes
            )
            return creds
        except Exception as e:
            print(f"Service account auth failed: {e}. Trying OAuth...", file=sys.stderr)

    # 2. Try existing token
    if os.path.exists(token_path):
        try:
            creds = Credentials.from_authorized_user_file(token_path, scopes)
        except Exception:
            creds = None

    # 3. Refresh or run OAuth flow
    if not creds or not creds.valid:
        if creds and creds.expired and creds.refresh_token:
            try:
                print("Refreshing OAuth token...", file=sys.stderr)
                creds.refresh(Request())
            except Exception as e:
                print(f"Token refresh failed: {e}", file=sys.stderr)
                creds = None

        if not creds:
            if not os.path.exists(credentials_path):
                print(f"Error: {credentials_path} not found.", file=sys.stderr)
                print("", file=sys.stderr)
                print("To set up Google OAuth credentials:", file=sys.stderr)
                print("1. Go to https://console.cloud.google.com/", file=sys.stderr)
                print("2. Create a project and enable Gmail API and Tasks API", file=sys.stderr)
                print("3. Go to APIs & Services > Credentials", file=sys.stderr)
                print("4. Create OAuth 2.0 Client ID (Desktop app)", file=sys.stderr)
                print(f"5. Download JSON and save as: {credentials_path}", file=sys.stderr)
                sys.exit(1)

            print("Initiating Google OAuth flow...", file=sys.stderr)
            flow = InstalledAppFlow.from_client_secrets_file(credentials_path, scopes)

            # Use OOB/manual flow for headless servers
            flow.redirect_uri = 'urn:ietf:wg:oauth:2.0:oob'
            auth_url, _ = flow.authorization_url(prompt='consent')

            print("", file=sys.stderr)
            print("=" * 60, file=sys.stderr)
            print("Visit this URL in your browser to authorize:", file=sys.stderr)
            print("", file=sys.stderr)
            print(f"  {auth_url}", file=sys.stderr)
            print("", file=sys.stderr)
            print("After authorizing, copy the code and paste it below.", file=sys.stderr)
            print("=" * 60, file=sys.stderr)
            print("", file=sys.stderr)

            code = input("Enter authorization code: ").strip()
            flow.fetch_token(code=code)
            creds = flow.credentials

        # Save token for next run
        with open(token_path, 'w') as token:
            token.write(creds.to_json())
        print(f"Token saved to {token_path}", file=sys.stderr)

    return creds


def build_gmail_service(creds: Credentials = None):
    """Build Gmail API service.

    Args:
        creds: Optional credentials. If not provided, will authenticate.

    Returns:
        Gmail API service resource
    """
    if creds is None:
        creds = get_google_credentials(GMAIL_SCOPES)
    return build('gmail', 'v1', credentials=creds)


def build_tasks_service(creds: Credentials = None):
    """Build Tasks API service.

    Args:
        creds: Optional credentials. If not provided, will authenticate.

    Returns:
        Tasks API service resource
    """
    if creds is None:
        creds = get_google_credentials(TASKS_SCOPES)
    return build('tasks', 'v1', credentials=creds)


def build_services():
    """Build both Gmail and Tasks services with shared credentials.

    Returns:
        tuple: (gmail_service, tasks_service)
    """
    creds = get_google_credentials(ALL_SCOPES)
    gmail = build('gmail', 'v1', credentials=creds)
    tasks = build('tasks', 'v1', credentials=creds)
    return gmail, tasks

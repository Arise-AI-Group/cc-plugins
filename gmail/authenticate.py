#!/usr/bin/env python3
"""One-time authentication script for Gmail plugin.

Run this interactively to complete OAuth flow:
    cd /home/trent/workspace/cc-plugins/gmail
    ./.venv/bin/python3 authenticate.py
"""
import sys
sys.path.insert(0, '.')

from tool.auth import get_google_credentials, ALL_SCOPES

if __name__ == '__main__':
    print("Gmail Plugin Authentication")
    print("=" * 40)
    print()
    creds = get_google_credentials(ALL_SCOPES)
    print()
    print("Authentication successful!")
    print("You can now use the Gmail plugin.")

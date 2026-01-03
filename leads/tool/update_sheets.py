#!/usr/bin/env python3
"""
Upload leads to Google Sheets.

Usage:
    python update_sheets.py <leads_file>

Arguments:
    leads_file: Path to JSON file containing leads

Output:
    Google Sheets URL printed to stdout
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

# If modifying these scopes, delete the file token.json.
SCOPES = ["https://www.googleapis.com/auth/spreadsheets"]
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
            print(f"Found {SERVICE_ACCOUNT_FILE}, attempting Service Account authentication...")
            creds = service_account.Credentials.from_service_account_file(
                SERVICE_ACCOUNT_FILE, scopes=SCOPES)
            return creds
        except Exception as e:
            print(f"Service Account auth failed: {e}. Falling back to OAuth...")

    # 2. Fallback to OAuth 2.0
    # The file token.json stores the user's access and refresh tokens, and is
    # created automatically when the authorization flow completes for the first
    # time.
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
                print("Error: neither service_account.json nor credentials.json found.")
                print("Please provide one of them to authenticate.")
                sys.exit(1)

            print("Initiating OAuth 2.0 flow...")
            flow = InstalledAppFlow.from_client_secrets_file(
                "credentials.json", SCOPES
            )
            creds = flow.run_local_server(port=8080)

        # Save the credentials for the next run
        with open("token.json", "w") as token:
            token.write(creds.to_json())

    return creds

def update_sheets(leads_file):
    """
    Uploads leads to Google Sheets.
    Returns the URL of the sheet.
    """
    print(f"Uploading leads from {leads_file} to Google Sheets...")

    creds = get_credentials()

    try:
        service = build("sheets", "v4", credentials=creds)

        # Create a new spreadsheet
        spreadsheet = {
            "properties": {
                "title": f"Leads Export - {os.path.basename(leads_file)}"
            }
        }
        spreadsheet = service.spreadsheets().create(body=spreadsheet, fields="spreadsheetId,spreadsheetUrl").execute()
        spreadsheet_id = spreadsheet.get("spreadsheetId")
        spreadsheet_url = spreadsheet.get("spreadsheetUrl")
        print(f"Created spreadsheet ID: {spreadsheet_id}")

        # Read leads data
        with open(leads_file, 'r') as f:
            leads = json.load(f)

        if not leads:
            print("No leads to upload.")
            return spreadsheet_url

        # Prepare data for upload
        # Assuming leads is a list of dicts, we'll take keys as headers
        headers = list(leads[0].keys())
        values = [headers]

        for lead in leads:
            row = []
            for header in headers:
                row.append(str(lead.get(header, "")))
            values.append(row)

        body = {
            "values": values
        }

        result = service.spreadsheets().values().update(
            spreadsheetId=spreadsheet_id, range="A1",
            valueInputOption="RAW", body=body).execute()

        print(f"{result.get('updatedCells')} cells updated.")
        print(f"Successfully uploaded to: {spreadsheet_url}")
        return spreadsheet_url

    except HttpError as err:
        print(f"An error occurred: {err}")
        return None

if __name__ == "__main__":
    if len(sys.argv) < 2:
        print("Usage: python update_sheets.py <leads_file>")
        sys.exit(1)

    file_path = sys.argv[1]
    if not os.path.exists(file_path):
        print(f"Error: File {file_path} not found.")
        sys.exit(1)

    url = update_sheets(file_path)
    if url:
        print(url)

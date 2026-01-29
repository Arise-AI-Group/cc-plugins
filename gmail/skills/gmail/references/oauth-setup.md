# OAuth Credential Setup

This guide explains how to set up Google OAuth credentials for the Gmail plugin.

## Prerequisites

- A Google account
- Access to Google Cloud Console

## Step 1: Create a Google Cloud Project

1. Go to [Google Cloud Console](https://console.cloud.google.com/)
2. Click the project dropdown at the top
3. Click "New Project"
4. Enter a project name (e.g., "Gmail CLI Tool")
5. Click "Create"

## Step 2: Enable APIs

1. In your project, go to **APIs & Services > Library**
2. Search for and enable:
   - **Gmail API**
   - **Tasks API**
3. Click "Enable" for each API

## Step 3: Configure OAuth Consent Screen

1. Go to **APIs & Services > OAuth consent screen**
2. Select **External** user type (unless you have Google Workspace)
3. Click "Create"
4. Fill in required fields:
   - App name: "Gmail CLI Tool"
   - User support email: your email
   - Developer contact: your email
5. Click "Save and Continue"
6. On Scopes page, just click "Save and Continue" (scopes are requested at runtime)
7. Add test users (your Gmail address)
8. Click "Save and Continue"

## Step 4: Create OAuth Client ID

1. Go to **APIs & Services > Credentials**
2. Click "Create Credentials" > "OAuth client ID"
3. Application type: **Desktop app**
4. Name: "Gmail CLI"
5. Click "Create"
6. Download the JSON file
7. Save it as `credentials.json` in the plugin directory:
   ```
   ~/.claude/plugins/gmail/credentials.json
   ```
   Or if using local development:
   ```
   /path/to/cc-plugins/gmail/credentials.json
   ```

## Step 5: First Authorization

**Always run OAuth in the terminal** - this is the recommended approach for security. It gives you full visibility into the authorization process and prevents automatic browser redirects.

1. Run the authenticate script in your terminal:
   ```bash
   cd /path/to/gmail
   ./.venv/bin/python3 authenticate.py
   ```
2. You'll see a URL printed - copy and open it in your browser
3. Sign in with your Google account
4. Review permissions and click "Allow"
5. Copy the authorization code shown after approval
6. Paste the code back into the terminal
7. A `token.json` file is created automatically

**Alternative:** You can transfer an existing `token.json` from another machine where you've already authorized.

## Token Management

### Token Location
```
gmail/token.json
```

### Token Refresh
Tokens automatically refresh when expired. If you encounter auth errors:
1. Delete `token.json`
2. Run any command to re-authenticate

### Revoking Access
To revoke the app's access:
1. Go to [Google Account Security](https://myaccount.google.com/security)
2. Under "Third-party apps with account access"
3. Find and remove "Gmail CLI Tool"

## Service Account (Optional)

For headless/automation use, you can use a service account:

1. In Cloud Console, go to **APIs & Services > Credentials**
2. Click "Create Credentials" > "Service Account"
3. Fill in details and create
4. Download the JSON key file
5. Save as `service_account.json` in the plugin directory

**Note:** Service accounts can't access regular Gmail accounts. They work for:
- Google Workspace accounts with domain-wide delegation
- Automation scenarios with proper setup

## Troubleshooting

### "Access blocked: App not verified"
- Add yourself as a test user in the OAuth consent screen
- Or submit for verification if deploying to others

### "Token expired"
- Delete `token.json` and re-authenticate

### "Invalid grant"
- Token may have been revoked
- Delete `token.json` and re-authenticate

### "Quota exceeded"
- Wait and retry
- Check quota in Cloud Console under APIs & Services > Quotas

### "credentials.json not found"
- Ensure the file is named exactly `credentials.json`
- Place it in the gmail plugin directory

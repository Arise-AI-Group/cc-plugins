#!/usr/bin/env python3
"""
Gmail and Google Tasks API Integration

Provides full email and task management via CLI:
- Messages: list, search, get, archive, trash, delete, mark read/unread, star
- Labels: list, create, delete, apply, remove
- Drafts: list, create, update, delete, send
- Send: new emails, reply, reply-all, forward with attachments
- Export: save emails/threads as .eml, .txt, or .md
- Tasks: lists, tasks, create, complete, delete

Usage (CLI):
    python gmail_api.py messages list --label INBOX --limit 20
    python gmail_api.py messages search "from:boss@company.com"
    python gmail_api.py messages get <message_id>
    python gmail_api.py labels list
    python gmail_api.py send new --to user@example.com --subject "Hello" --body "Message"
    python gmail_api.py tasks lists
    python gmail_api.py tasks create @default --title "Follow up" --due 2025-02-01

Usage (Module):
    from gmail_api import GmailClient, TasksClient
    gmail = GmailClient()
    messages = gmail.list_messages(label_ids=['INBOX'], max_results=10)
"""

import os
import sys
import json
import argparse
import base64
import re
import time
from pathlib import Path
from datetime import datetime, timezone
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
from email.mime.base import MIMEBase
from email import encoders
from typing import Optional, List, Dict, Any, Tuple

from googleapiclient.errors import HttpError

from .auth import (
    get_google_credentials,
    build_gmail_service,
    build_tasks_service,
    build_services,
    ALL_SCOPES,
    GMAIL_SCOPES,
    TASKS_SCOPES,
)


# ==============================================================================
# Exceptions
# ==============================================================================

class GmailError(Exception):
    """Base exception for Gmail API errors."""
    pass


class GmailAuthError(GmailError):
    """Authentication error."""
    pass


class GmailRateLimitError(GmailError):
    """Rate limit exceeded."""
    def __init__(self, retry_after: int = 60):
        self.retry_after = retry_after
        super().__init__(f"Rate limited. Retry after {retry_after} seconds.")


class GmailNotFoundError(GmailError):
    """Message/thread/label not found."""
    pass


class GmailQuotaError(GmailError):
    """API quota exceeded."""
    pass


class TasksError(Exception):
    """Base exception for Tasks API errors."""
    pass


class TasksNotFoundError(TasksError):
    """Task or task list not found."""
    pass


# ==============================================================================
# Gmail Client
# ==============================================================================

class GmailClient:
    """Client for interacting with Gmail API."""

    def __init__(self, service=None):
        """Initialize Gmail client.

        Args:
            service: Optional Gmail API service. If not provided, will authenticate.
        """
        self.service = service or build_gmail_service()
        self._label_cache: Dict[str, str] = {}  # name -> id cache
        self._user_id = 'me'

    def _handle_error(self, error: HttpError) -> None:
        """Convert Gmail API errors to custom exceptions."""
        status = error.resp.status
        try:
            reason = json.loads(error.content).get('error', {}).get('message', str(error))
        except (json.JSONDecodeError, AttributeError):
            reason = str(error)

        if status == 401:
            raise GmailAuthError("Invalid or expired credentials")
        elif status == 403:
            if 'quota' in reason.lower():
                raise GmailQuotaError("API quota exceeded")
            raise GmailError(f"Permission denied: {reason}")
        elif status == 404:
            raise GmailNotFoundError(f"Resource not found: {reason}")
        elif status == 429:
            retry_after = int(error.resp.get('Retry-After', 60))
            raise GmailRateLimitError(retry_after)
        else:
            raise GmailError(f"Gmail API error ({status}): {reason}")

    def _request_with_retry(self, request, max_retries: int = 3):
        """Execute request with automatic retry on rate limits."""
        for attempt in range(max_retries):
            try:
                return request.execute()
            except HttpError as e:
                if e.resp.status == 429 and attempt < max_retries - 1:
                    retry_after = int(e.resp.get('Retry-After', 2 ** attempt))
                    print(f"Rate limited, retrying in {retry_after}s...", file=sys.stderr)
                    time.sleep(retry_after)
                else:
                    self._handle_error(e)

    # ==================== Message Operations ====================

    def list_messages(
        self,
        query: str = None,
        label_ids: List[str] = None,
        max_results: int = 100,
        include_spam_trash: bool = False
    ) -> List[Dict]:
        """List messages with optional filtering.

        Args:
            query: Gmail search query (e.g., "from:boss@company.com")
            label_ids: Filter by label IDs (e.g., ['INBOX', 'UNREAD'])
            max_results: Maximum number of messages to return
            include_spam_trash: Include spam and trash

        Returns:
            List of message objects with id, threadId, and snippet
        """
        messages = []
        page_token = None

        while len(messages) < max_results:
            request = self.service.users().messages().list(
                userId=self._user_id,
                q=query,
                labelIds=label_ids,
                maxResults=min(max_results - len(messages), 100),
                pageToken=page_token,
                includeSpamTrash=include_spam_trash
            )
            response = self._request_with_retry(request)

            batch = response.get('messages', [])
            if not batch:
                break

            # Get message details for each
            for msg in batch:
                detail = self.get_message(msg['id'], format='metadata')
                messages.append(detail)

            page_token = response.get('nextPageToken')
            if not page_token:
                break

        return messages[:max_results]

    def search(self, query: str, max_results: int = 100) -> List[Dict]:
        """Search messages using Gmail query syntax.

        Args:
            query: Gmail search query
            max_results: Maximum results to return

        Returns:
            List of message objects
        """
        return self.list_messages(query=query, max_results=max_results)

    def get_message(self, message_id: str, format: str = 'full') -> Dict:
        """Get a single message.

        Args:
            message_id: Message ID
            format: 'minimal', 'metadata', 'full', or 'raw'

        Returns:
            Message object
        """
        request = self.service.users().messages().get(
            userId=self._user_id,
            id=message_id,
            format=format
        )
        message = self._request_with_retry(request)
        return self._parse_message(message, format)

    def get_thread(self, thread_id: str, format: str = 'full') -> Dict:
        """Get a full thread with all messages.

        Args:
            thread_id: Thread ID
            format: Message format

        Returns:
            Thread object with messages
        """
        request = self.service.users().threads().get(
            userId=self._user_id,
            id=thread_id,
            format=format
        )
        thread = self._request_with_retry(request)

        # Parse each message in the thread
        thread['messages'] = [
            self._parse_message(msg, format) for msg in thread.get('messages', [])
        ]
        return thread

    def _parse_message(self, message: Dict, format: str = 'full') -> Dict:
        """Parse API message into friendly format."""
        result = {
            'id': message.get('id'),
            'threadId': message.get('threadId'),
            'labelIds': message.get('labelIds', []),
            'snippet': message.get('snippet', ''),
        }

        if format == 'raw':
            result['raw'] = message.get('raw')
            return result

        payload = message.get('payload', {})
        headers = self._extract_headers(payload.get('headers', []))

        result.update({
            'subject': headers.get('Subject', ''),
            'from': headers.get('From', ''),
            'to': headers.get('To', ''),
            'cc': headers.get('Cc', ''),
            'date': headers.get('Date', ''),
            'messageId': headers.get('Message-ID', ''),
            'inReplyTo': headers.get('In-Reply-To', ''),
            'references': headers.get('References', ''),
        })

        if format in ('full', 'metadata'):
            # Extract body
            text_body, html_body = self._extract_body(payload)
            result['body'] = text_body or ''
            result['htmlBody'] = html_body or ''

            # Extract attachments info
            result['attachments'] = self._extract_attachment_info(payload)

        return result

    def _extract_headers(self, headers: List[Dict]) -> Dict[str, str]:
        """Extract headers into dict."""
        return {h['name']: h['value'] for h in headers}

    def _extract_body(self, payload: Dict) -> Tuple[str, str]:
        """Extract plain text and HTML body from payload."""
        text_body = None
        html_body = None

        def extract_parts(part):
            nonlocal text_body, html_body
            mime_type = part.get('mimeType', '')

            if 'parts' in part:
                for p in part['parts']:
                    extract_parts(p)
            elif mime_type == 'text/plain' and not text_body:
                data = part.get('body', {}).get('data', '')
                if data:
                    text_body = base64.urlsafe_b64decode(data).decode('utf-8', errors='replace')
            elif mime_type == 'text/html' and not html_body:
                data = part.get('body', {}).get('data', '')
                if data:
                    html_body = base64.urlsafe_b64decode(data).decode('utf-8', errors='replace')

        extract_parts(payload)
        return text_body, html_body

    def _extract_attachment_info(self, payload: Dict) -> List[Dict]:
        """Extract attachment information from payload."""
        attachments = []

        def extract_parts(part):
            if 'parts' in part:
                for p in part['parts']:
                    extract_parts(p)
            elif part.get('filename'):
                attachments.append({
                    'filename': part['filename'],
                    'mimeType': part.get('mimeType', ''),
                    'size': part.get('body', {}).get('size', 0),
                    'attachmentId': part.get('body', {}).get('attachmentId', ''),
                })

        extract_parts(payload)
        return attachments

    def get_attachment(self, message_id: str, attachment_id: str) -> bytes:
        """Download attachment data.

        Args:
            message_id: Message ID
            attachment_id: Attachment ID

        Returns:
            Raw attachment bytes
        """
        request = self.service.users().messages().attachments().get(
            userId=self._user_id,
            messageId=message_id,
            id=attachment_id
        )
        attachment = self._request_with_retry(request)
        data = attachment.get('data', '')
        return base64.urlsafe_b64decode(data)

    def modify_message(
        self,
        message_id: str,
        add_labels: List[str] = None,
        remove_labels: List[str] = None
    ) -> Dict:
        """Modify message labels.

        Args:
            message_id: Message ID
            add_labels: Label IDs to add
            remove_labels: Label IDs to remove

        Returns:
            Updated message
        """
        body = {
            'addLabelIds': add_labels or [],
            'removeLabelIds': remove_labels or [],
        }
        request = self.service.users().messages().modify(
            userId=self._user_id,
            id=message_id,
            body=body
        )
        return self._request_with_retry(request)

    def batch_modify(
        self,
        message_ids: List[str],
        add_labels: List[str] = None,
        remove_labels: List[str] = None
    ) -> None:
        """Batch modify multiple messages.

        Args:
            message_ids: List of message IDs
            add_labels: Label IDs to add
            remove_labels: Label IDs to remove
        """
        body = {
            'ids': message_ids,
            'addLabelIds': add_labels or [],
            'removeLabelIds': remove_labels or [],
        }
        request = self.service.users().messages().batchModify(
            userId=self._user_id,
            body=body
        )
        self._request_with_retry(request)

    def mark_read(self, message_ids: List[str]) -> None:
        """Mark messages as read."""
        self.batch_modify(message_ids, remove_labels=['UNREAD'])

    def mark_unread(self, message_ids: List[str]) -> None:
        """Mark messages as unread."""
        self.batch_modify(message_ids, add_labels=['UNREAD'])

    def star(self, message_ids: List[str]) -> None:
        """Star messages."""
        self.batch_modify(message_ids, add_labels=['STARRED'])

    def unstar(self, message_ids: List[str]) -> None:
        """Remove star from messages."""
        self.batch_modify(message_ids, remove_labels=['STARRED'])

    def archive(self, message_ids: List[str]) -> None:
        """Archive messages (remove INBOX label)."""
        self.batch_modify(message_ids, remove_labels=['INBOX'])

    def trash_message(self, message_id: str) -> Dict:
        """Move message to trash."""
        request = self.service.users().messages().trash(
            userId=self._user_id,
            id=message_id
        )
        return self._request_with_retry(request)

    def untrash_message(self, message_id: str) -> Dict:
        """Remove message from trash."""
        request = self.service.users().messages().untrash(
            userId=self._user_id,
            id=message_id
        )
        return self._request_with_retry(request)

    def delete_message(self, message_id: str) -> None:
        """Permanently delete message."""
        request = self.service.users().messages().delete(
            userId=self._user_id,
            id=message_id
        )
        self._request_with_retry(request)

    # ==================== Label Operations ====================

    def list_labels(self) -> List[Dict]:
        """List all labels."""
        request = self.service.users().labels().list(userId=self._user_id)
        response = self._request_with_retry(request)
        labels = response.get('labels', [])

        # Update cache
        for label in labels:
            self._label_cache[label['name'].lower()] = label['id']

        return labels

    def get_label(self, label_id: str) -> Dict:
        """Get label details."""
        request = self.service.users().labels().get(
            userId=self._user_id,
            id=label_id
        )
        return self._request_with_retry(request)

    def create_label(
        self,
        name: str,
        label_list_visibility: str = 'labelShow',
        message_list_visibility: str = 'show',
        background_color: str = None,
        text_color: str = None
    ) -> Dict:
        """Create a new label.

        Args:
            name: Label name
            label_list_visibility: 'labelShow', 'labelShowIfUnread', 'labelHide'
            message_list_visibility: 'show', 'hide'
            background_color: Hex color for background
            text_color: Hex color for text

        Returns:
            Created label
        """
        body = {
            'name': name,
            'labelListVisibility': label_list_visibility,
            'messageListVisibility': message_list_visibility,
        }
        if background_color or text_color:
            body['color'] = {}
            if background_color:
                body['color']['backgroundColor'] = background_color
            if text_color:
                body['color']['textColor'] = text_color

        request = self.service.users().labels().create(
            userId=self._user_id,
            body=body
        )
        label = self._request_with_retry(request)
        self._label_cache[name.lower()] = label['id']
        return label

    def update_label(self, label_id: str, **kwargs) -> Dict:
        """Update a label."""
        request = self.service.users().labels().update(
            userId=self._user_id,
            id=label_id,
            body=kwargs
        )
        return self._request_with_retry(request)

    def delete_label(self, label_id: str) -> None:
        """Delete a label."""
        request = self.service.users().labels().delete(
            userId=self._user_id,
            id=label_id
        )
        self._request_with_retry(request)

    def resolve_label(self, label_name_or_id: str) -> str:
        """Resolve label name to ID.

        Args:
            label_name_or_id: Label name or ID

        Returns:
            Label ID
        """
        # Check if it's already an ID (system labels are uppercase)
        if label_name_or_id.isupper() or label_name_or_id.startswith('Label_'):
            return label_name_or_id

        # Check cache
        key = label_name_or_id.lower()
        if key in self._label_cache:
            return self._label_cache[key]

        # Refresh cache
        self.list_labels()
        if key in self._label_cache:
            return self._label_cache[key]

        raise GmailNotFoundError(f"Label not found: {label_name_or_id}")

    # ==================== Draft Operations ====================

    def list_drafts(self, max_results: int = 100) -> List[Dict]:
        """List drafts."""
        drafts = []
        page_token = None

        while len(drafts) < max_results:
            request = self.service.users().drafts().list(
                userId=self._user_id,
                maxResults=min(max_results - len(drafts), 100),
                pageToken=page_token
            )
            response = self._request_with_retry(request)

            batch = response.get('drafts', [])
            if not batch:
                break

            for draft in batch:
                detail = self.get_draft(draft['id'])
                drafts.append(detail)

            page_token = response.get('nextPageToken')
            if not page_token:
                break

        return drafts[:max_results]

    def get_draft(self, draft_id: str) -> Dict:
        """Get draft content."""
        request = self.service.users().drafts().get(
            userId=self._user_id,
            id=draft_id,
            format='full'
        )
        draft = self._request_with_retry(request)
        draft['message'] = self._parse_message(draft.get('message', {}), 'full')
        return draft

    def create_draft(
        self,
        to: List[str],
        subject: str,
        body: str,
        cc: List[str] = None,
        bcc: List[str] = None,
        html: bool = False,
        attachments: List[str] = None,
        thread_id: str = None,
        in_reply_to: str = None,
        references: str = None
    ) -> Dict:
        """Create a draft email.

        Args:
            to: List of recipient emails
            subject: Email subject
            body: Email body (plain text or HTML)
            cc: CC recipients
            bcc: BCC recipients
            html: If True, body is HTML
            attachments: List of file paths to attach
            thread_id: Thread ID if replying
            in_reply_to: Message-ID header for reply
            references: References header for reply

        Returns:
            Created draft
        """
        message = self._build_message(
            to=to,
            subject=subject,
            body=body,
            cc=cc,
            bcc=bcc,
            html=html,
            attachments=attachments,
            in_reply_to=in_reply_to,
            references=references
        )

        draft_body = {'message': message}
        if thread_id:
            draft_body['message']['threadId'] = thread_id

        request = self.service.users().drafts().create(
            userId=self._user_id,
            body=draft_body
        )
        return self._request_with_retry(request)

    def update_draft(
        self,
        draft_id: str,
        to: List[str] = None,
        subject: str = None,
        body: str = None,
        cc: List[str] = None,
        bcc: List[str] = None,
        html: bool = False,
        attachments: List[str] = None
    ) -> Dict:
        """Update an existing draft."""
        message = self._build_message(
            to=to or [],
            subject=subject or '',
            body=body or '',
            cc=cc,
            bcc=bcc,
            html=html,
            attachments=attachments
        )

        request = self.service.users().drafts().update(
            userId=self._user_id,
            id=draft_id,
            body={'message': message}
        )
        return self._request_with_retry(request)

    def delete_draft(self, draft_id: str) -> None:
        """Delete a draft."""
        request = self.service.users().drafts().delete(
            userId=self._user_id,
            id=draft_id
        )
        self._request_with_retry(request)

    def send_draft(self, draft_id: str) -> Dict:
        """Send a draft."""
        request = self.service.users().drafts().send(
            userId=self._user_id,
            body={'id': draft_id}
        )
        return self._request_with_retry(request)

    # ==================== Send Operations ====================

    def send_message(
        self,
        to: List[str],
        subject: str,
        body: str,
        cc: List[str] = None,
        bcc: List[str] = None,
        html: bool = False,
        attachments: List[str] = None,
        thread_id: str = None,
        in_reply_to: str = None,
        references: str = None
    ) -> Dict:
        """Send a new email.

        Args:
            to: List of recipient emails
            subject: Email subject
            body: Email body
            cc: CC recipients
            bcc: BCC recipients
            html: If True, body is HTML
            attachments: List of file paths to attach
            thread_id: Thread ID if replying
            in_reply_to: Message-ID for reply threading
            references: References header for reply threading

        Returns:
            Sent message
        """
        message = self._build_message(
            to=to,
            subject=subject,
            body=body,
            cc=cc,
            bcc=bcc,
            html=html,
            attachments=attachments,
            in_reply_to=in_reply_to,
            references=references
        )

        if thread_id:
            message['threadId'] = thread_id

        request = self.service.users().messages().send(
            userId=self._user_id,
            body=message
        )
        return self._request_with_retry(request)

    def reply(
        self,
        message_id: str,
        body: str,
        html: bool = False,
        attachments: List[str] = None,
        reply_all: bool = False
    ) -> Dict:
        """Reply to a message.

        Args:
            message_id: Message ID to reply to
            body: Reply body
            html: If True, body is HTML
            attachments: File paths to attach
            reply_all: If True, reply to all recipients

        Returns:
            Sent message
        """
        # Get original message for threading info
        original = self.get_message(message_id, format='metadata')

        to = [original['from']]
        cc = None

        if reply_all:
            # Include all original recipients except self
            profile = self._get_profile()
            my_email = profile.get('emailAddress', '')

            all_recipients = []
            if original.get('to'):
                all_recipients.extend(self._parse_addresses(original['to']))
            if original.get('cc'):
                all_recipients.extend(self._parse_addresses(original['cc']))

            # Filter out self and original sender
            cc = [addr for addr in all_recipients
                  if addr.lower() != my_email.lower() and addr.lower() != original['from'].lower()]

        # Build subject with Re: prefix
        subject = original.get('subject', '')
        if not subject.lower().startswith('re:'):
            subject = f"Re: {subject}"

        # Build references for threading
        references = original.get('references', '')
        if original.get('messageId'):
            if references:
                references = f"{references} {original['messageId']}"
            else:
                references = original['messageId']

        return self.send_message(
            to=to,
            subject=subject,
            body=body,
            cc=cc,
            html=html,
            attachments=attachments,
            thread_id=original.get('threadId'),
            in_reply_to=original.get('messageId'),
            references=references
        )

    def forward(
        self,
        message_id: str,
        to: List[str],
        body: str = None,
        html: bool = False
    ) -> Dict:
        """Forward a message.

        Args:
            message_id: Message ID to forward
            to: Forward recipients
            body: Optional body to prepend
            html: If True, body is HTML

        Returns:
            Sent message
        """
        # Get original message
        original = self.get_message(message_id, format='full')

        # Build subject with Fwd: prefix
        subject = original.get('subject', '')
        if not subject.lower().startswith('fwd:'):
            subject = f"Fwd: {subject}"

        # Build forward body
        forward_header = (
            f"\n\n---------- Forwarded message ----------\n"
            f"From: {original.get('from', '')}\n"
            f"Date: {original.get('date', '')}\n"
            f"Subject: {original.get('subject', '')}\n"
            f"To: {original.get('to', '')}\n\n"
        )

        full_body = (body or '') + forward_header + (original.get('body', '') or original.get('htmlBody', ''))

        return self.send_message(
            to=to,
            subject=subject,
            body=full_body,
            html=html
        )

    def _build_message(
        self,
        to: List[str],
        subject: str,
        body: str,
        cc: List[str] = None,
        bcc: List[str] = None,
        html: bool = False,
        attachments: List[str] = None,
        in_reply_to: str = None,
        references: str = None
    ) -> Dict:
        """Build MIME message for sending."""
        if attachments:
            msg = MIMEMultipart()
            if html:
                msg.attach(MIMEText(body, 'html'))
            else:
                msg.attach(MIMEText(body, 'plain'))

            for filepath in attachments:
                path = Path(filepath)
                if not path.exists():
                    raise GmailError(f"Attachment not found: {filepath}")

                with open(path, 'rb') as f:
                    part = MIMEBase('application', 'octet-stream')
                    part.set_payload(f.read())
                    encoders.encode_base64(part)
                    part.add_header(
                        'Content-Disposition',
                        f'attachment; filename="{path.name}"'
                    )
                    msg.attach(part)
        else:
            msg = MIMEText(body, 'html' if html else 'plain')

        msg['To'] = ', '.join(to)
        msg['Subject'] = subject

        if cc:
            msg['Cc'] = ', '.join(cc)
        if bcc:
            msg['Bcc'] = ', '.join(bcc)
        if in_reply_to:
            msg['In-Reply-To'] = in_reply_to
        if references:
            msg['References'] = references

        raw = base64.urlsafe_b64encode(msg.as_bytes()).decode('utf-8')
        return {'raw': raw}

    def _get_profile(self) -> Dict:
        """Get user profile."""
        request = self.service.users().getProfile(userId=self._user_id)
        return self._request_with_retry(request)

    def _parse_addresses(self, address_string: str) -> List[str]:
        """Parse comma-separated email addresses."""
        # Simple parsing - could be improved for complex cases
        addresses = []
        for addr in address_string.split(','):
            addr = addr.strip()
            # Extract email from "Name <email>" format
            match = re.search(r'<([^>]+)>', addr)
            if match:
                addresses.append(match.group(1))
            elif '@' in addr:
                addresses.append(addr)
        return addresses

    # ==================== Export Operations ====================

    def export_message(
        self,
        message_id: str,
        output_dir: str,
        format: str = 'md'
    ) -> str:
        """Export message to file.

        Args:
            message_id: Message ID
            output_dir: Output directory
            format: 'eml', 'txt', or 'md'

        Returns:
            Path to exported file
        """
        output_path = Path(output_dir)
        output_path.mkdir(parents=True, exist_ok=True)

        if format == 'eml':
            message = self.get_message(message_id, format='raw')
            raw = base64.urlsafe_b64decode(message['raw'])

            # Parse for filename
            headers = {}
            for line in raw.decode('utf-8', errors='replace').split('\n')[:50]:
                if ':' in line:
                    key, value = line.split(':', 1)
                    headers[key.strip()] = value.strip()
                if line.strip() == '':
                    break

            filename = self._build_filename(headers.get('Date', ''), headers.get('Subject', ''), 'eml')
            filepath = output_path / filename
            filepath.write_bytes(raw)
        else:
            message = self.get_message(message_id, format='full')
            filename = self._build_filename(message.get('date', ''), message.get('subject', ''), format)
            filepath = output_path / filename

            if format == 'txt':
                content = (
                    f"From: {message.get('from', '')}\n"
                    f"To: {message.get('to', '')}\n"
                    f"Subject: {message.get('subject', '')}\n"
                    f"Date: {message.get('date', '')}\n"
                    f"\n{message.get('body', '')}"
                )
            else:  # md
                content = (
                    f"# {message.get('subject', 'No Subject')}\n\n"
                    f"**From:** {message.get('from', '')}\n"
                    f"**To:** {message.get('to', '')}\n"
                    f"**Date:** {message.get('date', '')}\n\n"
                    f"---\n\n"
                    f"{message.get('body', '')}"
                )

            filepath.write_text(content, encoding='utf-8')

        print(f"Exported: {filepath}", file=sys.stderr)
        return str(filepath)

    def export_thread(
        self,
        thread_id: str,
        output_dir: str,
        format: str = 'md'
    ) -> str:
        """Export full thread to file.

        Args:
            thread_id: Thread ID
            output_dir: Output directory
            format: 'txt' or 'md'

        Returns:
            Path to exported file
        """
        output_path = Path(output_dir)
        output_path.mkdir(parents=True, exist_ok=True)

        thread = self.get_thread(thread_id, format='full')
        messages = thread.get('messages', [])

        if not messages:
            raise GmailNotFoundError(f"Thread not found or empty: {thread_id}")

        # Use first message for filename
        first_msg = messages[0]
        filename = self._build_filename(
            first_msg.get('date', ''),
            first_msg.get('subject', ''),
            format,
            suffix='_thread'
        )
        filepath = output_path / filename

        if format == 'txt':
            parts = []
            for msg in messages:
                parts.append(
                    f"From: {msg.get('from', '')}\n"
                    f"To: {msg.get('to', '')}\n"
                    f"Date: {msg.get('date', '')}\n"
                    f"\n{msg.get('body', '')}\n"
                    f"\n{'=' * 60}\n"
                )
            content = '\n'.join(parts)
        else:  # md
            parts = [f"# {first_msg.get('subject', 'No Subject')}\n"]
            for i, msg in enumerate(messages, 1):
                parts.append(
                    f"\n## Message {i}\n\n"
                    f"**From:** {msg.get('from', '')}\n"
                    f"**To:** {msg.get('to', '')}\n"
                    f"**Date:** {msg.get('date', '')}\n\n"
                    f"---\n\n"
                    f"{msg.get('body', '')}\n"
                )
            content = '\n'.join(parts)

        filepath.write_text(content, encoding='utf-8')
        print(f"Exported thread ({len(messages)} messages): {filepath}", file=sys.stderr)
        return str(filepath)

    def export_attachments(self, message_id: str, output_dir: str) -> List[str]:
        """Download and save all attachments from a message.

        Args:
            message_id: Message ID
            output_dir: Output directory

        Returns:
            List of saved file paths
        """
        output_path = Path(output_dir)
        output_path.mkdir(parents=True, exist_ok=True)

        message = self.get_message(message_id, format='full')
        attachments = message.get('attachments', [])

        if not attachments:
            print("No attachments found", file=sys.stderr)
            return []

        saved = []
        for att in attachments:
            if not att.get('attachmentId'):
                continue

            data = self.get_attachment(message_id, att['attachmentId'])
            filename = att.get('filename', 'attachment')
            filepath = output_path / filename

            # Handle duplicate filenames
            counter = 1
            while filepath.exists():
                stem = Path(filename).stem
                suffix = Path(filename).suffix
                filepath = output_path / f"{stem}_{counter}{suffix}"
                counter += 1

            filepath.write_bytes(data)
            saved.append(str(filepath))
            print(f"Saved: {filepath}", file=sys.stderr)

        return saved

    def _build_filename(self, date_str: str, subject: str, ext: str, suffix: str = '') -> str:
        """Build filename from date and subject."""
        # Parse date
        try:
            # Gmail date format: "Wed, 1 Jan 2025 12:00:00 +0000"
            for fmt in ['%a, %d %b %Y %H:%M:%S %z', '%d %b %Y %H:%M:%S %z']:
                try:
                    dt = datetime.strptime(date_str.strip(), fmt)
                    date_part = dt.strftime('%Y%m%d')
                    break
                except ValueError:
                    continue
            else:
                date_part = datetime.now().strftime('%Y%m%d')
        except Exception:
            date_part = datetime.now().strftime('%Y%m%d')

        # Sanitize subject
        safe_subject = re.sub(r'[^\w\s-]', '', subject or 'no-subject')
        safe_subject = re.sub(r'\s+', '_', safe_subject)[:50]

        return f"{date_part}_{safe_subject}{suffix}.{ext}"


# ==============================================================================
# Tasks Client
# ==============================================================================

class TasksClient:
    """Client for interacting with Google Tasks API."""

    def __init__(self, service=None):
        """Initialize Tasks client.

        Args:
            service: Optional Tasks API service. If not provided, will authenticate.
        """
        self.service = service or build_tasks_service()

    def _handle_error(self, error: HttpError) -> None:
        """Convert Tasks API errors to custom exceptions."""
        status = error.resp.status
        try:
            reason = json.loads(error.content).get('error', {}).get('message', str(error))
        except (json.JSONDecodeError, AttributeError):
            reason = str(error)

        if status == 404:
            raise TasksNotFoundError(f"Resource not found: {reason}")
        else:
            raise TasksError(f"Tasks API error ({status}): {reason}")

    def _request_with_retry(self, request, max_retries: int = 3):
        """Execute request with automatic retry."""
        for attempt in range(max_retries):
            try:
                return request.execute()
            except HttpError as e:
                if e.resp.status == 429 and attempt < max_retries - 1:
                    retry_after = int(e.resp.get('Retry-After', 2 ** attempt))
                    print(f"Rate limited, retrying in {retry_after}s...", file=sys.stderr)
                    time.sleep(retry_after)
                else:
                    self._handle_error(e)

    # ==================== Task List Operations ====================

    def list_task_lists(self, max_results: int = 100) -> List[Dict]:
        """List all task lists."""
        lists = []
        page_token = None

        while len(lists) < max_results:
            request = self.service.tasklists().list(
                maxResults=min(max_results - len(lists), 100),
                pageToken=page_token
            )
            response = self._request_with_retry(request)

            batch = response.get('items', [])
            if not batch:
                break

            lists.extend(batch)

            page_token = response.get('nextPageToken')
            if not page_token:
                break

        return lists[:max_results]

    def get_task_list(self, tasklist_id: str) -> Dict:
        """Get task list details."""
        request = self.service.tasklists().get(tasklist=tasklist_id)
        return self._request_with_retry(request)

    def create_task_list(self, title: str) -> Dict:
        """Create a new task list."""
        request = self.service.tasklists().insert(body={'title': title})
        return self._request_with_retry(request)

    def update_task_list(self, tasklist_id: str, title: str) -> Dict:
        """Update task list title."""
        request = self.service.tasklists().update(
            tasklist=tasklist_id,
            body={'id': tasklist_id, 'title': title}
        )
        return self._request_with_retry(request)

    def delete_task_list(self, tasklist_id: str) -> None:
        """Delete a task list."""
        request = self.service.tasklists().delete(tasklist=tasklist_id)
        self._request_with_retry(request)

    # ==================== Task Operations ====================

    def list_tasks(
        self,
        tasklist_id: str = '@default',
        show_completed: bool = False,
        show_deleted: bool = False,
        show_hidden: bool = False,
        due_min: str = None,
        due_max: str = None,
        max_results: int = 100
    ) -> List[Dict]:
        """List tasks in a list.

        Args:
            tasklist_id: Task list ID (use '@default' for primary list)
            show_completed: Include completed tasks
            show_deleted: Include deleted tasks
            show_hidden: Include hidden tasks
            due_min: Minimum due date (RFC 3339)
            due_max: Maximum due date (RFC 3339)
            max_results: Maximum results

        Returns:
            List of tasks
        """
        tasks = []
        page_token = None

        while len(tasks) < max_results:
            request = self.service.tasks().list(
                tasklist=tasklist_id,
                maxResults=min(max_results - len(tasks), 100),
                pageToken=page_token,
                showCompleted=show_completed,
                showDeleted=show_deleted,
                showHidden=show_hidden,
                dueMin=due_min,
                dueMax=due_max
            )
            response = self._request_with_retry(request)

            batch = response.get('items', [])
            if not batch:
                break

            tasks.extend(batch)

            page_token = response.get('nextPageToken')
            if not page_token:
                break

        return tasks[:max_results]

    def get_task(self, tasklist_id: str, task_id: str) -> Dict:
        """Get task details."""
        request = self.service.tasks().get(
            tasklist=tasklist_id,
            task=task_id
        )
        return self._request_with_retry(request)

    def create_task(
        self,
        tasklist_id: str,
        title: str,
        notes: str = None,
        due: str = None,
        parent: str = None,
        previous: str = None
    ) -> Dict:
        """Create a new task.

        Args:
            tasklist_id: Task list ID
            title: Task title
            notes: Task notes/description
            due: Due date (RFC 3339 or YYYY-MM-DD)
            parent: Parent task ID (for subtasks)
            previous: Task ID to insert after

        Returns:
            Created task
        """
        body = {'title': title}

        if notes:
            body['notes'] = notes
        if due:
            # Convert simple date to RFC 3339
            if len(due) == 10:  # YYYY-MM-DD
                due = f"{due}T00:00:00.000Z"
            body['due'] = due

        request = self.service.tasks().insert(
            tasklist=tasklist_id,
            body=body,
            parent=parent,
            previous=previous
        )
        return self._request_with_retry(request)

    def update_task(
        self,
        tasklist_id: str,
        task_id: str,
        title: str = None,
        notes: str = None,
        due: str = None,
        status: str = None
    ) -> Dict:
        """Update an existing task.

        Args:
            tasklist_id: Task list ID
            task_id: Task ID
            title: New title
            notes: New notes
            due: New due date
            status: 'needsAction' or 'completed'

        Returns:
            Updated task
        """
        # Get current task
        task = self.get_task(tasklist_id, task_id)

        if title is not None:
            task['title'] = title
        if notes is not None:
            task['notes'] = notes
        if due is not None:
            if len(due) == 10:
                due = f"{due}T00:00:00.000Z"
            task['due'] = due
        if status is not None:
            task['status'] = status
            if status == 'completed':
                task['completed'] = datetime.now(timezone.utc).isoformat()

        request = self.service.tasks().update(
            tasklist=tasklist_id,
            task=task_id,
            body=task
        )
        return self._request_with_retry(request)

    def complete_task(self, tasklist_id: str, task_id: str) -> Dict:
        """Mark task as completed."""
        return self.update_task(tasklist_id, task_id, status='completed')

    def uncomplete_task(self, tasklist_id: str, task_id: str) -> Dict:
        """Mark task as not completed."""
        return self.update_task(tasklist_id, task_id, status='needsAction')

    def delete_task(self, tasklist_id: str, task_id: str) -> None:
        """Delete a task."""
        request = self.service.tasks().delete(
            tasklist=tasklist_id,
            task=task_id
        )
        self._request_with_retry(request)

    def move_task(
        self,
        tasklist_id: str,
        task_id: str,
        parent: str = None,
        previous: str = None
    ) -> Dict:
        """Move task within a list.

        Args:
            tasklist_id: Task list ID
            task_id: Task ID to move
            parent: New parent task ID (for making subtask)
            previous: Task ID to insert after

        Returns:
            Moved task
        """
        request = self.service.tasks().move(
            tasklist=tasklist_id,
            task=task_id,
            parent=parent,
            previous=previous
        )
        return self._request_with_retry(request)

    def clear_completed(self, tasklist_id: str) -> None:
        """Clear all completed tasks from a list."""
        request = self.service.tasks().clear(tasklist=tasklist_id)
        self._request_with_retry(request)


# ==============================================================================
# CLI
# ==============================================================================

def build_parser() -> argparse.ArgumentParser:
    """Build the argument parser."""
    parser = argparse.ArgumentParser(
        description="Gmail and Google Tasks CLI - Manage emails, labels, drafts, and tasks",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog=__doc__
    )

    subparsers = parser.add_subparsers(dest="category", help="Command category")

    # ==================== Messages ====================
    messages_parser = subparsers.add_parser("messages", help="Email message operations")
    messages_sub = messages_parser.add_subparsers(dest="action")

    # messages list
    list_msg = messages_sub.add_parser("list", help="List messages")
    list_msg.add_argument("--label", "-l", action="append", help="Filter by label (can repeat)")
    list_msg.add_argument("--query", "-q", help="Gmail search query")
    list_msg.add_argument("--limit", "-n", type=int, default=20, help="Max results (default: 20)")
    list_msg.add_argument("--include-spam-trash", action="store_true", help="Include spam/trash")

    # messages search
    search_msg = messages_sub.add_parser("search", help="Search messages")
    search_msg.add_argument("query", help="Gmail search query")
    search_msg.add_argument("--limit", "-n", type=int, default=20, help="Max results")

    # messages get
    get_msg = messages_sub.add_parser("get", help="Get message content")
    get_msg.add_argument("message_id", help="Message ID")
    get_msg.add_argument("--format", choices=["full", "metadata", "raw"], default="full")

    # messages thread
    thread_msg = messages_sub.add_parser("thread", help="Get full thread")
    thread_msg.add_argument("thread_id", help="Thread ID")

    # messages mark-read
    mark_read = messages_sub.add_parser("mark-read", help="Mark as read")
    mark_read.add_argument("message_ids", nargs="+", help="Message IDs")

    # messages mark-unread
    mark_unread = messages_sub.add_parser("mark-unread", help="Mark as unread")
    mark_unread.add_argument("message_ids", nargs="+", help="Message IDs")

    # messages star
    star_msg = messages_sub.add_parser("star", help="Star messages")
    star_msg.add_argument("message_ids", nargs="+", help="Message IDs")

    # messages unstar
    unstar_msg = messages_sub.add_parser("unstar", help="Unstar messages")
    unstar_msg.add_argument("message_ids", nargs="+", help="Message IDs")

    # messages archive
    archive_msg = messages_sub.add_parser("archive", help="Archive messages")
    archive_msg.add_argument("message_ids", nargs="+", help="Message IDs")

    # messages trash
    trash_msg = messages_sub.add_parser("trash", help="Move to trash")
    trash_msg.add_argument("message_ids", nargs="+", help="Message IDs")

    # messages delete
    delete_msg = messages_sub.add_parser("delete", help="Permanently delete")
    delete_msg.add_argument("message_ids", nargs="+", help="Message IDs")
    delete_msg.add_argument("--force", "-f", action="store_true", help="Skip confirmation")

    # ==================== Labels ====================
    labels_parser = subparsers.add_parser("labels", help="Label operations")
    labels_sub = labels_parser.add_subparsers(dest="action")

    # labels list
    labels_sub.add_parser("list", help="List all labels")

    # labels create
    create_label = labels_sub.add_parser("create", help="Create label")
    create_label.add_argument("name", help="Label name")
    create_label.add_argument("--bg-color", help="Background color (hex)")
    create_label.add_argument("--text-color", help="Text color (hex)")

    # labels delete
    delete_label = labels_sub.add_parser("delete", help="Delete label")
    delete_label.add_argument("label_id", help="Label ID or name")

    # labels apply
    apply_label = labels_sub.add_parser("apply", help="Apply labels to message")
    apply_label.add_argument("message_id", help="Message ID")
    apply_label.add_argument("--labels", "-l", nargs="+", required=True, help="Labels to apply")

    # labels remove
    remove_label = labels_sub.add_parser("remove", help="Remove labels from message")
    remove_label.add_argument("message_id", help="Message ID")
    remove_label.add_argument("--labels", "-l", nargs="+", required=True, help="Labels to remove")

    # ==================== Drafts ====================
    drafts_parser = subparsers.add_parser("drafts", help="Draft operations")
    drafts_sub = drafts_parser.add_subparsers(dest="action")

    # drafts list
    list_drafts = drafts_sub.add_parser("list", help="List drafts")
    list_drafts.add_argument("--limit", "-n", type=int, default=20, help="Max results")

    # drafts create
    create_draft = drafts_sub.add_parser("create", help="Create draft")
    create_draft.add_argument("--to", "-t", nargs="+", required=True, help="Recipients")
    create_draft.add_argument("--subject", "-s", required=True, help="Subject")
    create_draft.add_argument("--body", "-b", help="Body (or use --body-file)")
    create_draft.add_argument("--body-file", help="Read body from file")
    create_draft.add_argument("--cc", nargs="+", help="CC recipients")
    create_draft.add_argument("--bcc", nargs="+", help="BCC recipients")
    create_draft.add_argument("--html", action="store_true", help="Body is HTML")
    create_draft.add_argument("--attach", nargs="+", help="File paths to attach")

    # drafts update
    update_draft = drafts_sub.add_parser("update", help="Update draft")
    update_draft.add_argument("draft_id", help="Draft ID")
    update_draft.add_argument("--to", "-t", nargs="+", help="Recipients")
    update_draft.add_argument("--subject", "-s", help="Subject")
    update_draft.add_argument("--body", "-b", help="Body")
    update_draft.add_argument("--body-file", help="Read body from file")

    # drafts delete
    del_draft = drafts_sub.add_parser("delete", help="Delete draft")
    del_draft.add_argument("draft_id", help="Draft ID")

    # drafts send
    send_draft = drafts_sub.add_parser("send", help="Send draft")
    send_draft.add_argument("draft_id", help="Draft ID")

    # ==================== Send ====================
    send_parser = subparsers.add_parser("send", help="Send email operations")
    send_sub = send_parser.add_subparsers(dest="action")

    # send new
    send_new = send_sub.add_parser("new", help="Send new email")
    send_new.add_argument("--to", "-t", nargs="+", required=True, help="Recipients")
    send_new.add_argument("--subject", "-s", required=True, help="Subject")
    send_new.add_argument("--body", "-b", help="Body")
    send_new.add_argument("--body-file", help="Read body from file")
    send_new.add_argument("--cc", nargs="+", help="CC recipients")
    send_new.add_argument("--bcc", nargs="+", help="BCC recipients")
    send_new.add_argument("--html", action="store_true", help="Body is HTML")
    send_new.add_argument("--attach", nargs="+", help="Files to attach")

    # send reply
    send_reply = send_sub.add_parser("reply", help="Reply to message")
    send_reply.add_argument("message_id", help="Message ID to reply to")
    send_reply.add_argument("--body", "-b", help="Reply body")
    send_reply.add_argument("--body-file", help="Read body from file")
    send_reply.add_argument("--html", action="store_true", help="Body is HTML")
    send_reply.add_argument("--attach", nargs="+", help="Files to attach")

    # send reply-all
    send_reply_all = send_sub.add_parser("reply-all", help="Reply to all")
    send_reply_all.add_argument("message_id", help="Message ID to reply to")
    send_reply_all.add_argument("--body", "-b", help="Reply body")
    send_reply_all.add_argument("--body-file", help="Read body from file")
    send_reply_all.add_argument("--html", action="store_true", help="Body is HTML")
    send_reply_all.add_argument("--attach", nargs="+", help="Files to attach")

    # send forward
    send_forward = send_sub.add_parser("forward", help="Forward message")
    send_forward.add_argument("message_id", help="Message ID to forward")
    send_forward.add_argument("--to", "-t", nargs="+", required=True, help="Forward to")
    send_forward.add_argument("--body", "-b", help="Optional prepended body")

    # ==================== Export ====================
    export_parser = subparsers.add_parser("export", help="Export operations")
    export_sub = export_parser.add_subparsers(dest="action")

    # export messages
    export_msgs = export_sub.add_parser("messages", help="Export messages matching query")
    export_msgs.add_argument("query", help="Gmail search query")
    export_msgs.add_argument("--output-dir", "-o", required=True, help="Output directory")
    export_msgs.add_argument("--format", "-f", choices=["eml", "txt", "md"], default="md")
    export_msgs.add_argument("--limit", "-n", type=int, default=100, help="Max messages")

    # export thread
    export_thread = export_sub.add_parser("thread", help="Export thread")
    export_thread.add_argument("thread_id", help="Thread ID")
    export_thread.add_argument("--output-dir", "-o", required=True, help="Output directory")
    export_thread.add_argument("--format", "-f", choices=["txt", "md"], default="md")

    # export attachments
    export_attach = export_sub.add_parser("attachments", help="Export attachments")
    export_attach.add_argument("message_id", help="Message ID")
    export_attach.add_argument("--output-dir", "-o", required=True, help="Output directory")

    # ==================== Tasks ====================
    tasks_parser = subparsers.add_parser("tasks", help="Google Tasks operations")
    tasks_sub = tasks_parser.add_subparsers(dest="action")

    # tasks lists
    tasks_sub.add_parser("lists", help="List all task lists")

    # tasks list
    tasks_list = tasks_sub.add_parser("list", help="List tasks in a list")
    tasks_list.add_argument("tasklist_id", nargs="?", default="@default", help="Task list ID")
    tasks_list.add_argument("--show-completed", action="store_true", help="Include completed")
    tasks_list.add_argument("--due-before", help="Due before date (YYYY-MM-DD)")
    tasks_list.add_argument("--due-after", help="Due after date (YYYY-MM-DD)")
    tasks_list.add_argument("--limit", "-n", type=int, default=100, help="Max results")

    # tasks create
    tasks_create = tasks_sub.add_parser("create", help="Create task")
    tasks_create.add_argument("tasklist_id", nargs="?", default="@default", help="Task list ID")
    tasks_create.add_argument("--title", "-t", required=True, help="Task title")
    tasks_create.add_argument("--notes", "-n", help="Task notes")
    tasks_create.add_argument("--due", "-d", help="Due date (YYYY-MM-DD)")

    # tasks update
    tasks_update = tasks_sub.add_parser("update", help="Update task")
    tasks_update.add_argument("task_id", help="Task ID")
    tasks_update.add_argument("--tasklist", default="@default", help="Task list ID")
    tasks_update.add_argument("--title", "-t", help="New title")
    tasks_update.add_argument("--notes", "-n", help="New notes")
    tasks_update.add_argument("--due", "-d", help="New due date")

    # tasks complete
    tasks_complete = tasks_sub.add_parser("complete", help="Mark task complete")
    tasks_complete.add_argument("task_id", help="Task ID")
    tasks_complete.add_argument("--tasklist", default="@default", help="Task list ID")

    # tasks uncomplete
    tasks_uncomplete = tasks_sub.add_parser("uncomplete", help="Mark task incomplete")
    tasks_uncomplete.add_argument("task_id", help="Task ID")
    tasks_uncomplete.add_argument("--tasklist", default="@default", help="Task list ID")

    # tasks delete
    tasks_delete = tasks_sub.add_parser("delete", help="Delete task")
    tasks_delete.add_argument("task_id", help="Task ID")
    tasks_delete.add_argument("--tasklist", default="@default", help="Task list ID")

    # tasks clear
    tasks_clear = tasks_sub.add_parser("clear", help="Clear completed tasks")
    tasks_clear.add_argument("tasklist_id", nargs="?", default="@default", help="Task list ID")

    # tasks create-list
    tasks_create_list = tasks_sub.add_parser("create-list", help="Create task list")
    tasks_create_list.add_argument("title", help="List title")

    # tasks delete-list
    tasks_delete_list = tasks_sub.add_parser("delete-list", help="Delete task list")
    tasks_delete_list.add_argument("tasklist_id", help="Task list ID")

    return parser


def get_body(args) -> str:
    """Get body from args (--body or --body-file)."""
    if hasattr(args, 'body_file') and args.body_file:
        with open(args.body_file, 'r') as f:
            return f.read()
    return getattr(args, 'body', '') or ''


def main():
    parser = build_parser()
    args = parser.parse_args()

    if not args.category:
        parser.print_help()
        sys.exit(1)

    try:
        # Initialize clients
        gmail = GmailClient()
        tasks = TasksClient()

        # ==================== Messages ====================
        if args.category == "messages":
            if not args.action:
                parser.parse_args(["messages", "--help"])
                sys.exit(1)

            if args.action == "list":
                messages = gmail.list_messages(
                    query=args.query,
                    label_ids=args.label,
                    max_results=args.limit,
                    include_spam_trash=args.include_spam_trash
                )
                print(json.dumps(messages, indent=2))

            elif args.action == "search":
                messages = gmail.search(args.query, max_results=args.limit)
                print(json.dumps(messages, indent=2))

            elif args.action == "get":
                message = gmail.get_message(args.message_id, format=args.format)
                print(json.dumps(message, indent=2))

            elif args.action == "thread":
                thread = gmail.get_thread(args.thread_id)
                print(json.dumps(thread, indent=2))

            elif args.action == "mark-read":
                gmail.mark_read(args.message_ids)
                print(f"Marked {len(args.message_ids)} message(s) as read", file=sys.stderr)

            elif args.action == "mark-unread":
                gmail.mark_unread(args.message_ids)
                print(f"Marked {len(args.message_ids)} message(s) as unread", file=sys.stderr)

            elif args.action == "star":
                gmail.star(args.message_ids)
                print(f"Starred {len(args.message_ids)} message(s)", file=sys.stderr)

            elif args.action == "unstar":
                gmail.unstar(args.message_ids)
                print(f"Unstarred {len(args.message_ids)} message(s)", file=sys.stderr)

            elif args.action == "archive":
                gmail.archive(args.message_ids)
                print(f"Archived {len(args.message_ids)} message(s)", file=sys.stderr)

            elif args.action == "trash":
                for msg_id in args.message_ids:
                    gmail.trash_message(msg_id)
                print(f"Moved {len(args.message_ids)} message(s) to trash", file=sys.stderr)

            elif args.action == "delete":
                if not args.force:
                    print(f"WARNING: This will PERMANENTLY delete {len(args.message_ids)} message(s).", file=sys.stderr)
                    print("Use --force to confirm.", file=sys.stderr)
                    sys.exit(1)
                for msg_id in args.message_ids:
                    gmail.delete_message(msg_id)
                print(f"Permanently deleted {len(args.message_ids)} message(s)", file=sys.stderr)

        # ==================== Labels ====================
        elif args.category == "labels":
            if not args.action:
                parser.parse_args(["labels", "--help"])
                sys.exit(1)

            if args.action == "list":
                labels = gmail.list_labels()
                print(json.dumps(labels, indent=2))

            elif args.action == "create":
                label = gmail.create_label(
                    args.name,
                    background_color=args.bg_color,
                    text_color=args.text_color
                )
                print(json.dumps(label, indent=2))

            elif args.action == "delete":
                label_id = gmail.resolve_label(args.label_id)
                gmail.delete_label(label_id)
                print(f"Deleted label: {args.label_id}", file=sys.stderr)

            elif args.action == "apply":
                label_ids = [gmail.resolve_label(l) for l in args.labels]
                gmail.modify_message(args.message_id, add_labels=label_ids)
                print(f"Applied labels to message", file=sys.stderr)

            elif args.action == "remove":
                label_ids = [gmail.resolve_label(l) for l in args.labels]
                gmail.modify_message(args.message_id, remove_labels=label_ids)
                print(f"Removed labels from message", file=sys.stderr)

        # ==================== Drafts ====================
        elif args.category == "drafts":
            if not args.action:
                parser.parse_args(["drafts", "--help"])
                sys.exit(1)

            if args.action == "list":
                drafts = gmail.list_drafts(max_results=args.limit)
                print(json.dumps(drafts, indent=2))

            elif args.action == "create":
                body = get_body(args)
                draft = gmail.create_draft(
                    to=args.to,
                    subject=args.subject,
                    body=body,
                    cc=args.cc,
                    bcc=args.bcc,
                    html=args.html,
                    attachments=args.attach
                )
                print(json.dumps(draft, indent=2))

            elif args.action == "update":
                body = get_body(args) if args.body or getattr(args, 'body_file', None) else None
                draft = gmail.update_draft(
                    args.draft_id,
                    to=args.to,
                    subject=args.subject,
                    body=body
                )
                print(json.dumps(draft, indent=2))

            elif args.action == "delete":
                gmail.delete_draft(args.draft_id)
                print(f"Deleted draft: {args.draft_id}", file=sys.stderr)

            elif args.action == "send":
                result = gmail.send_draft(args.draft_id)
                print(json.dumps(result, indent=2))

        # ==================== Send ====================
        elif args.category == "send":
            if not args.action:
                parser.parse_args(["send", "--help"])
                sys.exit(1)

            if args.action == "new":
                body = get_body(args)
                result = gmail.send_message(
                    to=args.to,
                    subject=args.subject,
                    body=body,
                    cc=args.cc,
                    bcc=args.bcc,
                    html=args.html,
                    attachments=args.attach
                )
                print(json.dumps(result, indent=2))
                print(f"Sent email to: {', '.join(args.to)}", file=sys.stderr)

            elif args.action == "reply":
                body = get_body(args)
                result = gmail.reply(
                    args.message_id,
                    body=body,
                    html=args.html,
                    attachments=args.attach,
                    reply_all=False
                )
                print(json.dumps(result, indent=2))
                print("Sent reply", file=sys.stderr)

            elif args.action == "reply-all":
                body = get_body(args)
                result = gmail.reply(
                    args.message_id,
                    body=body,
                    html=args.html,
                    attachments=args.attach,
                    reply_all=True
                )
                print(json.dumps(result, indent=2))
                print("Sent reply-all", file=sys.stderr)

            elif args.action == "forward":
                result = gmail.forward(
                    args.message_id,
                    to=args.to,
                    body=args.body
                )
                print(json.dumps(result, indent=2))
                print(f"Forwarded to: {', '.join(args.to)}", file=sys.stderr)

        # ==================== Export ====================
        elif args.category == "export":
            if not args.action:
                parser.parse_args(["export", "--help"])
                sys.exit(1)

            if args.action == "messages":
                messages = gmail.search(args.query, max_results=args.limit)
                exported = []
                for msg in messages:
                    path = gmail.export_message(msg['id'], args.output_dir, args.format)
                    exported.append(path)
                print(json.dumps({"exported": exported, "count": len(exported)}, indent=2))

            elif args.action == "thread":
                path = gmail.export_thread(args.thread_id, args.output_dir, args.format)
                print(json.dumps({"exported": path}, indent=2))

            elif args.action == "attachments":
                paths = gmail.export_attachments(args.message_id, args.output_dir)
                print(json.dumps({"exported": paths, "count": len(paths)}, indent=2))

        # ==================== Tasks ====================
        elif args.category == "tasks":
            if not args.action:
                parser.parse_args(["tasks", "--help"])
                sys.exit(1)

            if args.action == "lists":
                lists = tasks.list_task_lists()
                print(json.dumps(lists, indent=2))

            elif args.action == "list":
                due_min = f"{args.due_after}T00:00:00.000Z" if args.due_after else None
                due_max = f"{args.due_before}T23:59:59.999Z" if args.due_before else None

                task_list = tasks.list_tasks(
                    args.tasklist_id,
                    show_completed=args.show_completed,
                    due_min=due_min,
                    due_max=due_max,
                    max_results=args.limit
                )
                print(json.dumps(task_list, indent=2))

            elif args.action == "create":
                task = tasks.create_task(
                    args.tasklist_id,
                    title=args.title,
                    notes=args.notes,
                    due=args.due
                )
                print(json.dumps(task, indent=2))
                print(f"Created task: {args.title}", file=sys.stderr)

            elif args.action == "update":
                task = tasks.update_task(
                    args.tasklist,
                    args.task_id,
                    title=args.title,
                    notes=args.notes,
                    due=args.due
                )
                print(json.dumps(task, indent=2))

            elif args.action == "complete":
                task = tasks.complete_task(args.tasklist, args.task_id)
                print(json.dumps(task, indent=2))
                print(f"Marked task complete", file=sys.stderr)

            elif args.action == "uncomplete":
                task = tasks.uncomplete_task(args.tasklist, args.task_id)
                print(json.dumps(task, indent=2))
                print(f"Marked task incomplete", file=sys.stderr)

            elif args.action == "delete":
                tasks.delete_task(args.tasklist, args.task_id)
                print(f"Deleted task: {args.task_id}", file=sys.stderr)

            elif args.action == "clear":
                tasks.clear_completed(args.tasklist_id)
                print(f"Cleared completed tasks", file=sys.stderr)

            elif args.action == "create-list":
                task_list = tasks.create_task_list(args.title)
                print(json.dumps(task_list, indent=2))
                print(f"Created task list: {args.title}", file=sys.stderr)

            elif args.action == "delete-list":
                tasks.delete_task_list(args.tasklist_id)
                print(f"Deleted task list: {args.tasklist_id}", file=sys.stderr)

    except (GmailError, TasksError) as e:
        print(f"Error: {e}", file=sys.stderr)
        sys.exit(1)
    except KeyboardInterrupt:
        print("\nInterrupted", file=sys.stderr)
        sys.exit(130)


if __name__ == "__main__":
    main()

#!/usr/bin/env python3
"""PandaDoc API Integration Script.

Create, send, and manage documents via PandaDoc API.

Usage (CLI):
    python tool/pandadoc_api.py list-templates [--tag TAG]
    python tool/pandadoc_api.py get-template <template_id>
    python tool/pandadoc_api.py create-document --template-id ID --name NAME --recipients JSON [--tokens JSON]
    python tool/pandadoc_api.py send-document <document_id> [--message MSG]
    python tool/pandadoc_api.py document-status <document_id>
    python tool/pandadoc_api.py download-document <document_id> [--output PATH]
    python tool/pandadoc_api.py list-documents [--status STATUS] [--limit N]
    python tool/pandadoc_api.py delete-document <document_id>
    python tool/pandadoc_api.py delete-template <template_id>

Usage (Module):
    from tool.pandadoc_api import PandaDocClient
    client = PandaDocClient()
    templates = client.list_templates()
"""

import argparse
import json
import sys
import time
from pathlib import Path
from typing import Any

import pandadoc_client
from pandadoc_client.api import documents_api, templates_api

from .config import get_api_key


class PandaDocClient:
    """PandaDoc API client wrapper."""

    def __init__(self, api_key: str | None = None):
        """Initialize client with API key.

        Args:
            api_key: PandaDoc API key. If not provided, loads from environment.
        """
        self.api_key = api_key or get_api_key("PANDADOC_API_KEY")
        if not self.api_key:
            raise ValueError(
                "PANDADOC_API_KEY not found. "
                "Add it to ~/.config/cc-plugins/.env or set environment variable."
            )

        self.config = pandadoc_client.Configuration(
            host="https://api.pandadoc.com",
            api_key={"apiKey": f"API-Key {self.api_key}"},
        )

    def _get_api_client(self):
        """Get configured API client."""
        return pandadoc_client.ApiClient(self.config)

    # Template operations

    def list_templates(self, tag: str | None = None) -> list[dict]:
        """List available templates.

        Args:
            tag: Optional tag to filter templates.

        Returns:
            List of template dictionaries.
        """
        with self._get_api_client() as api_client:
            api = templates_api.TemplatesApi(api_client)
            kwargs = {}
            if tag:
                kwargs["tag"] = [tag]
            response = api.list_templates(**kwargs)
            return [self._template_to_dict(t) for t in response.results]

    def get_template(self, template_id: str) -> dict:
        """Get template details.

        Args:
            template_id: Template UUID.

        Returns:
            Template details dictionary.
        """
        with self._get_api_client() as api_client:
            api = templates_api.TemplatesApi(api_client)
            response = api.details_template(template_id)
            return self._template_details_to_dict(response)

    def delete_template(self, template_id: str) -> bool:
        """Delete a template.

        Args:
            template_id: Template UUID.

        Returns:
            True if deleted successfully.
        """
        with self._get_api_client() as api_client:
            api = templates_api.TemplatesApi(api_client)
            api.delete_template(template_id)
            return True

    # Document operations

    def create_document(
        self,
        template_id: str,
        name: str,
        recipients: list[dict],
        tokens: dict | None = None,
        folder_uuid: str | None = None,
    ) -> dict:
        """Create a document from a template.

        Args:
            template_id: Template UUID to use.
            name: Document name.
            recipients: List of recipient dicts with email, first_name, last_name, role.
            tokens: Dict of token name -> value for template variables.
            folder_uuid: Optional folder UUID to place document in.

        Returns:
            Created document details.
        """
        with self._get_api_client() as api_client:
            api = documents_api.DocumentsApi(api_client)

            # Build recipients list
            recipient_list = []
            for r in recipients:
                recipient_list.append({
                    "email": r.get("email"),
                    "first_name": r.get("first_name", ""),
                    "last_name": r.get("last_name", ""),
                    "role": r.get("role", ""),
                })

            # Build tokens list
            token_list = []
            if tokens:
                for name_key, value in tokens.items():
                    token_list.append({"name": name_key, "value": str(value)})

            # Build request
            request_data = {
                "name": name,
                "template_uuid": template_id,
                "recipients": recipient_list,
            }
            if token_list:
                request_data["tokens"] = token_list
            if folder_uuid:
                request_data["folder_uuid"] = folder_uuid

            response = api.create_document(
                document_create_request=request_data
            )
            return self._document_to_dict(response)

    def send_document(self, document_id: str, message: str | None = None, subject: str | None = None) -> dict:
        """Send a document for signing.

        Args:
            document_id: Document UUID.
            message: Optional message to include in email.
            subject: Optional email subject.

        Returns:
            Send response details.
        """
        # Wait for document to be ready (not in draft.uploaded state)
        self._wait_for_document_ready(document_id)

        with self._get_api_client() as api_client:
            api = documents_api.DocumentsApi(api_client)

            request_data = {}
            if message:
                request_data["message"] = message
            if subject:
                request_data["subject"] = subject

            response = api.send_document(
                document_id,
                document_send_request=request_data if request_data else None,
            )
            return {"status": "sent", "document_id": document_id}

    def _wait_for_document_ready(self, document_id: str, max_wait: int = 30) -> None:
        """Wait for document to be ready for sending.

        Args:
            document_id: Document UUID.
            max_wait: Maximum seconds to wait.

        Raises:
            TimeoutError: If document not ready within max_wait.
        """
        start = time.time()
        while time.time() - start < max_wait:
            status = self.document_status(document_id)
            if status.get("status") == "document.draft":
                return
            if status.get("status") not in ("document.uploaded", "document.draft"):
                # Already sent or in another state
                return
            time.sleep(1)
        raise TimeoutError(f"Document {document_id} not ready after {max_wait}s")

    def document_status(self, document_id: str) -> dict:
        """Get document status.

        Args:
            document_id: Document UUID.

        Returns:
            Document status details.
        """
        with self._get_api_client() as api_client:
            api = documents_api.DocumentsApi(api_client)
            response = api.status_document(document_id)
            return self._status_to_dict(response)

    def get_document(self, document_id: str) -> dict:
        """Get full document details.

        Args:
            document_id: Document UUID.

        Returns:
            Document details.
        """
        with self._get_api_client() as api_client:
            api = documents_api.DocumentsApi(api_client)
            response = api.details_document(document_id)
            return self._document_details_to_dict(response)

    def download_document(self, document_id: str, output_path: str | None = None) -> str:
        """Download document as PDF.

        Args:
            document_id: Document UUID.
            output_path: Path to save PDF. If None, uses document name.

        Returns:
            Path to downloaded file.
        """
        with self._get_api_client() as api_client:
            api = documents_api.DocumentsApi(api_client)

            # Get document details for name if no output path
            if not output_path:
                details = self.get_document(document_id)
                output_path = f"{details.get('name', document_id)}.pdf"

            response = api.download_document(document_id)

            # Write the PDF content
            output_file = Path(output_path)
            output_file.write_bytes(response)

            return str(output_file.absolute())

    def list_documents(
        self,
        status: str | None = None,
        limit: int = 50,
    ) -> list[dict]:
        """List documents.

        Args:
            status: Filter by status (draft, sent, completed, etc.).
            limit: Maximum number of documents to return.

        Returns:
            List of document dictionaries.
        """
        with self._get_api_client() as api_client:
            api = documents_api.DocumentsApi(api_client)

            kwargs = {"count": limit}
            if status:
                # Map friendly status names to API status values
                status_map = {
                    "draft": 0,
                    "sent": 1,
                    "completed": 2,
                    "viewed": 5,
                    "waiting_approval": 6,
                    "rejected": 8,
                    "waiting_pay": 10,
                }
                if status.lower() in status_map:
                    kwargs["status"] = status_map[status.lower()]

            response = api.list_documents(**kwargs)
            return [self._document_list_to_dict(d) for d in response.results]

    def delete_document(self, document_id: str) -> bool:
        """Delete a document.

        Args:
            document_id: Document UUID.

        Returns:
            True if deleted successfully.
        """
        with self._get_api_client() as api_client:
            api = documents_api.DocumentsApi(api_client)
            api.delete_document(document_id)
            return True

    # Helper methods for converting API responses to dicts

    def _template_to_dict(self, template: Any) -> dict:
        """Convert template response to dict."""
        return {
            "id": getattr(template, "id", None),
            "name": getattr(template, "name", None),
            "date_created": str(getattr(template, "date_created", "")),
            "date_modified": str(getattr(template, "date_modified", "")),
        }

    def _template_details_to_dict(self, template: Any) -> dict:
        """Convert template details response to dict."""
        result = self._template_to_dict(template)

        # Extract tokens/fields if available
        tokens = getattr(template, "tokens", [])
        if tokens:
            result["tokens"] = [
                {"name": getattr(t, "name", ""), "value": getattr(t, "value", "")}
                for t in tokens
            ]

        fields = getattr(template, "fields", [])
        if fields:
            result["fields"] = [
                {
                    "name": getattr(f, "name", ""),
                    "type": getattr(f, "type", ""),
                    "role": getattr(f, "role", ""),
                }
                for f in fields
            ]

        roles = getattr(template, "roles", [])
        if roles:
            result["roles"] = [
                {"name": getattr(r, "name", "")}
                for r in roles
            ]

        return result

    def _document_to_dict(self, document: Any) -> dict:
        """Convert document response to dict."""
        return {
            "id": getattr(document, "id", None),
            "name": getattr(document, "name", None),
            "status": getattr(document, "status", None),
            "date_created": str(getattr(document, "date_created", "")),
            "uuid": getattr(document, "uuid", None),
        }

    def _document_details_to_dict(self, document: Any) -> dict:
        """Convert document details response to dict."""
        result = self._document_to_dict(document)

        recipients = getattr(document, "recipients", [])
        if recipients:
            result["recipients"] = [
                {
                    "email": getattr(r, "email", ""),
                    "first_name": getattr(r, "first_name", ""),
                    "last_name": getattr(r, "last_name", ""),
                    "role": getattr(r, "role", ""),
                    "has_completed": getattr(r, "has_completed", False),
                }
                for r in recipients
            ]

        return result

    def _document_list_to_dict(self, document: Any) -> dict:
        """Convert document list item to dict."""
        return {
            "id": getattr(document, "id", None),
            "name": getattr(document, "name", None),
            "status": getattr(document, "status", None),
            "date_created": str(getattr(document, "date_created", "")),
            "date_modified": str(getattr(document, "date_modified", "")),
            "expiration_date": str(getattr(document, "expiration_date", "")),
        }

    def _status_to_dict(self, status: Any) -> dict:
        """Convert status response to dict."""
        return {
            "id": getattr(status, "id", None),
            "name": getattr(status, "name", None),
            "status": getattr(status, "status", None),
            "date_created": str(getattr(status, "date_created", "")),
            "date_modified": str(getattr(status, "date_modified", "")),
        }


def format_output(data: Any, output_format: str) -> str:
    """Format data for output.

    Args:
        data: Data to format.
        output_format: 'json' or 'text'.

    Returns:
        Formatted string.
    """
    if output_format == "json":
        return json.dumps(data, indent=2, default=str)

    # Text format
    if isinstance(data, list):
        if not data:
            return "No results found."
        lines = []
        for item in data:
            if isinstance(item, dict):
                lines.append(format_dict_as_text(item))
                lines.append("")
        return "\n".join(lines).strip()
    elif isinstance(data, dict):
        return format_dict_as_text(data)
    else:
        return str(data)


def format_dict_as_text(d: dict) -> str:
    """Format a dictionary as readable text."""
    lines = []
    for key, value in d.items():
        if isinstance(value, list):
            lines.append(f"{key}:")
            for item in value:
                if isinstance(item, dict):
                    for k, v in item.items():
                        lines.append(f"  - {k}: {v}")
                else:
                    lines.append(f"  - {item}")
        else:
            lines.append(f"{key}: {value}")
    return "\n".join(lines)


def main():
    """Main CLI entry point."""
    parser = argparse.ArgumentParser(
        description="PandaDoc API client",
        formatter_class=argparse.RawDescriptionHelpFormatter,
    )
    parser.add_argument(
        "--output-format",
        choices=["json", "text"],
        default="text",
        help="Output format (default: text)",
    )

    subparsers = parser.add_subparsers(dest="command", help="Command to run")

    # list-templates
    list_templates_parser = subparsers.add_parser(
        "list-templates", help="List available templates"
    )
    list_templates_parser.add_argument("--tag", help="Filter by tag")

    # get-template
    get_template_parser = subparsers.add_parser(
        "get-template", help="Get template details"
    )
    get_template_parser.add_argument("template_id", help="Template UUID")

    # delete-template
    delete_template_parser = subparsers.add_parser(
        "delete-template", help="Delete a template"
    )
    delete_template_parser.add_argument("template_id", help="Template UUID")

    # create-document
    create_doc_parser = subparsers.add_parser(
        "create-document", help="Create document from template"
    )
    create_doc_parser.add_argument(
        "--template-id", required=True, help="Template UUID"
    )
    create_doc_parser.add_argument("--name", required=True, help="Document name")
    create_doc_parser.add_argument(
        "--recipients",
        required=True,
        help='Recipients JSON array: [{"email": "...", "first_name": "...", "last_name": "...", "role": "..."}]',
    )
    create_doc_parser.add_argument(
        "--tokens",
        help='Tokens JSON object: {"token_name": "value", ...}',
    )
    create_doc_parser.add_argument("--folder-uuid", help="Folder UUID to place document in")

    # send-document
    send_doc_parser = subparsers.add_parser(
        "send-document", help="Send document for signing"
    )
    send_doc_parser.add_argument("document_id", help="Document UUID")
    send_doc_parser.add_argument("--message", help="Message to include in email")
    send_doc_parser.add_argument("--subject", help="Email subject")

    # document-status
    status_parser = subparsers.add_parser(
        "document-status", help="Get document status"
    )
    status_parser.add_argument("document_id", help="Document UUID")

    # download-document
    download_parser = subparsers.add_parser(
        "download-document", help="Download document as PDF"
    )
    download_parser.add_argument("document_id", help="Document UUID")
    download_parser.add_argument("--output", help="Output file path")

    # list-documents
    list_docs_parser = subparsers.add_parser(
        "list-documents", help="List documents"
    )
    list_docs_parser.add_argument(
        "--status",
        choices=["draft", "sent", "completed", "viewed", "waiting_approval", "rejected", "waiting_pay"],
        help="Filter by status",
    )
    list_docs_parser.add_argument(
        "--limit", type=int, default=50, help="Maximum results (default: 50)"
    )

    # delete-document
    delete_doc_parser = subparsers.add_parser(
        "delete-document", help="Delete a document"
    )
    delete_doc_parser.add_argument("document_id", help="Document UUID")

    args = parser.parse_args()

    if not args.command:
        parser.print_help()
        sys.exit(1)

    try:
        client = PandaDocClient()
        result = None

        if args.command == "list-templates":
            result = client.list_templates(tag=args.tag)

        elif args.command == "get-template":
            result = client.get_template(args.template_id)

        elif args.command == "delete-template":
            client.delete_template(args.template_id)
            result = {"status": "deleted", "template_id": args.template_id}

        elif args.command == "create-document":
            recipients = json.loads(args.recipients)
            tokens = json.loads(args.tokens) if args.tokens else None
            result = client.create_document(
                template_id=args.template_id,
                name=args.name,
                recipients=recipients,
                tokens=tokens,
                folder_uuid=args.folder_uuid,
            )

        elif args.command == "send-document":
            result = client.send_document(
                args.document_id,
                message=args.message,
                subject=args.subject,
            )

        elif args.command == "document-status":
            result = client.document_status(args.document_id)

        elif args.command == "download-document":
            output_path = client.download_document(args.document_id, args.output)
            result = {"status": "downloaded", "path": output_path}

        elif args.command == "list-documents":
            result = client.list_documents(status=args.status, limit=args.limit)

        elif args.command == "delete-document":
            client.delete_document(args.document_id)
            result = {"status": "deleted", "document_id": args.document_id}

        print(format_output(result, args.output_format))

    except ValueError as e:
        print(f"Configuration error: {e}", file=sys.stderr)
        sys.exit(1)
    except pandadoc_client.ApiException as e:
        error_body = json.loads(e.body) if e.body else {}
        print(f"API error ({e.status}): {error_body.get('detail', str(e))}", file=sys.stderr)
        sys.exit(1)
    except json.JSONDecodeError as e:
        print(f"Invalid JSON: {e}", file=sys.stderr)
        sys.exit(1)
    except Exception as e:
        print(f"Error: {e}", file=sys.stderr)
        sys.exit(1)


if __name__ == "__main__":
    main()

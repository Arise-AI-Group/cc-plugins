"""Unipile API client for LinkedIn automation.

Wraps the Unipile REST API for accounts, profiles, connections,
messaging, posts, search, and webhooks.

Usage (CLI):
    python -m tool.unipile_api accounts list
    python -m tool.unipile_api accounts get <account_id>

    python -m tool.unipile_api profiles me <account_id>
    python -m tool.unipile_api profiles get <identifier> <account_id> [--sections '*']

    python -m tool.unipile_api connections list <account_id> [--limit 100] [--cursor ...]
    python -m tool.unipile_api connections invite <account_id> <linkedin_identifier> [--message "..."]
    python -m tool.unipile_api connections cancel <account_id> <provider_id>
    python -m tool.unipile_api connections sent <account_id> [--limit 100]
    python -m tool.unipile_api connections received <account_id> [--limit 100]

    python -m tool.unipile_api chats list <account_id> [--limit 50]
    python -m tool.unipile_api chats start <account_id> <attendee_id> --text "Hello!"
    python -m tool.unipile_api chats messages <chat_id> [--limit 50]
    python -m tool.unipile_api chats send <chat_id> --text "Follow-up message"

    python -m tool.unipile_api posts get <post_id> <account_id>
    python -m tool.unipile_api posts create <account_id> --text "Post content"
    python -m tool.unipile_api posts comments <post_id> <account_id> [--limit 50]
    python -m tool.unipile_api posts comment <post_id> <account_id> --text "Great post!"
    python -m tool.unipile_api posts react <post_id> <account_id> [--reaction LIKE]

    python -m tool.unipile_api search <account_id> <query> [--category people] [--limit 25]

    python -m tool.unipile_api webhooks list
    python -m tool.unipile_api webhooks create <request_url> <source>
    python -m tool.unipile_api webhooks delete <webhook_id>

Usage (Module):
    from tool.unipile_api import UnipileClient
    client = UnipileClient()
    accounts = client.list_accounts()
"""

import re
import sys
import json
import argparse
from typing import Optional, List, Dict, Any

import httpx

from .config import get_api_key


class UnipileError(Exception):
    """Base exception for Unipile API errors."""

    def __init__(self, message: str, status_code: int = 0, response_data: Any = None):
        super().__init__(message)
        self.status_code = status_code
        self.response_data = response_data


class UnipileAuthError(UnipileError):
    pass


class UnipileNotFoundError(UnipileError):
    pass


class UnipileRateLimitError(UnipileError):
    def __init__(self, retry_after: int = 60):
        super().__init__(f"Rate limited. Retry after {retry_after}s", status_code=429)
        self.retry_after = retry_after


class UnipileValidationError(UnipileError):
    pass


class UnipileClient:
    """Synchronous Unipile API client."""

    def __init__(self, api_key: str = None, dsn: str = None):
        self.api_key = api_key or get_api_key("UNIPILE_API_KEY")
        self.dsn = dsn or get_api_key("UNIPILE_DSN")

        if not self.api_key:
            raise ValueError(
                "UNIPILE_API_KEY not configured. "
                "Add to ~/.config/cc-plugins/.env"
            )
        if not self.dsn:
            raise ValueError(
                "UNIPILE_DSN not configured. "
                "Add to ~/.config/cc-plugins/.env"
            )

        self.base_url = f"https://{self.dsn}/api/v1"
        self._client = httpx.Client(
            base_url=self.base_url,
            headers={
                "Accept": "application/json",
                "X-API-KEY": self.api_key,
            },
            timeout=30.0,
        )

    def _request(
        self,
        method: str,
        path: str,
        params: Optional[Dict] = None,
        json: Optional[Dict] = None,
        **kwargs,
    ) -> Any:
        """Central HTTP request handler with error mapping."""
        resp = self._client.request(method, path, params=params, json=json, **kwargs)

        if resp.status_code in (200, 201):
            try:
                return resp.json()
            except Exception:
                return {"status": "ok"}

        # Error mapping
        try:
            data = resp.json()
        except Exception:
            data = {"message": resp.text}

        msg = data.get("message") or data.get("detail") or str(data)

        if resp.status_code == 401:
            raise UnipileAuthError(f"Authentication failed: {msg}", 401, data)
        elif resp.status_code == 404:
            raise UnipileNotFoundError(f"Not found: {msg}", 404, data)
        elif resp.status_code == 429:
            retry_after = int(resp.headers.get("Retry-After", 60))
            raise UnipileRateLimitError(retry_after)
        elif resp.status_code == 422:
            raise UnipileValidationError(f"Validation error: {msg}", 422, data)
        else:
            raise UnipileError(
                f"HTTP {resp.status_code}: {msg}", resp.status_code, data
            )

    # === Accounts ===

    def list_accounts(self) -> dict:
        """List connected social accounts."""
        return self._request("GET", "/accounts")

    def get_account(self, account_id: str) -> dict:
        """Get details for a connected account."""
        return self._request("GET", f"/accounts/{account_id}")

    # === Profiles ===

    def get_my_profile(self, account_id: str) -> dict:
        """Get own LinkedIn profile."""
        return self._request("GET", "/users/me", params={"account_id": account_id})

    def get_user_profile(
        self,
        identifier: str,
        account_id: str,
        linkedin_sections: Optional[str] = None,
    ) -> dict:
        """Get a user's profile by public identifier or provider ID.

        Args:
            identifier: LinkedIn public ID (e.g. 'jane-doe') or provider ID
            account_id: Unipile account ID
            linkedin_sections: Pass '*' for full profile (experience, skills, education)
        """
        params: Dict[str, Any] = {"account_id": account_id}
        if linkedin_sections:
            params["linkedin_sections"] = linkedin_sections
        return self._request("GET", f"/users/{identifier}", params=params)

    # === Connections & Invitations ===

    def list_relations(
        self,
        account_id: str,
        limit: int = 100,
        cursor: Optional[str] = None,
    ) -> dict:
        """List LinkedIn connections with pagination."""
        params: Dict[str, Any] = {"account_id": account_id, "limit": limit}
        if cursor:
            params["cursor"] = cursor
        return self._request("GET", "/users/relations", params=params)

    def send_invitation(
        self,
        account_id: str,
        provider_id: str,
        message: Optional[str] = None,
    ) -> dict:
        """Send a LinkedIn connection request.

        Args:
            account_id: Unipile account ID
            provider_id: LinkedIn provider ID (use resolve_provider_id to get this)
            message: Optional invite note (max 300 chars)
        """
        body: Dict[str, Any] = {
            "account_id": account_id,
            "provider_id": provider_id,
        }
        if message:
            body["message"] = message[:300]
        return self._request("POST", "/users/invite", json=body)

    def cancel_invitation(self, account_id: str, provider_id: str) -> dict:
        """Cancel a pending connection request."""
        return self._request(
            "POST",
            "/users/cancel-invite",
            json={"account_id": account_id, "provider_id": provider_id},
        )

    def list_sent_invitations(
        self,
        account_id: str,
        limit: int = 100,
        cursor: Optional[str] = None,
    ) -> dict:
        """List sent connection invitations."""
        params: Dict[str, Any] = {"account_id": account_id, "limit": limit}
        if cursor:
            params["cursor"] = cursor
        return self._request("GET", "/users/invite/sent", params=params)

    def list_received_invitations(
        self,
        account_id: str,
        limit: int = 100,
        cursor: Optional[str] = None,
    ) -> dict:
        """List received connection invitations."""
        params: Dict[str, Any] = {"account_id": account_id, "limit": limit}
        if cursor:
            params["cursor"] = cursor
        return self._request("GET", "/users/invite/received", params=params)

    # === Messaging ===

    def list_chats(
        self,
        account_id: str,
        limit: int = 50,
        cursor: Optional[str] = None,
    ) -> dict:
        """List conversations/chats."""
        params: Dict[str, Any] = {"account_id": account_id, "limit": limit}
        if cursor:
            params["cursor"] = cursor
        return self._request("GET", "/chats", params=params)

    def start_chat(
        self,
        account_id: str,
        attendees_ids: List[str],
        text: str,
    ) -> dict:
        """Start a new conversation and send the first message.

        Args:
            account_id: Unipile account ID
            attendees_ids: List of LinkedIn provider IDs
            text: First message text
        """
        return self._request(
            "POST",
            "/chats",
            json={
                "account_id": account_id,
                "attendees_ids": attendees_ids,
                "text": text,
            },
        )

    def get_messages(
        self,
        chat_id: str,
        limit: int = 50,
        cursor: Optional[str] = None,
    ) -> dict:
        """Get messages in a conversation."""
        params: Dict[str, Any] = {"limit": limit}
        if cursor:
            params["cursor"] = cursor
        return self._request("GET", f"/chats/{chat_id}/messages", params=params)

    def send_message(self, chat_id: str, text: str) -> dict:
        """Send a message in an existing chat."""
        return self._request(
            "POST", f"/chats/{chat_id}/messages", json={"text": text}
        )

    # === Posts & Engagement ===

    def get_post(self, post_id: str, account_id: str) -> dict:
        """Get a LinkedIn post by ID."""
        return self._request(
            "GET", f"/posts/{post_id}", params={"account_id": account_id}
        )

    def create_post(self, account_id: str, text: str) -> dict:
        """Create a new LinkedIn post."""
        return self._request(
            "POST", "/posts", json={"account_id": account_id, "text": text}
        )

    def get_comments(
        self,
        post_id: str,
        account_id: str,
        limit: int = 50,
    ) -> dict:
        """Get comments on a LinkedIn post."""
        return self._request(
            "GET",
            f"/posts/{post_id}/comments",
            params={"account_id": account_id, "limit": limit},
        )

    def add_comment(self, post_id: str, account_id: str, text: str) -> dict:
        """Add a comment to a LinkedIn post."""
        return self._request(
            "POST",
            f"/posts/{post_id}/comments",
            json={"account_id": account_id, "text": text},
        )

    def react_to_post(
        self,
        post_id: str,
        account_id: str,
        reaction: str = "LIKE",
    ) -> dict:
        """React to a LinkedIn post.

        Args:
            reaction: LIKE, CELEBRATE, SUPPORT, LOVE, INSIGHTFUL, FUNNY
        """
        return self._request(
            "POST",
            f"/posts/{post_id}/reactions",
            json={"account_id": account_id, "reaction_type": reaction},
        )

    # === LinkedIn Search ===

    def linkedin_search(
        self,
        account_id: str,
        query: str,
        category: str = "people",
        limit: int = 25,
    ) -> dict:
        """Search LinkedIn for people, companies, or content.

        Args:
            category: people, companies, posts, groups
        """
        return self._request(
            "POST",
            "/linkedin/search",
            json={
                "account_id": account_id,
                "query": query,
                "category": category,
                "limit": limit,
            },
        )

    # === Webhooks ===

    def list_webhooks(self) -> dict:
        """List registered webhooks."""
        return self._request("GET", "/webhooks")

    def create_webhook(
        self,
        request_url: str,
        source: str,
        headers: Optional[List[Dict[str, str]]] = None,
    ) -> dict:
        """Register a webhook endpoint.

        Args:
            request_url: URL to receive webhook events
            source: messaging, users, email, email_tracking, accounts
            headers: Optional custom headers as [{"key": "...", "value": "..."}]
        """
        body: Dict[str, Any] = {"request_url": request_url, "source": source}
        if headers:
            body["headers"] = headers
        return self._request("POST", "/webhooks", json=body)

    def delete_webhook(self, webhook_id: str) -> dict:
        """Delete a registered webhook."""
        return self._request("DELETE", f"/webhooks/{webhook_id}")

    # === Helpers ===

    def resolve_provider_id(
        self, account_id: str, linkedin_url_or_identifier: str
    ) -> str:
        """Extract public identifier from LinkedIn URL and look up provider_id.

        Args:
            linkedin_url_or_identifier: LinkedIn URL or public ID (e.g. 'jane-doe')

        Returns:
            The LinkedIn provider_id string
        """
        # Extract public identifier from URL if needed
        match = re.match(
            r"(?:https?://)?(?:www\.)?linkedin\.com/in/([a-zA-Z0-9_-]+)",
            linkedin_url_or_identifier,
        )
        identifier = match.group(1) if match else linkedin_url_or_identifier

        profile = self.get_user_profile(identifier, account_id)
        provider_id = profile.get("provider_id")
        if not provider_id:
            raise UnipileError(f"No provider_id returned for '{identifier}'")
        return provider_id


# --- CLI Interface ---


def build_parser() -> argparse.ArgumentParser:
    """Build the argument parser."""
    parser = argparse.ArgumentParser(
        description="Unipile API CLI - LinkedIn automation",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog=__doc__,
    )
    subparsers = parser.add_subparsers(dest="category", help="Command category")

    # === Accounts ===
    acc_parser = subparsers.add_parser("accounts", help="Account operations")
    acc_sub = acc_parser.add_subparsers(dest="action")

    acc_sub.add_parser("list", help="List connected accounts")

    acc_get = acc_sub.add_parser("get", help="Get account details")
    acc_get.add_argument("account_id", help="Account ID")

    # === Profiles ===
    prof_parser = subparsers.add_parser("profiles", help="Profile operations")
    prof_sub = prof_parser.add_subparsers(dest="action")

    prof_me = prof_sub.add_parser("me", help="Get own profile")
    prof_me.add_argument("account_id", help="Account ID")

    prof_get = prof_sub.add_parser("get", help="Get user profile")
    prof_get.add_argument("identifier", help="LinkedIn public ID (e.g. 'jane-doe') or provider ID")
    prof_get.add_argument("account_id", help="Account ID")
    prof_get.add_argument("--sections", default=None, help="Pass '*' for full profile")

    # === Connections ===
    conn_parser = subparsers.add_parser("connections", help="Connection operations")
    conn_sub = conn_parser.add_subparsers(dest="action")

    conn_list = conn_sub.add_parser("list", help="List connections")
    conn_list.add_argument("account_id", help="Account ID")
    conn_list.add_argument("--limit", type=int, default=100)
    conn_list.add_argument("--cursor", default=None)

    conn_invite = conn_sub.add_parser("invite", help="Send connection request")
    conn_invite.add_argument("account_id", help="Account ID")
    conn_invite.add_argument("linkedin_identifier", help="LinkedIn URL or public ID")
    conn_invite.add_argument("--message", default=None, help="Invite note (max 300 chars)")

    conn_cancel = conn_sub.add_parser("cancel", help="Cancel connection request")
    conn_cancel.add_argument("account_id", help="Account ID")
    conn_cancel.add_argument("provider_id", help="Provider ID")

    conn_sent = conn_sub.add_parser("sent", help="List sent invitations")
    conn_sent.add_argument("account_id", help="Account ID")
    conn_sent.add_argument("--limit", type=int, default=100)
    conn_sent.add_argument("--cursor", default=None)

    conn_recv = conn_sub.add_parser("received", help="List received invitations")
    conn_recv.add_argument("account_id", help="Account ID")
    conn_recv.add_argument("--limit", type=int, default=100)
    conn_recv.add_argument("--cursor", default=None)

    # === Chats ===
    chat_parser = subparsers.add_parser("chats", help="Chat/messaging operations")
    chat_sub = chat_parser.add_subparsers(dest="action")

    chat_list = chat_sub.add_parser("list", help="List conversations")
    chat_list.add_argument("account_id", help="Account ID")
    chat_list.add_argument("--limit", type=int, default=50)
    chat_list.add_argument("--cursor", default=None)

    chat_start = chat_sub.add_parser("start", help="Start new conversation")
    chat_start.add_argument("account_id", help="Account ID")
    chat_start.add_argument("attendee_id", help="LinkedIn provider ID of the person")
    chat_start.add_argument("--text", required=True, help="First message text")

    chat_msgs = chat_sub.add_parser("messages", help="Get messages in a chat")
    chat_msgs.add_argument("chat_id", help="Chat ID")
    chat_msgs.add_argument("--limit", type=int, default=50)
    chat_msgs.add_argument("--cursor", default=None)

    chat_send = chat_sub.add_parser("send", help="Send message in existing chat")
    chat_send.add_argument("chat_id", help="Chat ID")
    chat_send.add_argument("--text", required=True, help="Message text")

    # === Posts ===
    post_parser = subparsers.add_parser("posts", help="Post & engagement operations")
    post_sub = post_parser.add_subparsers(dest="action")

    post_get = post_sub.add_parser("get", help="Get a post")
    post_get.add_argument("post_id", help="Post ID")
    post_get.add_argument("account_id", help="Account ID")

    post_create = post_sub.add_parser("create", help="Create a post")
    post_create.add_argument("account_id", help="Account ID")
    post_create.add_argument("--text", required=True, help="Post content")

    post_comments = post_sub.add_parser("comments", help="Get post comments")
    post_comments.add_argument("post_id", help="Post ID")
    post_comments.add_argument("account_id", help="Account ID")
    post_comments.add_argument("--limit", type=int, default=50)

    post_comment = post_sub.add_parser("comment", help="Add comment to post")
    post_comment.add_argument("post_id", help="Post ID")
    post_comment.add_argument("account_id", help="Account ID")
    post_comment.add_argument("--text", required=True, help="Comment text")

    post_react = post_sub.add_parser("react", help="React to a post")
    post_react.add_argument("post_id", help="Post ID")
    post_react.add_argument("account_id", help="Account ID")
    post_react.add_argument("--reaction", default="LIKE",
                            help="LIKE, CELEBRATE, SUPPORT, LOVE, INSIGHTFUL, FUNNY")

    # === Search ===
    search_parser = subparsers.add_parser("search", help="LinkedIn search")
    search_parser.add_argument("account_id", help="Account ID")
    search_parser.add_argument("query", help="Search query")
    search_parser.add_argument("--category", default="people", dest="search_category",
                               help="people, companies, posts, groups")
    search_parser.add_argument("--limit", type=int, default=25)

    # === Webhooks ===
    wh_parser = subparsers.add_parser("webhooks", help="Webhook operations")
    wh_sub = wh_parser.add_subparsers(dest="action")

    wh_sub.add_parser("list", help="List webhooks")

    wh_create = wh_sub.add_parser("create", help="Register webhook")
    wh_create.add_argument("request_url", help="Webhook endpoint URL")
    wh_create.add_argument("source", help="messaging, users, email, email_tracking, accounts")

    wh_delete = wh_sub.add_parser("delete", help="Delete webhook")
    wh_delete.add_argument("webhook_id", help="Webhook ID")

    return parser


def main():
    parser = build_parser()
    args = parser.parse_args()

    if not args.category:
        parser.print_help()
        sys.exit(1)

    try:
        client = UnipileClient()
    except ValueError as e:
        print(f"Error: {e}", file=sys.stderr)
        sys.exit(1)

    try:
        result = _dispatch(client, args)
        print(json.dumps(result, indent=2, default=str))
    except UnipileError as e:
        print(json.dumps({"error": str(e), "status_code": e.status_code}, indent=2),
              file=sys.stderr)
        sys.exit(1)


def _dispatch(client: UnipileClient, args) -> Any:
    """Route CLI args to client methods."""
    cat = args.category
    act = getattr(args, "action", None)

    # --- Accounts ---
    if cat == "accounts":
        if act == "list":
            return client.list_accounts()
        elif act == "get":
            return client.get_account(args.account_id)

    # --- Profiles ---
    elif cat == "profiles":
        if act == "me":
            return client.get_my_profile(args.account_id)
        elif act == "get":
            return client.get_user_profile(
                args.identifier, args.account_id, linkedin_sections=args.sections
            )

    # --- Connections ---
    elif cat == "connections":
        if act == "list":
            return client.list_relations(args.account_id, limit=args.limit, cursor=args.cursor)
        elif act == "invite":
            provider_id = client.resolve_provider_id(args.account_id, args.linkedin_identifier)
            return client.send_invitation(args.account_id, provider_id, message=args.message)
        elif act == "cancel":
            return client.cancel_invitation(args.account_id, args.provider_id)
        elif act == "sent":
            return client.list_sent_invitations(args.account_id, limit=args.limit, cursor=args.cursor)
        elif act == "received":
            return client.list_received_invitations(args.account_id, limit=args.limit, cursor=args.cursor)

    # --- Chats ---
    elif cat == "chats":
        if act == "list":
            return client.list_chats(args.account_id, limit=args.limit, cursor=args.cursor)
        elif act == "start":
            return client.start_chat(args.account_id, [args.attendee_id], args.text)
        elif act == "messages":
            return client.get_messages(args.chat_id, limit=args.limit, cursor=args.cursor)
        elif act == "send":
            return client.send_message(args.chat_id, args.text)

    # --- Posts ---
    elif cat == "posts":
        if act == "get":
            return client.get_post(args.post_id, args.account_id)
        elif act == "create":
            return client.create_post(args.account_id, args.text)
        elif act == "comments":
            return client.get_comments(args.post_id, args.account_id, limit=args.limit)
        elif act == "comment":
            return client.add_comment(args.post_id, args.account_id, args.text)
        elif act == "react":
            return client.react_to_post(args.post_id, args.account_id, reaction=args.reaction)

    # --- Search ---
    elif cat == "search":
        return client.linkedin_search(
            args.account_id, args.query, category=args.search_category, limit=args.limit
        )

    # --- Webhooks ---
    elif cat == "webhooks":
        if act == "list":
            return client.list_webhooks()
        elif act == "create":
            return client.create_webhook(args.request_url, args.source)
        elif act == "delete":
            return client.delete_webhook(args.webhook_id)

    # Fallback
    parser = build_parser()
    if cat:
        # Find the subparser and print its help
        for action in parser._subparsers._actions:
            if isinstance(action, argparse._SubParsersAction):
                if cat in action.choices:
                    action.choices[cat].print_help()
                    sys.exit(1)
    parser.print_help()
    sys.exit(1)


if __name__ == "__main__":
    main()

---
name: unipile
description: This skill should be used when the user asks to "send a LinkedIn message", "look up a LinkedIn profile", "send a connection request", "search LinkedIn", "check my LinkedIn connections", "comment on a LinkedIn post", "create a LinkedIn post", "manage LinkedIn DMs", "research a prospect on LinkedIn", "check invitation status", "list my LinkedIn conversations". Provides LinkedIn automation via the Unipile unified messaging API.
---

# LinkedIn Automation (Unipile)

## Execution Method

**Always use Python**: `tool/unipile_api.py`

## Purpose

Automate LinkedIn operations: send/receive messages, manage connections, research profiles, engage with posts/comments, and search for people or content. Powered by the Unipile unified API.

## Trigger Phrases

- "Send a LinkedIn message to..."
- "Send a connection request to..."
- "Look up this person on LinkedIn"
- "Research this prospect's LinkedIn profile"
- "Check my LinkedIn connections"
- "Search LinkedIn for people in..."
- "Comment on this LinkedIn post"
- "Like/react to this post"
- "Create a LinkedIn post"
- "Check the status of my sent invitations"
- "List my LinkedIn conversations"
- "Set up a webhook for LinkedIn messages"

---

## Account ID

Most operations require an `account_id`. To find it:

```bash
./run tool/unipile_api.py accounts list
```

Use the `id` field from the LinkedIn account. The account_id is stable — cache it in conversation context.

---

## Account Operations

```bash
# List connected accounts
./run tool/unipile_api.py accounts list

# Get account details
./run tool/unipile_api.py accounts get <account_id>
```

## Profile Operations

```bash
# Get own profile
./run tool/unipile_api.py profiles me <account_id>

# Get user profile by public identifier or LinkedIn URL
./run tool/unipile_api.py profiles get jane-doe <account_id>

# Full profile with experience, skills, education
./run tool/unipile_api.py profiles get jane-doe <account_id> --sections '*'
```

## Connection Operations

```bash
# List connections
./run tool/unipile_api.py connections list <account_id>
./run tool/unipile_api.py connections list <account_id> --limit 250

# Send connection request (auto-resolves LinkedIn URL or public ID)
./run tool/unipile_api.py connections invite <account_id> jane-doe
./run tool/unipile_api.py connections invite <account_id> jane-doe --message "Hi Jane!"
./run tool/unipile_api.py connections invite <account_id> "https://linkedin.com/in/jane-doe" --message "Hi!"

# Cancel pending request
./run tool/unipile_api.py connections cancel <account_id> <provider_id>

# Check invitation status
./run tool/unipile_api.py connections sent <account_id>
./run tool/unipile_api.py connections received <account_id>
```

## Chat/Messaging Operations

```bash
# List conversations
./run tool/unipile_api.py chats list <account_id>

# Start new conversation (sends first message)
./run tool/unipile_api.py chats start <account_id> <attendee_provider_id> --text "Hello!"

# Get messages from a conversation
./run tool/unipile_api.py chats messages <chat_id>

# Send message in existing chat
./run tool/unipile_api.py chats send <chat_id> --text "Follow-up message"
```

## Post & Engagement Operations

```bash
# Get a post
./run tool/unipile_api.py posts get <post_id> <account_id>

# Create a post
./run tool/unipile_api.py posts create <account_id> --text "Post content here"

# Get comments on a post
./run tool/unipile_api.py posts comments <post_id> <account_id>

# Add comment to a post
./run tool/unipile_api.py posts comment <post_id> <account_id> --text "Great insight!"

# React to a post
./run tool/unipile_api.py posts react <post_id> <account_id>
./run tool/unipile_api.py posts react <post_id> <account_id> --reaction CELEBRATE
```

## LinkedIn Search

```bash
# Search for people
./run tool/unipile_api.py search <account_id> "CTO manufacturing"

# Search by category
./run tool/unipile_api.py search <account_id> "AI automation" --category companies
./run tool/unipile_api.py search <account_id> "machine learning" --category posts
```

Categories: people, companies, posts, groups

## Webhook Operations

```bash
# List webhooks
./run tool/unipile_api.py webhooks list

# Register webhook
./run tool/unipile_api.py webhooks create https://your-endpoint.com/webhook messaging

# Delete webhook
./run tool/unipile_api.py webhooks delete <webhook_id>
```

Sources: messaging, users, email, email_tracking, accounts

---

## Core Workflows

### Research a Prospect

1. `./run tool/unipile_api.py profiles get jane-doe <account_id> --sections '*'`
2. Use the profile data for personalization

### Send Connection Request

1. `./run tool/unipile_api.py connections invite <account_id> jane-doe --message "Hi Jane..."`
   - Auto-resolves public ID or LinkedIn URL to provider_id
   - Message max 300 chars (omit for no-note invite)

### Send a DM

**To existing chat:**
1. `./run tool/unipile_api.py chats list <account_id>` — find conversation
2. `./run tool/unipile_api.py chats send <chat_id> --text "..."` — send

**Start new conversation:**
1. `./run tool/unipile_api.py profiles get jane-doe <account_id>` — get provider_id
2. `./run tool/unipile_api.py chats start <account_id> <provider_id> --text "Hello!"`

---

## LinkedIn Safety Limits

| Action | Daily Limit | Notes |
|--------|------------|-------|
| Connection invites | 80-100 (paid) | 300 char note max |
| Profile views | ~100 | More with Sales Navigator |
| Messages | Unlimited* | 1st-degree only |
| Posts/comments/reactions | ~100 combined | |

**Best practices:** Randomize timing, back off on HTTP 429, don't exceed daily limits.

---

## Environment Variables

Required in `~/.config/cc-plugins/.env`:

```
UNIPILE_API_KEY=your_access_token
UNIPILE_DSN=api27.unipile.com:15796
```

## Additional Resources

- [references/api-reference.md](references/api-reference.md) - Full endpoint docs, pagination, webhook payloads, rate limits

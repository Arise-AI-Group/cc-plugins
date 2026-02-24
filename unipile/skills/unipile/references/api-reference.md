# Unipile API Reference

**Base URL:** `https://{YOUR_DSN}/api/v1` (e.g., `https://api27.unipile.com:15796/api/v1`)
**Auth Header:** `X-API-KEY: {access_token}`

## Endpoint Cheat Sheet

| Action | Method | Path |
|--------|--------|------|
| List accounts | GET | `/accounts` |
| Get account | GET | `/accounts/{account_id}` |
| **Send invitation** | POST | `/users/invite` |
| List relations | GET | `/users/relations` |
| Get user profile | GET | `/users/{identifier}` |
| List sent invitations | GET | `/users/invite/sent` |
| List received invitations | GET | `/users/invite/received` |
| Cancel invitation | POST | `/users/cancel-invite` |
| **Start new chat** | POST | `/chats` |
| List chats | GET | `/chats` |
| **Send message** | POST | `/chats/{chat_id}/messages` |
| List messages in chat | GET | `/chats/{chat_id}/messages` |
| **Create webhook** | POST | `/webhooks` |
| List webhooks | GET | `/webhooks` |
| Delete webhook | DELETE | `/webhooks/{webhook_id}` |

## Pagination

All list endpoints support cursor-based pagination:
- `cursor` (string) — token from prior response
- `limit` (integer) — items per page, 1-250

## Key Endpoints

### POST /users/invite — Send Connection Request

```json
{
  "account_id": "Z_3ZuK31ThGTLKx0X5y5fQ",
  "provider_id": "ACoAAAcDMMQBODyLwZrRcgYhrkCafURGqva0U4E",
  "message": "Optional invite note (max 300 chars)"
}
```

**Note:** `provider_id` is the LinkedIn internal ID — get it by looking up the user first:
`GET /users/{public_identifier}?account_id=...` → response includes `provider_id`.

**Response:** `201 Created`

### GET /users/relations — List Connections

`GET /users/relations?account_id={id}&limit=100&cursor={cursor}`

Response items:
```json
{
  "object": "UserRelation",
  "connection_urn": "urn:li:fsd_connection:...",
  "created_at": 1771943752000,
  "first_name": "Jane",
  "last_name": "Doe",
  "member_id": "ACoAAABUlmuEB...",
  "member_urn": "urn:li:fsd_profile:...",
  "headline": "...",
  "public_identifier": "jane-doe"
}
```

### GET /users/invite/sent — List Sent Invitations

`GET /users/invite/sent?account_id={id}&limit=100`

Response items:
```json
{
  "object": "InvitationSent",
  "id": "7432050021786857473",
  "date": "Sent today",
  "parsed_datetime": "2026-02-24T14:50:17.878Z",
  "invitation_text": null,
  "invited_user": "Johnny Correa",
  "invited_user_id": "ACoAAADNJKAB...",
  "invited_user_public_id": "johnny-correa-2a86044"
}
```

### GET /users/{identifier} — Get User Profile

`GET /users/{public_identifier}?account_id={id}`

Pass `linkedin_sections=*` for full profile (experience, skills, education).

### POST /chats — Start New Chat / Send First Message

```json
{
  "account_id": "Z_3ZuK31ThGTLKx0X5y5fQ",
  "attendees_ids": ["ACoAAAcDMMQB..."],
  "text": "Hello!"
}
```

Supports `multipart/form-data` for attachments. Can only message 1st-degree connections (unless using InMail).

### POST /chats/{chat_id}/messages — Send Message

```json
{ "text": "Follow-up message" }
```

### POST /webhooks — Create Webhook

```json
{
  "request_url": "https://your-endpoint.com/webhook",
  "source": "messaging",
  "headers": [
    { "key": "Content-Type", "value": "application/json" }
  ]
}
```

**Sources:** `messaging`, `users`, `email`, `email_tracking`, `accounts`

Must respond with HTTP 200 within 30 seconds. Retries up to 5 times on failure.

## Webhook Event Payloads

### `message_received` (source: messaging)

```json
{
  "event": "message_received",
  "account_id": "...",
  "account_type": "LINKEDIN",
  "account_info": { "type": "...", "user_id": "ACoAAA..." },
  "chat_id": "...",
  "message_id": "...",
  "message": "Hey, thanks for reaching out!",
  "sender": {
    "attendee_id": "...",
    "attendee_provider_id": "ACoAAAcDMMQ...",
    "attendee_name": "Jane Doe",
    "attendee_profile_url": "https://linkedin.com/in/jane-doe"
  },
  "timestamp": "2026-02-24T15:30:00.000Z"
}
```

**Detect own messages:** Compare `account_info.user_id` with `sender.attendee_provider_id`.

### `new_relation` (source: users)

```json
{
  "event": "new_relation",
  "account_id": "...",
  "account_type": "LINKEDIN",
  "user_full_name": "Jane Doe",
  "user_provider_id": "ACoAAAh_Ffq...",
  "user_public_identifier": "jane-doe",
  "user_profile_url": "https://www.linkedin.com/in/jane-doe/"
}
```

**Important:** NOT real-time. Unipile polls LinkedIn at randomized intervals. Expect up to 8 hours delay.

## LinkedIn Limits & Best Practices

### Connection Invitations
| Account Type | Daily | Weekly | Note Length |
|---|---|---|---|
| Paid/Active | 80-100 | ~200 | 300 chars |
| Free | ~5/month | 150 (no note) | 200 chars |

Exceeding limits → HTTP 422 `cannot_resend_yet`

### Daily Action Limits
- **Profile views:** ~100/day (standard), more with Sales Navigator
- **General actions** (posts, comments, reactions): ~100/day
- **InMail:** 30-50/day recommended

### Best Practices
1. **Randomize timing** — never use fixed intervals
2. **Use established accounts** — 150+ connections, normal prior activity
3. **Relations polling** — don't poll hourly; use `new_relation` webhook + occasional first-page checks at random intervals
4. **Rate limit response** — HTTP 429 or 500 = back off immediately
5. **Messaging inbox** — managed server-side, unlimited access via Chats/Messages routes

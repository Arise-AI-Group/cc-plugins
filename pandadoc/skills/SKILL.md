---
name: pandadoc
description: This skill should be used when the user asks to "create a contract", "send a proposal", "build document from template", "check document status", "list PandaDoc templates", "download signed document", "send document for signature". Provides PandaDoc API integration for document generation, e-signatures, and template management.
---

# PandaDoc Integration

Create, send, and manage documents via PandaDoc API.

## Trigger Phrases

- "create a contract for [client]"
- "send a proposal to [client]"
- "build document from template"
- "list my PandaDoc templates"
- "check document status"
- "download the signed contract"
- "send document for signature"
- "what PandaDoc templates do I have"

## Execution

Run commands via the CLI tool:

```bash
./run tool/pandadoc_api.py <command> [options]
```

## Core Operations

### Template Operations

```bash
# List all templates
./run tool/pandadoc_api.py list-templates

# List templates with tag filter
./run tool/pandadoc_api.py list-templates --tag proposals

# Get template details (shows available tokens/fields)
./run tool/pandadoc_api.py get-template <template_id>

# Delete a template
./run tool/pandadoc_api.py delete-template <template_id>
```

### Document Creation

```bash
# Create document from template
./run tool/pandadoc_api.py create-document \
  --template-id <template_uuid> \
  --name "Proposal for Acme Corp" \
  --recipients '[{"email": "client@example.com", "first_name": "John", "last_name": "Doe", "role": "Client"}]' \
  --tokens '{"client_name": "Acme Corp", "project_scope": "Website redesign", "total_amount": "$5,000"}'
```

**Recipients format** (JSON array):
- `email` (required): Recipient email
- `first_name`, `last_name`: Recipient name
- `role`: Role in template (e.g., "Client", "Signer")

**Tokens format** (JSON object):
- Key-value pairs matching template variables
- Get available tokens with `get-template`

### Document Lifecycle

```bash
# Send document for signing
./run tool/pandadoc_api.py send-document <document_id>
./run tool/pandadoc_api.py send-document <document_id> --message "Please review and sign by Friday"

# Check document status
./run tool/pandadoc_api.py document-status <document_id>

# Download completed document as PDF
./run tool/pandadoc_api.py download-document <document_id>
./run tool/pandadoc_api.py download-document <document_id> --output ~/Documents/signed-contract.pdf

# Delete a document
./run tool/pandadoc_api.py delete-document <document_id>
```

### Listing Documents

```bash
# List recent documents
./run tool/pandadoc_api.py list-documents

# Filter by status
./run tool/pandadoc_api.py list-documents --status completed
./run tool/pandadoc_api.py list-documents --status sent --limit 10
```

**Status values**: `draft`, `sent`, `completed`, `viewed`, `waiting_approval`, `rejected`, `waiting_pay`

## Output Formats

All commands support `--output-format`:
- `text` (default): Human-readable output
- `json`: Machine-parseable JSON

```bash
./run tool/pandadoc_api.py list-templates --output-format json | jq '.[] | .name'
```

## Environment Variables

Required in `~/.config/cc-plugins/.env`:

```
PANDADOC_API_KEY=your_api_key_here
```

Get your API key from: PandaDoc Settings > Integrations > API

## Typical Workflow

1. **List templates** to find the right one:
   ```bash
   ./run tool/pandadoc_api.py list-templates --tag proposals
   ```

2. **Get template details** to see required tokens:
   ```bash
   ./run tool/pandadoc_api.py get-template <template_id>
   ```

3. **Create document** with populated variables:
   ```bash
   ./run tool/pandadoc_api.py create-document \
     --template-id <id> \
     --name "Proposal - Acme Corp" \
     --recipients '[{"email": "ceo@acme.com", "first_name": "Jane", "last_name": "Smith", "role": "Client"}]' \
     --tokens '{"client_name": "Acme Corp", "project_name": "Q1 Initiative"}'
   ```

4. **Send for signature**:
   ```bash
   ./run tool/pandadoc_api.py send-document <document_id> --message "Please review and sign"
   ```

5. **Monitor status**:
   ```bash
   ./run tool/pandadoc_api.py document-status <document_id>
   ```

6. **Download when complete**:
   ```bash
   ./run tool/pandadoc_api.py download-document <document_id> --output ~/signed-contract.pdf
   ```

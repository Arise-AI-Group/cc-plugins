# PandaDoc Plugin

PandaDoc document generation and e-signatures - create contracts, proposals, and send for signing.

## Installation

```bash
/plugin install pandadoc@cc-plugins
```

## Commands

- `pandadoc:skills` - See available commands and usage

## Environment Variables

Add to `~/.config/cc-plugins/.env`:

```
PANDADOC_API_KEY=your_api_key_here
```

Get your API key from: PandaDoc Settings > Integrations > API

## Usage

### Via CLI

```bash
# List templates
./run tool/pandadoc_api.py list-templates

# Create document from template
./run tool/pandadoc_api.py create-document \
  --template-id <id> \
  --name "Proposal" \
  --recipients '[{"email": "client@example.com", "first_name": "John", "last_name": "Doe", "role": "Client"}]' \
  --tokens '{"client_name": "Acme Corp"}'

# Send for signature
./run tool/pandadoc_api.py send-document <document_id>

# Check status
./run tool/pandadoc_api.py document-status <document_id>

# Download completed document
./run tool/pandadoc_api.py download-document <document_id> --output contract.pdf
```

## Skills

Auto-triggered skills for document generation:
- Create contracts and proposals from templates
- Send documents for e-signature
- Check document status
- Download signed documents

## License

MIT

# Add Sandbox
> Deploy a new n8n sandbox instance for a team member.

## Variables
initials: $1

## Instructions
- Read `runbooks/team_infrastructure.md` for the full process
- This creates:
  1. Docker compose deployment via Dokploy
  2. Cloudflare tunnel route
  3. DNS record: `{initials}-n8n.example.com`

## Run
```bash
# Create DNS record (replace with your zone and tunnel ID)
./run tools/cloudflare_api.py dns create <zone> "$initials-n8n" <tunnel-id>.cfargotunnel.com --proxied

# Add Cloudflare tunnel route
./run tools/cloudflare_api.py tunnel route-add <tunnel-id> "$initials-n8n.<zone>" "http://localhost:<PORT>"

# Create Dokploy compose project
./run tools/dokploy_api.py compose create <environment_id> "n8n-$initials" --file compose.yaml
```

## Report
- Confirm all resources were created
- Report the sandbox URL
- Note the assigned port number
- List any manual steps needed

# Remove Sandbox
> Teardown an n8n sandbox instance.

## Variables
initials: $1

## Instructions
- Read `runbooks/team_infrastructure.md` for the full process
- This removes:
  1. Docker compose deployment from Dokploy
  2. Cloudflare tunnel route
  3. DNS record

## Run
```bash
# Remove Dokploy compose project
./run tools/dokploy_api.py compose delete "n8n-$initials" -y

# Remove Cloudflare tunnel route
./run tools/cloudflare_api.py tunnel route-remove <tunnel-id> "$initials-n8n.<zone>"

# Remove DNS record
./run tools/cloudflare_api.py dns delete <zone> "$initials-n8n" -y
```

## Report
- Confirm all resources were removed
- Note any cleanup that may still be needed

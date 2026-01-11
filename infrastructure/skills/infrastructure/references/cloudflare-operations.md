# Cloudflare Operations Reference

## DNS Management

### List Zones
```bash
./run tool/cloudflare_api.py zones list
```

### List DNS Records
```bash
./run tool/cloudflare_api.py dns list example.com
```

### Create DNS Record
```bash
./run tool/cloudflare_api.py dns create example.com <subdomain> <tunnel-id>.cfargotunnel.com --proxied
```

### Delete DNS Record
```bash
./run tool/cloudflare_api.py dns delete example.com <record-id>
```

---

## Tunnel Management

### List Tunnels
```bash
./run tool/cloudflare_api.py tunnel list
```

### Get Tunnel Config
```bash
./run tool/cloudflare_api.py tunnel config <tunnel-id>
```

### Add Tunnel Route
```bash
./run tool/cloudflare_api.py tunnel route-add <tunnel-id> <hostname> http://localhost:<port>
```

### Remove Tunnel Route
```bash
./run tool/cloudflare_api.py tunnel route-remove <tunnel-id> <hostname>
```

---

## Current Setup

**Tunnel ID:** See `SECRETS.md`

**DNS Records:**
| Record | Type | Target | Notes |
|--------|------|--------|-------|
| `*` (wildcard) | CNAME | `86c6d6ed-...cfargotunnel.com` | Covers all subdomains |
| `dokploy` | CNAME | `86c6d6ed-...cfargotunnel.com` | Legacy specific |

**Tunnel Ingress Rules:**
```
dokploy.arisegroup-tools.com → http://localhost:3000
n8n.arisegroup-tools.com → http://localhost:5678
[other specific routes...]
*.arisegroup-tools.com → http://localhost:80  (Traefik)
(catch-all) → http_status:404
```

**Important:** The wildcard route MUST be last before the catch-all. Specific routes take priority over wildcard.

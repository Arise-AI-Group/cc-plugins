---
name: infrastructure
description: This skill should be used when the user asks to "deploy to Dokploy", "configure DNS", "set up tunnel", "manage containers", "create sandbox", "set up demo instance". Manages team infrastructure with Cloudflare DNS/tunnels and Dokploy containers.
---

# Team Infrastructure

## Trigger Phrases

- "deploy n8n for [name]"
- "set up team sandbox"
- "create demo instance"
- "infrastructure", "dokploy", "cloudflare"
- Any request about team member development environments

## Overview

This directive manages team demo infrastructure using Dokploy for container orchestration and Cloudflare for DNS and tunnel routing.

## Architecture

### Two-Tier Design

| Tier | Instance | Stack | Why |
|------|----------|-------|-----|
| **Production** | `n8n.arisegroup-tools.com` | PostgreSQL + Redis + Worker | Business-critical, concurrent use |
| **Sandboxes** | `{xx}-n8n.arisegroup-tools.com` | SQLite only | Single-user dev, disposable |
| **Demos** | `{name}.arisegroup-tools.com` | Varies | Just-in-time sales demos |

### Routing Architecture

Traffic flows: **Browser** → **Cloudflare (TLS)** → **Tunnel** → **Traefik** → **Container**

Key points:
- Cloudflare handles TLS termination (HTTPS to users)
- Wildcard DNS means no new DNS records needed per service
- Traefik routes by hostname to containers on `dokploy-network`
- New services only need domain added in DokPloy UI

---

## Execution Tools

### Cloudflare API (`tool/cloudflare_api.py`)

```bash
# DNS Management
./run tool/cloudflare_api.py zones list
./run tool/cloudflare_api.py dns list example.com
./run tool/cloudflare_api.py dns create example.com <subdomain> <tunnel-id>.cfargotunnel.com --proxied

# Tunnel Management
./run tool/cloudflare_api.py tunnel list
./run tool/cloudflare_api.py tunnel config <tunnel-id>
./run tool/cloudflare_api.py tunnel route-add <tunnel-id> <hostname> http://localhost:<port>
```

For detailed Cloudflare operations, see [references/cloudflare-operations.md](references/cloudflare-operations.md).

### Dokploy API (`tool/dokploy_api.py`)

```bash
# Compose operations
./run tools/dokploy_api.py compose create <environment_id> <name> --file compose.yaml
./run tools/dokploy_api.py compose deploy <compose_id>
./run tools/dokploy_api.py compose get <compose_id> -v
./run tools/dokploy_api.py compose start <compose_id>
./run tools/dokploy_api.py compose stop <compose_id>
```

For detailed Dokploy operations and user management, see [references/dokploy-operations.md](references/dokploy-operations.md).

---

## Common Workflows

### Adding a New Demo/Service (Traefik-routed)

With wildcard DNS + Traefik routing, adding new services is simple:

1. **Create compose in DokPloy** (UI or API)
2. **Add domain in DokPloy**:
   - Host: `myservice.arisegroup-tools.com`
   - Port: container's internal port
   - **HTTPS: OFF** (Cloudflare handles HTTPS)
3. **Redeploy the service** - Regenerates Traefik labels
4. URL works immediately!

### Adding a Legacy Sandbox (Direct Route)

For services needing direct port access (bypassing Traefik):

1. Choose a unique port
2. Add tunnel route: `./run tool/cloudflare_api.py tunnel route-add <tunnel-id> <hostname> http://localhost:<port>`
3. Create compose in DokPloy with host port mapping
4. Deploy and verify

### Deployment Checklist

Before deploying any new service via Traefik:

- [ ] Compose has `dokploy-network` with `external: true`
- [ ] Public service on both `dokploy-network` + `internal` networks
- [ ] Internal services (db, cache) on `internal` only
- [ ] Domain added with **HTTPS: OFF**
- [ ] Redeployed after adding domain

---

## Multi-Container Networking

When adding a domain to a compose service, DokPloy moves the main service to `dokploy-network`. Dependent services stay isolated, breaking inter-container communication.

**Solution: Dual-Network Pattern**
- Public-facing service: both `dokploy-network` AND `internal`
- Internal services (db, cache): `internal` only

For detailed networking patterns and troubleshooting, see [references/networking-patterns.md](references/networking-patterns.md).

For compose templates, see [examples/compose-templates.md](examples/compose-templates.md).

---

## Environment Variables

Required in `~/.config/cc-plugins/.env`:

```
CLOUDFLARE_API_TOKEN=...
CLOUDFLARE_ACCOUNT_ID=...
DOKPLOY_API_KEY=...
DOKPLOY_URL=https://dokploy.arisegroup-tools.com
```

---

## Additional Resources

- [references/cloudflare-operations.md](references/cloudflare-operations.md) - DNS and tunnel management
- [references/dokploy-operations.md](references/dokploy-operations.md) - Compose and user permissions
- [references/networking-patterns.md](references/networking-patterns.md) - Multi-container networking, Traefik config
- [references/supabase-setup.md](references/supabase-setup.md) - Dev Supabase instance documentation
- [examples/compose-templates.md](examples/compose-templates.md) - Docker compose templates

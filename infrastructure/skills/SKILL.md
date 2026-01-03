---
name: infrastructure
description: Manage team infrastructure with Cloudflare DNS/tunnels and Dokploy containers. Use when the user asks about infrastructure operations, management, or automation.
---

# Team Infrastructure

## When to Use
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
| **Production** | `n8n.arisegroup-tools.com` | PostgreSQL + Redis + Worker | Business-critical, concurrent use, scalability |
| **Sandboxes** | `{xx}-n8n.arisegroup-tools.com` | SQLite only | Single-user dev, simple, disposable |
| **Demos** | `{name}.arisegroup-tools.com` | Varies | Just-in-time sales demos |

### Routing Architecture

Traffic flows: **Browser** → **Cloudflare (TLS)** → **Tunnel** → **Traefik** → **Container**

```
*.arisegroup-tools.com (wildcard DNS)
        ↓
Cloudflare Tunnel (86c6d6ed-...)
        ↓
    ┌─────────────────────────────────────┐
    │ Specific routes (legacy services):  │
    │   dokploy.* → localhost:3000        │
    │   n8n.* → localhost:5678            │
    │   ca-n8n.* → localhost:5679         │
    │   etc.                              │
    ├─────────────────────────────────────┤
    │ Wildcard route (new services):      │
    │   *.* → localhost:80 (Traefik)      │
    └─────────────────────────────────────┘
        ↓
Traefik (dokploy-network)
        ↓
Container (by hostname match)
```

**Key points:**
- Cloudflare handles TLS termination (HTTPS to users)
- Wildcard DNS means no new DNS records needed per service
- Traefik routes by hostname to containers on `dokploy-network`
- New services only need domain added in DokPloy UI

---

## Tools Reference

### Cloudflare API (`tool/cloudflare_api.py`)

**DNS Management:**
```bash
./run tools/cloudflare_api.py zones list
./run tools/cloudflare_api.py dns list example.com
./run tools/cloudflare_api.py dns create example.com <subdomain> <tunnel-id>.cfargotunnel.com --proxied
./run tools/cloudflare_api.py dns delete example.com <record-id>
```

**Tunnel Management:**
```bash
./run tools/cloudflare_api.py tunnel list
./run tools/cloudflare_api.py tunnel config <tunnel-id>
./run tools/cloudflare_api.py tunnel route-add <tunnel-id> <hostname> http://localhost:<port>
./run tools/cloudflare_api.py tunnel route-remove <tunnel-id> <hostname>
```

### Dokploy API (`tool/dokploy_api.py`)

```bash
./run tools/dokploy_api.py compose create <environment_id> <name> --file compose.yaml
./run tools/dokploy_api.py compose update <compose_id> --yaml "..." --env "KEY=value"
./run tools/dokploy_api.py compose deploy <compose_id>
./run tools/dokploy_api.py compose get <compose_id> -v
./run tools/dokploy_api.py compose start <compose_id>
./run tools/dokploy_api.py compose stop <compose_id>
./run tools/dokploy_api.py compose delete <compose_id>
```

### Dokploy User Management (via curl)

**List all users and their permissions:**
```bash
curl -s -H "x-api-key: $DOKPLOY_API_KEY" "$DOKPLOY_URL/user.all" | python3 -m json.tool
```

**Assign permissions to a user:**
```bash
curl -s -X POST -H "x-api-key: $DOKPLOY_API_KEY" -H "Content-Type: application/json" \
  "$DOKPLOY_URL/user.assignPermissions" -d '{
  "id": "<user-id>",
  "canCreateProjects": true,
  "canCreateServices": true,
  "canDeleteProjects": true,
  "canDeleteServices": true,
  "canAccessToDocker": true,
  "canAccessToAPI": true,
  "canAccessToSSHKeys": true,
  "canAccessToGitProviders": true,
  "canAccessToTraefikFiles": true,
  "canCreateEnvironments": true,
  "canDeleteEnvironments": true,
  "accessedProjects": [],
  "accessedEnvironments": [],
  "accessedServices": []
}'
```

**Get user ID:** Run `user.all` and find the `userId` field for the target user.

---

## User Permissions

### Roles vs Permissions (Known Bug)

DokPloy has three roles: **Owner**, **Admin**, and **Member**.

**Bug:** Promoting a user to "Admin" via the UI does NOT automatically enable their granular permissions. The `role` field changes to "admin" but all `canCreate*`, `canDelete*`, `canAccess*` flags remain `false`.

**Symptoms:**
- User is shown as "Admin" in Settings → Users
- User can see existing projects
- User cannot create new projects/services (buttons missing)

**Fix:** Use the API to explicitly set permissions:
1. Get the user's ID via `user.all`
2. Call `user.assignPermissions` with all flags set to `true`
3. Have the user log out and back in

### Permission Flags

| Flag | What it controls |
|------|------------------|
| `canCreateProjects` | Create new projects |
| `canDeleteProjects` | Delete projects |
| `canCreateServices` | Add services to projects |
| `canDeleteServices` | Remove services |
| `canCreateEnvironments` | Add environments |
| `canDeleteEnvironments` | Remove environments |
| `canAccessToDocker` | View Docker tab |
| `canAccessToAPI` | Generate API keys |
| `canAccessToSSHKeys` | Manage SSH keys |
| `canAccessToGitProviders` | Configure GitHub/GitLab |
| `canAccessToTraefikFiles` | Edit Traefik config |

---

## Deployment Workflow

### Adding a New Demo/Service (Simplified)

With wildcard DNS + Traefik routing, adding new services is simple:

1. **Create compose in DokPloy** (UI or API)
2. **Add domain in DokPloy**:
   - Go to service → Domains → Add Domain
   - Enter hostname (e.g., `acme-demo.arisegroup-tools.com`)
   - Port: container's internal port (e.g., 5678 for n8n)
   - Service name: the service name from docker-compose
   - **HTTPS: OFF** (Cloudflare handles HTTPS; enabling causes redirect loops)
3. **Redeploy the service** - This regenerates Traefik labels with the new domain
4. URL works immediately!

**Via API:**
```bash
# Add domain to compose service
# IMPORTANT: Use https: false to avoid redirect loops (Cloudflare handles HTTPS)
curl -s -X POST -H "x-api-key: $DOKPLOY_API_KEY" -H "Content-Type: application/json" \
  "$DOKPLOY_URL/domain.create" -d '{
  "composeId": "<compose-id>",
  "host": "my-demo.arisegroup-tools.com",
  "port": 5678,
  "serviceName": "n8n",
  "domainType": "compose",
  "https": false,
  "path": "/"
}'

# Redeploy to apply
curl -s -X POST -H "x-api-key: $DOKPLOY_API_KEY" -H "Content-Type: application/json" \
  "$DOKPLOY_URL/compose.deploy" -d '{"composeId":"<compose-id>"}'
```

### Adding a New Sandbox (Legacy with specific port)

For services that need direct port access (bypassing Traefik):

1. **Choose a unique port** (next available in sequence)
2. **Add tunnel route:**
   ```bash
   ./run tools/cloudflare_api.py tunnel route-add <tunnel-id> <initials>-n8n.arisegroup-tools.com http://localhost:<port>
   ```
3. **Create compose in DokPloy** with host port mapping
4. **Deploy and verify**

### Removing a Service

**Traefik-routed (new style):**
1. Delete domain in DokPloy (UI or API)
2. Stop/delete compose if no longer needed

**Direct-routed (legacy):**
1. Stop and delete compose in Dokploy
2. Remove tunnel route: `./run tools/cloudflare_api.py tunnel route-remove <tunnel_id> <hostname>`

### Deployment Checklist

Before deploying any new service via Traefik:

- [ ] **Check compose ownership** — Can you modify the docker-compose.yml?
  - YES → Continue with Traefik routing
  - NO → Use direct Cloudflare tunnel route instead
- [ ] **Add network config** to docker-compose.yml:
  - Add `dokploy-network` as external network
  - Public service: both `dokploy-network` + `internal`
  - Internal services (db, cache): `internal` only
- [ ] **Add domain in DokPloy**:
  - Host: `myservice.arisegroup-tools.com`
  - Port: container's internal port (e.g., 5678)
  - serviceName: matches service name in docker-compose.yml
  - **HTTPS: OFF** (Cloudflare handles HTTPS)
- [ ] **Redeploy the service** — Domain changes require redeploy
- [ ] **Verify connectivity** — Check logs for DNS resolution errors

---

## Cloudflare Configuration

### Current Setup

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

---

## Multi-Container Networking

### The Problem

When you add a domain to a compose service in DokPloy, it moves the **main service** to `dokploy-network` so Traefik can reach it. However, **dependent services** (postgres, redis) stay on the compose-specific network (e.g., `compose-xxx_default`). This breaks inter-container communication.

**Symptoms:**
- Main service returns 502 or connection errors
- Logs show DNS resolution failures: `getaddrinfo EAI_AGAIN postgres`
- Container can't reach `postgres`, `redis`, or other services by hostname

### The Solution: Dual-Network Pattern

Containers can be on **multiple networks**. The pattern:
- **Public-facing service**: On both `dokploy-network` (Traefik routing) AND `internal` (database access)
- **Internal services** (db, cache): On `internal` only (isolated from other projects)

```
┌─────────────────────────────────────────────────┐
│                 dokploy-network                  │
│  ┌─────────┐  ┌─────────┐  ┌─────────┐         │
│  │ Traefik │  │ proj-A  │  │ proj-B  │         │
│  │         │  │  app    │  │  app    │         │
│  └─────────┘  └────┬────┘  └────┬────┘         │
└────────────────────┼────────────┼──────────────┘
                     │            │
         ┌───────────┴───┐  ┌─────┴───────────┐
         │ proj-A internal│  │ proj-B internal │
         │  ┌──────────┐  │  │  ┌──────────┐  │
         │  │ postgres │  │  │  │ postgres │  │
         │  └──────────┘  │  │  └──────────┘  │
         └────────────────┘  └────────────────┘
              ISOLATED            ISOLATED
```

**Key benefits:**
- Traefik routes to apps via `dokploy-network`
- Apps talk to their databases via `internal`
- proj-A cannot reach proj-B's postgres (different internal networks)

### Decision Tree: Traefik vs Direct Route

```
Is the service from a repo you can modify?
├── YES → Can you add network config to docker-compose.yml?
│   ├── YES → Use Traefik routing (add domain in DokPloy)
│   └── NO → Use direct Cloudflare tunnel route
└── NO (external repo) → Use direct Cloudflare tunnel route
```

**Use Traefik routing when:**
- You control the docker-compose.yml
- No unique port needed
- Want simplified domain management

**Use direct Cloudflare tunnel route when:**
- External repo you can't modify
- Service needs specific port access
- Legacy services already configured

---

## Compose Templates

### Single-Container (Sandboxes, Traefik-routed)

```yaml
services:
  n8n:
    image: n8nio/n8n:latest
    restart: unless-stopped
    networks:
      - dokploy-network
    environment:
      - DB_TYPE=sqlite
      - N8N_HOST=${N8N_HOST}
      - N8N_PROTOCOL=https
    volumes:
      - n8n_data:/home/node/.n8n

networks:
  dokploy-network:
    external: true

volumes:
  n8n_data:
```

**Note:** No `ports:` mapping needed—Traefik routes by hostname to container's internal port.

### Multi-Container (Production, Traefik-routed)

```yaml
services:
  n8n:
    image: n8nio/n8n:latest
    restart: unless-stopped
    networks:
      - dokploy-network
      - internal
    environment:
      - NODE_ENV=production
      - DB_TYPE=postgresdb
      - DB_POSTGRESDB_HOST=postgres
      - EXECUTIONS_MODE=queue
      - QUEUE_BULL_REDIS_HOST=redis
    depends_on:
      - postgres
      - redis

  n8n-worker:
    image: n8nio/n8n:latest
    restart: always
    command: worker
    networks:
      - internal
    depends_on:
      - n8n
      - redis

  redis:
    image: redis:7-alpine
    restart: unless-stopped
    networks:
      - internal

  postgres:
    image: postgres:17-alpine
    restart: unless-stopped
    networks:
      - internal

networks:
  dokploy-network:
    external: true
  internal:
    # Private to this compose - other projects can't access

volumes:
  n8n_data:
  postgres_data:
  redis_data:
```

### Legacy Sandbox (Direct route, host port)

For services that need direct Cloudflare tunnel routing (bypassing Traefik):

```yaml
services:
  n8n:
    image: n8nio/n8n:latest
    restart: unless-stopped
    ports:
      - "${HOST_PORT}:5678"
    environment:
      - DB_TYPE=sqlite
      - N8N_HOST=${N8N_HOST}
      - N8N_PROTOCOL=https
    volumes:
      - n8n_data:/home/node/.n8n

volumes:
  n8n_data:
```

**Note:** Requires unique `HOST_PORT` per service and corresponding Cloudflare tunnel route.

---

## Learnings & Edge Cases

### Traefik Network Connectivity
**Issue:** New domains added via DokPloy returned 504 Gateway Timeout.
**Cause:** Traefik container was not connected to `dokploy-network` where app containers run.
**Solution:** Connect Traefik to the network:
```bash
docker network connect dokploy-network dokploy-traefik
```
**Note:** This may need to be re-run if Traefik is recreated.

### Traefik TLS Configuration
**Issue:** Wildcard tunnel route to `https://localhost:443` returned 404.
**Cause:** Traefik's websecure entrypoint expected TLS certificates, but Let's Encrypt challenges failed (traffic routed to containers, not Traefik).
**Solution:** Route to HTTP port 80 instead. Cloudflare handles TLS to users, Traefik uses HTTP internally.

### Port Conflicts (Legacy)
**Issue:** All sandboxes initially used port 5678, causing deployment failures.
**Solution:** For direct-routed services, each must have a unique host port. For Traefik-routed services, no port mapping needed - Traefik routes by hostname.

### Deploy vs Start
**Issue:** `compose deploy` sometimes errors but containers start successfully.
**Solution:** If deploy shows "error" status, try `compose start` - the containers may have already been created.

### SQLite vs PostgreSQL
- **SQLite:** Fine for single-user sandboxes. All data stored in single file.
- **PostgreSQL:** Required for production with queue mode (workers). Enables concurrent access.

### Admin Role Doesn't Grant Permissions
**Issue:** Added user as Admin, but they couldn't create projects (no buttons visible).
**Cause:** DokPloy bug - setting role to "admin" doesn't enable the granular permission flags.
**Solution:** Use `user.assignPermissions` API to explicitly enable all `canCreate*`, `canDelete*`, `canAccess*` flags. See "User Permissions" section above.

### Domain Type for Compose Services
**Issue:** Domain added via API with wrong `domainType` didn't route correctly.
**Solution:** For compose services, always use `domainType: "compose"` and specify `serviceName` matching the service name in docker-compose.yml.

### HTTPS Redirect Loop
**Issue:** New domains via Traefik return 301/308 redirect loop.
**Cause:** Domain configured with `https: true` in DokPloy adds `redirect-to-https` middleware. But Cloudflare already handles HTTPS externally and sends HTTP to Traefik, causing infinite redirect.
**Solution:** Always set `https: false` for domains when using Cloudflare tunnel + Traefik. Cloudflare provides HTTPS to users; Traefik handles HTTP internally.

### Domain Changes Require Redeploy
**Issue:** Added or modified domain in DokPloy but URL returns 404.
**Cause:** Traefik routes are generated from Docker labels when the container starts. Adding a domain in DokPloy UI doesn't automatically update the running container's labels.
**Solution:** After adding or modifying a domain, **redeploy the compose service** to regenerate Traefik labels.

### External Repos Without Network Config
**Issue:** Service from external GitHub repo returns 404 via Traefik even with domain configured correctly.
**Cause:** The docker-compose.yml has no network config, so the container only runs on the default compose network—not `dokploy-network`. Traefik can't discover or route to it.
**Solution:** If you can't modify the compose file, use a **direct Cloudflare tunnel route** instead of Traefik routing. Add a specific route in the tunnel config pointing to the container's host port.

### Multi-Container Network Isolation
**Issue:** After adding domain to multi-container compose, main service can't reach database (DNS resolution fails).
**Cause:** DokPloy moves the main service to `dokploy-network` for Traefik, but dependencies stay on the compose-default network. They're on different networks and can't communicate.
**Solution:** Use the dual-network pattern—configure the public service on both `dokploy-network` AND an `internal` network, with dependencies on `internal` only. See "Multi-Container Networking" section above.


---

# Dev Supabase Setup

## Quick Reference

| Item | Value |
|------|-------|
| **Studio URL** | https://dev-supabase.arisegroup-tools.com/project/default |
| **API URL** | https://dev-supabase.arisegroup-tools.com |
| **Dashboard User** | `supabase` |
| **Dashboard Password** | See `SECRETS.md` |

**Keys** (also in `.env`):
- `DEV_SUPABASE_URL`
- `DEV_SUPABASE_ANON_KEY`
- `DEV_SUPABASE_SERVICE_ROLE_KEY`

---

## Database Connection (Direct PostgreSQL)

For bulk operations from n8n or other services on the same Dokploy server.

| Setting | Value |
|---------|-------|
| **Host** | `host.docker.internal` (from containers) |
| **Port** | `5432` |
| **Database** | `postgres` |
| **User** | `postgres` |
| **Password** | See `SECRETS.md` |

**Connection String:** See `SECRETS.md`

**When to use Direct vs REST API:**
| Use Case | Recommended |
|----------|-------------|
| Bulk sync (1000s of records) | Direct PostgreSQL |
| n8n Jobber sync workflow | Direct PostgreSQL |
| Simple CRUD operations | REST API |
| Client-side apps | REST API (with RLS) |
| Complex SQL/analytics | Direct PostgreSQL |

---

## Setup Checklist

**Completed:**
- [x] Deploy Supabase on Dokploy
- [x] Configure dev URLs (`dev-supabase.arisegroup-tools.com`)
- [x] Add domain routing via Traefik
- [x] Create Jobber schema SQL (`extras/sql/jobber_schema.sql`)
- [x] Document credentials and connection info

**Manual Steps (in Studio):**
- [ ] Enable pgvector: `CREATE EXTENSION IF NOT EXISTS vector;`
- [ ] Run Jobber schema SQL (copy from `extras/sql/jobber_schema.sql`)

**Next Session:**
- [ ] Connect n8n to Supabase (Direct PostgreSQL)
- [ ] Install Jobber nodes in n8n (`@arisegroup/n8n-nodes-jobber`)
- [ ] Build Jobber → Supabase sync workflow
- [ ] Build vector embeddings workflow

---

## Manual Steps Required

### 1. Enable pgvector

1. Open [Supabase Studio](https://dev-supabase.arisegroup-tools.com/project/default)
2. Go to **SQL Editor**
3. Run:
   ```sql
   CREATE EXTENSION IF NOT EXISTS vector;
   ```

### 2. Run Jobber Schema

1. Open [Supabase Studio SQL Editor](https://dev-supabase.arisegroup-tools.com/project/default/sql)
2. Copy contents of `extras/sql/jobber_schema.sql`
3. Paste and run

---

## Dokploy Details

| Property | Value |
|----------|-------|
| **Compose ID** | `NMv-4GR1dXZb9PTcTyqhd` |
| **Project** | `services-sandbox` |
| **Environment** | `production` |
| **Status** | Running |

### View/Manage via CLI
```bash
./run modules/infrastructure/tool/dokploy_api.py compose get NMv-4GR1dXZb9PTcTyqhd -v
```

---

## API Usage Examples

### REST API (with anon key)
```bash
curl -H "apikey: $DEV_SUPABASE_ANON_KEY" \
     -H "Authorization: Bearer $DEV_SUPABASE_ANON_KEY" \
     "https://dev-supabase.arisegroup-tools.com/rest/v1/jobber_clients?limit=10"
```

### Insert Data (with service role key)
```bash
curl -X POST \
     -H "apikey: $DEV_SUPABASE_SERVICE_ROLE_KEY" \
     -H "Authorization: Bearer $DEV_SUPABASE_SERVICE_ROLE_KEY" \
     -H "Content-Type: application/json" \
     -d '{"jobber_id": "123", "name": "Test Client", "data": {}}' \
     "https://dev-supabase.arisegroup-tools.com/rest/v1/jobber_clients"
```

### Auth Health Check
```bash
curl "https://dev-supabase.arisegroup-tools.com/auth/v1/health"
```

---

## Troubleshooting

### 401 Unauthorized
- Ensure you're passing the `apikey` header
- Check that the key hasn't expired (JWT exp claim)

### 502 Bad Gateway
- Check if Supabase containers are running in Dokploy
- Verify Traefik is connected to `dokploy-network`

### Database Connection Issues
- Internal services communicate via container names (db, kong, etc.)
- External access is through the Kong API gateway only

---

## Related Files

- Schema: `extras/sql/jobber_schema.sql`
- Env vars: `.env` (DEV_SUPABASE_* entries)
- Plan: `.claude/plans/zany-chasing-wilkinson.md`


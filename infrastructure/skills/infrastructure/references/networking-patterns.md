# Networking Patterns Reference

## Multi-Container Networking

### The Problem

When adding a domain to a compose service in DokPloy, it moves the **main service** to `dokploy-network` so Traefik can reach it. However, **dependent services** (postgres, redis) stay on the compose-specific network. This breaks inter-container communication.

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

---

## Decision Tree: Traefik vs Direct Route

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
**Cause:** Traefik's websecure entrypoint expected TLS certificates, but Let's Encrypt challenges failed.
**Solution:** Route to HTTP port 80 instead. Cloudflare handles TLS to users, Traefik uses HTTP internally.

### Port Conflicts (Legacy)
**Issue:** All sandboxes initially used port 5678, causing deployment failures.
**Solution:** For direct-routed services, each must have a unique host port. For Traefik-routed services, no port mapping needed.

### Deploy vs Start
**Issue:** `compose deploy` sometimes errors but containers start successfully.
**Solution:** If deploy shows "error" status, try `compose start` - the containers may have already been created.

### SQLite vs PostgreSQL
- **SQLite:** Fine for single-user sandboxes. All data stored in single file.
- **PostgreSQL:** Required for production with queue mode (workers). Enables concurrent access.

### Admin Role Doesn't Grant Permissions
**Issue:** Added user as Admin, but they couldn't create projects.
**Cause:** DokPloy bug - setting role to "admin" doesn't enable the granular permission flags.
**Solution:** Use `user.assignPermissions` API to explicitly enable all `canCreate*`, `canDelete*`, `canAccess*` flags.

### Domain Type for Compose Services
**Issue:** Domain added via API with wrong `domainType` didn't route correctly.
**Solution:** For compose services, always use `domainType: "compose"` and specify `serviceName`.

### HTTPS Redirect Loop
**Issue:** New domains via Traefik return 301/308 redirect loop.
**Cause:** Domain configured with `https: true` causes infinite redirect since Cloudflare already handles HTTPS.
**Solution:** Always set `https: false` for domains when using Cloudflare tunnel + Traefik.

### Domain Changes Require Redeploy
**Issue:** Added domain in DokPloy but URL returns 404.
**Cause:** Traefik routes are generated from Docker labels when the container starts.
**Solution:** After adding or modifying a domain, **redeploy the compose service**.

### External Repos Without Network Config
**Issue:** Service from external GitHub repo returns 404 via Traefik.
**Cause:** The docker-compose.yml has no network config, so the container isn't on `dokploy-network`.
**Solution:** Use a **direct Cloudflare tunnel route** instead of Traefik routing.

### Multi-Container Network Isolation
**Issue:** After adding domain, main service can't reach database.
**Cause:** DokPloy moves main service to `dokploy-network`, dependencies stay on default network.
**Solution:** Use dual-network pattern (see above).

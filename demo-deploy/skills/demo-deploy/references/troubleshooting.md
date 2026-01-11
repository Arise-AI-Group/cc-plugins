# Demo Deploy Troubleshooting

## Error Reference

| Error | Cause | Fix |
|-------|-------|-----|
| 404 | Domain not added or needs redeploy | Redeploy: `./run tool/demo_deploy.py redeploy <name>` |
| 502 | Can't reach database (`getaddrinfo EAI_AGAIN`) | Use dual-network pattern: app on both networks, db on internal only |
| 301 loop | HTTPS enabled in Dokploy | Go to Dokploy UI → Domain → Set HTTPS to OFF |
| 504 | Traefik not on dokploy-network | SSH to server: `docker network connect dokploy-network dokploy-traefik` |
| Build fails | Dockerfile or compose issue | Check Dokploy logs for build errors |
| "user not specified" | GitHub source missing `owner` field | See GitHub Configuration reference |
| GitHub pull fails | Wrong `githubId` or no access | Verify GitHub provider has access to repo |
| "Repository not found" | Private repo not in GitHub App's access list | See Private Repository Access section |

---

## Common Issues

### Domain Returns 404

**Symptoms:** URL returns 404, service appears running in Dokploy

**Solutions:**
1. Verify domain was added in Dokploy
2. Check `serviceName` matches service in docker-compose.yml
3. **Redeploy** - domain changes require redeploy to update Traefik labels

### 502 Bad Gateway

**Symptoms:** Main app can't reach database containers

**Cause:** DokPloy moved app to `dokploy-network` but dependencies stayed on default network

**Fix:** Use dual-network pattern in docker-compose.yml:
```yaml
services:
  app:
    networks:
      - dokploy-network  # For Traefik
      - internal         # For database access
  postgres:
    networks:
      - internal         # Isolated
```

### HTTPS Redirect Loop

**Symptoms:** Browser shows too many redirects

**Cause:** Domain configured with `https: true` causes infinite redirect (Cloudflare already handles HTTPS)

**Fix:** Set HTTPS to OFF in Dokploy domain settings

### GitHub Repository Not Found

**Symptoms:** Deployment fails with "Repository not found" error

**Cause:** GitHub App doesn't have access to the private repository

**Fix:** See [github-configuration.md](github-configuration.md) for solutions

---

## Debugging Commands

```bash
# Check if demo exists
./run tool/demo_deploy.py list | grep <name>

# Get compose details
./run tool/demo_deploy.py list -v

# Validate compose file
./run tool/demo_deploy.py validate docker-compose.yml

# Check GitHub access
./run tool/demo_deploy.py github-debug --list-repos --check-repo owner/repo

# Check subdomain availability
./run tool/demo_deploy.py check <slug>
```

---

## Environment Variables

### View Current Env Vars
```bash
./run tool/demo_deploy.py env <name> --show
```

### Push from .env File
```bash
./run tool/demo_deploy.py env <name> --file .env
```
Note: This will redeploy automatically.

### Set Single Variable
```bash
./run tool/demo_deploy.py env <name> --set DATABASE_URL=postgres://...
```

### Best Practices
- **Never commit** `.env` files with secrets to GitHub
- Store sensitive values in Dokploy only
- Reference vars in docker-compose.yml with `${VAR_NAME}`
- Changes require redeploy (tool does this automatically)

---
name: demo-deploy
description: This skill should be used when the user asks to "deploy demo for client", "set up demo at subdomain", "push to demo", "redeploy demo", "update demo". Deploys demo applications to Dokploy with GitHub integration and Traefik routing.
---

# Demo Deployment

## Purpose

Deploy demo applications to Dokploy with GitHub integration and Traefik routing. This runbook guides through an interactive deployment process with verification checkpoints.

## Trigger Phrases

- "deploy demo for [client]"
- "set up demo at [subdomain]"
- "push to demo"
- "update demo"
- "redeploy demo"

## Prerequisites

- Application code ready to deploy
- docker-compose.yml with proper networking (see validation below)
- GitHub repository (or will create one)
- Internal port known (what port does the app run on inside the container?)

---

## Quick Reference

```bash
# List existing demos
./run tool/demo_deploy.py list

# List projects and environments
./run tool/demo_deploy.py projects

# Create new project/environment
./run tool/demo_deploy.py create-env --project-name <name>

# Check if subdomain is available
./run tool/demo_deploy.py check <slug>

# Validate compose file
./run tool/demo_deploy.py validate [docker-compose.yml]

# Deploy new demo
./run tool/demo_deploy.py deploy \
  --environment <env-id> \
  --name <name> \
  --repo <owner/repo> \
  --subdomain <slug> \
  --port <port> \
  --service <service-name>

# Redeploy existing demo
./run tool/demo_deploy.py redeploy <name-or-id>

# Delete a demo (with safety checks)
./run tool/demo_deploy.py delete <name-or-id>

# Manage environment variables
./run tool/demo_deploy.py env <name> --show
./run tool/demo_deploy.py env <name> --file .env
./run tool/demo_deploy.py env <name> --set KEY=value

# Debug GitHub provider access
./run tool/demo_deploy.py github-debug --list-repos
```

---

## Interactive Deployment Workflow

### Phase 1: Pre-flight Checks

1. **Check existing demos:** `./run tool/demo_deploy.py list`
2. **Determine GitHub location:** org repo, personal, or existing
3. **Select environment:** `./run tool/demo_deploy.py projects`
4. **Choose subdomain:** `./run tool/demo_deploy.py check <slug>`
5. **Identify internal port:** (3000, 8080, 5000, etc.)
6. **Validate compose:** `./run tool/demo_deploy.py validate`

### Phase 2: Deployment

1. **Push to GitHub:** `gh repo create <owner>/<repo> --private --source=. --push`
2. **Deploy:**
   ```bash
   ./run tool/demo_deploy.py deploy \
     --environment "<env-id>" \
     --name "<demo-name>" \
     --repo "<owner/repo>" \
     --subdomain "<slug>" \
     --port <port> \
     --service "<service-name>"
   ```
3. **Verify:** Check `https://<slug>.arisegroup-tools.com`

### Phase 3: Post-deployment

1. **Set env vars:** `./run tool/demo_deploy.py env <name> --file .env`
2. **Report success:** Provide URL, Dokploy dashboard link, GitHub repo

---

## Deployment Checklist

**Before deploying:**
- [ ] Compose has `dokploy-network` with `external: true`
- [ ] Multi-container: public service on both networks
- [ ] Code pushed to GitHub
- [ ] Subdomain available

**After deploying:**
- [ ] Domain added with correct serviceName and port
- [ ] **HTTPS is OFF** (Cloudflare handles TLS)
- [ ] Redeployed after adding domain
- [ ] URL returns 200

---

## Architecture Reference

Traffic flows:
1. **Browser** → HTTPS to `slug.arisegroup-tools.com`
2. **Cloudflare** → TLS termination, routes to tunnel
3. **Cloudflare Tunnel** → Wildcard route to localhost:80
4. **Traefik** → Routes by hostname to container
5. **Container** → Serves the application

**No Cloudflare API interaction needed** - wildcard DNS handles all subdomains.

---

## Additional Resources

- [references/github-configuration.md](references/github-configuration.md) - GitHub provider setup, private repos
- [references/troubleshooting.md](references/troubleshooting.md) - Error codes and debugging
- [examples/compose-templates.md](examples/compose-templates.md) - Docker compose templates

---
name: demo-deploy
description: Deploy demo applications with GitHub integration and Traefik routing. Use when the user asks about demo-deploy operations, management, or automation.
---

# Demo Deployment

## Purpose

Deploy demo applications to Dokploy with GitHub integration and Traefik routing. This runbook guides through an interactive deployment process with verification checkpoints.

## When to Use

- "deploy demo for [client]"
- "set up demo at [subdomain]"
- "push to demo"
- "update demo"
- "redeploy demo"

## Prerequisites

- Application code ready to deploy
- docker-compose.yml with proper networking (see Compose Validation below)
- GitHub repository (or will create one)
- Internal port known (what port does the app run on inside the container?)

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
./run tool/demo_deploy.py github-debug --list-repos --check-repo owner/repo
```

---

## Interactive Deployment Workflow

### Phase 1: Pre-flight Checks

#### 1.1 Check for Existing Demos

**Ask the user:** "Should I check for existing demo instances that could be reused or updated?"

If yes, run:
```bash
./run tool/demo_deploy.py list
```

Present the list and ask:
- "Would you like to update an existing demo, or create a new one?"

If updating existing:
- Get the compose ID
- Skip to Phase 2, Step 2.3 (Configure GitHub source)

#### 1.2 Determine GitHub Location

**Ask the user:** "Where should the GitHub repo be?"

Options:
1. **Organization repo** - Create in a GitHub org (e.g., `arisegroup/demo-name`)
2. **Personal repo** - Create under personal account
3. **Already exists** - Repo already exists at a specific URL

Record the repository in `owner/repo` format.

**⚠️ Private Repo Limitation:** Private repos may fail with "Repository not found" when deployed via API. This happens because of GitHub App installation repository access settings. See [Private Repository Access](#private-repository-access) below for details and solutions.

#### 1.3 Select Environment

**List available environments:**
```bash
./run tool/demo_deploy.py projects
```

**Ask the user:** "Which environment should this demo be deployed to?"

Options:
1. Select from existing environments (present list with IDs)
2. **Create new project** - For client-specific or isolated demos

If creating new:
```bash
./run tool/demo_deploy.py create-env --project-name "<client>-demos"
```

This creates a project with a default "production" environment and returns the environment ID.

#### 1.4 Choose Subdomain Slug

**Suggest options** based on the project/demo name:
- `acme-demo` → suggests: `acme`, `acme-demo`, `ad-demo`

**Check availability:**
```bash
./run tool/demo_deploy.py check <slug>
```

If not available, suggest alternatives or ask user for a different slug.

**Final URL will be:** `https://<slug>.arisegroup-tools.com`

#### 1.5 Identify Internal Port

**Ask the user:** "What port does the application run on inside the container?"

Common defaults:
- Node.js: 3000
- Go/Java: 8080
- Python/Flask: 5000
- nginx: 80
- n8n: 5678

#### 1.6 Validate Compose File

**Run validation:**
```bash
./run tool/demo_deploy.py validate ./docker-compose.yml
```

If validation fails:
1. Show the errors to the user
2. **Do not proceed** until issues are fixed
3. Re-validate after fixes

**Required for valid compose:**
- `dokploy-network` declared with `external: true`
- At least one service connected to `dokploy-network`
- Database services (postgres, redis, etc.) should be on `internal` network only

---

### Phase 2: Deployment

#### 2.1 Push Code to GitHub

**Create repo and push (if new):**
```bash
gh repo create <owner>/<repo> --private --source=. --push
```

**Or if repo already exists:**
```bash
git remote add origin git@github.com:<owner>/<repo>.git
git push -u origin main
```

#### 2.2 Deploy to Dokploy

```bash
./run tool/demo_deploy.py deploy \
  --environment "<environment-id>" \
  --name "<demo-name>" \
  --repo "<owner/repo>" \
  --branch "main" \
  --subdomain "<slug>" \
  --port <internal-port> \
  --service "<main-service-name>"
```

This will:
1. Create a new compose service in Dokploy
2. Configure GitHub as the source
3. Add domain routing
4. Trigger deployment

#### 2.3 Verify Deployment

Wait for deployment to complete, then:

1. **Check the URL:** `https://<slug>.arisegroup-tools.com`
2. **Verify response:** Should return 200 (not 404, 502, or redirect loop)

If issues occur, see Troubleshooting section.

---

### Phase 3: Post-deployment

#### 3.1 Report Success

Provide the user with:
- **Live URL:** `https://<slug>.arisegroup-tools.com`
- **Dokploy dashboard:** Link to the compose service
- **GitHub repo:** `https://github.com/<owner>/<repo>`

#### 3.2 Set Environment Variables

If the app needs environment variables:

```bash
# View current env vars
./run tool/demo_deploy.py env <name> --show

# Push from .env file (will redeploy automatically)
./run tool/demo_deploy.py env <name> --file .env

# Set a single variable
./run tool/demo_deploy.py env <name> --set DATABASE_URL=postgres://...
```

**How it works:**
- Env vars are stored in Dokploy, NOT in the GitHub repo
- They're injected at runtime into all containers in the compose
- Reference them in `docker-compose.yml` with `${VAR_NAME}` syntax
- Changes require a redeploy to take effect (the tool does this automatically)

**Best practices:**
- **Never commit** `.env` files with secrets to GitHub
- Store sensitive values (API keys, passwords) in Dokploy only
- Use the local `.env` file as a template, push to Dokploy for deployment
- The tool masks sensitive values in output (SECRET, KEY, PASSWORD, TOKEN, API)

**Example docker-compose.yml using env vars:**
```yaml
services:
  app:
    build: .
    environment:
      - DATABASE_URL=${DATABASE_URL}
      - API_KEY=${API_KEY}
      - NODE_ENV=production  # Can hardcode non-sensitive values
```

#### 3.3 Note Other Follow-up Items

Common follow-ups:
- Webhook configuration for automatic deploys
- Database migrations to run
- SSL certificate verification

---

## Deployment Checklist

Before deploying, verify:

- [ ] Compose has `dokploy-network` with `external: true`
- [ ] Multi-container: public service on both networks, internal services on `internal` only
- [ ] Code pushed to GitHub repository
- [ ] Subdomain is available

After deploying, verify:

- [ ] Domain added with correct serviceName and port
- [ ] **HTTPS is OFF** in Dokploy domain settings (Cloudflare handles TLS)
- [ ] Redeployed after adding domain
- [ ] URL returns 200

---

## Troubleshooting

| Error | Cause | Fix |
|-------|-------|-----|
| 404 | Domain not added or needs redeploy | Redeploy: `./run tool/demo_deploy.py redeploy <name>` |
| 502 | Can't reach database (`getaddrinfo EAI_AGAIN`) | Use dual-network pattern: app on both networks, db on internal only |
| 301 loop | HTTPS enabled in Dokploy | Go to Dokploy UI → Domain → Set HTTPS to OFF |
| 504 | Traefik not on dokploy-network | SSH to server: `docker network connect dokploy-network dokploy-traefik` |
| Build fails | Dockerfile or compose issue | Check Dokploy logs for build errors |
| "user not specified" | GitHub source missing `owner` field | See GitHub Configuration below |
| GitHub pull fails | Wrong `githubId` or no access | Verify GitHub provider has access to repo |
| "Repository not found" | Private repo not in GitHub App's access list | See [Private Repository Access](#private-repository-access) - change to "All repositories" or add repo manually |

---

## GitHub Configuration

### API Requirements

When configuring GitHub source via API, Dokploy requires **three separate fields**:

| Field | Description | Example |
|-------|-------------|---------|
| `owner` | GitHub username or organization | `trent-40hero` |
| `repository` | Repository name only (not full path) | `hello-world-demo` |
| `githubId` | Dokploy's internal GitHub provider ID | `l_gapBHHy7IdsBEZZ5geK` |

**Common mistake:** Passing `owner/repo` in the `repository` field alone won't work.

### Multiple GitHub Providers

Dokploy can have multiple GitHub providers connected (different accounts/orgs). Each provider has a unique `githubId`.

**To find available GitHub providers:**
1. Go to Dokploy UI → Settings → Git Providers
2. Or check an existing GitHub-linked compose for its `githubId`

**The tool auto-detects `githubId`** by scanning existing GitHub-linked composes. If you have multiple providers, you may need to:
1. Link the repo via Dokploy UI first (which sets the correct provider)
2. Or manually specify the `githubId` in the API call

### GitHub Provider Setup

Before deploying GitHub-sourced demos:

1. **Install GitHub App in Dokploy:**
   - Dokploy UI → Settings → Git Providers → Add GitHub
   - Authorize via OAuth or install the GitHub App
   - Grant access to repos you want to deploy

2. **Verify repo access:**
   - The GitHub provider must have access to the target repository
   - For org repos: GitHub App must be installed on that org
   - For personal repos: OAuth must have access to that account

### Learnings from Testing

1. **UI vs API:** When linking GitHub via UI, Dokploy automatically sets `owner`, `repository`, and `githubId`. The API requires all three explicitly.

2. **Auto-detection:** The tool tries to auto-detect `githubId` from existing GitHub composes. This works if all your repos use the same GitHub account.

3. **Multiple accounts:** If deploying from different GitHub accounts/orgs, you may need to link via UI first or specify the correct `githubId`.

4. **fetchSourceType step:** After setting GitHub source via API (`compose.update`), you must call `compose.fetchSourceType` to actually clone the repository. The tool does this automatically.

### Private Repository Access

**Root Cause:** When Dokploy clones a GitHub repository, it uses an installation access token from the connected GitHub App. This token can **only access repositories that the GitHub App installation was granted access to**.

#### How GitHub App Installation Works

When you install the Dokploy GitHub App on your account, you choose between:
- **All repositories** - Token can access all current AND future repos
- **Only select repositories** (default) - Token can only access the specific repos you selected

**The Problem:** If you selected "Only select repositories" during installation, newly created repos are NOT automatically added to the access list. When you create a new private repo and try to deploy via API, Dokploy's token can't access it → "Repository not found" error.

**Why Public Repos Work:** GitHub returns "Repository not found" (not "Access denied") when a token lacks permission for private repos. For public repos, no special permission is needed to clone.

**Why UI Linking Works:** The Dokploy UI may use a different authentication flow (OAuth user token) that has broader access to your repositories.

#### Solutions

**Option 1: Change to "All repositories" (Recommended)**
1. Go to GitHub → Settings → Applications (or Integrations)
2. Find the Dokploy GitHub App → Click "Configure"
3. Under "Repository access", change from "Only select repositories" to "All repositories"
4. Save changes

This grants access to all current and future repos automatically.

**Option 2: Manually add each new repo**
1. Go to GitHub → Settings → Applications
2. Find the Dokploy GitHub App → Click "Configure"
3. Under "Repository access", add the new repo to the selection
4. Save changes
5. Then redeploy in Dokploy

**Option 3: Link via Dokploy UI**
1. Create the compose service via API (without GitHub source)
2. Go to Dokploy UI → Select the compose → General → GitHub
3. Link the private repo through the UI
4. Redeploy

**Option 4: Use public repos**
For demos and non-sensitive projects, use public repositories. They work reliably with API deployment.

#### Diagnosing with the Debug Command

Use the diagnostic command to verify GitHub provider access:

```bash
# Basic diagnostics
./run tool/demo_deploy.py github-debug

# List accessible repositories
./run tool/demo_deploy.py github-debug --list-repos

# Check if specific repo is accessible
./run tool/demo_deploy.py github-debug --list-repos --check-repo owner/repo
```

If the repo appears in the list with `(private)`, the GitHub App has access. If it doesn't appear, see solutions above.

#### Timing Issues with Newly Created Repos

**Important:** When you create a new private repository, the GitHub App's installation token might not have immediate access. This can cause "Repository not found" errors even with "All repositories" selected.

**Symptoms:**
- Brand new private repo fails to deploy
- Same repo works after making it public, then private again
- Repo appears in diagnostic tool but deployment fails

**Solutions:**
1. **Wait a few minutes** after creating the repo before deploying
2. **Use the diagnostic command** to verify the repo appears in the accessible list
3. **Make public temporarily** - Make the repo public, deploy once, then make it private again. This "registers" the repo with the GitHub App.

#### Verification

To check your GitHub App installation settings:
1. Go to https://github.com/settings/installations
2. Find the Dokploy app
3. Check the "Repository access" setting

If it shows "Only select repositories" with specific repos listed, that's the issue. Either add your new repo or switch to "All repositories".

---

## Compose Templates

### Single-Container (simple apps)

```yaml
services:
  app:
    build: .
    restart: unless-stopped
    networks:
      - dokploy-network
    environment:
      - NODE_ENV=production

networks:
  dokploy-network:
    external: true
```

### Multi-Container (with database)

```yaml
services:
  app:
    build: .
    restart: unless-stopped
    networks:
      - dokploy-network
      - internal
    environment:
      - DATABASE_URL=postgres://user:pass@postgres:5432/db
    depends_on:
      - postgres

  postgres:
    image: postgres:17-alpine
    restart: unless-stopped
    networks:
      - internal
    environment:
      - POSTGRES_USER=user
      - POSTGRES_PASSWORD=pass
      - POSTGRES_DB=db
    volumes:
      - postgres_data:/var/lib/postgresql/data

networks:
  dokploy-network:
    external: true
  internal:

volumes:
  postgres_data:
```

**Key points:**
- Public-facing service: both `dokploy-network` + `internal`
- Internal services (db, cache): `internal` only
- No `ports:` mapping needed for Traefik routing

---

## Architecture Reference

Traffic flows through:
1. **Browser** → HTTPS request to `slug.arisegroup-tools.com`
2. **Cloudflare** → TLS termination, routes to tunnel
3. **Cloudflare Tunnel** → Wildcard route to localhost:80
4. **Traefik** → Routes by hostname to container on `dokploy-network`
5. **Container** → Serves the application

**No Cloudflare API interaction needed** - wildcard DNS handles all subdomains automatically.


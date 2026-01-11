# GitHub Configuration Reference

## API Requirements

When configuring GitHub source via API, Dokploy requires **three separate fields**:

| Field | Description | Example |
|-------|-------------|---------|
| `owner` | GitHub username or organization | `trent-40hero` |
| `repository` | Repository name only (not full path) | `hello-world-demo` |
| `githubId` | Dokploy's internal GitHub provider ID | `l_gapBHHy7IdsBEZZ5geK` |

**Common mistake:** Passing `owner/repo` in the `repository` field alone won't work.

---

## Multiple GitHub Providers

Dokploy can have multiple GitHub providers connected (different accounts/orgs). Each provider has a unique `githubId`.

**To find available GitHub providers:**
1. Go to Dokploy UI → Settings → Git Providers
2. Or check an existing GitHub-linked compose for its `githubId`

**The tool auto-detects `githubId`** by scanning existing GitHub-linked composes.

---

## GitHub Provider Setup

Before deploying GitHub-sourced demos:

1. **Install GitHub App in Dokploy:**
   - Dokploy UI → Settings → Git Providers → Add GitHub
   - Authorize via OAuth or install the GitHub App
   - Grant access to repos you want to deploy

2. **Verify repo access:**
   - The GitHub provider must have access to the target repository
   - For org repos: GitHub App must be installed on that org
   - For personal repos: OAuth must have access to that account

---

## Private Repository Access

**Root Cause:** When Dokploy clones a GitHub repository, it uses an installation access token that can **only access repositories the GitHub App was granted access to**.

### How GitHub App Installation Works

When you install the Dokploy GitHub App, you choose between:
- **All repositories** - Token can access all current AND future repos
- **Only select repositories** (default) - Token can only access specific repos

**The Problem:** If you selected "Only select repositories", newly created repos are NOT automatically added. Deployment fails with "Repository not found".

**Why Public Repos Work:** No special permission needed to clone public repos.

### Solutions

**Option 1: Change to "All repositories" (Recommended)**
1. Go to GitHub → Settings → Applications
2. Find the Dokploy GitHub App → Configure
3. Change to "All repositories"
4. Save

**Option 2: Manually add each new repo**
1. GitHub → Settings → Applications → Dokploy → Configure
2. Add the new repo to selection
3. Save and redeploy

**Option 3: Link via Dokploy UI**
1. Create compose via API (without GitHub source)
2. Link private repo through Dokploy UI
3. Redeploy

**Option 4: Use public repos**
Public repos work reliably with API deployment.

### Diagnosing with Debug Command

```bash
# Basic diagnostics
./run tool/demo_deploy.py github-debug

# List accessible repositories
./run tool/demo_deploy.py github-debug --list-repos

# Check if specific repo is accessible
./run tool/demo_deploy.py github-debug --list-repos --check-repo owner/repo
```

### Timing Issues

New private repos might not have immediate access. Solutions:
1. Wait a few minutes after creating the repo
2. Use diagnostic command to verify access
3. Make public temporarily, deploy once, then make private

### Verification

Check GitHub App installation settings:
1. Go to https://github.com/settings/installations
2. Find the Dokploy app
3. Check "Repository access" setting

---

## Learnings from Testing

1. **UI vs API:** UI automatically sets all three fields. API requires all explicitly.
2. **Auto-detection:** Tool auto-detects `githubId` from existing composes.
3. **Multiple accounts:** Different accounts may need manual `githubId` specification.
4. **fetchSourceType step:** After setting source via API, must call `compose.fetchSourceType` to clone.

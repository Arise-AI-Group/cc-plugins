# /demo-deploy

Deploy demo applications to Dokploy with GitHub integration and Traefik routing.

## Variables

- $1: action or demo name
- $2: additional argument

## Subcommands

- `/demo-deploy` - Start interactive deployment workflow
- `/demo-deploy list` - List existing demo deployments
- `/demo-deploy projects` - List available projects and environments
- `/demo-deploy check <slug>` - Check if subdomain is available
- `/demo-deploy validate [file]` - Validate compose file for Traefik compatibility
- `/demo-deploy redeploy <name>` - Redeploy an existing demo

## Instructions

1. **Read the runbook first:** `modules/demo-deploy/runbook/demo_deploy.md`

2. **For interactive deployment (no args or just a name):**
   Follow the runbook's interactive workflow:
   - Check for existing demos
   - Ask about GitHub location
   - Select environment
   - Choose subdomain
   - Identify port
   - Validate compose
   - Deploy

3. **For subcommands** (list, check, validate, etc.):
   ```bash
   ./run tool/demo_deploy.py $1 $2
   ```

4. **Key verification points:**
   - Always validate compose file before deploying
   - Always check subdomain availability
   - Always ask user about GitHub location
   - Always confirm environment selection

## Report

- For deployments: Report the live URL, compose ID, and GitHub repo
- For list: Show all demos with their URLs and status
- For check: Confirm availability or suggest alternatives
- For validate: Show errors/warnings and fix instructions

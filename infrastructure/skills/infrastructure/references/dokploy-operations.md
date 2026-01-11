# Dokploy Operations Reference

## Compose Operations

### Create Compose
```bash
./run tools/dokploy_api.py compose create <environment_id> <name> --file compose.yaml
```

### Update Compose
```bash
./run tools/dokploy_api.py compose update <compose_id> --yaml "..." --env "KEY=value"
```

### Deploy Compose
```bash
./run tools/dokploy_api.py compose deploy <compose_id>
```

### Get Compose Details
```bash
./run tools/dokploy_api.py compose get <compose_id> -v
```

### Start/Stop Compose
```bash
./run tools/dokploy_api.py compose start <compose_id>
./run tools/dokploy_api.py compose stop <compose_id>
```

### Delete Compose
```bash
./run tools/dokploy_api.py compose delete <compose_id>
```

---

## User Management (via curl)

### List All Users
```bash
curl -s -H "x-api-key: $DOKPLOY_API_KEY" "$DOKPLOY_URL/user.all" | python3 -m json.tool
```

### Assign Permissions
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

## Domain Management (via curl)

### Add Domain to Compose Service
```bash
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

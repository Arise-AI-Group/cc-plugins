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
./run tool/dokploy_api.py compose get NMv-4GR1dXZb9PTcTyqhd -v
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

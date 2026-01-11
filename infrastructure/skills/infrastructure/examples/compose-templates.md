# Compose Templates

## Single-Container (Sandboxes, Traefik-routed)

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

**Note:** No `ports:` mapping needed - Traefik routes by hostname to container's internal port.

---

## Multi-Container (Production, Traefik-routed)

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

**Key points:**
- Public-facing service (`n8n`): both `dokploy-network` + `internal`
- Internal services (`postgres`, `redis`, `worker`): `internal` only
- No `ports:` mapping for Traefik routing

---

## Legacy Sandbox (Direct route, host port)

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

## Generic App with Database

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

---

## Template Checklist

Before deploying any compose file:

- [ ] `dokploy-network` declared with `external: true`
- [ ] Public service on both networks
- [ ] Internal services (db, cache) on `internal` only
- [ ] No `ports:` for Traefik-routed services
- [ ] Volumes declared for persistent data

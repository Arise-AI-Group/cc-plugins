# Demo Deploy Compose Templates

## Single-Container (Simple Apps)

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

**Key points:**
- No `ports:` mapping needed - Traefik routes by hostname
- Must have `dokploy-network` with `external: true`

---

## Multi-Container (With Database)

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
- No `ports:` mapping for Traefik routing

---

## With Redis Cache

```yaml
services:
  app:
    build: .
    restart: unless-stopped
    networks:
      - dokploy-network
      - internal
    environment:
      - REDIS_URL=redis://redis:6379
    depends_on:
      - redis

  redis:
    image: redis:7-alpine
    restart: unless-stopped
    networks:
      - internal

networks:
  dokploy-network:
    external: true
  internal:
```

---

## Next.js / Node.js App

```yaml
services:
  app:
    build: .
    restart: unless-stopped
    networks:
      - dokploy-network
    environment:
      - NODE_ENV=production
      - NEXT_TELEMETRY_DISABLED=1

networks:
  dokploy-network:
    external: true
```

**Internal port:** Usually 3000 for Next.js

---

## Python / Flask App

```yaml
services:
  app:
    build: .
    restart: unless-stopped
    networks:
      - dokploy-network
    environment:
      - FLASK_ENV=production

networks:
  dokploy-network:
    external: true
```

**Internal port:** Usually 5000 for Flask

---

## Validation Checklist

Before deploying, verify:

- [ ] `dokploy-network` declared with `external: true`
- [ ] At least one service connected to `dokploy-network`
- [ ] Database services on `internal` network only
- [ ] No hardcoded `ports:` for Traefik-routed services
- [ ] Environment variables use `${VAR_NAME}` syntax

**Validate with:**
```bash
./run tool/demo_deploy.py validate docker-compose.yml
```

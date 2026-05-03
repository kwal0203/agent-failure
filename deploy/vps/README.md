## VPS Deployment (Docker Compose)

### 1) Prepare env

```bash
cd /path/to/agent-failure/deploy/vps
cp .env.prod.example .env.prod
# edit .env.prod
```

### 2) Run DB migrations (from repo root)

```bash
cd /path/to/agent-failure
set -a && source deploy/vps/.env.prod && set +a
uv run alembic upgrade head
```

### 3) Configure domain

Edit `Caddyfile` and replace `api.yourdomain.com` with your real API domain.

### 4) Start services

```bash
cd /path/to/agent-failure/deploy/vps
docker compose -f docker-compose.prod.yml up -d --build
```

### 5) Verify

```bash
curl -i https://api.yourdomain.com/healthz
docker compose -f docker-compose.prod.yml ps
docker compose -f docker-compose.prod.yml logs -f control-plane-api
```

### Optional: enable Kubernetes-coupled workers

Only if this host has access/config for your Kubernetes runtime control-plane.

```bash
docker compose -f docker-compose.prod.yml --profile k8s-workers up -d
```

### Notes

- This deploy serves only API domain via Caddy.
- Frontend can remain on Vercel and call `https://api.yourdomain.com`.
- Ensure API CORS allowlist includes your frontend origin.

# Local Kind Runbook (Control-Plane + Workers + Lab Launch)

This runbook starts a local `kind` cluster, deploys the control-plane into Kubernetes, starts required workers on host, and verifies a lab can be launched and used from the UI.

## Prereqs

- Docker is running.
- `kind`, `kubectl`, `uv`, `node/npm` installed.
- Postgres container running and reachable from kind node (`172.17.0.1:5432`).
- Runtime image already built/pushed and selected in `deploy/k8s/staging/runtime-image.lock`.
- GHCR pull token available for cluster image pulls.

## 1) Start/Reset Kind Cluster

```bash
kind delete cluster --name agent-failure-staging || true
kind create cluster --name agent-failure-staging
kubectl config use-context kind-agent-failure-staging
```

```bash
kubectl get ns runtime-pool || kubectl create ns runtime-pool
```

## 2) Create Runtime GHCR Pull Secret

```bash
# export GHCR_TOKEN=... first
kubectl -n runtime-pool delete secret ghcr-pull --ignore-not-found
kubectl -n runtime-pool create secret docker-registry ghcr-pull \
  --docker-server=ghcr.io \
  --docker-username=kwal0203 \
  --docker-password="$GHCR_TOKEN"
```

## 3) Build + Push Control-Plane Image

```bash
./scripts/build_control_plane_image.sh
./scripts/push_control_plane_image.sh
```

Then update `deploy/k8s/staging/control-plane-deployment.yaml` to the new control-plane digest image.

## 4) Deploy Control-Plane Service + Deployment

```bash
kubectl apply -f deploy/k8s/staging/control-plane-service.yaml
kubectl apply -f deploy/k8s/staging/control-plane-deployment.yaml
kubectl -n runtime-pool rollout status deploy/control-plane
```

Check health from inside cluster:

```bash
kubectl -n runtime-pool logs deploy/control-plane --tail=100
```

## 5) Expose Control-Plane to Host (for frontend)

```bash
kubectl -n runtime-pool port-forward svc/control-plane 8000:8000
```

Keep that terminal open.

## 6) Start Host Workers

In new terminals:

```bash
uv run python -m apps.control_plane.src.interfaces.runtime.provisioning_worker
```

```bash
uv run python -m apps.evaluator.src.interfaces.runtime.evaluator_worker
```

Notes:
- Learner feedback worker is started by control-plane app lifespan.
- Provisioning worker now loads repo `.env`; restart it after env changes.

## 7) Start Frontend

```bash
cd apps/frontend
npm run dev
```

Ensure frontend API base URL points to `http://127.0.0.1:8000`.

## 8) Launch and Verify

1. Open frontend and click **Launch Lab**.
2. Confirm session reaches `ACTIVE`.
3. Send a prompt (for example: `List my inbox`).
4. Confirm transcript streams and learner feedback eventually appears after evaluator worker processes outbox items.

## 9) Quick Debug Commands

```bash
kubectl -n runtime-pool get pods,svc
kubectl -n runtime-pool logs deploy/control-plane --since=5m
kubectl -n runtime-pool get events --sort-by=.metadata.creationTimestamp | tail -n 30
```

Check runtime binding persisted:

```bash
docker exec -it agent-failure-postgres psql -U postgres -d agent_failure \
  -c "select session_id, status, base_url, last_error, updated_at from session_runtime_bindings order by updated_at desc limit 5;"
```

If runtime pods fail image pulls, verify `ghcr-pull` secret exists and pod spec has `imagePullSecrets`.

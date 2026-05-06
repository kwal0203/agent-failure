#!/usr/bin/env bash
set -euo pipefail

# Create an isolated Postgres for local dev cluster usage.
# Safe to re-run; uses kubectl apply.

NS="${NS:-runtime-pool}"
PG_NAME="${PG_NAME:-postgres-dev}"
PG_USER="${PG_USER:-postgres}"
PG_PASSWORD="${PG_PASSWORD:-devpass}"
PG_DB="${PG_DB:-agent_failure_dev}"
PG_STORAGE="${PG_STORAGE:-5Gi}"

need() {
  command -v "$1" >/dev/null 2>&1 || {
    echo "Missing required command: $1"
    exit 2
  }
}

need kubectl

kubectl get ns "$NS" >/dev/null 2>&1 || kubectl create ns "$NS" >/dev/null

cat <<YAML | kubectl apply -f -
apiVersion: v1
kind: Secret
metadata:
  name: ${PG_NAME}-auth
  namespace: ${NS}
type: Opaque
stringData:
  POSTGRES_USER: "${PG_USER}"
  POSTGRES_PASSWORD: "${PG_PASSWORD}"
  POSTGRES_DB: "${PG_DB}"
---
apiVersion: v1
kind: PersistentVolumeClaim
metadata:
  name: ${PG_NAME}-data
  namespace: ${NS}
spec:
  accessModes: ["ReadWriteOnce"]
  resources:
    requests:
      storage: ${PG_STORAGE}
---
apiVersion: v1
kind: Service
metadata:
  name: ${PG_NAME}
  namespace: ${NS}
spec:
  selector:
    app: ${PG_NAME}
  ports:
    - name: pg
      port: 5432
      targetPort: 5432
---
apiVersion: apps/v1
kind: Deployment
metadata:
  name: ${PG_NAME}
  namespace: ${NS}
spec:
  replicas: 1
  selector:
    matchLabels:
      app: ${PG_NAME}
  template:
    metadata:
      labels:
        app: ${PG_NAME}
    spec:
      containers:
        - name: postgres
          image: postgres:16-alpine
          ports:
            - containerPort: 5432
          envFrom:
            - secretRef:
                name: ${PG_NAME}-auth
          volumeMounts:
            - name: data
              mountPath: /var/lib/postgresql/data
          readinessProbe:
            exec:
              command: ["sh","-c","pg_isready -U \"$$POSTGRES_USER\" -d \"$$POSTGRES_DB\""]
            initialDelaySeconds: 5
            periodSeconds: 5
          livenessProbe:
            exec:
              command: ["sh","-c","pg_isready -U \"$$POSTGRES_USER\" -d \"$$POSTGRES_DB\""]
            initialDelaySeconds: 15
            periodSeconds: 10
      volumes:
        - name: data
          persistentVolumeClaim:
            claimName: ${PG_NAME}-data
YAML

echo "Waiting for ${PG_NAME} rollout..."
kubectl -n "$NS" rollout status deploy/"$PG_NAME"

echo ""
echo "Set this in your .env (or export before bootstrap):"
echo "DATABASE_URL_DEV=postgresql+psycopg://${PG_USER}:${PG_PASSWORD}@${PG_NAME}.${NS}.svc.cluster.local:5432/${PG_DB}"
echo ""
echo "Then run:"
echo "  ./scripts/bootstrap_dev_secrets_from_env.sh"

# External Secrets Setup (Staging/Production)

This enables automatic sync of `runtime-secrets` from AWS Secrets Manager into Kubernetes.

## What gets deployed via Flux

Per environment overlay (`deploy/k8s/staging`, `deploy/k8s/production`):

- External Secrets Operator (HelmRelease in `flux-system`)
- `SecretStore` in `runtime-pool` using AWS Secrets Manager
- `ExternalSecret` in `runtime-pool` targeting Kubernetes secret `runtime-secrets`

AWS secret names expected:

- Staging: `agent-failure/staging/runtime-secrets`
- Production: `agent-failure/prod/runtime-secrets`

## One-time bootstrap per cluster

Create AWS credentials secret used by External Secrets:

```bash
kubectl -n runtime-pool create secret generic aws-secretsmanager-credentials \
  --from-literal=access-key-id="$AWS_ACCESS_KEY_ID" \
  --from-literal=secret-access-key="$AWS_SECRET_ACCESS_KEY" \
  --dry-run=client -o yaml | kubectl apply -f -
```

Use an IAM user/role with minimum required policy:

- `secretsmanager:GetSecretValue`
- `secretsmanager:DescribeSecret`

Scoped to:

- `arn:aws:secretsmanager:us-east-2:<account-id>:secret:agent-failure/staging/runtime-secrets*`
- `arn:aws:secretsmanager:us-east-2:<account-id>:secret:agent-failure/prod/runtime-secrets*`

## Verify reconciliation

```bash
kubectl -n flux-system get helmrelease external-secrets
kubectl -n runtime-pool get secretstore aws-secretsmanager
kubectl -n runtime-pool get externalsecret runtime-secrets
kubectl -n runtime-pool describe externalsecret runtime-secrets
./scripts/check_k8s_secrets.sh
```

## Rotation/update flow

1. Update AWS Secrets Manager value.
2. Wait up to `refreshInterval` (5m) or force refresh:

```bash
kubectl -n runtime-pool annotate externalsecret runtime-secrets force-sync="$(date +%s)" --overwrite
```

3. Restart workloads if needed:

```bash
kubectl -n runtime-pool rollout restart deploy
```

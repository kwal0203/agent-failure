# External Secrets Reference (Staging/Production)

The repository no longer connects to or automatically reconciles a staging or
production cluster. These manifests are retained as an optional reference for
operators who choose to install Flux and External Secrets Operator themselves.
They demonstrate syncing `runtime-secrets` from AWS Secrets Manager into
Kubernetes and must be adapted for a new environment.

## Reference manifests

The files under each environment's `external-secrets` directory describe:

- External Secrets Operator (HelmRelease in `flux-system`)
- `SecretStore` in `runtime-pool` using AWS Secrets Manager
- `ExternalSecret` in `runtime-pool` targeting Kubernetes secret `runtime-secrets`

They are deliberately not included by the staging or production
`kustomization.yaml` files. Applying an environment overlay does not install
Flux, connect a cluster to this repository, or configure AWS access.

AWS secret names expected:

- Staging: `agent-failure/staging/runtime-secrets`
- Production: `agent-failure/prod/runtime-secrets`

The generated runtime Pods specifically read these keys from the synchronized
`runtime-secrets` Secret:

- `RUNTIME_SHARED_TOKEN`
- `OPENROUTER_API_KEY` when `MODEL_CLIENT_MODE=gateway`

They receive the values through Kubernetes `secretKeyRef`; the values are not
embedded in generated Pod manifests. The control-plane and worker Deployments
also read their own required keys from the same Secret.

## Example operator setup

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

Install and configure Flux and External Secrets Operator according to their
current upstream documentation before applying adapted copies of these
resources.

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

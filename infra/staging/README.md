# Staging Bootstrap (E4-T1)

## Prereqs
- `kubectl` configured to the staging cluster context

## Bootstrap
```bash
bash infra/staging/bootstrap.sh
```

## Verify
```bash
kubectl get ns control-plane runtime-pool
kubectl -n runtime-pool get pod runtime-smoke
kubectl -n runtime-pool logs runtime-smoke
```

Expected log line: `runtime-scheduling-ok`

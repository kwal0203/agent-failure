## Production API Ingress

This folder contains production-facing manifests that should stay separate from local/staging defaults.

### 1) Update domain

Edit `control-plane-ingress.yaml` and replace:
- `api.yourdomain.com`

### 2) Apply

```bash
kubectl apply -f deploy/k8s/production/control-plane-ingress.yaml
```

### 3) Verify

```bash
kubectl -n runtime-pool get ingress
curl -i https://api.yourdomain.com/healthz
```

Notes:
- This manifest assumes ingress-nginx (`ingressClassName: nginx`).
- TLS annotation assumes cert-manager with ClusterIssuer `letsencrypt-prod`.
- If your cluster uses a different ingress class or issuer, change those fields.

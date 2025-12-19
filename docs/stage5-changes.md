# Stage 5 Changes (Monitoring & Observability)

## Modified
- `.gitignore` (ignore observability secrets/overrides)
- `requirements.api.txt` (add `prometheus-client`)
- `app/main.py` (add `/metrics` + Prometheus instrumentation)
- `k8s/21-svc-backend.yaml` (add `metadata.labels.app=backend` for ServiceMonitor selector)

## Added
- `k8s/observability/servicemonitor-backend.yaml`
- `k8s/observability/prometheusrule-backend.yaml`
- `k8s/observability/grafana-dashboards.yaml`
- `k8s/observability/grafana-admin-secret.yaml.example`
- `observability/kube-prometheus-stack.values.yaml`
- `observability/loki-stack.values.yaml`
- `observability/dashboards/dashboard-backend.json`
- `observability/dashboards/dashboard-cluster.json`
- `observability/dashboards/dashboard-logs.json`
- `docs/runbooks/observability.md`
- `docs/stage5-verify.md`
- `scripts/verify_stage5.ps1`

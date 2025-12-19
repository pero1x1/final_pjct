# Observability Runbook (Stage 5)

This runbook covers where to look (Grafana/Prometheus/Loki), how to validate scraping, and how to respond to alerts.

## Port-forward access

Grafana:

```bash
kubectl -n monitoring port-forward svc/kube-prometheus-stack-grafana 3000:80
```

Prometheus UI:

```bash
kubectl -n monitoring port-forward svc/kube-prometheus-stack-prometheus 9090:9090
```

## Validate scraping (ServiceMonitor)

1) Ensure ServiceMonitor exists:

```bash
kubectl -n monitoring get servicemonitor
kubectl -n monitoring describe servicemonitor backend
```

2) Ensure backend service has the label used by ServiceMonitor (`app=backend`):

```bash
kubectl -n credit-scoring get svc backend-svc -o jsonpath='{.metadata.labels}'
```

3) Check Prometheus targets:
- Prometheus UI: `Status` -> `Targets`
- Expect target `job="backend"` to be `UP`

Useful PromQL:

```promql
up{job="backend",namespace="credit-scoring"}
```

## Logs (Loki)

Example Loki queries:
- `{namespace="credit-scoring"}`
- `{namespace="credit-scoring", app="backend"} |= "uvicorn"`

## Alert response

### BackendDown
**Meaning:** Prometheus cannot scrape the backend target.

Steps:
1) Check pods and service:
```bash
kubectl -n credit-scoring get pods -o wide
kubectl -n credit-scoring get svc backend-svc -o wide
kubectl -n credit-scoring get endpoints backend-svc -o wide
```
2) Check backend logs:
```bash
kubectl -n credit-scoring logs deploy/backend --tail=200
```
3) Check `/metrics` from inside cluster:
```bash
kubectl -n credit-scoring port-forward svc/backend-svc 18080:80
curl -fsS http://127.0.0.1:18080/metrics | head
```

### High5xxRate
**Meaning:** 5xx response ratio is above 5% for 10 minutes.

Steps:
1) Inspect logs (Loki or kubectl):
```bash
kubectl -n credit-scoring logs deploy/backend --tail=200
```
2) Reproduce via API:
```bash
kubectl -n credit-scoring port-forward svc/frontend-svc 8080:80
curl -fsS http://127.0.0.1:8080/api/health
curl -fsS http://127.0.0.1:8080/api/docs
```
3) If the last deployment introduced regressions:
```bash
kubectl -n credit-scoring rollout undo deploy/backend
kubectl -n credit-scoring rollout status deploy/backend --timeout=300s
```

### HighLatencyP95
**Meaning:** p95 latency is above 0.5s for 10 minutes.

Steps:
1) Check node/pod CPU/memory dashboards in Grafana.
2) Check if backend is CPU throttled or OOM-killed:
```bash
kubectl -n credit-scoring top pods
kubectl -n credit-scoring describe pod -l app=backend
```
3) Inspect request patterns (Grafana dashboard `Credit Scoring - Backend`).

### PodCrashLooping
**Meaning:** container restarts increased in `credit-scoring`.

Steps:
```bash
kubectl -n credit-scoring get pods -o wide
kubectl -n credit-scoring describe pod <POD_NAME>
kubectl -n credit-scoring logs <POD_NAME> --previous --tail=200
kubectl -n credit-scoring get events --sort-by=.metadata.creationTimestamp | tail -n 50
```

### ModelMissing
**Meaning:** `MODEL_PATH` does not exist in the backend container.

Steps:
1) Check initContainer `dvc pull` logs:
```bash
kubectl -n credit-scoring logs deploy/backend -c dvc-pull --tail=200
```
2) Check model path inside the running container:
```bash
kubectl -n credit-scoring exec deploy/backend -c backend -- ls -la /app/models
```
3) Verify S3 credentials secret exists:
```bash
kubectl -n credit-scoring get secret s3-credentials
```

If needed, rollback:
```bash
kubectl -n credit-scoring rollout undo deploy/backend
```


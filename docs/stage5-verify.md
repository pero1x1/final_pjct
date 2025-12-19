# Stage 5 Verification (Monitoring & Observability)

This document contains commands to install the observability stack (Prometheus/Grafana/Loki), apply app scraping + alerts, and verify everything works.  
Do not commit any secrets; use `*.example` manifests or `kubectl create secret`.

## 0) Prerequisites

- `kubectl` points to your YC Managed Kubernetes cluster.
- `helm` installed locally.

## 1) Install kube-prometheus-stack (monitoring)

```bash
helm repo add prometheus-community https://prometheus-community.github.io/helm-charts
helm repo update
kubectl create namespace monitoring --dry-run=client -o yaml | kubectl apply -f -
```

Create Grafana admin secret (PowerShell-friendly):

```bash
kubectl -n monitoring create secret generic grafana-admin `
  --from-literal=admin-user=admin `
  --from-literal=admin-password="PUT_STRONG_PASSWORD_HERE" `
  --dry-run=client -o yaml | kubectl apply -f -
```

Install:

```bash
helm upgrade --install kube-prometheus-stack prometheus-community/kube-prometheus-stack `
  -n monitoring `
  -f observability/kube-prometheus-stack.values.yaml
```

## 2) Install Loki + Promtail (logging)

```bash
helm repo add grafana https://grafana.github.io/helm-charts
helm repo update
kubectl create namespace logging --dry-run=client -o yaml | kubectl apply -f -
helm upgrade --install loki grafana/loki-stack `
  -n logging `
  -f observability/loki-stack.values.yaml
```

## 3) Apply app scraping + alerts + dashboards

Make sure the backend service has label `app=backend` (required for ServiceMonitor selector):

```bash
kubectl apply -f k8s/21-svc-backend.yaml
```

Apply observability manifests:

```bash
kubectl apply -f k8s/observability/servicemonitor-backend.yaml
kubectl apply -f k8s/observability/prometheusrule-backend.yaml
kubectl apply -f k8s/observability/grafana-dashboards.yaml
```

## 4) Port-forward

Grafana:

```bash
kubectl -n monitoring port-forward svc/kube-prometheus-stack-grafana 3000:80
```

Prometheus:

```bash
kubectl -n monitoring port-forward svc/kube-prometheus-stack-prometheus 9090:9090
```

## 5) What to check (expected results)

### Prometheus Targets
- Open `http://127.0.0.1:9090/targets`
- Expect `job="backend"` to be `UP`

### Prometheus query examples

```promql
up{job="backend",namespace="credit-scoring"}
rate(http_requests_total{job="backend",namespace="credit-scoring"}[1m])
histogram_quantile(0.95, sum(rate(http_request_duration_seconds_bucket{job="backend",namespace="credit-scoring"}[5m])) by (le))
model_file_present{job="backend",namespace="credit-scoring"}
```

### Grafana dashboards
- Open `http://127.0.0.1:3000`
- Login with secret `grafana-admin` (`admin-user` / `admin-password`)
- Dashboards should appear:
  - `Credit Scoring - Backend`
  - `Credit Scoring - Cluster`
  - `Credit Scoring - Logs`

### Loki datasource + logs
In Grafana Explore, select datasource `Loki` and run:
- `{namespace="credit-scoring"}`
- `{namespace="credit-scoring", app="backend"} |= "uvicorn"`


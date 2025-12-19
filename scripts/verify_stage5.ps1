param(
  [string]$AppNamespace = "credit-scoring",
  [string]$MonitoringNamespace = "monitoring",
  [string]$LoggingNamespace = "logging"
)

$ErrorActionPreference = "Stop"

function Section([string]$Title) {
  Write-Host ""
  Write-Host "== $Title =="
}

Section "Cluster connectivity"
kubectl version --client
kubectl cluster-info | Out-Host

Section "Namespaces"
kubectl get ns $AppNamespace,$MonitoringNamespace,$LoggingNamespace -o wide

Section "App pods"
kubectl -n $AppNamespace get pods -o wide

Section "Monitoring pods (Prometheus/Grafana)"
kubectl -n $MonitoringNamespace get pods -o wide

Section "Logging pods (Loki/Promtail)"
kubectl -n $LoggingNamespace get pods -o wide

Section "ServiceMonitor / PrometheusRule"
kubectl -n $MonitoringNamespace get servicemonitor backend -o wide
kubectl -n $MonitoringNamespace get prometheusrule credit-scoring-backend-alerts -o wide

Section "Grafana dashboards ConfigMap"
kubectl -n $MonitoringNamespace get configmap grafana-dashboards-credit-scoring -o name

Write-Host ""
Write-Host "Next checks (run in separate terminals):"
Write-Host "  kubectl -n $MonitoringNamespace port-forward svc/kube-prometheus-stack-grafana 3000:80"
Write-Host "  kubectl -n $MonitoringNamespace port-forward svc/kube-prometheus-stack-prometheus 9090:9090"
Write-Host ""
Write-Host "Prometheus:"
Write-Host "  http://127.0.0.1:9090/targets   (expect job=""backend"" UP)"
Write-Host ""
Write-Host "Grafana:"
Write-Host "  http://127.0.0.1:3000  (Dashboards: Credit Scoring - Backend/Cluster/Logs)"
Write-Host ""


# Проверка проекта (коротко)

Это общий чеклист. Подробно:
- Stage 5: `docs/stage5-verify.md`
- Stage 7: `docs/stage7-verify.md`
- Runbook: `docs/runbooks/observability.md`

## 1) API в Kubernetes

```powershell
kubectl -n credit-scoring get pods -o wide
kubectl -n credit-scoring get ingress
curl http://<INGRESS_IP>/api/health
curl http://<INGRESS_IP>/api/docs
```

## 2) DVC артефакты в backend

```powershell
kubectl -n credit-scoring logs deploy/backend -c dvc-pull --tail=200
kubectl -n credit-scoring exec deploy/backend -c backend -- ls -la /app/models
```

## 3) Метрики/логи (Stage 5)

```powershell
kubectl -n monitoring port-forward svc/kube-prometheus-stack-prometheus 9090:9090
kubectl -n monitoring port-forward svc/kube-prometheus-stack-grafana 3000:80
```

В Prometheus (Targets):
- `job="backend"` должен быть `UP`

В Grafana:
- есть дашборды `Credit Scoring - Backend/Cluster/Logs`

## 4) Retraining (Stage 7)

Проверка в Airflow:
- DAG `credit_scoring_retraining` виден
- `check_new_data` видит `retraining/current.csv`
- `compute_drift` грузит отчёт в `retraining/reports/<RUN_ID>/`
- `retrain_model` пишет модель в `retraining/models/<RUN_ID>/`


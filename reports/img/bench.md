# Лог проекта (bench.md)

Файл для сдачи: тут коротко по этапам 1-7, с командами и кусками вывода.

## Этап 1. Benchmark (NN -> ONNX -> INT8)

Качество (AUC):

```
Torch AUC: 0.76781
ONNX  AUC: 0.76781
INT8  AUC: 0.76533
Drop INT8 vs ONNX: 0.00248
```

Скорость (CPU):

```
Torch (threads=4): 0.183 ms/batch
ONNX FP32: 6.974 ms/batch
ONNX INT8: 7.386 ms/batch
```

Скрипты: `src/onnx/` (export, validate, quantize, benchmark).

## Этап 2. Terraform (YC)

Валидация:

```powershell
cd infra/terraform/environments/staging
terraform validate
```

Ожидаемо:

```
Success! The configuration is valid.
```

Ключевые ресурсы в state (пример):

```powershell
terraform state list
```

```
module.kubernetes.yandex_kubernetes_cluster.this
module.kubernetes.yandex_kubernetes_node_group.cpu
module.network.yandex_vpc_network.this
module.network.yandex_vpc_subnet.this
module.storage.yandex_storage_bucket.tfstate
module.storage.yandex_iam_service_account.tfstate
```

Object Storage (бакеты):

```powershell
yc storage bucket list
```

Пример вывода:

```
credit-scoring-tfstate-staging-b1gh235jp3f284fe2gdn
credit-scoring-monitoring-staging-b1gh235jp3f284fe2gdn
```

## Этап 3. Docker + Kubernetes + DVC pull (staging)

Применить манифесты:

```powershell
kubectl apply -f k8s/00-namespace.yaml
kubectl apply -f k8s/10-configmap-backend.yaml
kubectl apply -f k8s/20-deploy-backend.yaml
kubectl apply -f k8s/21-svc-backend.yaml
kubectl apply -f k8s/30-deploy-frontend.yaml
kubectl apply -f k8s/31-svc-frontend.yaml
kubectl apply -f k8s/40-ingress.yaml
```

Ingress IP:

```powershell
kubectl -n credit-scoring get ingress
```

Пример:

```
NAME            CLASS   HOSTS   ADDRESS          PORTS   AGE
backend-ingress  nginx   *       158.160.208.83   80      35m
frontend-ingress nginx   *       158.160.208.83   80      35m
```

Проверка API:

```powershell
curl http://158.160.208.83/api/health
curl http://158.160.208.83/api/docs
```

Ожидаемо (health):

```
StatusCode : 200
Content    : {"status":"ok","model":"/app/models/credit_default_model.pkl"}
```

Проверка DVC pull (initContainer):

```powershell
kubectl -n credit-scoring logs deploy/backend -c dvc-pull --tail=100
```

## Этап 4. CI/CD (GitHub Actions)

Workflows: `.github/workflows/`

- `build-and-test.yml` (lint/test + security scans)
- `deploy-staging.yml` (build+push в YCR -> apply k8s -> smoke checks -> rollback при фейле)
- `deploy-production.yml`, `rollback.yml`, `canary-release.yml`

Скрины успешных раннов:
- `reports/img/deploy.png`, `reports/img/deploy2.png`
- `reports/img/deploy3.png`, `reports/img/deploy4.png`

## Этап 5. Monitoring & Observability (Prometheus/Grafana/Loki)

Подробный гайд: `docs/stage5-verify.md`

Проверка, что всё поднялось:

```powershell
kubectl -n monitoring get pods -o wide
kubectl -n logging get pods -o wide
kubectl -n monitoring get servicemonitor backend
kubectl -n monitoring get prometheusrule credit-scoring-backend-alerts
```

Скрины:
- Grafana: `reports/img/grafana.png`
- Prometheus Targets: `reports/img/prometeus.png`

## Этап 6. Стратегии релиза/надёжность (минимум)

Есть canary и rollback workflows:
- `.github/workflows/canary-release.yml`
- `.github/workflows/rollback.yml`

HPA для backend (опционально):

```powershell
kubectl apply -f k8s/autoscaling/hpa-backend.yaml
kubectl -n credit-scoring get hpa
```

## Этап 7. Retraining pipeline (Airflow)

Подробный гайд: `docs/stage7-verify.md`

Коротко по шагам:

1) Собрать trainer image:

```powershell
$REGISTRY_ID = "<YOUR_YCR_REGISTRY_ID>"
docker build -t cr.yandex/$REGISTRY_ID/credit-trainer:staging -f docker/trainer/Dockerfile .
docker push cr.yandex/$REGISTRY_ID/credit-trainer:staging
```

2) Поставить Airflow и создать secret `airflow-s3` (ключи не коммитим).

3) Залить датасеты:

```
s3://<BUCKET>/retraining/reference.csv
s3://<BUCKET>/retraining/current.csv
```

4) Запустить DAG `credit_scoring_retraining`.

5) Проверить артефакты:

```
s3://<BUCKET>/retraining/models/<RUN_ID>/credit_default_model.pkl
s3://<BUCKET>/retraining/reports/<RUN_ID>/drift_report.html
s3://<BUCKET>/retraining/metrics/<RUN_ID>/metrics.json
```


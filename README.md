# Credit Default Prediction (MLOps)

Проект про предсказание дефолта по кредитной карте. Тут есть DVC пайплайн данных/модели, API на FastAPI, фронт на nginx, деплой в YC Managed Kubernetes и автоматизация через GitHub Actions + Airflow.

## Архитектура

- Backend (FastAPI): `app/main.py` (`/predict`, `/health`, `/metrics`)
- Frontend (nginx): `frontend/` + `docker/frontend/`
- DVC пайплайн: `dvc.yaml` (prepare -> features -> train -> monitor)
- Артефакты: `models/credit_default_model.pkl` (через DVC pull в K8s initContainer)
- Kubernetes манифесты: `k8s/` (namespace `credit-scoring`, Ingress nginx)
- CI/CD: `.github/workflows/` (build/test/security + deploy staging + rollback)
- Мониторинг: `observability/` + `k8s/observability/` (Prometheus/Grafana/Loki)
- Retraining: `airflow/dags/` + `docker/trainer/` + `orchestration/airflow/`

Скрины для отчёта: `reports/img/`.

## Быстрый запуск локально (минимум)

```bash
python -m venv .venv
pip install -r requirements.txt -r requirements.api.txt

# собрать данные + модель + метрики
dvc repro

# запустить API
uvicorn app.main:app --host 0.0.0.0 --port 8000
```

Проверка:

```bash
curl http://127.0.0.1:8000/health
curl http://127.0.0.1:8000/docs
```

## Деплой в staging (GitHub Actions -> YC Managed K8s)

Основной деплой: `.github/workflows/deploy-staging.yml`.

Нужные Secrets в GitHub:
- `YC_SA_KEY_JSON`
- `YC_K8S_CLUSTER_ID_STAGING`
- `YC_REGISTRY_ID`
- `S3_ACCESS_KEY_ID`
- `S3_SECRET_ACCESS_KEY`

Где смотреть:
- GitHub -> Actions -> `build-and-test` и `deploy-staging`

## Проверка по этапам 1-7

Коротко, что где проверять. Подробные команды в `reports/img/bench.md` и в `docs/`.

### Этап 1. Benchmark (NN -> ONNX -> INT8)
- Скрипты: `src/onnx/`
- Доказательства/цифры: `reports/img/bench.md`

### Этап 2. Terraform (YC)
- Код: `infra/terraform/`
- Быстрая проверка:
  ```bash
  cd infra/terraform/environments/staging
  terraform validate
  terraform plan
  ```

### Этап 3. Docker + Kubernetes + DVC pull
- Dockerfiles: `docker/backend/Dockerfile`, `docker/frontend/Dockerfile`
- Манифесты: `k8s/`
- Проверка:
  ```bash
  kubectl -n credit-scoring get pods -o wide
  kubectl -n credit-scoring logs deploy/backend -c dvc-pull --tail=50
  kubectl -n credit-scoring get ingress
  ```

### Этап 4. CI/CD (build -> test -> deploy -> monitor -> rollback)
- Workflows: `.github/workflows/build-and-test.yml`, `.github/workflows/deploy-staging.yml`, `.github/workflows/rollback.yml`
- Проверка: Actions зелёные, деплой обновляет образы по `github.sha`

### Этап 5. Monitoring & Observability
- Helm values: `observability/`
- ServiceMonitor/alerts/dashboards: `k8s/observability/`
- Команды: `docs/stage5-verify.md`

### Этап 6. Стратегии/надёжность (минимум)
- Canary/rollback: `.github/workflows/canary-release.yml`, `.github/workflows/rollback.yml`
- HPA (опц.): `k8s/autoscaling/hpa-backend.yaml`

### Этап 7. Retraining pipeline (Airflow)
- DAG: `airflow/dags/credit_scoring_retraining.py`
- Trainer image: `docker/trainer/Dockerfile`
- Helm values: `orchestration/airflow/values.yaml`
- Команды: `docs/stage7-verify.md`

## Метрики, логи, алерты

- Метрики API: `GET /metrics` (Prometheus)
- PrometheusRule/ServiceMonitor: `k8s/observability/`
- Runbook: `docs/runbooks/observability.md`

## Security checks в CI

Смотри `.github/workflows/build-and-test.yml`:
- trivy fs scan
- pip-audit
- dependency review (PR)
- npm audit (если есть `frontend/package.json`)

## Откат (rollback)

- Авто откат в деплое: `.github/workflows/deploy-staging.yml` (rollout undo при ошибке)
- Ручной откат: `.github/workflows/rollback.yml`

## Что получилось

- Есть DVC пайплайн и метрики качества/дрейфа.
- API + фронт работают в K8s через Ingress.
- Модель и данные приезжают через `dvc pull` (initContainer).
- CI делает линт, тесты и security checks.
- CD деплоит в staging и делает rollback при проблемах.
- Есть мониторинг (Prometheus/Grafana/Loki) и алерты.
- Есть Airflow DAG для retrain по данным + дрейфу.


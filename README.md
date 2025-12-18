# README.md

```markdown
# Credit Default Prediction — end-to-end MLOps

Стек: **Python 3.11, scikit-learn, DVC, MLflow, FastAPI, Docker, Pandera, flake8/black/isort, GitHub Actions**.  
Цель: построить и автоматизировать пайплайн PD-модели (вероятность дефолта) на датасете **Default of Credit Card Clients**.

<p align="center">
  <img src="reports/img/mlflowui.png" alt="MLflow UI" width="720"/>
</p>

## Содержание
- [Структура репо](#структура-репо)
- [Быстрый старт](#быстрый-старт)
- [Пайплайн DVC](#пайплайн-dvc)
- [Эксперименты и MLflow](#эксперименты-и-mlflow)
- [API (FastAPI) и Docker](#api-fastapi-и-docker)
- [Мониторинг дрифта (PSI)](#мониторинг-дрифта-psi)
- [Качество кода и CI](#качество-кода-и-ci)
- [Скриншоты](#скриншоты)

---

## Структура репо

```
<p align="center">
  <img src="reports/img/prjct.png" width="720"/>
</p>

````

---

## Быстрый старт

1) Клонируем и ставим зависимости:
```bash
python -m venv .venv
# активируй venv и затем
pip install -r requirements.txt
````

2. Прогоняем весь пайплайн:

```bash
dvc repro
```

3. Проверяем качество кода и тесты (или одной командой):

```bash
make check
# включает: make format && make lint && make test
```

4. MLflow UI (локально):

```bash
make mlflow-ui
# открой http://localhost:5000
```

---

## Пайплайн DVC

Стадии (см. `dvc.yaml`):

* **prepare** → загрузка/сплит
* **features** → генерация фич
* **train** → обучение базовой модели и сохранение `models/credit_default_model.pkl`
* **monitor** → расчёт PSI по train vs test (`artifacts/psi.json`)

Запуск:

```bash
make dvc-repro
```

---

## Эксперименты и MLflow

Гиперпараметрический поиск для двух пайплайнов (LogReg/GBDT) — `src/models/search.py` (RandomizedSearchCV, scoring=roc_auc, cv=3).
Лучшие модели и метрики логируются в MLflow, артефакт `model` доступен в UI.

Пример запуска поиска:

```bash
make search
# сохранение лучшей модели в models/best_search_model
```

Скриншоты:

<p align="center">
  <img src="reports/img/search_gbdt.png" width="720"/>
</p>

---

## API (FastAPI) и Docker

Локально (без Docker):

```bash
make api PORT=8000
# /docs → Swagger UI, /health
```

### Docker

Собрать:

```bash
make docker-build DOCKER_IMG=credit-api TAG=latest
```

Запустить (с подмонтированной локальной папкой `models/`):

> **Windows (PowerShell/Linux/Mac):**

```bash
make docker-run DOCKER_IMG=credit-api TAG=latest PORT=8000
```

> **Windows CMD (если вручную):**

```bat
docker run --rm -d --name credit-api -p 8000:8000 ^
  -v %cd%\models:/app/models ^
  -e MODEL_PATH=/app/models/credit_default_model.pkl ^
  credit-api:latest
```

Проверка:

```bash
curl http://localhost:8000/health
```

`POST /predict` — пример payload:

```json
{
  "LIMIT_BAL": 120000,
  "AGE": 29,
  "BILL_AMT1": 500, "BILL_AMT2": 600, "BILL_AMT3": 600, "BILL_AMT4": 600, "BILL_AMT5": 600, "BILL_AMT6": 400,
  "PAY_AMT1": 0, "PAY_AMT2": 0, "PAY_AMT3": 0, "PAY_AMT4": 0, "PAY_AMT5": 0, "PAY_AMT6": 0,
  "utilization1": 0, "payment_ratio1": 0, "max_delay": 0,
  "SEX": 2, "EDUCATION": 2, "MARRIAGE": 1,
  "PAY_0": 0, "PAY_2": 0, "PAY_3": 0, "PAY_4": 0, "PAY_5": 0, "PAY_6": 0
}
```

Ответ:

```json
{
  "proba_default": 0.26,
  "predicted_class": 0,
  "model_info": "pipeline"
}
```

<p align="center">
  <img src="reports/img/creditapi.png" width="720"/>
  <img src="reports/img/successful_response.png" width="720"/>
</p>

---

## Kubernetes (Stage 3: Docker + K8s + DVC pull)

### Установка ingress-nginx (через Helm)

> Нужен Ingress Controller, т.к. доступ снаружи идёт через `k8s/40-ingress.yaml`.

```bash
helm repo add ingress-nginx https://kubernetes.github.io/ingress-nginx
helm repo update
kubectl create namespace ingress-nginx --dry-run=client -o yaml | kubectl apply -f -
helm upgrade --install ingress-nginx ingress-nginx/ingress-nginx -n ingress-nginx
kubectl -n ingress-nginx get svc
```

### Secret для Object Storage (нужен для `dvc pull` в initContainer)

Вариант 1 (через `--from-literal`, файл не создаём):

```bash
kubectl -n credit-scoring create secret generic s3-credentials \
  --from-literal=AWS_ACCESS_KEY_ID="<PUT_HERE>" \
  --from-literal=AWS_SECRET_ACCESS_KEY="<PUT_HERE>"
```

Вариант 2 (через yaml, но **не коммитим**):

```bash
cp k8s/11-secret-s3.yaml.example k8s/11-secret-s3.yaml
kubectl apply -f k8s/11-secret-s3.yaml
```

> `k8s/11-secret-s3.yaml` игнорируется через `.gitignore`.

### Деплой

```bash
kubectl apply -f k8s/00-namespace.yaml
kubectl apply -f k8s/10-configmap-backend.yaml
# secret: см. выше
kubectl apply -f k8s/20-deploy-backend.yaml
kubectl apply -f k8s/21-svc-backend.yaml
kubectl apply -f k8s/30-deploy-frontend.yaml
kubectl apply -f k8s/31-svc-frontend.yaml
kubectl apply -f k8s/40-ingress.yaml
```

## Мониторинг дрифта (PSI)

Скрипт: `src/monitor/psi.py`
Запуск отдельно:

```bash
make psi
# отчёт → artifacts/psi.json (средний PSI и пофичево)
```

---

## Качество кода и CI

Локально:

```bash
make format   # black + isort
make lint     # flake8
make test     # pytest
```

GitHub Actions:

* **ci.yml** — формат, линт, тесты, `dvc repro`, загрузка артефактов (метрики, ROC и т.д.)
* **ci-docker.yml** — сборка Docker-образа по релиз-тегу `v*.*.*` и пуш в Docker Hub
  Для пуша выстави секреты репозитория:

  * `DOCKERHUB_USERNAME`
  * `DOCKERHUB_TOKEN`

---

## Скриншоты

<p align="center">
  <img src="reports/img/best_search.png" width="720"/>
  <img src="reports/img/docker.png" width="720"/>
  <img src="reports/img/dockerhealth.png" width="720"/>
  <img src="reports/img/mlflowui.png" width="720"/>
  <img src="reports/img/search_gbdt.png" width="720"/>
</p>

---

```

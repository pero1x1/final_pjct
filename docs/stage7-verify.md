# Stage 7 Verification (Retraining pipeline & automation)

This document contains exact commands to install Airflow on Kubernetes, deploy the retraining DAG, upload new data, trigger the DAG, and verify artifacts in Yandex Object Storage (S3).

## 0) Variables used below (PowerShell)

Set these first:

```powershell
$BUCKET = "<YOUR_BUCKET_NAME>"
$REGISTRY_ID = "<YOUR_YCR_REGISTRY_ID>"
```

## 1) Build & push trainer image

```powershell
docker build -t cr.yandex/$REGISTRY_ID/credit-trainer:staging -f docker/trainer/Dockerfile .
docker push cr.yandex/$REGISTRY_ID/credit-trainer:staging
```

Expected:
- Image exists in YCR with tag `staging`.

## 2) Install Airflow via Helm (namespace `airflow`)

```powershell
helm repo add apache-airflow https://airflow.apache.org
helm repo update

kubectl create namespace airflow --dry-run=client -o yaml | kubectl apply -f -
```

### Create S3 secret (do not commit)

```powershell
kubectl -n airflow create secret generic airflow-s3 `
  --from-literal=AWS_ACCESS_KEY_ID="$env:S3_ACCESS_KEY_ID" `
  --from-literal=AWS_SECRET_ACCESS_KEY="$env:S3_SECRET_ACCESS_KEY" `
  --from-literal=AWS_DEFAULT_REGION="ru-central1" `
  --from-literal=S3_ENDPOINT_URL="https://storage.yandexcloud.net" `
  --from-literal=BUCKET="$BUCKET" `
  --dry-run=client -o yaml | kubectl apply -f -
```

Expected:
- `secret/airflow-s3 created` (or `configured`)

### Install Airflow chart

```powershell
helm upgrade --install airflow apache-airflow/airflow `
  -n airflow `
  -f orchestration/airflow/values.yaml
```

Check pods:

```powershell
kubectl -n airflow get pods -o wide
```

Expected:
- Airflow webserver + scheduler pods are `Running` (postgres may also be running).

## 3) Open Airflow UI

Port-forward:

```powershell
kubectl -n airflow port-forward svc/airflow-webserver 8081:8080
```

Open:
- `http://127.0.0.1:8081`

Default credentials (chart default):
- user: `admin`
- password: `admin`

## 4) Configure Airflow Variables (trainer image + optional namespace)

Set variables via CLI (run inside scheduler pod):

```powershell
$SCHED = kubectl -n airflow get pods -l component=scheduler -o jsonpath='{.items[0].metadata.name}'
kubectl -n airflow exec $SCHED -- airflow variables set TRAINER_IMAGE "cr.yandex/$REGISTRY_ID/credit-trainer:staging"
kubectl -n airflow exec $SCHED -- airflow variables set AIRFLOW_TRAIN_NAMESPACE "airflow"
```

Expected:
- Variables are set without errors.

## 5) Upload “current.csv” to S3 (new data signal)

Use an existing dataset file from repo as an example:

```powershell
yc storage s3api put-object `
  --bucket $BUCKET `
  --key retraining/current.csv `
  --body data/processed/train.csv
```

Expected:
- `ETag` is returned.

## 6) Trigger DAG manually

Trigger from CLI:

```powershell
kubectl -n airflow exec $SCHED -- airflow dags trigger credit_scoring_retraining
kubectl -n airflow exec $SCHED -- airflow dags list-runs -d credit_scoring_retraining --no-backfill
```

Expected:
- New run appears (state will move from `queued/running` to `success`).

## 7) Verify task logs (what should appear)

In Airflow UI, open the DAG run and check task logs:

- `check_new_data` should log:
  - `current.csv found`
  - `has_new_data=True` (first run after upload)
- `compute_drift` should log:
  - `[DRIFT] avg_psi=... exceeded=true/false`
  - `Uploaded drift report to s3://.../retraining/reports/<RUN_ID>/drift_report.html`
- `retrain_model` (pod logs) should print:
  - `[TRAIN] model -> s3://.../retraining/models/<RUN_ID>/credit_default_model.pkl`
  - `[TRAIN] metrics -> s3://.../retraining/metrics/<RUN_ID>/metrics.json`

## 8) Verify outputs in S3

```powershell
yc storage s3api list-objects --bucket $BUCKET --prefix retraining/models/
yc storage s3api list-objects --bucket $BUCKET --prefix retraining/reports/
yc storage s3api list-objects --bucket $BUCKET --prefix retraining/metrics/
```

Expected:
- Keys exist for the latest run, for example:
  - `retraining/models/<RUN_ID>/credit_default_model.pkl`
  - `retraining/reports/<RUN_ID>/drift_report.html`
  - `retraining/metrics/<RUN_ID>/metrics.json`

## 9) Optional: apply HPA for backend

```powershell
kubectl apply -f k8s/autoscaling/hpa-backend.yaml
kubectl -n credit-scoring get hpa
```

Expected:
- `backend-hpa` exists (may show `<unknown>` targets if metrics-server/resources are not configured).


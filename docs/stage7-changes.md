# Stage 7 Changes (Retraining pipeline & automation)

## Added
- `airflow/dags/credit_scoring_retraining.py` (Airflow DAG: new data + PSI drift triggers, retrain via KubernetesPodOperator)
- `docker/trainer/Dockerfile` (trainer image)
- `requirements.train.txt` (trainer dependencies)
- `scripts/model_training/train_model.py` (train + upload artifacts to S3)
- `orchestration/airflow/values.yaml` (Airflow Helm values)
- `orchestration/airflow/airflow-s3-secret.yaml.example` (S3 secret example; do not commit real secrets)
- `k8s/autoscaling/hpa-backend.yaml` (optional HPA for backend)
- `docs/stage7-verify.md` (commands + expected results)

## Modified
- `.gitignore` (ignore Airflow/orchestration secret manifests)


from __future__ import annotations

import csv
import json
import logging
import math
import os
import re
import statistics
import tempfile
from bisect import bisect_right
from datetime import datetime, timedelta, timezone
from pathlib import Path
from typing import Dict, List, Tuple

from airflow import DAG
from airflow.models import Variable
from airflow.operators.empty import EmptyOperator
from airflow.operators.python import BranchPythonOperator, PythonOperator
from airflow.providers.cncf.kubernetes.operators.pod import KubernetesPodOperator
from airflow.kubernetes.secret import Secret


TARGET_COL = "default.payment.next.month"
DRIFT_THRESHOLD_DEFAULT = 0.1

NUM_FEATURES = [
    "LIMIT_BAL",
    "AGE",
    "BILL_AMT1",
    "BILL_AMT2",
    "BILL_AMT3",
    "BILL_AMT4",
    "BILL_AMT5",
    "BILL_AMT6",
    "PAY_AMT1",
    "PAY_AMT2",
    "PAY_AMT3",
    "PAY_AMT4",
    "PAY_AMT5",
    "PAY_AMT6",
    "utilization1",
    "payment_ratio1",
    "max_delay",
]


def _safe_run_id(run_id: str) -> str:
    return re.sub(r"[^0-9A-Za-z_.-]+", "_", run_id).strip("_") or "run"


def _require_env(name: str) -> str:
    value = os.getenv(name)
    if not value:
        raise RuntimeError(f"Missing required env var: {name}")
    return value


def _s3_client():
    import boto3

    endpoint = os.getenv("S3_ENDPOINT_URL", "https://storage.yandexcloud.net")
    region = os.getenv("AWS_DEFAULT_REGION", "ru-central1")
    return boto3.client("s3", endpoint_url=endpoint, region_name=region)


def _parse_s3_uri(uri: str) -> Tuple[str, str]:
    if not uri.startswith("s3://"):
        raise ValueError(f"Invalid S3 URI: {uri}")
    rest = uri.removeprefix("s3://")
    if "/" not in rest:
        raise ValueError(f"Invalid S3 URI: {uri}")
    bucket, key = rest.split("/", 1)
    return bucket, key


def _download_s3_to_file(bucket: str, key: str) -> str:
    s3 = _s3_client()
    with tempfile.NamedTemporaryFile(delete=False, suffix=Path(key).suffix or ".bin") as f:
        s3.download_fileobj(bucket, key, f)
        return f.name


def _load_numeric_columns(csv_path: str, columns: List[str], max_rows: int = 50_000) -> Dict[str, List[float]]:
    values: Dict[str, List[float]] = {c: [] for c in columns}
    with open(csv_path, "r", encoding="utf-8") as f:
        reader = csv.DictReader(f)
        if not reader.fieldnames:
            return values
        present = set(reader.fieldnames)
        cols = [c for c in columns if c in present]
        for i, row in enumerate(reader):
            if i >= max_rows:
                break
            for c in cols:
                raw = row.get(c)
                if raw is None or raw == "":
                    continue
                try:
                    values[c].append(float(raw))
                except ValueError:
                    continue
    return values


def _psi(base: List[float], current: List[float], bins: int = 10, eps: float = 1e-8) -> float:
    if len(base) < bins + 1 or len(current) == 0:
        return 0.0
    try:
        cuts = statistics.quantiles(base, n=bins, method="exclusive")
    except statistics.StatisticsError:
        return 0.0

    bounds = [-math.inf, *cuts, math.inf]
    base_counts = [0] * bins
    cur_counts = [0] * bins

    for v in base:
        idx = bisect_right(bounds, v) - 1
        idx = min(max(idx, 0), bins - 1)
        base_counts[idx] += 1

    for v in current:
        idx = bisect_right(bounds, v) - 1
        idx = min(max(idx, 0), bins - 1)
        cur_counts[idx] += 1

    base_total = float(sum(base_counts)) or 1.0
    cur_total = float(sum(cur_counts)) or 1.0
    base_pct = [(c / base_total) for c in base_counts]
    cur_pct = [(c / cur_total) for c in cur_counts]

    psi_val = 0.0
    for b, c in zip(base_pct, cur_pct):
        b = max(b, eps)
        c = max(c, eps)
        psi_val += (b - c) * math.log(b / c)
    return float(psi_val)


def check_new_data(**_context):
    bucket = _require_env("BUCKET")
    key = "retraining/current.csv"
    uri = f"s3://{bucket}/{key}"

    try:
        from botocore.exceptions import ClientError
    except Exception as e:  # noqa: BLE001
        raise RuntimeError("Missing python dependency: botocore/boto3") from e

    s3 = _s3_client()
    try:
        head = s3.head_object(Bucket=bucket, Key=key)
    except ClientError as e:
        code = (e.response or {}).get("Error", {}).get("Code")
        if code in {"404", "NoSuchKey", "NotFound"}:
            logging.info("No current dataset found at %s", uri)
            return {"exists": False, "has_new_data": False, "etag": None, "s3_uri": uri}
        raise

    etag = str(head.get("ETag", "")).strip('"')
    last_modified = head.get("LastModified")
    last_modified_iso = (
        last_modified.astimezone(timezone.utc).isoformat() if last_modified else None
    )

    prev_etag = Variable.get("LAST_DATA_ETAG", default_var="")
    has_new_data = bool(etag) and etag != prev_etag

    Variable.set("LAST_DATA_ETAG", etag)
    if last_modified_iso:
        Variable.set("LAST_DATA_LASTMOD", last_modified_iso)

    logging.info(
        "current.csv found: s3_uri=%s etag=%s last_modified=%s has_new_data=%s",
        uri,
        etag,
        last_modified_iso,
        has_new_data,
    )
    return {
        "exists": True,
        "has_new_data": has_new_data,
        "etag": etag,
        "s3_uri": uri,
        "last_modified": last_modified_iso,
    }


def compute_drift(**context):
    bucket = _require_env("BUCKET")
    run_id = _safe_run_id(context["run_id"])
    threshold = float(os.getenv("DRIFT_THRESHOLD", str(DRIFT_THRESHOLD_DEFAULT)))

    report_key = f"retraining/reports/{run_id}/drift_report.html"
    report_uri = f"s3://{bucket}/{report_key}"

    ti = context["ti"]
    new_data = ti.xcom_pull(task_ids="check_new_data") or {}
    current_uri = str(new_data.get("s3_uri") or f"s3://{bucket}/retraining/current.csv")

    drift_score = 0.0
    drift_exceeded = False
    per_feature: Dict[str, float] = {}
    note = ""

    if not new_data.get("exists"):
        note = f"No current dataset found at {current_uri}. Drift check skipped."
        logging.info(note)
    else:
        reference_local = Path("data/processed/train_base.csv")
        reference_s3_uri = os.getenv("REFERENCE_S3_URI", "")

        if reference_local.exists():
            ref_path = str(reference_local)
            logging.info("Using local reference dataset: %s", ref_path)
        elif reference_s3_uri:
            ref_bucket, ref_key = _parse_s3_uri(reference_s3_uri)
            ref_path = _download_s3_to_file(ref_bucket, ref_key)
            logging.info("Downloaded reference dataset from %s", reference_s3_uri)
        else:
            ref_path = ""
            note = (
                "Reference dataset is missing. "
                "Provide REFERENCE_S3_URI (e.g. s3://<bucket>/retraining/reference.csv)."
            )
            logging.warning(note)

        cur_bucket, cur_key = _parse_s3_uri(current_uri)
        cur_path = _download_s3_to_file(cur_bucket, cur_key)
        logging.info("Downloaded current dataset from %s", current_uri)

        if ref_path:
            ref_vals = _load_numeric_columns(ref_path, NUM_FEATURES)
            cur_vals = _load_numeric_columns(cur_path, NUM_FEATURES)
            for feat in NUM_FEATURES:
                base = ref_vals.get(feat, [])
                cur = cur_vals.get(feat, [])
                if base and cur:
                    per_feature[feat] = _psi(base, cur)

            if per_feature:
                drift_score = float(sum(per_feature.values()) / len(per_feature))
                drift_exceeded = drift_score > threshold
                logging.info(
                    "[DRIFT] avg_psi=%.4f threshold=%.4f exceeded=%s",
                    drift_score,
                    threshold,
                    drift_exceeded,
                )
            else:
                note = "No common numeric features found for drift calculation."
                logging.warning(note)
        else:
            drift_score = 0.0
            drift_exceeded = False

    html_rows = "\n".join(
        f"<tr><td>{k}</td><td>{v:.6f}</td></tr>"
        for k, v in sorted(per_feature.items(), key=lambda kv: kv[1], reverse=True)
    )
    note_html = f"<p><b>Note:</b> {note}</p>" if note else ""
    html = f"""<!doctype html>
<html>
  <head>
    <meta charset="utf-8"/>
    <title>Credit Scoring Drift Report</title>
  </head>
  <body>
    <h1>Credit Scoring Drift Report</h1>
    <ul>
      <li><b>run_id</b>: {run_id}</li>
      <li><b>current</b>: {current_uri}</li>
      <li><b>drift_score (avg PSI)</b>: {drift_score:.6f}</li>
      <li><b>threshold</b>: {threshold:.6f}</li>
      <li><b>drift_exceeded</b>: {str(drift_exceeded).lower()}</li>
      <li><b>generated_at</b>: {datetime.now(timezone.utc).isoformat()}</li>
    </ul>
    {note_html}
    <h2>Per-feature PSI</h2>
    <table border="1" cellpadding="6" cellspacing="0">
      <thead><tr><th>feature</th><th>psi</th></tr></thead>
      <tbody>
        {html_rows}
      </tbody>
    </table>
  </body>
</html>
"""

    s3 = _s3_client()
    s3.put_object(
        Bucket=bucket,
        Key=report_key,
        Body=html.encode("utf-8"),
        ContentType="text/html; charset=utf-8",
    )
    logging.info("Uploaded drift report to %s", report_uri)

    return {
        "drift_score": float(drift_score),
        "drift_exceeded": bool(drift_exceeded),
        "report_s3_uri": report_uri,
    }


def branch_should_retrain(**context):
    ti = context["ti"]
    new_data = ti.xcom_pull(task_ids="check_new_data") or {}
    drift = ti.xcom_pull(task_ids="compute_drift") or {}

    has_new_data = bool(new_data.get("has_new_data"))
    drift_exceeded = bool(drift.get("drift_exceeded"))

    logging.info("Decision inputs: has_new_data=%s drift_exceeded=%s", has_new_data, drift_exceeded)
    return "retrain_model" if (has_new_data and drift_exceeded) else "skip_retrain"


def validate_model(**context):
    bucket = _require_env("BUCKET")
    run_id = _safe_run_id(context["run_id"])
    model_key = f"retraining/models/{run_id}/credit_default_model.pkl"
    metrics_key = f"retraining/metrics/{run_id}/metrics.json"

    try:
        from botocore.exceptions import ClientError
    except Exception as e:  # noqa: BLE001
        raise RuntimeError("Missing python dependency: botocore/boto3") from e

    s3 = _s3_client()
    for key in (model_key, metrics_key):
        try:
            s3.head_object(Bucket=bucket, Key=key)
        except ClientError as e:
            raise RuntimeError(f"Missing expected artifact: s3://{bucket}/{key}") from e

    obj = s3.get_object(Bucket=bucket, Key=metrics_key)
    metrics = json.loads(obj["Body"].read().decode("utf-8"))

    auc = metrics.get("test_auc")
    if auc is not None:
        threshold = float(os.getenv("AUC_THRESHOLD", "0.6"))
        if float(auc) < threshold:
            raise RuntimeError(f"Model validation failed: test_auc={auc} < {threshold}")

    logging.info("Validation OK: s3://%s/%s", bucket, model_key)
    logging.info("Metrics: s3://%s/%s -> %s", bucket, metrics_key, metrics)


with DAG(
    dag_id="credit_scoring_retraining",
    description="Retraining pipeline for credit scoring (new data + PSI drift triggers)",
    schedule="@daily",
    start_date=datetime(2024, 1, 1),
    catchup=False,
    default_args={"retries": 1, "retry_delay": timedelta(minutes=5)},
    tags=["credit-scoring", "retraining"],
) as dag:
    t_check_new_data = PythonOperator(
        task_id="check_new_data",
        python_callable=check_new_data,
    )

    t_compute_drift = PythonOperator(
        task_id="compute_drift",
        python_callable=compute_drift,
    )

    t_branch = BranchPythonOperator(
        task_id="branch_should_retrain",
        python_callable=branch_should_retrain,
    )

    t_skip = EmptyOperator(task_id="skip_retrain")

    s3_secret_name = os.getenv("AIRFLOW_S3_SECRET_NAME", "airflow-s3")
    s3_secrets = [
        Secret("env", "AWS_ACCESS_KEY_ID", s3_secret_name, "AWS_ACCESS_KEY_ID"),
        Secret("env", "AWS_SECRET_ACCESS_KEY", s3_secret_name, "AWS_SECRET_ACCESS_KEY"),
        Secret("env", "AWS_DEFAULT_REGION", s3_secret_name, "AWS_DEFAULT_REGION"),
        Secret("env", "S3_ENDPOINT_URL", s3_secret_name, "S3_ENDPOINT_URL"),
        Secret("env", "BUCKET", s3_secret_name, "BUCKET"),
    ]

    t_retrain = KubernetesPodOperator(
        task_id="retrain_model",
        name="credit-scoring-train",
        namespace="{{ var.value.get('AIRFLOW_TRAIN_NAMESPACE', 'airflow') }}",
        image="{{ var.value.get('TRAINER_IMAGE', 'cr.yandex/<REGISTRY_ID>/credit-trainer:staging') }}",
        cmds=["python", "-u", "scripts/model_training/train_model.py"],
        env_vars={
            "RUN_ID": "{{ run_id }}",
        },
        secrets=s3_secrets,
        get_logs=True,
        is_delete_operator_pod=True,
    )

    t_validate = PythonOperator(
        task_id="validate_model",
        python_callable=validate_model,
    )

    t_success = EmptyOperator(task_id="mark_success")

    t_check_new_data >> t_compute_drift >> t_branch
    t_branch >> t_skip >> t_success
    t_branch >> t_retrain >> t_validate >> t_success

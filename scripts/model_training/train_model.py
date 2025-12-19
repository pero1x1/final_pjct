from __future__ import annotations

import json
import os
from datetime import datetime, timezone
from pathlib import Path

import boto3
import pandas as pd
from joblib import dump
from sklearn.compose import ColumnTransformer
from sklearn.ensemble import GradientBoostingClassifier
from sklearn.impute import SimpleImputer
from sklearn.metrics import f1_score, precision_score, recall_score, roc_auc_score
from sklearn.model_selection import train_test_split
from sklearn.pipeline import Pipeline
from sklearn.preprocessing import OneHotEncoder, StandardScaler

TARGET = "default.payment.next.month"

NUM = [
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

CAT = ["SEX", "EDUCATION", "MARRIAGE", "PAY_0", "PAY_2", "PAY_3", "PAY_4", "PAY_5", "PAY_6"]


def build_pipeline() -> Pipeline:
    num_tf = Pipeline([("imp", SimpleImputer(strategy="median")), ("sc", StandardScaler())])
    cat_tf = Pipeline(
        [("imp", SimpleImputer(strategy="most_frequent")), ("oh", OneHotEncoder(handle_unknown="ignore"))]
    )

    pre = ColumnTransformer([("num", num_tf, NUM), ("cat", cat_tf, CAT)])
    return Pipeline(
        [
            ("pre", pre),
            (
                "clf",
                GradientBoostingClassifier(
                    n_estimators=230,
                    learning_rate=0.06,
                    max_depth=3,
                ),
            ),
        ]
    )


def safe_run_id(run_id: str) -> str:
    import re

    return re.sub(r"[^0-9A-Za-z_.-]+", "_", run_id).strip("_") or "run"


def require_env(name: str) -> str:
    value = os.getenv(name)
    if not value:
        raise RuntimeError(f"Missing required env var: {name}")
    return value


def s3_client():
    endpoint = os.getenv("S3_ENDPOINT_URL", "https://storage.yandexcloud.net")
    region = os.getenv("AWS_DEFAULT_REGION", "ru-central1")
    return boto3.client("s3", endpoint_url=endpoint, region_name=region)


def main() -> None:
    run_id_raw = require_env("RUN_ID")
    run_id = safe_run_id(run_id_raw)
    bucket = require_env("BUCKET")
    key_current = "retraining/current.csv"

    model_key = f"retraining/models/{run_id}/credit_default_model.pkl"
    metrics_key = f"retraining/metrics/{run_id}/metrics.json"

    s3 = s3_client()
    tmp_dir = Path("/tmp/retraining")
    tmp_dir.mkdir(parents=True, exist_ok=True)
    current_path = tmp_dir / "current.csv"
    s3.download_file(bucket, key_current, str(current_path))

    df = pd.read_csv(current_path)
    if TARGET not in df.columns:
        raise RuntimeError(f"Dataset must contain target column '{TARGET}', got columns={list(df.columns)}")

    X = df.drop(columns=[TARGET])
    y = df[TARGET]

    X_train, X_test, y_train, y_test = train_test_split(
        X,
        y,
        test_size=float(os.getenv("TEST_SIZE", "0.2")),
        random_state=int(os.getenv("RANDOM_STATE", "42")),
        stratify=y if y.nunique() > 1 else None,
    )

    pipe = build_pipeline()
    pipe.fit(X_train, y_train)

    proba = pipe.predict_proba(X_test)[:, 1]
    pred = (proba >= 0.5).astype(int)

    metrics = {
        "run_id": run_id,
        "run_id_raw": run_id_raw,
        "timestamp": datetime.now(timezone.utc).isoformat(),
        "rows": int(df.shape[0]),
        "columns": int(df.shape[1]),
        "model": "gbdt",
        "test_auc": float(roc_auc_score(y_test, proba)) if y_test.nunique() > 1 else None,
        "test_f1": float(f1_score(y_test, pred)),
        "test_precision": float(precision_score(y_test, pred, zero_division=0)),
        "test_recall": float(recall_score(y_test, pred)),
    }

    model_path = tmp_dir / "credit_default_model.pkl"
    dump(pipe, model_path)

    metrics_path = tmp_dir / "metrics.json"
    metrics_path.write_text(json.dumps(metrics, indent=2, ensure_ascii=False), encoding="utf-8")

    s3.upload_file(str(model_path), bucket, model_key)
    s3.upload_file(str(metrics_path), bucket, metrics_key)

    print(f"[TRAIN] model -> s3://{bucket}/{model_key}")
    print(f"[TRAIN] metrics -> s3://{bucket}/{metrics_key}")
    print(f"[TRAIN] metrics content: {json.dumps(metrics, ensure_ascii=False)}")


if __name__ == "__main__":
    main()

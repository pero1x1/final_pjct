from pathlib import Path
import json

import matplotlib.pyplot as plt
import mlflow
import mlflow.sklearn
import pandas as pd
from joblib import dump
from sklearn.compose import ColumnTransformer
from sklearn.ensemble import GradientBoostingClassifier
from sklearn.impute import SimpleImputer
from sklearn.metrics import (
    RocCurveDisplay,
    f1_score,
    precision_score,
    recall_score,
    roc_auc_score,
)
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
    num_tf = Pipeline(
        [
            ("imp", SimpleImputer(strategy="median")),
            ("sc", StandardScaler()),
        ]
    )

    cat_tf = Pipeline(
        [
            ("imp", SimpleImputer(strategy="most_frequent")),
            ("oh", OneHotEncoder(handle_unknown="ignore")),
        ]
    )

    pre = ColumnTransformer(
        [
            ("num", num_tf, NUM),
            ("cat", cat_tf, CAT),
        ]
    )

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


def main(proc_dir: str, model_path: str, metrics_path: str, roc_path: str) -> None:
    d = Path(proc_dir)

    train = pd.read_csv(d / "train.csv")
    test = pd.read_csv(d / "test.csv")

    X_train, y_train = train.drop(columns=[TARGET]), train[TARGET]
    X_test, y_test = test.drop(columns=[TARGET]), test[TARGET]

    pipe = build_pipeline()
    pipe.fit(X_train, y_train)

    proba = pipe.predict_proba(X_test)[:, 1]
    pred = (proba >= 0.5).astype(int)

    metrics = {
        "model": "gbdt",
        "test_auc": float(roc_auc_score(y_test, proba)),
        "test_f1": float(f1_score(y_test, pred)),
        "test_precision": float(precision_score(y_test, pred, zero_division=0)),
        "test_recall": float(recall_score(y_test, pred)),
    }

    Path(model_path).parent.mkdir(parents=True, exist_ok=True)
    dump(pipe, model_path)

    Path(metrics_path).write_text(json.dumps(metrics, indent=2, ensure_ascii=False))

    RocCurveDisplay.from_predictions(y_test, proba)
    Path(roc_path).parent.mkdir(parents=True, exist_ok=True)
    plt.tight_layout()
    plt.savefig(roc_path)
    plt.close()

    mlflow.set_tracking_uri("file:./mlruns")
    mlflow.set_experiment("CreditDefault_Prediction")

    with mlflow.start_run():
        for k, v in metrics.items():
            if k.startswith("test_"):
                mlflow.log_metric(k, v)
        mlflow.log_param("model", "gbdt")
        mlflow.log_artifact(roc_path)
        mlflow.sklearn.log_model(pipe, artifact_path="model")

    print("Saved model, metrics, roc.")


if __name__ == "__main__":
    import argparse

    parser = argparse.ArgumentParser()
    parser.add_argument("--proc_dir", default="data/processed")
    parser.add_argument("--model_path", default="models/credit_default_model.pkl")
    parser.add_argument("--metrics_path", default="metrics.json")
    parser.add_argument("--roc_path", default="artifacts/roc.png")
    args = parser.parse_args()

    main(args.proc_dir, args.model_path, args.metrics_path, args.roc_path)
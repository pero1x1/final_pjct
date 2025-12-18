# src/models/search.py
from __future__ import annotations
from pathlib import Path
from datetime import datetime
import json
import numpy as np
import pandas as pd

from sklearn.compose import ColumnTransformer
from sklearn.pipeline import Pipeline
from sklearn.preprocessing import StandardScaler, OneHotEncoder
from sklearn.impute import SimpleImputer
from sklearn.linear_model import LogisticRegression
from sklearn.ensemble import GradientBoostingClassifier
from sklearn.model_selection import RandomizedSearchCV
from sklearn.metrics import roc_auc_score, f1_score, precision_score, recall_score

import mlflow
import mlflow.sklearn
from mlflow.models.signature import infer_signature


TARGET = "default.payment.next.month"

NUM = [
    "LIMIT_BAL", "AGE",
    "BILL_AMT1","BILL_AMT2","BILL_AMT3","BILL_AMT4","BILL_AMT5","BILL_AMT6",
    "PAY_AMT1","PAY_AMT2","PAY_AMT3","PAY_AMT4","PAY_AMT5","PAY_AMT6",
    "utilization1","payment_ratio1","max_delay",
]
CAT = ["SEX","EDUCATION","MARRIAGE","PAY_0","PAY_2","PAY_3","PAY_4","PAY_5","PAY_6"]


def build_preprocess() -> ColumnTransformer:
    num_tf = Pipeline([("imp", SimpleImputer(strategy="median")), ("sc", StandardScaler())])
    cat_tf = Pipeline([("imp", SimpleImputer(strategy="most_frequent")),
                       ("oh", OneHotEncoder(handle_unknown="ignore"))])
    return ColumnTransformer([("num", num_tf, NUM), ("cat", cat_tf, CAT)])


def main(proc_dir: str,
         n_iter: int = 20,
         seed: int = 42,
         save_root: str | None = "models/best_search"):

    d = Path(proc_dir)
    train = pd.read_csv(d / "train.csv")
    test  = pd.read_csv(d / "test.csv")
    Xtr, ytr = train.drop(columns=[TARGET]), train[TARGET]
    Xte, yte = test.drop(columns=[TARGET]),  test[TARGET]

    pre = build_preprocess()

    models = {
        "logreg": Pipeline([("pre", pre), ("clf", LogisticRegression(max_iter=5000))]),
        "gbdt":   Pipeline([("pre", pre), ("clf", GradientBoostingClassifier())]),
    }

    search_spaces = {
        "logreg": {
            "clf__C": np.logspace(-3, 2, 30),
            "clf__penalty": ["l2"],
            "clf__solver": ["lbfgs", "liblinear", "saga"],
        },
        "gbdt": {
            "clf__n_estimators": np.arange(80, 401, 20),
            "clf__learning_rate": np.logspace(-3, -0.1, 20),
            "clf__max_depth": np.arange(2, 6),
        },
    }

    mlflow.set_tracking_uri("file:./mlruns")
    mlflow.set_experiment("CreditDefault_Prediction")

    best_global: tuple[float, str, Pipeline] | None = None

    for name, pipe in models.items():
        with mlflow.start_run(run_name=f"search_{name}") as run:
            rs = RandomizedSearchCV(
                pipe, search_spaces[name], n_iter=n_iter, scoring="roc_auc",
                random_state=seed, n_jobs=-1, cv=3, verbose=0
            )
            rs.fit(Xtr, ytr)

            best = rs.best_estimator_
            proba = best.predict_proba(Xte)[:, 1]
            pred  = (proba >= 0.5).astype(int)

            metrics = {
                "model": name,
                "cv_best_score": float(rs.best_score_),
                "test_auc": float(roc_auc_score(yte, proba)),
                "test_f1": float(f1_score(yte, pred)),
                "test_precision": float(precision_score(yte, pred, zero_division=0)),
                "test_recall": float(recall_score(yte, pred)),
            }

            # подпись и пример входа, чтобы убрать предупреждения
            input_example = Xte.head(3)
            signature = infer_signature(input_example, best.predict_proba(input_example)[:, 1])

            mlflow.log_params(rs.best_params_)
            for k, v in metrics.items():
                if k.startswith("test_") or k == "cv_best_score":
                    mlflow.log_metric(k, v)

            # логируем в MLflow с подписью
            mlflow.sklearn.log_model(
                best, artifact_path="model", input_example=input_example, signature=signature
            )

            # сохраняем локально в уникальную папку
            if save_root:
                run_id = run.info.run_id[:8]
                save_dir = Path(save_root) / f"{name}_seed{seed}_iter{n_iter}_{run_id}"
                save_dir.parent.mkdir(parents=True, exist_ok=True)
                mlflow.sklearn.save_model(best, path=str(save_dir),
                                          input_example=input_example, signature=signature)
                print(f"Saved {name} to {save_dir}")

            if (best_global is None) or (metrics["test_auc"] > best_global[0]):
                best_global = (metrics["test_auc"], name, best)

    if best_global:
        print(f"Best by AUC: {best_global[1]} (AUC={best_global[0]:.5f})")


if __name__ == "__main__":
    import argparse
    p = argparse.ArgumentParser()
    p.add_argument("--proc_dir", default="data/processed")
    p.add_argument("--n_iter", type=int, default=20)
    p.add_argument("--seed", type=int, default=42)
    p.add_argument("--save_root", default="models/best_search")
    args = p.parse_args()
    main(args.proc_dir, args.n_iter, args.seed, args.save_root)
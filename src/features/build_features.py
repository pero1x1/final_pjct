import json
from pathlib import Path

import pandas as pd

TARGET = "default.payment.next.month"


def add_basic_features(df: pd.DataFrame) -> pd.DataFrame:
    f = df.copy()
    f["utilization1"] = (f["BILL_AMT1"] / f["LIMIT_BAL"].clip(lower=1)).fillna(0)
    f["payment_ratio1"] = (f["PAY_AMT1"] / f["BILL_AMT1"].abs().clip(lower=1)).fillna(0)
    pay_cols = ["PAY_0", "PAY_2", "PAY_3", "PAY_4", "PAY_5", "PAY_6"]
    f["max_delay"] = f[pay_cols].max(axis=1)
    return f


def main(proc_dir: str):
    d = Path(proc_dir)
    train = pd.read_csv(d / "train_base.csv")
    test = pd.read_csv(d / "test_base.csv")

    train = add_basic_features(train)
    test = add_basic_features(test)

    train.to_csv(d / "train.csv", index=False)
    test.to_csv(d / "test.csv", index=False)

    summary = {
        "train_rows": int(len(train)),
        "test_rows": int(len(test)),
        "n_features": int(train.shape[1] - 1),
        "target_mean_train": float(train[TARGET].mean()),
        "target_mean_test": float(test[TARGET].mean()),
        "utilization1_p95_test": float(test["utilization1"].quantile(0.95)),
    }
    (d / "summary.json").write_text(json.dumps(summary, indent=2, ensure_ascii=False))
    print("Features added and summary.json written.")


if __name__ == "__main__":
    import argparse

    p = argparse.ArgumentParser()
    p.add_argument("proc_dir")
    args = p.parse_args()
    main(args.proc_dir)

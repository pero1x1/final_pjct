import json
from pathlib import Path

import numpy as np
import pandas as pd
from sklearn.model_selection import train_test_split

TARGET = "default.payment.next.month"


def clean_frame(df: pd.DataFrame) -> pd.DataFrame:
    df = df.copy()
    if "ID" in df:
        df = df.drop(columns=["ID"])
    df["EDUCATION"] = df["EDUCATION"].replace({0: 4, 5: 4, 6: 4})
    df["MARRIAGE"] = df["MARRIAGE"].replace({0: 3})
    money = [c for c in df if c.startswith(("BILL_AMT", "PAY_AMT"))]
    lo = {c: df[c].quantile(0.01) for c in money}
    hi = {c: df[c].quantile(0.99) for c in money}
    for c in money:
        df[c] = np.clip(df[c], lo[c], hi[c])
    int_cols = [
        "SEX",
        "EDUCATION",
        "MARRIAGE",
        "AGE",
        "PAY_0",
        "PAY_2",
        "PAY_3",
        "PAY_4",
        "PAY_5",
        "PAY_6",
        TARGET,
    ]
    for c in int_cols:
        s = pd.to_numeric(df[c], errors="coerce")
        mode_val = s.mode(dropna=True)[0] if not s.mode(dropna=True).empty else 0
        df[c] = s.fillna(mode_val).round().astype(int)
    df = df.drop_duplicates()
    return df


def main(raw_csv: str, out_dir: str):
    out = Path(out_dir)
    out.mkdir(parents=True, exist_ok=True)
    df = pd.read_csv(raw_csv)
    df = clean_frame(df)
    train_df, test_df = train_test_split(df, test_size=0.2, random_state=42, stratify=df[TARGET])
    train_df.to_csv(out / "train_base.csv", index=False)
    test_df.to_csv(out / "test_base.csv", index=False)
    summary = {
        "train_rows": int(len(train_df)),
        "test_rows": int(len(test_df)),
        "n_features_raw": int(train_df.shape[1] - 1),
        "target_mean_train": float(train_df[TARGET].mean()),
        "target_mean_test": float(test_df[TARGET].mean()),
        "utilization1_p95_test": None,
    }
    (out / "summary_base.json").write_text(json.dumps(summary, indent=2, ensure_ascii=False))
    print("Saved train/test and summary.json")


if __name__ == "__main__":
    import argparse

    p = argparse.ArgumentParser()
    p.add_argument("raw_csv")
    p.add_argument("out_dir")
    args = p.parse_args()
    main(args.raw_csv, args.out_dir)

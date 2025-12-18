import json
from pathlib import Path

import numpy as np
import pandas as pd
import onnxruntime as ort
import torch
from sklearn.model_selection import train_test_split
from sklearn.metrics import roc_auc_score
from sklearn.preprocessing import StandardScaler

from nn_model import CreditMLP


def detect_target(df: pd.DataFrame) -> str:
    if "target" in df.columns:
        return "target"
    for c in df.columns:
        low = c.lower().replace(".", "").replace(" ", "").replace("_", "")
        if "default" in low and ("nextmonth" in low or "payment" in low):
            return c
    return df.columns[-1]


def sigmoid(x: np.ndarray) -> np.ndarray:
    return 1.0 / (1.0 + np.exp(-x))


def onnx_predict_logits(model_path: str, x: np.ndarray) -> np.ndarray:
    sess = ort.InferenceSession(model_path, providers=["CPUExecutionProvider"])
    out = sess.run(None, {"x": x})[0]
    return np.asarray(out).reshape(-1)


def main():
    meta = json.loads(Path("models/nn_meta.json").read_text(encoding="utf-8"))
    feature_list = meta["feature_list"]
    seed = 42

    df = pd.read_csv("UCI_Credit_Card.csv")

    for c in ["ID", "id", "Id"]:
        if c in df.columns:
            df = df.drop(columns=[c])

    target = detect_target(df)
    X = df[feature_list].astype(np.float32).values
    y = df[target].astype(np.float32).values

    X_train, X_val, y_train, y_val = train_test_split(
        X, y, test_size=0.2, random_state=seed, stratify=y
    )

    scaler = StandardScaler()
    X_train = scaler.fit_transform(X_train).astype(np.float32)
    X_val = scaler.transform(X_val).astype(np.float32)

    # Torch (FP32 baseline)
    ckpt = torch.load("models/nn_model.pt", map_location="cpu")
    model = CreditMLP(n_features=X_val.shape[1])
    model.load_state_dict(ckpt["state_dict"])
    model.eval()

    with torch.no_grad():
        torch_logits = model(torch.from_numpy(X_val)).numpy()
    torch_auc = roc_auc_score(y_val, sigmoid(torch_logits))

    # ONNX FP32 clean
    fp32_logits = onnx_predict_logits("models/model.fp32.clean.onnx", X_val)
    fp32_auc = roc_auc_score(y_val, sigmoid(fp32_logits))

    # ONNX INT8 clean
    int8_logits = onnx_predict_logits("models/model.int8.clean.onnx", X_val)
    int8_auc = roc_auc_score(y_val, sigmoid(int8_logits))

    print(f"Torch AUC: {torch_auc:.5f}")
    print(f"ONNX  AUC: {fp32_auc:.5f}")
    print(f"INT8  AUC: {int8_auc:.5f}")
    print(f"Drop INT8 vs ONNX: {(fp32_auc - int8_auc):.5f}")


if __name__ == "__main__":
    main()

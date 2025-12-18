import argparse
import json
from pathlib import Path

import numpy as np
import onnxruntime as ort
import torch

from nn_model import CreditMLP


def sigmoid(x: np.ndarray) -> np.ndarray:
    return 1.0 / (1.0 + np.exp(-x))


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--onnx", default="models/model.onnx")
    ap.add_argument("--tol", type=float, default=1e-4)
    args = ap.parse_args()

    meta = json.loads(Path("models/nn_meta.json").read_text(encoding="utf-8"))
    n_features = int(meta["n_features"])

    ckpt = torch.load("models/nn_model.pt", map_location="cpu")
    model = CreditMLP(n_features=n_features)
    model.load_state_dict(ckpt["state_dict"])
    model.eval()

    sess = ort.InferenceSession(args.onnx, providers=["CPUExecutionProvider"])
    x = np.random.randn(256, n_features).astype(np.float32)

    with torch.no_grad():
        torch_logits = model(torch.from_numpy(x)).numpy()
    onnx_logits = sess.run(None, {"x": x})[0]
    onnx_logits = np.asarray(onnx_logits).reshape(-1)

    diff = np.max(np.abs(torch_logits - onnx_logits))
    print("max_abs_diff_logits:", float(diff))

    torch_p = sigmoid(torch_logits)
    onnx_p = sigmoid(onnx_logits)
    diff_p = np.max(np.abs(torch_p - onnx_p))
    print("max_abs_diff_proba :", float(diff_p))

    assert diff < args.tol, f"ONNX mismatch: diff={diff} tol={args.tol}"
    print(f"OK: ONNX validated (<{args.tol})")


if __name__ == "__main__":
    main()

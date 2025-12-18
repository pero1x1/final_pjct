import argparse
import json
import time
from pathlib import Path

import numpy as np
import onnxruntime as ort
import torch

from nn_model import CreditMLP


def sigmoid(x: np.ndarray) -> np.ndarray:
    return 1.0 / (1.0 + np.exp(-x))


def bench_torch(model, x: np.ndarray, iters: int, warmup: int):
    xb = torch.from_numpy(x)
    with torch.no_grad():
        for _ in range(warmup):
            _ = model(xb)
    t0 = time.perf_counter()
    with torch.no_grad():
        for _ in range(iters):
            _ = model(xb)
    t = (time.perf_counter() - t0) / iters
    return t


def bench_onnx(sess, x: np.ndarray, iters: int, warmup: int):
    # warmup
    for _ in range(warmup):
        _ = sess.run(None, {"x": x})
    t0 = time.perf_counter()
    for _ in range(iters):
        _ = sess.run(None, {"x": x})
    t = (time.perf_counter() - t0) / iters
    return t


def make_session(model_path: str, provider: str):
    so = ort.SessionOptions()
    so.graph_optimization_level = ort.GraphOptimizationLevel.ORT_ENABLE_ALL
    so.intra_op_num_threads = 8
    so.inter_op_num_threads = 1
    return ort.InferenceSession(model_path, sess_options=so, providers=[provider])



def main():
    torch.set_num_threads(4)
    ap = argparse.ArgumentParser()
    ap.add_argument("--batch", type=int, default=1024)
    ap.add_argument("--iters", type=int, default=300)
    ap.add_argument("--warmup", type=int, default=30)
    ap.add_argument("--provider", default="CPUExecutionProvider")  # или CUDAExecutionProvider
    args = ap.parse_args()

    meta = json.loads(Path("models/nn_meta.json").read_text(encoding="utf-8"))
    n_features = int(meta["n_features"])

    batch = args.batch
    x = np.random.randn(batch, n_features).astype(np.float32)

    # торч
    ckpt = torch.load("models/nn_model.pt", map_location="cpu")
    model = CreditMLP(n_features=n_features)
    model.load_state_dict(ckpt["state_dict"])
    model.eval()

    t_torch = bench_torch(model, x, iters=args.iters, warmup=args.warmup)

    # оннх fp32 и int8
    fp32_path = "models/model.onnx"
    int8_path = "models/model.int8.onnx"

    sess_fp32 = make_session(fp32_path, args.provider)
    sess_int8 = make_session(int8_path, args.provider)

    t_fp32 = bench_onnx(sess_fp32, x, iters=args.iters, warmup=args.warmup)
    t_int8 = bench_onnx(sess_int8, x, iters=args.iters, warmup=args.warmup)

    def fmt_ms(sec): return sec * 1000.0
    def rps(sec): return batch / sec

    print(f"Provider: {args.provider}")
    print(f"Batch: {batch}, Iters: {args.iters}")
    print(f"Torch (cpu)   ms/batch: {fmt_ms(t_torch):.3f} | batches/s: {1/t_torch:.2f} | rows/s: {rps(t_torch):.0f}")
    print(f"ONNX FP32     ms/batch: {fmt_ms(t_fp32):.3f} | batches/s: {1/t_fp32:.2f} | rows/s: {rps(t_fp32):.0f}")
    print(f"ONNX INT8     ms/batch: {fmt_ms(t_int8):.3f} | batches/s: {1/t_int8:.2f} | rows/s: {rps(t_int8):.0f}")
    print(f"Speedup ONNX FP32 vs Torch: {t_torch/t_fp32:.2f}x")
    print(f"Speedup INT8 vs ONNX FP32:  {t_fp32/t_int8:.2f}x")
    print(f"Speedup INT8 vs Torch:      {t_torch/t_int8:.2f}x")


if __name__ == "__main__":
    main()
    

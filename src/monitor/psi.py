from __future__ import annotations

import json
from pathlib import Path
from typing import Dict, Iterable, List, Tuple

import numpy as np
import pandas as pd


def _bin_edges(series: pd.Series, bins: int = 10) -> np.ndarray:
    """Квантили как границы бинов (устойчивее к выбросам, чем равные интервалы)."""
    # Исключаем NaN
    s = series.dropna().astype(float)
    # Если все значения одинаковые, вернём одну «коробку»
    if s.nunique() <= 1:
        return np.array([s.min(), s.max()])
    qs = np.linspace(0.0, 1.0, bins + 1)
    edges = np.unique(np.quantile(s, qs))
    # На всякий случай гарантируем строгую монотонность
    if len(edges) < 2:
        edges = np.array([s.min(), s.max()])
    return edges


def psi(base: pd.Series, current: pd.Series, bins: int = 10, eps: float = 1e-8) -> float:
    """
    Population Stability Index для одного признака.
    Чем выше PSI, тем сильнее сдвиг распределения (обычно пороги 0.1/0.25).
    """
    edges = _bin_edges(base, bins=bins)
    # hist по одинаковым границам
    base_cnt, _ = np.histogram(base.dropna().astype(float), bins=edges)
    curr_cnt, _ = np.histogram(current.dropna().astype(float), bins=edges)

    base_p = base_cnt / max(base_cnt.sum(), eps)
    curr_p = curr_cnt / max(curr_cnt.sum(), eps)

    # Избегаем деления на ноль и log(0)
    base_p = np.maximum(base_p, eps)
    curr_p = np.maximum(curr_p, eps)

    return float(np.sum((curr_p - base_p) * np.log(curr_p / base_p)))


def compute_psi_report(
    train: pd.DataFrame,
    stream: pd.DataFrame,
    features: Iterable[str],
    bins: int = 10,
) -> Tuple[float, Dict[str, float]]:
    """Возвращает (avg_psi, per_feature_psi)."""
    per_feature: Dict[str, float] = {}
    for col in features:
        if col not in train.columns or col not in stream.columns:
            continue
        try:
            per_feature[col] = psi(train[col], stream[col], bins=bins)
        except Exception:
            # На случай строковых/категориальных коллапсов — пропустим
            continue

    avg = float(np.mean(list(per_feature.values()))) if per_feature else 0.0
    return avg, per_feature


def main(
    train_path: str = "data/processed/train.csv",
    stream_path: str = "data/processed/test.csv",
    features_path: str = "feature_list.json",
    out_path: str = "reports/psi.json",
    bins: int = 10,
) -> None:
    Path(out_path).parent.mkdir(parents=True, exist_ok=True)

    train = pd.read_csv(train_path)
    stream = pd.read_csv(stream_path)

    # Берём список фич из feature_list.json, если он есть
    features: List[str]
    if Path(features_path).exists():
        with open(features_path, "r", encoding="utf-8") as f:
            features = json.load(f)
    else:
        # иначе — все числовые столбцы пересечения
        num_train = train.select_dtypes(include=["number"]).columns
        num_stream = stream.select_dtypes(include=["number"]).columns
        features = sorted(set(num_train).intersection(set(num_stream)))

    avg, per_feature = compute_psi_report(train, stream, features, bins=bins)

    report = {
        "avg_psi": avg,
        "bins": bins,
        "n_features": len(per_feature),
        "per_feature": per_feature,
    }
    with open(out_path, "w", encoding="utf-8") as f:
        json.dump(report, f, indent=2, ensure_ascii=False)

    print(f"[PSI] avg={avg:.4f}; report -> {out_path}")


if __name__ == "__main__":
    import argparse

    parser = argparse.ArgumentParser(description="Compute PSI drift report")
    parser.add_argument("--train", default="data/processed/train.csv")
    parser.add_argument("--stream", default="data/processed/test.csv")
    parser.add_argument("--features", default="feature_list.json")
    parser.add_argument("--out", default="reports/psi.json")
    parser.add_argument("--bins", type=int, default=10)
    args = parser.parse_args()

    main(
        train_path=args.train,
        stream_path=args.stream,
        features_path=args.features,
        out_path=args.out,
        bins=args.bins,
    )

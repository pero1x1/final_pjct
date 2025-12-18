import argparse
import json
from pathlib import Path

import numpy as np
import pandas as pd
import torch
from sklearn.metrics import roc_auc_score
from sklearn.model_selection import train_test_split
from sklearn.preprocessing import StandardScaler
from torch.utils.data import DataLoader, TensorDataset
from tqdm import tqdm

from nn_model import CreditMLP


def detect_target(df: pd.DataFrame) -> str:
    if "target" in df.columns:
        return "target"
    for c in df.columns:
        low = c.lower().replace(".", "").replace(" ", "").replace("_", "")
        if "default" in low and ("nextmonth" in low or "payment" in low or "y" == low):
            return c
    # fallback
    return df.columns[-1]


def load_feature_list(path: Path) -> list[str] | None:
    if path.exists():
        with path.open("r", encoding="utf-8") as f:
            data = json.load(f)
        if isinstance(data, list) and len(data) > 0:
            return data
    return None


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--data", default="UCI_Credit_Card.csv")
    ap.add_argument("--epochs", type=int, default=10)
    ap.add_argument("--batch", type=int, default=512)
    ap.add_argument("--lr", type=float, default=1e-3)
    ap.add_argument("--seed", type=int, default=42)
    args = ap.parse_args()

    np.random.seed(args.seed)
    torch.manual_seed(args.seed)

    data_path = Path(args.data)
    if not data_path.exists():
        raise FileNotFoundError(f"Не найден файл данных: {data_path.resolve()}")

    df = pd.read_csv(data_path)

    #  если лишняя колонка
    for c in ["ID", "id", "Id"]:
        if c in df.columns:
            df = df.drop(columns=[c])

    target_col = detect_target(df)

    feature_list = load_feature_list(Path("feature_list.json"))
    if feature_list is None:
        feature_list = [c for c in df.columns if c != target_col]

    # на всякий чистка
    feature_list = [c for c in feature_list if c in df.columns and c != target_col]

    X = df[feature_list].astype(np.float32).values
    y = df[target_col].astype(np.float32).values

    X_train, X_val, y_train, y_val = train_test_split(
        X, y, test_size=0.2, random_state=args.seed, stratify=y if len(np.unique(y)) == 2 else None
    )

    scaler = StandardScaler()
    X_train = scaler.fit_transform(X_train).astype(np.float32)
    X_val = scaler.transform(X_val).astype(np.float32)

    device = torch.device("cuda" if torch.cuda.is_available() else "cpu")

    train_ds = TensorDataset(torch.from_numpy(X_train), torch.from_numpy(y_train))
    val_ds = TensorDataset(torch.from_numpy(X_val), torch.from_numpy(y_val))
    train_dl = DataLoader(train_ds, batch_size=args.batch, shuffle=True, drop_last=False)
    val_dl = DataLoader(val_ds, batch_size=args.batch, shuffle=False, drop_last=False)

    model = CreditMLP(n_features=X_train.shape[1]).to(device)
    opt = torch.optim.Adam(model.parameters(), lr=args.lr)
    loss_fn = torch.nn.BCEWithLogitsLoss()

    best_auc = -1.0
    best_state = None

    for epoch in range(1, args.epochs + 1):
        model.train()
        pbar = tqdm(train_dl, desc=f"epoch {epoch}/{args.epochs}")
        for xb, yb in pbar:
            xb = xb.to(device)
            yb = yb.to(device)

            opt.zero_grad()
            logits = model(xb)
            loss = loss_fn(logits, yb)
            loss.backward()
            opt.step()
            pbar.set_postfix(loss=float(loss.detach().cpu().item()))

        # val auc
        model.eval()
        preds = []
        ys = []
        with torch.no_grad():
            for xb, yb in val_dl:
                xb = xb.to(device)
                logits = model(xb)
                prob = torch.sigmoid(logits).detach().cpu().numpy()
                preds.append(prob)
                ys.append(yb.numpy())
        preds = np.concatenate(preds)
        ys = np.concatenate(ys)

        auc = roc_auc_score(ys, preds) if len(np.unique(ys)) == 2 else float("nan")
        print(f"[val] roc_auc={auc:.5f}")

        if auc > best_auc:
            best_auc = auc
            best_state = {k: v.detach().cpu() for k, v in model.state_dict().items()}

    Path("models").mkdir(exist_ok=True)

    torch.save(
        {
            "state_dict": best_state,
            "n_features": int(X_train.shape[1]),
        },
        "models/nn_model.pt",
    )

    meta = {
        "n_features": int(X_train.shape[1]),
        "feature_list": feature_list,
        "scaler_mean": scaler.mean_.tolist(),
        "scaler_scale": scaler.scale_.tolist(),
        "best_val_roc_auc": float(best_auc),
    }
    with open("models/nn_meta.json", "w", encoding="utf-8") as f:
        json.dump(meta, f, ensure_ascii=False, indent=2)

    print("Saved:")
    print(" - models/nn_model.pt")
    print(" - models/nn_meta.json")


if __name__ == "__main__":
    main()

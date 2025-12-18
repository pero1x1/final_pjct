import json
from pathlib import Path

import torch
import torch.nn as nn

from nn_model import CreditMLP


class ExportWrapper(nn.Module):
    def __init__(self, model: CreditMLP):
        super().__init__()
        self.model = model

    def forward(self, x):
        return self.model.net(x)


def main():
    meta_path = Path("models/nn_meta.json")
    ckpt_path = Path("models/nn_model.pt")

    meta = json.loads(meta_path.read_text(encoding="utf-8"))
    n_features = int(meta["n_features"])

    ckpt = torch.load(ckpt_path, map_location="cpu")
    base = CreditMLP(n_features=n_features)
    base.load_state_dict(ckpt["state_dict"])
    base.eval()

    model = ExportWrapper(base).eval()

    dummy = torch.randn(1, n_features, dtype=torch.float32)

    out_path = Path("models/model.onnx")
    torch.onnx.export(
        model,
        dummy,
        out_path.as_posix(),
        input_names=["x"],
        output_names=["logits"],
        dynamic_axes={"x": {0: "batch"}, "logits": {0: "batch"}},
        opset_version=17,
        do_constant_folding=True,
    )
    print(f"Saved: {out_path}")


if __name__ == "__main__":
    main()

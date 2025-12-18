from pathlib import Path

import onnx
from onnxruntime.quantization import QuantType, quantize_dynamic


def prepare_model(inp: Path, out: Path) -> None:
    m = onnx.load(str(inp))

    # чистим спорные value_info (часто они ломают shape inference)
    m.graph.ClearField("value_info")

    # прогоняем shape inference уже на "чистом" графе
    m = onnx.shape_inference.infer_shapes(m)

    onnx.save(m, str(out))


def main():
    inp = Path("models/model.onnx")
    prepared = Path("models/model.prepared.onnx")
    out = Path("models/model.int8.onnx")

    if not inp.exists():
        raise FileNotFoundError("Нет models/model.onnx (сначала export_onnx.py)")

    prepare_model(inp, prepared)
    print(f"Prepared: {prepared}")

    quantize_dynamic(
        model_input=str(prepared),
        model_output=str(out),
        weight_type=QuantType.QInt8,
        # важные опции для таких графов:
        extra_options={
            "MatMulConstBOnly": True,                 # не трогать MatMul без константных весов
            "DefaultTensorType": onnx.TensorProto.FLOAT,
        },
    )

    print(f"Saved: {out}")


if __name__ == "__main__":
    main()

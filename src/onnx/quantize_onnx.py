from pathlib import Path

import onnx
from onnxruntime.quantization import QuantType, quantize_dynamic


def prepare_model(inp: Path, out: Path) -> None:
    model = onnx.load(str(inp))

    # чистим value_info для shapes
    model.graph.ClearField("value_info")
    model = onnx.shape_inference.infer_shapes(model)

    onnx.save(model, str(out))


def main() -> None:
    inp = Path("models/model.onnx")
    prepared = Path("models/model.prepared.onnx")
    out = Path("models/model.int8.onnx")

    if not inp.exists():
        raise FileNotFoundError("models/model.onnx not found (run export_onnx.py)")

    prepare_model(inp, prepared)
    print(f"Prepared: {prepared}")

    quantize_dynamic(
        model_input=str(prepared),
        model_output=str(out),
        weight_type=QuantType.QInt8,
        extra_options={
            "MatMulConstBOnly": True,
            "DefaultTensorType": onnx.TensorProto.FLOAT,
        },
    )

    print(f"Saved: {out}")


if __name__ == "__main__":
    main()

from pathlib import Path
import onnx


def fix(inp: str, out: str):
    m = onnx.load(inp)

    # убираем жёстко заданные размеры у output, чтобы батчи не ругались
    for vi in list(m.graph.output):
        t = vi.type.tensor_type
        if t.HasField("shape"):
            t.shape.ClearField("dim")

    onnx.save(m, out)
    print(f"Saved: {out}")


def main():
    p = Path("models")
    fix(str(p / "model.onnx"), str(p / "model.fp32.clean.onnx"))
    fix(str(p / "model.int8.onnx"), str(p / "model.int8.clean.onnx"))


if __name__ == "__main__":
    main()

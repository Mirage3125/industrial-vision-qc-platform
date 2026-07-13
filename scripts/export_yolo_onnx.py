import argparse
import importlib
from pathlib import Path

import onnx


def main() -> None:
    parser = argparse.ArgumentParser(description="Export a trained Ultralytics YOLO model to ONNX")
    parser.add_argument("--weights", type=Path, required=True)
    parser.add_argument("--imgsz", type=int, default=640)
    parser.add_argument("--opset", type=int, default=17)
    parser.add_argument("--half", action="store_true")
    args = parser.parse_args()
    if not args.weights.is_file():
        raise SystemExit(f"Best PyTorch weights do not exist: {args.weights}")
    try:
        yolo_class = importlib.import_module("ultralytics").YOLO
    except ImportError as error:
        raise SystemExit("Ultralytics/PyTorch is not installed; export cannot run") from error
    exported = yolo_class(str(args.weights)).export(
        format="onnx",
        imgsz=args.imgsz,
        opset=args.opset,
        dynamic=True,
        simplify=False,
        half=args.half,
        batch=1,
    )
    onnx_path = Path(str(exported))
    model = onnx.load(onnx_path)
    onnx.checker.check_model(model, full_check=True)
    print(f"Valid ONNX model: {onnx_path.resolve()}")


if __name__ == "__main__":
    main()

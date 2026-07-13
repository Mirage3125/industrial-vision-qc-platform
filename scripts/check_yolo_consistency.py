import argparse
import importlib
import json
from pathlib import Path
from typing import Any

import cv2
import numpy as np
import onnxruntime as ort

from backend.app.inference.yolo_postprocess import postprocess_yolo, preprocess_image


def _numpy(value: Any) -> np.ndarray[Any, Any]:
    if isinstance(value, (tuple, list)):
        value = value[0]
    return value.detach().cpu().numpy()


def main() -> None:
    parser = argparse.ArgumentParser(description="Compare PyTorch and ONNX raw and decoded outputs")
    parser.add_argument("--weights", type=Path, required=True)
    parser.add_argument("--onnx", type=Path, required=True)
    parser.add_argument("--image", type=Path, required=True)
    parser.add_argument("--output", type=Path, default=Path("artifacts/detection/consistency.json"))
    parser.add_argument("--atol", type=float, default=1e-3)
    parser.add_argument("--rtol", type=float, default=1e-3)
    args = parser.parse_args()
    if not all(path.is_file() for path in (args.weights, args.onnx, args.image)):
        raise SystemExit("Weights, ONNX model and image must exist")
    try:
        torch = importlib.import_module("torch")
        yolo_class = importlib.import_module("ultralytics").YOLO
    except ImportError as error:
        raise SystemExit("PyTorch/Ultralytics is required for consistency checking") from error
    session = ort.InferenceSession(str(args.onnx), providers=["CPUExecutionProvider"])
    input_meta = session.get_inputs()[0]
    height = int(input_meta.shape[2]) if isinstance(input_meta.shape[2], int) else 640
    width = int(input_meta.shape[3]) if isinstance(input_meta.shape[3], int) else 640
    image = cv2.imread(str(args.image))
    tensor, info = preprocess_image(image, (height, width))
    batched = tensor[None, ...]
    pytorch_model = yolo_class(str(args.weights)).model.eval()
    with torch.no_grad():
        pytorch_output = _numpy(pytorch_model(torch.from_numpy(batched)))
    onnx_output = session.run(None, {input_meta.name: batched})[0]
    same_shape = pytorch_output.shape == onnx_output.shape
    close = same_shape and np.allclose(pytorch_output, onnx_output, atol=args.atol, rtol=args.rtol)
    names = list(yolo_class(str(args.weights)).names.values())
    pytorch_regions = postprocess_yolo(pytorch_output, info, names, 0.25, 0.7)
    onnx_regions = postprocess_yolo(onnx_output, info, names, 0.25, 0.7)
    report = {
        "same_shape": same_shape,
        "raw_outputs_close": bool(close),
        "max_absolute_difference": (
            float(np.max(np.abs(pytorch_output - onnx_output))) if same_shape else None
        ),
        "pytorch_detection_count": len(pytorch_regions),
        "onnx_detection_count": len(onnx_regions),
        "atol": args.atol,
        "rtol": args.rtol,
    }
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(report, indent=2), encoding="utf-8")
    print(args.output)
    if not close:
        raise SystemExit(2)


if __name__ == "__main__":
    main()

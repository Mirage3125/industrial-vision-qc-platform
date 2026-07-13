import argparse
import json
from pathlib import Path

import onnx
import onnxruntime as ort


def main() -> None:
    parser = argparse.ArgumentParser(
        description="Validate ONNX structure and list runtime providers"
    )
    parser.add_argument("--model", type=Path, required=True)
    args = parser.parse_args()
    model = onnx.load(args.model)
    onnx.checker.check_model(model, full_check=True)
    session = ort.InferenceSession(str(args.model), providers=["CPUExecutionProvider"])
    payload = {
        "valid": True,
        "ir_version": model.ir_version,
        "opset": [item.version for item in model.opset_import],
        "inputs": [{"name": item.name, "shape": item.shape} for item in session.get_inputs()],
        "outputs": [{"name": item.name, "shape": item.shape} for item in session.get_outputs()],
        "available_providers": ort.get_available_providers(),
    }
    print(json.dumps(payload, indent=2))


if __name__ == "__main__":
    main()

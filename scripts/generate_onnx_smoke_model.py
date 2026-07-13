import argparse
from pathlib import Path

import onnx
from onnx import TensorProto, helper


def main() -> None:
    parser = argparse.ArgumentParser(
        description="Generate a non-YOLO ONNX model for runtime smoke tests"
    )
    parser.add_argument("--output", type=Path, default=Path("artifacts/onnx/smoke-average.onnx"))
    args = parser.parse_args()
    input_info = helper.make_tensor_value_info("images", TensorProto.FLOAT, ["batch", 3, 64, 64])
    output_info = helper.make_tensor_value_info("features", TensorProto.FLOAT, ["batch", 3, 1, 1])
    node = helper.make_node("GlobalAveragePool", ["images"], ["features"])
    graph = helper.make_graph([node], "runtime-smoke-not-yolo", [input_info], [output_info])
    model = helper.make_model(graph, opset_imports=[helper.make_opsetid("", 17)])
    model.ir_version = 10
    onnx.checker.check_model(model, full_check=True)
    args.output.parent.mkdir(parents=True, exist_ok=True)
    onnx.save(model, args.output)
    print(args.output)


if __name__ == "__main__":
    main()

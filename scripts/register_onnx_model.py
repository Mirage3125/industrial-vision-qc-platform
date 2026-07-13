import argparse
import json
from pathlib import Path

import onnx

from backend.app.db.session import SessionLocal
from backend.app.schemas.domain import ModelVersionCreate
from backend.app.services import ModelService


def main() -> None:
    parser = argparse.ArgumentParser(
        description="Register and optionally activate a valid ONNX model"
    )
    parser.add_argument("--model", type=Path, required=True)
    parser.add_argument("--name", required=True)
    parser.add_argument("--version", required=True)
    parser.add_argument("--metrics", type=Path)
    parser.add_argument("--operator", default="cli-admin")
    parser.add_argument("--activate", action="store_true")
    args = parser.parse_args()
    graph = onnx.load(args.model)
    onnx.checker.check_model(graph, full_check=True)
    dimensions = graph.graph.input[0].type.tensor_type.shape.dim
    input_size = [dimension.dim_value for dimension in dimensions[-2:] if dimension.dim_value]
    metrics = json.loads(args.metrics.read_text(encoding="utf-8")) if args.metrics else {}
    with SessionLocal() as session:
        model = ModelService(session).register(
            ModelVersionCreate(
                model_name=args.name,
                model_type="detection",
                version=args.version,
                framework="onnxruntime",
                model_path=str(args.model.resolve()),
                metrics=metrics,
                input_size=input_size,
                precision="fp32",
            ),
            operator=args.operator,
        )
        model_id = model.id
    if args.activate:
        with SessionLocal() as session:
            ModelService(session).activate(model_id, args.operator)
    print(model_id)


if __name__ == "__main__":
    main()

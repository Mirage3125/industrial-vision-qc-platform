import argparse
import json
from pathlib import Path

from backend.app.db.session import SessionLocal
from backend.app.schemas.domain import ModelVersionCreate
from backend.app.services import ModelService


def main() -> None:
    parser = argparse.ArgumentParser(description="Register a trained detection model")
    parser.add_argument("--weights", type=Path, required=True)
    parser.add_argument("--metadata", type=Path, required=True)
    parser.add_argument("--name", required=True)
    parser.add_argument("--version", required=True)
    parser.add_argument("--framework", choices=["pytorch", "onnx"], default="pytorch")
    parser.add_argument("--operator", default="cli-admin")
    args = parser.parse_args()
    if not args.weights.is_file() or not args.metadata.is_file():
        raise SystemExit("Weights and observed metadata files must both exist")
    metadata = json.loads(args.metadata.read_text(encoding="utf-8"))
    metrics = metadata.get("metrics", {})
    training_config = metadata.get("training_config", {})
    with SessionLocal() as session:
        model = ModelService(session).register(
            ModelVersionCreate(
                model_name=args.name,
                model_type="detection",
                version=args.version,
                framework=args.framework,
                model_path=str(args.weights.resolve()),
                metrics=metrics,
                input_size=[int(training_config.get("imgsz", 640))] * 2,
                precision="fp16" if training_config.get("amp") else "fp32",
            ),
            operator=args.operator,
        )
    print(model.id)


if __name__ == "__main__":
    main()

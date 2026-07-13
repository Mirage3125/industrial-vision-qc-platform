from __future__ import annotations

from pathlib import Path

from sqlalchemy import select

from backend.app.db.session import SessionLocal
from backend.app.models.domain import ModelVersion

RUNTIME_MODELS = [
    {
        "model_name": "neu-det-yolo11n-onnx",
        "model_type": "detection",
        "version": "runtime-best-onnx",
        "framework": "onnxruntime",
        "model_path": "artifacts/training/neu_det_baseline/weights/best.onnx",
        "metrics": {},
        "input_size": [640, 640],
        "precision": "fp32",
    },
    {
        "model_name": "padim_statistical_metal_nut",
        "model_type": "anomaly_detection",
        "version": "runtime-mvtec-metal-nut",
        "framework": "opencv-numpy",
        "model_path": "artifacts/training/anomaly/padim_statistical_metal_nut/model.npz",
        "metrics": {},
        "input_size": [256, 256],
        "precision": "fp32",
    },
]


def register_runtime_models() -> None:
    with SessionLocal() as session:
        for item in RUNTIME_MODELS:
            if not Path(str(item["model_path"])).is_file():
                print(f"Skipping missing runtime model: {item['model_path']}")
                continue
            existing = session.scalar(
                select(ModelVersion).where(
                    ModelVersion.model_name == item["model_name"],
                    ModelVersion.version == item["version"],
                )
            )
            if existing is None:
                existing = ModelVersion(**item)
                session.add(existing)
                session.flush()
            for row in session.scalars(
                select(ModelVersion).where(ModelVersion.model_type == item["model_type"])
            ):
                row.active = row.id == existing.id
        session.commit()


if __name__ == "__main__":
    register_runtime_models()
    print("Runtime model records are ready.")

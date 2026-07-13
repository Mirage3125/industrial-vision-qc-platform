from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

sys.path.append(str(Path(__file__).resolve().parents[1]))

from backend.app.db.session import SessionLocal
from backend.app.models.domain import ModelVersion
from backend.app.repositories.core import AuditRepository, ModelVersionRepository


def main() -> None:
    parser = argparse.ArgumentParser(description="Register trained anomaly model")
    parser.add_argument("--model-name", default="padim_statistical_metal_nut")
    parser.add_argument("--version", default="v1")
    parser.add_argument("--model-path", type=Path, required=True)
    parser.add_argument("--metrics", type=Path, required=True)
    parser.add_argument("--active", action="store_true")
    args = parser.parse_args()
    metrics = json.loads(args.metrics.read_text(encoding="utf-8"))
    with SessionLocal() as session:
        repo = ModelVersionRepository(session)
        existing = repo.get_by_name_version(args.model_name, args.version)
        if args.active:
            repo.deactivate_type("anomaly_detection")
        model = existing or ModelVersion(
            model_name=args.model_name,
            model_type="anomaly_detection",
            version=args.version,
            framework="opencv-numpy",
            model_path=str(args.model_path),
            metrics=metrics,
            input_size=[256, 256],
            precision="fp32",
            active=args.active,
        )
        if existing is None:
            repo.add(model)
        else:
            existing.model_path = str(args.model_path)
            existing.metrics = metrics
            existing.active = args.active
        AuditRepository(session).record(
            "register_anomaly_model",
            "model_versions",
            model.id,
            "system",
            {"model_name": args.model_name, "version": args.version},
        )
        session.commit()
        print(json.dumps({"id": model.id, "model_name": model.model_name, "active": model.active}))


if __name__ == "__main__":
    main()

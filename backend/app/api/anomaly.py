from __future__ import annotations

import json
from pathlib import Path

from fastapi import APIRouter, Depends, Request
from sqlalchemy import select
from sqlalchemy.orm import Session

from backend.app.anomaly_detection.predictor import PaDiMStyleAnomalyDetector
from backend.app.core.errors import AppError
from backend.app.db.session import get_db
from backend.app.models.domain import ModelVersion
from backend.app.schemas.anomaly import AnomalyBatchRequest, AnomalyPredictRequest
from backend.app.schemas.common import success_response

router = APIRouter(prefix="/anomaly", tags=["anomaly"])
DB_SESSION = Depends(get_db)


def _load_detector(model_path: str) -> PaDiMStyleAnomalyDetector:
    path = Path(model_path)
    if not path.is_file():
        raise AppError("MODEL_NOT_READY", f"Anomaly model does not exist: {path}", 503)
    try:
        return PaDiMStyleAnomalyDetector(path)
    except Exception as error:
        raise AppError("MODEL_LOAD_FAILED", str(error), 503) from error


@router.post("/predict")
def predict(payload: AnomalyPredictRequest, request: Request) -> dict[str, object]:
    image_path = Path(payload.image_path)
    if not image_path.is_file():
        raise AppError("INVALID_IMAGE", f"Image does not exist: {image_path}", 400)
    if image_path.suffix.lower() not in {".jpg", ".jpeg", ".png", ".bmp", ".tif", ".tiff"}:
        raise AppError("INVALID_IMAGE", "Unsupported image format", 400)
    detector = _load_detector(payload.model_path)
    result = detector.predict_anomaly(image_path, Path(payload.output_dir), payload.include_map)
    return success_response({"result": result.model_dump(mode="json")}, request.state.request_id)


@router.post("/batch")
def batch(payload: AnomalyBatchRequest, request: Request) -> dict[str, object]:
    detector = _load_detector(payload.model_path)
    output_dir = Path(payload.output_dir)
    results = []
    for image_path_text in payload.image_paths:
        image_path = Path(image_path_text)
        if not image_path.is_file():
            raise AppError("INVALID_IMAGE", f"Image does not exist: {image_path}", 400)
        results.append(detector.predict_anomaly(image_path, output_dir).model_dump(mode="json"))
    return success_response({"count": len(results), "results": results}, request.state.request_id)


@router.get("/models")
def models(request: Request, db: Session = DB_SESSION) -> dict[str, object]:
    rows = db.scalars(
        select(ModelVersion).where(ModelVersion.model_type == "anomaly_detection")
    ).all()
    return success_response(
        {
            "models": [
                {
                    "id": row.id,
                    "model_name": row.model_name,
                    "version": row.version,
                    "framework": row.framework,
                    "model_path": row.model_path,
                    "metrics": row.metrics,
                    "active": row.active,
                }
                for row in rows
            ]
        },
        request.state.request_id,
    )


@router.get("/models/{model_id}/metrics")
def model_metrics(
    model_id: str, request: Request, db: Session = DB_SESSION
) -> dict[str, object]:
    row = db.get(ModelVersion, model_id)
    if row is None or row.model_type != "anomaly_detection":
        raise AppError("MODEL_NOT_FOUND", f"Anomaly model not found: {model_id}", 404)
    metrics_path = Path("artifacts/anomaly_evaluation") / row.model_name / "metrics.json"
    metrics = row.metrics
    if metrics_path.is_file():
        metrics = json.loads(metrics_path.read_text(encoding="utf-8"))
    return success_response({"model_id": model_id, "metrics": metrics}, request.state.request_id)

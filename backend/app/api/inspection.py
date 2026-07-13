from __future__ import annotations

import base64
import binascii
from datetime import UTC, datetime
from pathlib import Path

from fastapi import APIRouter, Depends, Request
from sqlalchemy import select
from sqlalchemy.orm import Session

from backend.app.core.errors import AppError
from backend.app.db.session import get_db
from backend.app.inspection.service import InspectionPredictionService
from backend.app.models.domain import Inspection
from backend.app.schemas.common import success_response
from backend.app.schemas.inspection import InspectionPredictRequest, InspectionUploadPredictRequest

router = APIRouter(prefix="/inspection", tags=["inspection"])
DB_SESSION = Depends(get_db)


@router.post("/predict")
def predict(
    payload: InspectionPredictRequest, request: Request, db: Session = DB_SESSION
) -> dict[str, object]:
    image_path = Path(payload.image_path)
    service = InspectionPredictionService(db)
    try:
        result = service.predict(
            image_path=image_path,
            inference_mode=payload.inference_mode,
            model_version=payload.model_version,
            station_id=payload.station_id,
            batch_id=payload.batch_id,
            idempotency_key=payload.idempotency_key,
            force_review=payload.force_review,
        )
        db.commit()
    except Exception:
        db.rollback()
        raise
    inspection = result["inspection"]
    review = result.get("review")
    return success_response(
        {
            "idempotent": result["idempotent"],
            "inspection_id": inspection.id,
            "review_id": None if review is None else review.id,
            "requires_review": bool(inspection.review_reasons),
            "review_reasons": inspection.review_reasons,
            "decision_rule_version": inspection.decision_rule_version,
            "final_status": inspection.final_status,
            "predicted_class": inspection.predicted_class,
            "confidence": inspection.confidence,
            "anomaly_score": inspection.anomaly_score,
            "step_timings": inspection.step_timings,
            "model_versions": inspection.model_versions,
        },
        request.state.request_id,
    )


@router.post("/upload-predict")
def upload_predict(
    payload: InspectionUploadPredictRequest, request: Request, db: Session = DB_SESSION
) -> dict[str, object]:
    suffix = Path(payload.filename).suffix.lower()
    if suffix not in {".jpg", ".jpeg", ".png", ".bmp", ".tif", ".tiff"}:
        raise AppError("INVALID_IMAGE", "Unsupported image format", 400)
    try:
        binary = base64.b64decode(payload.content_base64, validate=True)
    except (binascii.Error, ValueError) as error:
        raise AppError("INVALID_IMAGE", "Invalid base64 image payload", 400) from error
    if len(binary) > 10 * 1024 * 1024:
        raise AppError("INVALID_IMAGE", "Image exceeds 10MB limit", 400)
    upload_dir = Path("artifacts/uploads") / datetime.now(UTC).strftime("%Y%m%d")
    upload_dir.mkdir(parents=True, exist_ok=True)
    safe_name = f"{datetime.now(UTC).strftime('%H%M%S%f')}{suffix}"
    image_path = upload_dir / safe_name
    image_path.write_bytes(binary)
    service = InspectionPredictionService(db)
    try:
        result = service.predict(
            image_path=image_path,
            inference_mode=payload.inference_mode,
            model_version=payload.model_version,
            station_id=payload.station_id,
            batch_id=payload.batch_id,
            idempotency_key=payload.idempotency_key,
            force_review=payload.force_review,
        )
        db.commit()
    except Exception:
        db.rollback()
        raise
    inspection = result["inspection"]
    review = result.get("review")
    return success_response(
        {
            "idempotent": result["idempotent"],
            "inspection_id": inspection.id,
            "review_id": None if review is None else review.id,
            "image_path": inspection.image_path,
            "requires_review": bool(inspection.review_reasons),
            "review_reasons": inspection.review_reasons,
            "decision_rule_version": inspection.decision_rule_version,
            "final_status": inspection.final_status,
            "predicted_class": inspection.predicted_class,
            "confidence": inspection.confidence,
            "anomaly_score": inspection.anomaly_score,
            "quality_result": inspection.quality_result,
            "yolo_result": inspection.yolo_result,
            "anomaly_result": inspection.anomaly_result,
            "step_timings": inspection.step_timings,
            "model_versions": inspection.model_versions,
        },
        request.state.request_id,
    )


@router.get("/records")
def records(request: Request, db: Session = DB_SESSION) -> dict[str, object]:
    rows = db.scalars(select(Inspection).order_by(Inspection.created_at.desc()).limit(200)).all()
    return success_response(
        {
            "records": [
                {
                    "id": row.id,
                    "image_path": row.image_path,
                    "final_status": row.final_status,
                    "predicted_class": row.predicted_class,
                    "confidence": row.confidence,
                    "anomaly_score": row.anomaly_score,
                    "review_reasons": row.review_reasons,
                    "station_id": row.station_id,
                    "batch_id": row.batch_id,
                    "processing_time_ms": row.processing_time_ms,
                    "created_at": row.created_at.isoformat(),
                }
                for row in rows
            ]
        },
        request.state.request_id,
    )

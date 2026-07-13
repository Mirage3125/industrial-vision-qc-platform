from __future__ import annotations

from pathlib import Path

from fastapi import APIRouter, Depends, Request
from sqlalchemy import select
from sqlalchemy.orm import Session

from backend.app.anomaly_detection.predictor import PaDiMStyleAnomalyDetector
from backend.app.core.errors import AppError
from backend.app.db.base import utc_now
from backend.app.db.session import get_db
from backend.app.inference.onnx_runtime import OnnxYoloDetector
from backend.app.models.domain import AuditLog, ModelVersion
from backend.app.schemas.common import success_response
from backend.app.schemas.inspection import ModelActivateRequest

router = APIRouter(prefix="/models", tags=["models"])
DB_SESSION = Depends(get_db)


@router.get("")
def list_models(request: Request, db: Session = DB_SESSION) -> dict[str, object]:
    rows = db.scalars(select(ModelVersion).order_by(ModelVersion.created_at.desc())).all()
    return success_response(
        {
            "models": [
                {
                    "id": row.id,
                    "model_name": row.model_name,
                    "model_type": row.model_type,
                    "version": row.version,
                    "framework": row.framework,
                    "model_path": row.model_path,
                    "active": row.active,
                    "metrics": row.metrics,
                }
                for row in rows
            ]
        },
        request.state.request_id,
    )


def _health_check(model: ModelVersion) -> None:
    path = Path(model.model_path)
    if not path.is_file():
        raise AppError("MODEL_FILE_MISSING", f"Model file does not exist: {path}", 400)
    if model.model_type == "anomaly_detection":
        PaDiMStyleAnomalyDetector(path)
    elif model.model_type == "detection" and model.framework == "onnxruntime":
        OnnxYoloDetector(
            path,
            ["crazing", "inclusion", "patches", "pitted_surface", "rolled_in_scale", "scratches"],
            provider="cpu",
        )


@router.post("/{model_id}/activate")
def activate_model(
    model_id: str, payload: ModelActivateRequest, request: Request, db: Session = DB_SESSION
) -> dict[str, object]:
    model = db.get(ModelVersion, model_id)
    if model is None:
        raise AppError("MODEL_NOT_FOUND", "Model not found", 404)
    _health_check(model)
    for row in db.scalars(select(ModelVersion).where(ModelVersion.model_type == model.model_type)):
        row.active = False
    model.active = True
    db.add(
        AuditLog(
            action="model.activated",
            entity_type="model_version",
            entity_id=model.id,
            operator=payload.operator,
            details={"version": model.version},
            created_at=utc_now(),
        )
    )
    db.commit()
    return success_response({"id": model.id, "active": model.active}, request.state.request_id)


@router.post("/{model_id}/rollback")
def rollback_model(
    model_id: str, payload: ModelActivateRequest, request: Request, db: Session = DB_SESSION
) -> dict[str, object]:
    return activate_model(model_id, payload, request, db)

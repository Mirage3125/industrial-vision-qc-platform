from pathlib import Path

from fastapi import APIRouter, Request

from backend.app.core.errors import AppError
from backend.app.detection import YoloPyTorchDetector
from backend.app.schemas.common import success_response
from backend.app.schemas.detection import YoloBatchRequest, YoloPredictRequest

router = APIRouter(prefix="/detection", tags=["detection"])


def _detector(weights: str, confidence: float, iou: float, device: str) -> YoloPyTorchDetector:
    path = Path(weights)
    if not path.is_file():
        raise AppError("MODEL_NOT_READY", f"YOLO weights do not exist: {path}", 503)
    return YoloPyTorchDetector(path, confidence=confidence, iou=iou, device=device)


@router.post("/predict")
def predict(payload: YoloPredictRequest, request: Request) -> dict[str, object]:
    try:
        result = _detector(
            payload.weights_path, payload.confidence, payload.iou, payload.device
        ).predict(Path(payload.image_path), Path(payload.output_dir))
    except RuntimeError as error:
        raise AppError("MODEL_NOT_READY", str(error), 503) from error
    return success_response({"result": result.model_dump(mode="json")}, request.state.request_id)


@router.post("/batch")
def predict_batch(payload: YoloBatchRequest, request: Request) -> dict[str, object]:
    try:
        results = _detector(
            payload.weights_path, payload.confidence, payload.iou, payload.device
        ).predict_batch(
            [Path(image_path) for image_path in payload.image_paths], Path(payload.output_dir)
        )
    except RuntimeError as error:
        raise AppError("MODEL_NOT_READY", str(error), 503) from error
    return success_response(
        {"count": len(results), "results": [result.model_dump(mode="json") for result in results]},
        request.state.request_id,
    )

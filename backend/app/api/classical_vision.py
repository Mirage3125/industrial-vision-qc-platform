from pathlib import Path

from fastapi import APIRouter, Request

from backend.app.classical_vision import ClassicalVisionDetector, load_classical_config
from backend.app.schemas.classical_vision import ClassicalBatchRequest, ClassicalPredictRequest
from backend.app.schemas.common import success_response

router = APIRouter(prefix="/classical-vision", tags=["classical-vision"])


@router.post("/predict")
def predict(payload: ClassicalPredictRequest, request: Request) -> dict[str, object]:
    """Run the configured OpenCV baseline for one server-local image."""

    detector = ClassicalVisionDetector(load_classical_config(Path(payload.config_path)))
    result = detector.predict(Path(payload.image_path), Path(payload.output_dir))
    return success_response({"result": result.model_dump(mode="json")}, request.state.request_id)


@router.post("/batch")
def predict_batch(payload: ClassicalBatchRequest, request: Request) -> dict[str, object]:
    """Run deterministic sequential inference for a bounded image list."""

    detector = ClassicalVisionDetector(load_classical_config(Path(payload.config_path)))
    results = detector.predict_batch(
        [Path(image_path) for image_path in payload.image_paths], Path(payload.output_dir)
    )
    data = {
        "count": len(results),
        "results": [result.model_dump(mode="json") for result in results],
    }
    return success_response(data, request.state.request_id)

from backend.app.inference.base import BoundingBox, DefectRegion, Detector, InferenceResult

try:
    from backend.app.inference.onnx_runtime import (
        OnnxYoloDetector,
        TensorRTDetector,
        available_providers,
    )
except ImportError:
    OnnxYoloDetector = None  # type: ignore[misc, assignment]
    TensorRTDetector = None  # type: ignore[misc, assignment]

    def available_providers() -> list[str]:
        return []

__all__ = [
    "BoundingBox",
    "DefectRegion",
    "Detector",
    "InferenceResult",
    "OnnxYoloDetector",
    "TensorRTDetector",
    "available_providers",
]

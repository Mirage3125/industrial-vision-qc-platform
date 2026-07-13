from __future__ import annotations

from abc import ABC, abstractmethod
from pathlib import Path
from typing import Any

from pydantic import BaseModel, Field


class BoundingBox(BaseModel):
    x1: int
    y1: int
    x2: int
    y2: int


class DefectRegion(BaseModel):
    region_id: int
    bounding_box: BoundingBox
    area: float = Field(ge=0)
    aspect_ratio: float = Field(ge=0)
    circularity: float = Field(ge=0)
    centroid: tuple[float, float]
    source: str
    class_id: int | None = None
    class_name: str | None = None
    confidence: float | None = Field(default=None, ge=0, le=1)
    anomaly_score: float | None = Field(default=None, ge=0)


class InferenceResult(BaseModel):
    detector_type: str
    image_path: str
    image_width: int
    image_height: int
    defect_count: int
    regions: list[DefectRegion]
    processing_time_ms: float = Field(ge=0)
    artifacts: dict[str, str] = Field(default_factory=dict)
    metadata: dict[str, Any] = Field(default_factory=dict)


class Detector(ABC):
    """Common inference contract for OpenCV, YOLO and anomaly detectors."""

    @abstractmethod
    def predict(self, image_path: Path, output_dir: Path | None = None) -> InferenceResult:
        """Run inference for one image and return a normalized result."""

    def predict_batch(
        self, image_paths: list[Path], output_dir: Path | None = None
    ) -> list[InferenceResult]:
        """Default deterministic batch implementation; providers may optimize it."""

        return [self.predict(path, output_dir) for path in image_paths]

from __future__ import annotations

import importlib
import time
from pathlib import Path
from typing import Any

from backend.app.inference import BoundingBox, DefectRegion, Detector, InferenceResult


class YoloPyTorchDetector(Detector):
    """Ultralytics PyTorch adapter implementing the shared Detector contract."""

    def __init__(
        self,
        weights: Path,
        confidence: float = 0.25,
        iou: float = 0.7,
        device: str = "0",
        model: Any | None = None,
    ) -> None:
        self.weights = weights
        self.confidence = confidence
        self.iou = iou
        self.device = device
        self._model = model

    def _get_model(self) -> Any:
        if self._model is None:
            if not self.weights.is_file():
                raise RuntimeError(f"YOLO weights do not exist: {self.weights}")
            try:
                yolo_class = importlib.import_module("ultralytics").YOLO
            except ImportError as error:
                raise RuntimeError(
                    "Ultralytics/PyTorch is not installed in the active environment"
                ) from error
            self._model = yolo_class(str(self.weights))
        return self._model

    def predict(self, image_path: Path, output_dir: Path | None = None) -> InferenceResult:
        started = time.perf_counter()
        model = self._get_model()
        raw_result = model.predict(
            source=str(image_path),
            conf=self.confidence,
            iou=self.iou,
            device=self.device,
            verbose=False,
        )[0]
        regions: list[DefectRegion] = []
        names = raw_result.names
        for index, box in enumerate(raw_result.boxes):
            x1, y1, x2, y2 = (float(value) for value in box.xyxy[0].tolist())
            class_id = int(box.cls[0].item())
            confidence = float(box.conf[0].item())
            width, height = x2 - x1, y2 - y1
            regions.append(
                DefectRegion(
                    region_id=index + 1,
                    bounding_box=BoundingBox(
                        x1=round(x1), y1=round(y1), x2=round(x2), y2=round(y2)
                    ),
                    area=round(width * height, 3),
                    aspect_ratio=round(width / height, 4) if height else 0,
                    circularity=0,
                    centroid=(round((x1 + x2) / 2, 2), round((y1 + y2) / 2, 2)),
                    source="yolo_pytorch",
                    class_id=class_id,
                    class_name=str(names[class_id]),
                    confidence=confidence,
                )
            )
        shape = raw_result.orig_shape
        result = InferenceResult(
            detector_type="yolo_pytorch",
            image_path=str(image_path.resolve()),
            image_width=int(shape[1]),
            image_height=int(shape[0]),
            defect_count=len(regions),
            regions=regions,
            processing_time_ms=round((time.perf_counter() - started) * 1000, 3),
            metadata={"weights": str(self.weights), "device": self.device},
        )
        if output_dir is not None:
            output_dir.mkdir(parents=True, exist_ok=True)
            image_output = output_dir / f"{image_path.stem}-yolo.jpg"
            json_output = output_dir / f"{image_path.stem}-yolo.json"
            plotted = raw_result.plot()
            import cv2

            cv2.imwrite(str(image_output), plotted)
            result.artifacts = {
                "visualization": str(image_output.resolve()),
                "json_result": str(json_output.resolve()),
            }
            json_output.write_text(result.model_dump_json(indent=2), encoding="utf-8")
        return result

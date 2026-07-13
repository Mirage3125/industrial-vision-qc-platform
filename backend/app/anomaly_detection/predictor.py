from __future__ import annotations

import time
from pathlib import Path
from typing import Any

import cv2
import numpy as np

from backend.app.anomaly_detection.trainer import _features
from backend.app.anomaly_detection.types import AnomalyPrediction
from backend.app.anomaly_detection.visualization import write_visualizations
from backend.app.inference.base import BoundingBox, DefectRegion, Detector, InferenceResult


class PaDiMStyleAnomalyDetector(Detector):
    def __init__(self, model_path: Path, runtime_provider: str = "opencv-numpy") -> None:
        if not model_path.is_file():
            raise FileNotFoundError(f"Anomaly model does not exist: {model_path}")
        data = np.load(model_path, allow_pickle=False)
        self.model_path = model_path
        self.mean = data["mean"].astype(np.float32)
        self.std = data["std"].astype(np.float32)
        self.threshold = float(data["threshold"])
        self.mask_threshold = float(data["mask_threshold"])
        self.image_size = int(data["image_size"])
        self.algorithm = str(data["algorithm"])
        self.category = str(data["category"])
        self.runtime_provider = runtime_provider
        self.model_version = f"{self.algorithm}-{self.category}"

    def predict_anomaly(
        self, image_path: Path, output_dir: Path | None = None, include_map: bool = False
    ) -> AnomalyPrediction:
        started = time.perf_counter()
        features = _features(image_path, self.image_size)
        anomaly_map = np.sqrt((((features - self.mean) / self.std) ** 2).mean(axis=-1))
        anomaly_map = cv2.GaussianBlur(anomaly_map, (9, 9), 0)
        score = float(anomaly_map.max())
        mask = anomaly_map > self.mask_threshold
        heatmap_path = overlay_path = predicted_mask_path = None
        if output_dir is not None:
            heatmap_path, overlay_path, predicted_mask_path = [
                str(path)
                for path in write_visualizations(image_path, anomaly_map, mask, output_dir)
            ]
        elapsed_ms = (time.perf_counter() - started) * 1000
        return AnomalyPrediction(
            image_path=str(image_path),
            is_anomaly=score >= self.threshold,
            anomaly_score=score,
            threshold=self.threshold,
            anomaly_map=anomaly_map.tolist() if include_map else None,
            heatmap_path=heatmap_path,
            overlay_path=overlay_path,
            predicted_mask_path=predicted_mask_path,
            processing_time_ms=elapsed_ms,
            model_version=self.model_version,
            runtime_provider=self.runtime_provider,
            metadata={
                "model_path": str(self.model_path),
                "algorithm": self.algorithm,
                "category": self.category,
                "mask_threshold": self.mask_threshold,
            },
        )

    def predict(self, image_path: Path, output_dir: Path | None = None) -> InferenceResult:
        prediction = self.predict_anomaly(image_path, output_dir)
        image = cv2.imread(str(image_path), cv2.IMREAD_COLOR)
        if image is None:
            raise ValueError(f"Failed to read image: {image_path}")
        height, width = image.shape[:2]
        regions: list[DefectRegion] = []
        if prediction.predicted_mask_path:
            mask = cv2.imread(prediction.predicted_mask_path, cv2.IMREAD_GRAYSCALE)
            if mask is not None:
                contours, _ = cv2.findContours(mask, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)
                for index, contour in enumerate(contours, start=1):
                    area = float(cv2.contourArea(contour))
                    if area < 16:
                        continue
                    x, y, w, h = cv2.boundingRect(contour)
                    regions.append(
                        DefectRegion(
                            region_id=index,
                            bounding_box=BoundingBox(x1=x, y1=y, x2=x + w, y2=y + h),
                            area=area,
                            aspect_ratio=float(w / max(h, 1)),
                            circularity=0.0,
                            centroid=(float(x + w / 2), float(y + h / 2)),
                            source="anomaly_detection",
                            anomaly_score=prediction.anomaly_score,
                        )
                    )
        artifacts = {
            key: value
            for key, value in {
                "heatmap": prediction.heatmap_path,
                "overlay": prediction.overlay_path,
                "predicted_mask": prediction.predicted_mask_path,
            }.items()
            if value is not None
        }
        return InferenceResult(
            detector_type="anomaly_detection",
            image_path=str(image_path),
            image_width=width,
            image_height=height,
            defect_count=len(regions),
            regions=regions,
            processing_time_ms=prediction.processing_time_ms,
            artifacts=artifacts,
            metadata=prediction.model_dump(mode="json"),
        )

    def metadata(self) -> dict[str, Any]:
        return {
            "model_path": str(self.model_path),
            "model_version": self.model_version,
            "algorithm": self.algorithm,
            "category": self.category,
            "threshold": self.threshold,
            "runtime_provider": self.runtime_provider,
        }

import math
import time
from pathlib import Path
from typing import Any

import cv2
import numpy as np

from backend.app.classical_vision.config import ClassicalVisionConfig
from backend.app.inference import BoundingBox, DefectRegion, Detector, InferenceResult

ImageArray = np.ndarray[Any, Any]


class ClassicalVisionDetector(Detector):
    """Configurable deterministic baseline for high-contrast geometric defects."""

    def __init__(self, config: ClassicalVisionConfig) -> None:
        self.config = config

    def predict(self, image_path: Path, output_dir: Path | None = None) -> InferenceResult:
        started = time.perf_counter()
        image = self._read_image(image_path)
        if image is None:
            raise ValueError(f"Unable to decode image: {image_path}")
        binary = self.segment(image)
        regions = self.extract_regions(binary)
        processing_time_ms = (time.perf_counter() - started) * 1000
        result = InferenceResult(
            detector_type="opencv_classical",
            image_path=str(image_path.resolve()),
            image_width=image.shape[1],
            image_height=image.shape[0],
            defect_count=len(regions),
            regions=regions,
            processing_time_ms=round(processing_time_ms, 3),
            metadata={
                "segmentation_method": self.config.segmentation_method,
                "analysis_method": self.config.analysis_method,
            },
        )
        if output_dir is not None:
            result.artifacts = self.save_artifacts(image, binary, result, output_dir)
        return result

    def segment(self, image: ImageArray) -> ImageArray:
        """Apply configured grayscale, denoising, enhancement and segmentation."""

        gray = cv2.cvtColor(image, cv2.COLOR_BGR2GRAY) if image.ndim == 3 else image.copy()
        if self.config.blur_method == "gaussian":
            gaussian_size = self.config.gaussian_kernel_size
            gray = cv2.GaussianBlur(
                gray, (gaussian_size, gaussian_size), self.config.gaussian_sigma
            )
        elif self.config.blur_method == "median":
            gray = cv2.medianBlur(gray, self.config.median_kernel_size)
        if self.config.clahe_enabled:
            clahe = cv2.createCLAHE(
                clipLimit=self.config.clahe_clip_limit,
                tileGridSize=(self.config.clahe_tile_grid_size,) * 2,
            )
            gray = clahe.apply(gray)

        method = self.config.segmentation_method
        if method == "otsu":
            threshold_type = (
                cv2.THRESH_BINARY_INV if self.config.invert_binary else cv2.THRESH_BINARY
            )
            _, binary = cv2.threshold(gray, 0, 255, threshold_type | cv2.THRESH_OTSU)
        elif method == "adaptive":
            threshold_type = (
                cv2.THRESH_BINARY_INV if self.config.invert_binary else cv2.THRESH_BINARY
            )
            binary = cv2.adaptiveThreshold(
                gray,
                255,
                cv2.ADAPTIVE_THRESH_GAUSSIAN_C,
                threshold_type,
                self.config.adaptive_block_size,
                self.config.adaptive_c,
            )
        else:
            binary = cv2.Canny(
                gray, self.config.canny_low_threshold, self.config.canny_high_threshold
            )

        if self.config.opening_enabled:
            morphology_kernel = cv2.getStructuringElement(
                cv2.MORPH_ELLIPSE,
                (self.config.opening_kernel_size,) * 2,
            )
            binary = cv2.morphologyEx(
                binary,
                cv2.MORPH_OPEN,
                morphology_kernel,
                iterations=self.config.opening_iterations,
            )
        if self.config.closing_enabled:
            morphology_kernel = cv2.getStructuringElement(
                cv2.MORPH_ELLIPSE,
                (self.config.closing_kernel_size,) * 2,
            )
            binary = cv2.morphologyEx(
                binary,
                cv2.MORPH_CLOSE,
                morphology_kernel,
                iterations=self.config.closing_iterations,
            )
        return binary

    def extract_regions(self, binary: ImageArray) -> list[DefectRegion]:
        if self.config.analysis_method == "connected_components":
            return self._connected_component_regions(binary)
        return self._contour_regions(binary)

    def _contour_regions(self, binary: ImageArray) -> list[DefectRegion]:
        contours, _ = cv2.findContours(binary, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)
        regions: list[DefectRegion] = []
        for contour in contours:
            area = float(cv2.contourArea(contour))
            x, y, width, height = cv2.boundingRect(contour)
            perimeter = float(cv2.arcLength(contour, True))
            circularity = 4 * math.pi * area / (perimeter**2) if perimeter > 0 else 0.0
            moments = cv2.moments(contour)
            centroid = (
                (moments["m10"] / moments["m00"], moments["m01"] / moments["m00"])
                if moments["m00"]
                else (x + width / 2, y + height / 2)
            )
            region = self._build_region(
                len(regions) + 1,
                x,
                y,
                width,
                height,
                area,
                circularity,
                centroid,
                "contour",
            )
            if region is not None:
                regions.append(region)
        return sorted(regions, key=lambda region: region.area, reverse=True)

    def _connected_component_regions(self, binary: ImageArray) -> list[DefectRegion]:
        count, labels, stats, centroids = cv2.connectedComponentsWithStats(binary, connectivity=8)
        regions: list[DefectRegion] = []
        for label in range(1, count):
            x, y, width, height, area = (int(value) for value in stats[label])
            component_mask: ImageArray = (labels == label).astype(np.uint8) * 255
            contours, _ = cv2.findContours(
                component_mask, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE
            )
            perimeter = sum(cv2.arcLength(contour, True) for contour in contours)
            circularity = 4 * math.pi * area / (perimeter**2) if perimeter > 0 else 0.0
            region = self._build_region(
                len(regions) + 1,
                x,
                y,
                width,
                height,
                float(area),
                float(circularity),
                (float(centroids[label][0]), float(centroids[label][1])),
                "connected_component",
            )
            if region is not None:
                regions.append(region)
        return sorted(regions, key=lambda region: region.area, reverse=True)

    def _build_region(
        self,
        region_id: int,
        x: int,
        y: int,
        width: int,
        height: int,
        area: float,
        circularity: float,
        centroid: tuple[float, float],
        source: str,
    ) -> DefectRegion | None:
        aspect_ratio = width / height if height else 0.0
        if not self.config.min_area <= area <= self.config.max_area:
            return None
        if not self.config.min_aspect_ratio <= aspect_ratio <= self.config.max_aspect_ratio:
            return None
        if not self.config.min_circularity <= circularity <= self.config.max_circularity:
            return None
        return DefectRegion(
            region_id=region_id,
            bounding_box=BoundingBox(x1=x, y1=y, x2=x + width, y2=y + height),
            area=round(area, 3),
            aspect_ratio=round(aspect_ratio, 4),
            circularity=round(circularity, 4),
            centroid=(round(centroid[0], 2), round(centroid[1], 2)),
            source=source,
        )

    def save_artifacts(
        self,
        image: ImageArray,
        binary: ImageArray,
        result: InferenceResult,
        output_dir: Path,
    ) -> dict[str, str]:
        output_dir.mkdir(parents=True, exist_ok=True)
        stem = Path(result.image_path).stem
        binary_path = output_dir / f"{stem}-binary.png"
        contour_path = output_dir / f"{stem}-contours.jpg"
        result_path = output_dir / f"{stem}-result.json"
        visualized = image.copy()
        for region in result.regions:
            box = region.bounding_box
            cv2.rectangle(visualized, (box.x1, box.y1), (box.x2, box.y2), (0, 0, 255), 2)
            cv2.putText(
                visualized,
                f"#{region.region_id} A={region.area:.0f}",
                (box.x1, max(12, box.y1 - 4)),
                cv2.FONT_HERSHEY_SIMPLEX,
                0.4,
                (0, 0, 255),
                1,
            )
        self._write_image(binary_path, binary)
        self._write_image(contour_path, visualized)
        artifacts = {
            "binary_image": str(binary_path.resolve()),
            "contour_image": str(contour_path.resolve()),
            "json_result": str(result_path.resolve()),
        }
        result.artifacts = artifacts
        result_path.write_text(result.model_dump_json(indent=2), encoding="utf-8")
        return artifacts

    @staticmethod
    def _read_image(path: Path) -> ImageArray | None:
        try:
            return cv2.imdecode(np.fromfile(path, dtype=np.uint8), cv2.IMREAD_COLOR)
        except (OSError, cv2.error):
            return None

    @staticmethod
    def _write_image(path: Path, image: ImageArray) -> None:
        success, encoded = cv2.imencode(path.suffix, image)
        if not success:
            raise ValueError(f"Unable to encode artifact: {path}")
        encoded.tofile(path)

from __future__ import annotations

import time
from pathlib import Path
from typing import Any, cast

import cv2
import numpy as np
import onnxruntime as ort

from backend.app.inference.base import Detector, InferenceResult
from backend.app.inference.yolo_postprocess import LetterboxInfo, postprocess_yolo, preprocess_image

Array = np.ndarray[Any, Any]


def available_providers() -> list[str]:
    return cast(list[str], ort.get_available_providers())


class OnnxYoloDetector(Detector):
    PROVIDERS = {
        "cpu": ["CPUExecutionProvider"],
        "cuda": ["CUDAExecutionProvider", "CPUExecutionProvider"],
    }

    def __init__(
        self,
        model_path: Path,
        class_names: list[str],
        provider: str = "cpu",
        confidence: float = 0.25,
        iou: float = 0.7,
    ) -> None:
        if provider not in self.PROVIDERS:
            raise ValueError(f"Unsupported provider: {provider}")
        if not model_path.is_file():
            raise ValueError(f"ONNX model does not exist: {model_path}")
        requested = self.PROVIDERS[provider]
        if requested[0] not in available_providers():
            raise RuntimeError(f"Provider is unavailable: {requested[0]}")
        started = time.perf_counter()
        self.session = ort.InferenceSession(str(model_path), providers=requested)
        self.session_initialization_ms = (time.perf_counter() - started) * 1000
        if self.session.get_providers()[0] != requested[0]:
            raise RuntimeError(f"Provider fallback detected: {self.session.get_providers()}")
        self.model_path, self.class_names = model_path, class_names
        self.provider, self.confidence, self.iou = provider, confidence, iou
        self.input = self.session.get_inputs()[0]
        shape = self.input.shape
        self.input_size = (
            int(shape[2]) if isinstance(shape[2], int) else 640,
            int(shape[3]) if isinstance(shape[3], int) else 640,
        )

    def predict(self, image_path: Path, output_dir: Path | None = None) -> InferenceResult:
        image = cv2.imread(str(image_path))
        if image is None:
            raise ValueError(f"Unable to decode image: {image_path}")
        tensor, info = preprocess_image(image, self.input_size)
        started = time.perf_counter()
        output = self.session.run(None, {self.input.name: tensor[None, ...]})[0]
        latency = (time.perf_counter() - started) * 1000
        regions = postprocess_yolo(output, info, self.class_names, self.confidence, self.iou)
        result = InferenceResult(
            detector_type=f"yolo_onnx_{self.provider}",
            image_path=str(image_path.resolve()),
            image_width=image.shape[1],
            image_height=image.shape[0],
            defect_count=len(regions),
            regions=regions,
            processing_time_ms=round(latency, 3),
            metadata={
                "provider": self.session.get_providers()[0],
                "model_path": str(self.model_path.resolve()),
                "session_initialization_ms": round(self.session_initialization_ms, 3),
            },
        )
        if output_dir is not None:
            self._save_artifacts(image, result, output_dir)
        return result

    def predict_batch(
        self, image_paths: list[Path], output_dir: Path | None = None
    ) -> list[InferenceResult]:
        images: list[Array] = []
        tensors: list[Array] = []
        infos: list[LetterboxInfo] = []
        for path in image_paths:
            image = cv2.imread(str(path))
            if image is None:
                raise ValueError(f"Unable to decode image: {path}")
            tensor, info = preprocess_image(image, self.input_size)
            images.append(image)
            tensors.append(tensor)
            infos.append(info)
        started = time.perf_counter()
        outputs = self.session.run(None, {self.input.name: np.stack(tensors)})[0]
        total_ms = (time.perf_counter() - started) * 1000
        results: list[InferenceResult] = []
        for index, (path, image, info) in enumerate(zip(image_paths, images, infos, strict=True)):
            regions = postprocess_yolo(
                outputs[index : index + 1], info, self.class_names, self.confidence, self.iou
            )
            result = InferenceResult(
                detector_type=f"yolo_onnx_{self.provider}",
                image_path=str(path.resolve()),
                image_width=image.shape[1],
                image_height=image.shape[0],
                defect_count=len(regions),
                regions=regions,
                processing_time_ms=round(total_ms / len(image_paths), 3),
                metadata={"batch_size": len(image_paths), "batch_total_ms": round(total_ms, 3)},
            )
            if output_dir is not None:
                self._save_artifacts(image, result, output_dir)
            results.append(result)
        return results

    @staticmethod
    def _save_artifacts(image: Array, result: InferenceResult, output_dir: Path) -> None:
        output_dir.mkdir(parents=True, exist_ok=True)
        visualization = image.copy()
        for region in result.regions:
            box = region.bounding_box
            cv2.rectangle(visualization, (box.x1, box.y1), (box.x2, box.y2), (0, 0, 255), 2)
        stem = Path(result.image_path).stem
        image_path, json_path = output_dir / f"{stem}-onnx.jpg", output_dir / f"{stem}-onnx.json"
        cv2.imwrite(str(image_path), visualization)
        result.artifacts = {
            "visualization": str(image_path.resolve()),
            "json_result": str(json_path.resolve()),
        }
        json_path.write_text(result.model_dump_json(indent=2), encoding="utf-8")


class TensorRTDetector(Detector):
    def predict(self, image_path: Path, output_dir: Path | None = None) -> InferenceResult:
        raise RuntimeError("TensorRT is optional and has not been validated in this environment")

from dataclasses import dataclass
from typing import Any

import cv2
import numpy as np

from backend.app.inference.base import BoundingBox, DefectRegion

Array = np.ndarray[Any, Any]


@dataclass(frozen=True)
class LetterboxInfo:
    ratio: float
    pad_x: float
    pad_y: float
    original_width: int
    original_height: int


def preprocess_image(image: Array, input_size: tuple[int, int]) -> tuple[Array, LetterboxInfo]:
    target_height, target_width = input_size
    height, width = image.shape[:2]
    ratio = min(target_width / width, target_height / height)
    resized_width, resized_height = round(width * ratio), round(height * ratio)
    resized = cv2.resize(image, (resized_width, resized_height), interpolation=cv2.INTER_LINEAR)
    pad_x, pad_y = (target_width - resized_width) / 2, (target_height - resized_height) / 2
    left, top = round(pad_x - 0.1), round(pad_y - 0.1)
    right, bottom = round(pad_x + 0.1), round(pad_y + 0.1)
    padded = cv2.copyMakeBorder(
        resized, top, bottom, left, right, cv2.BORDER_CONSTANT, value=(114, 114, 114)
    )
    rgb = cv2.cvtColor(padded, cv2.COLOR_BGR2RGB)
    tensor = np.ascontiguousarray(rgb.transpose(2, 0, 1), dtype=np.float32) / 255.0
    return tensor, LetterboxInfo(ratio, pad_x, pad_y, width, height)


def postprocess_yolo(
    output: Array,
    letterbox: LetterboxInfo,
    class_names: list[str],
    confidence_threshold: float,
    iou_threshold: float,
) -> list[DefectRegion]:
    """Decode direct Nx6 or raw Ultralytics output and apply shared NMS."""

    predictions = np.asarray(output).squeeze(0)
    if predictions.ndim != 2:
        raise ValueError(f"Unsupported YOLO output shape: {output.shape}")
    if predictions.shape[1] == 6:
        boxes_xyxy = predictions[:, :4]
        confidences = predictions[:, 4]
        class_ids = predictions[:, 5].astype(int)
    else:
        if predictions.shape[0] < predictions.shape[1]:
            predictions = predictions.T
        if predictions.shape[1] < 5:
            raise ValueError(f"Unsupported YOLO output shape: {output.shape}")
        class_scores = predictions[:, 4:]
        class_ids = np.argmax(class_scores, axis=1)
        confidences = class_scores[np.arange(len(predictions)), class_ids]
        xywh = predictions[:, :4]
        boxes_xyxy = np.column_stack(
            (
                xywh[:, 0] - xywh[:, 2] / 2,
                xywh[:, 1] - xywh[:, 3] / 2,
                xywh[:, 0] + xywh[:, 2] / 2,
                xywh[:, 1] + xywh[:, 3] / 2,
            )
        )
    keep = confidences >= confidence_threshold
    boxes_xyxy, confidences, class_ids = boxes_xyxy[keep], confidences[keep], class_ids[keep]
    if not len(boxes_xyxy):
        return []
    boxes_xywh = [
        [float(x1), float(y1), float(x2 - x1), float(y2 - y1)] for x1, y1, x2, y2 in boxes_xyxy
    ]
    selected = cv2.dnn.NMSBoxes(
        boxes_xywh, confidences.astype(float).tolist(), confidence_threshold, iou_threshold
    )
    regions: list[DefectRegion] = []
    for raw_index in np.asarray(selected).reshape(-1):
        index = int(raw_index)
        x1, y1, x2, y2 = boxes_xyxy[index]
        x1 = (x1 - letterbox.pad_x) / letterbox.ratio
        y1 = (y1 - letterbox.pad_y) / letterbox.ratio
        x2 = (x2 - letterbox.pad_x) / letterbox.ratio
        y2 = (y2 - letterbox.pad_y) / letterbox.ratio
        x1, x2 = np.clip([x1, x2], 0, letterbox.original_width)
        y1, y2 = np.clip([y1, y2], 0, letterbox.original_height)
        width, height = float(x2 - x1), float(y2 - y1)
        class_id = int(class_ids[index])
        regions.append(
            DefectRegion(
                region_id=len(regions) + 1,
                bounding_box=BoundingBox(
                    x1=round(float(x1)),
                    y1=round(float(y1)),
                    x2=round(float(x2)),
                    y2=round(float(y2)),
                ),
                area=max(0.0, width * height),
                aspect_ratio=width / height if height else 0.0,
                circularity=0.0,
                centroid=(float((x1 + x2) / 2), float((y1 + y2) / 2)),
                source="yolo_onnx",
                class_id=class_id,
                class_name=class_names[class_id] if class_id < len(class_names) else str(class_id),
                confidence=float(confidences[index]),
            )
        )
    return regions

from __future__ import annotations

import json
from pathlib import Path

import cv2
import numpy as np
from numpy.typing import NDArray

from backend.app.anomaly_detection.config import AnomalyConfig
from backend.app.anomaly_detection.dataset import train_good_images


def _features(path: Path, image_size: int) -> NDArray[np.float32]:
    image = cv2.imread(str(path), cv2.IMREAD_COLOR)
    if image is None:
        raise ValueError(f"Failed to read image: {path}")
    image = cv2.resize(image, (image_size, image_size), interpolation=cv2.INTER_AREA)
    lab = cv2.cvtColor(image, cv2.COLOR_BGR2LAB).astype(np.float32) / 255.0
    gray = cv2.cvtColor(image, cv2.COLOR_BGR2GRAY).astype(np.float32) / 255.0
    gx = cv2.Sobel(gray, cv2.CV_32F, 1, 0, ksize=3)
    gy = cv2.Sobel(gray, cv2.CV_32F, 0, 1, ksize=3)
    grad = cv2.magnitude(gx, gy)
    return np.dstack([lab, grad]).astype(np.float32)


def train_padim_statistical(config: AnomalyConfig) -> dict[str, object]:
    images = train_good_images(config.data_root, config.category)
    if not images:
        raise RuntimeError(
            f"No train/good images found for {config.category} under {config.data_root}"
        )
    stack = np.stack([_features(path, config.image_size) for path in images], axis=0)
    mean = stack.mean(axis=0).astype(np.float32)
    std = np.maximum(stack.std(axis=0), 1e-4).astype(np.float32)
    scores = np.sqrt((((stack - mean) / std) ** 2).mean(axis=-1))
    image_scores = scores.reshape(scores.shape[0], -1).max(axis=1)
    threshold = float(np.quantile(image_scores, config.threshold_quantile))
    mask_threshold = float(np.quantile(scores, config.mask_threshold_quantile))
    config.artifact_dir.mkdir(parents=True, exist_ok=True)
    np.savez_compressed(
        config.model_path,
        mean=mean,
        std=std,
        threshold=np.asarray(threshold, dtype=np.float32),
        mask_threshold=np.asarray(mask_threshold, dtype=np.float32),
        image_size=np.asarray(config.image_size, dtype=np.int32),
        algorithm=np.asarray(config.algorithm),
        category=np.asarray(config.category),
    )
    metadata = {
        "algorithm": config.algorithm,
        "category": config.category,
        "image_size": config.image_size,
        "train_good_count": len(images),
        "threshold": threshold,
        "mask_threshold": mask_threshold,
        "model_path": str(config.model_path),
    }
    (config.artifact_dir / "training-metadata.json").write_text(
        json.dumps(metadata, ensure_ascii=False, indent=2), encoding="utf-8"
    )
    return metadata

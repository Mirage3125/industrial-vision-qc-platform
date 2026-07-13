from __future__ import annotations

from pathlib import Path
from typing import Any

import cv2
import numpy as np

from backend.app.inspection.config import HybridInspectionConfig


def inspect_image_quality(image_path: Path, config: HybridInspectionConfig) -> dict[str, Any]:
    if not image_path.is_file():
        return {"valid": False, "issues": ["IMAGE_NOT_FOUND"], "path": str(image_path)}
    if image_path.suffix.lower() not in {".jpg", ".jpeg", ".png", ".bmp", ".tif", ".tiff"}:
        return {"valid": False, "issues": ["UNSUPPORTED_FORMAT"], "path": str(image_path)}
    image = cv2.imread(str(image_path), cv2.IMREAD_COLOR)
    if image is None:
        return {"valid": False, "issues": ["CORRUPT_IMAGE"], "path": str(image_path)}
    height, width = image.shape[:2]
    issues: list[str] = []
    if width < config.min_width or height < config.min_height:
        issues.append("RESOLUTION_TOO_SMALL")
    gray = cv2.cvtColor(image, cv2.COLOR_BGR2GRAY)
    blur_variance = float(cv2.Laplacian(gray, cv2.CV_64F).var())
    bright_ratio = float(np.mean(gray >= config.overexposed_gray_threshold))
    dark_ratio = float(np.mean(gray <= config.underexposed_gray_threshold))
    if blur_variance < config.blur_variance_threshold:
        issues.append("BLURRY_IMAGE")
    if bright_ratio >= config.overexposed_ratio_threshold:
        issues.append("OVEREXPOSED_IMAGE")
    if dark_ratio >= config.underexposed_ratio_threshold:
        issues.append("UNDEREXPOSED_IMAGE")
    return {
        "valid": not issues,
        "issues": issues,
        "width": width,
        "height": height,
        "blur_variance": round(blur_variance, 4),
        "bright_ratio": round(bright_ratio, 4),
        "dark_ratio": round(dark_ratio, 4),
    }

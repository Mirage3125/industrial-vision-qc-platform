from __future__ import annotations

from pathlib import Path
from typing import cast

import cv2
import numpy as np
from numpy.typing import NDArray


def normalize_map(anomaly_map: NDArray[np.float32]) -> NDArray[np.uint8]:
    value = anomaly_map.astype(np.float32)
    min_value = float(value.min())
    max_value = float(value.max())
    if max_value <= min_value:
        return cast(NDArray[np.uint8], np.zeros_like(value, dtype=np.uint8))
    normalized = np.clip((value - min_value) * 255.0 / (max_value - min_value), 0, 255)
    return cast(NDArray[np.uint8], normalized.astype(np.uint8))


def write_visualizations(
    image_path: Path,
    anomaly_map: NDArray[np.float32],
    mask: NDArray[np.bool_],
    output_dir: Path,
    stem_suffix: str = "",
) -> tuple[Path, Path, Path]:
    output_dir.mkdir(parents=True, exist_ok=True)
    image = cv2.imread(str(image_path), cv2.IMREAD_COLOR)
    if image is None:
        raise ValueError(f"Failed to read image: {image_path}")
    resized_map = cv2.resize(anomaly_map, (image.shape[1], image.shape[0])).astype(np.float32)
    heat_uint8 = normalize_map(resized_map)
    heatmap = cast(NDArray[np.uint8], cv2.applyColorMap(heat_uint8, cv2.COLORMAP_JET))
    overlay = cv2.addWeighted(image, 0.65, heatmap, 0.35, 0.0)
    mask_uint8 = cv2.resize(mask.astype(np.uint8) * 255, (image.shape[1], image.shape[0]))
    stem = f"{image_path.stem}{stem_suffix}"
    heatmap_path = output_dir / f"{stem}_heatmap.png"
    overlay_path = output_dir / f"{stem}_overlay.png"
    mask_path = output_dir / f"{stem}_mask.png"
    cv2.imwrite(str(heatmap_path), heatmap)
    cv2.imwrite(str(overlay_path), overlay)
    cv2.imwrite(str(mask_path), mask_uint8)
    return heatmap_path, overlay_path, mask_path

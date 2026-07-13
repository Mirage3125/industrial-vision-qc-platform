from __future__ import annotations

import hashlib
import json
from collections import Counter
from pathlib import Path
from typing import Any

import cv2

IMAGE_EXTENSIONS = {".png", ".jpg", ".jpeg", ".bmp", ".tif", ".tiff"}


def category_root(data_root: Path, category: str) -> Path:
    root = data_root / category
    if not root.is_dir():
        raise FileNotFoundError(f"MVTec category not found: {root}")
    return root


def list_images(directory: Path) -> list[Path]:
    if not directory.is_dir():
        return []
    return sorted(path for path in directory.rglob("*") if path.suffix.lower() in IMAGE_EXTENSIONS)


def train_good_images(data_root: Path, category: str) -> list[Path]:
    return list_images(category_root(data_root, category) / "train" / "good")


def test_images(data_root: Path, category: str) -> list[tuple[Path, str]]:
    test_root = category_root(data_root, category) / "test"
    samples: list[tuple[Path, str]] = []
    for defect_dir in sorted(path for path in test_root.iterdir() if path.is_dir()):
        for image in list_images(defect_dir):
            samples.append((image, defect_dir.name))
    return samples


def mask_path_for(image_path: Path, data_root: Path, category: str, label: str) -> Path | None:
    if label == "good":
        return None
    gt_dir = category_root(data_root, category) / "ground_truth" / label
    stem = image_path.stem
    candidates = list(gt_dir.glob(f"{stem}_mask.*")) + list(gt_dir.glob(f"{stem}.*"))
    return candidates[0] if candidates else None


def file_sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as file:
        for chunk in iter(lambda: file.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def image_size(path: Path) -> tuple[int, int] | None:
    image = cv2.imread(str(path), cv2.IMREAD_COLOR)
    if image is None:
        return None
    height, width = image.shape[:2]
    return width, height


def build_manifest(
    data_root: Path, category: str, source: str, output_path: Path
) -> dict[str, Any]:
    train_good = train_good_images(data_root, category)
    test = test_images(data_root, category)
    label_counts = Counter(label for _, label in test)
    masks = [
        mask_path_for(path, data_root, category, label)
        for path, label in test
        if mask_path_for(path, data_root, category, label) is not None
    ]
    all_images = train_good + [path for path, _ in test]
    hashes = {str(path): file_sha256(path) for path in all_images}
    sizes = Counter(str(image_size(path)) for path in all_images if image_size(path) is not None)
    corrupted = [str(path) for path in all_images if image_size(path) is None]
    manifest: dict[str, Any] = {
        "source": source,
        "category": category,
        "train_good_count": len(train_good),
        "test_good_count": label_counts.get("good", 0),
        "test_anomaly_counts": {k: v for k, v in sorted(label_counts.items()) if k != "good"},
        "mask_count": len([mask for mask in masks if mask is not None]),
        "corrupted_image_count": len(corrupted),
        "corrupted_images": corrupted,
        "file_hashes": hashes,
        "image_size_distribution": dict(sizes),
    }
    output_path.parent.mkdir(parents=True, exist_ok=True)
    output_path.write_text(json.dumps(manifest, ensure_ascii=False, indent=2), encoding="utf-8")
    return manifest

import hashlib
import random
import shutil
import xml.etree.ElementTree as ET
from collections import Counter
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

from backend.app.detection.config import DetectionDatasetConfig


@dataclass
class DatasetCheckResult:
    image_count: int = 0
    annotation_count: int = 0
    class_distribution: Counter[str] = field(default_factory=Counter)
    errors: list[dict[str, Any]] = field(default_factory=list)
    warnings: list[dict[str, Any]] = field(default_factory=list)
    leakage_pairs: list[tuple[str, str]] = field(default_factory=list)

    @property
    def valid(self) -> bool:
        return not self.errors

    def as_dict(self) -> dict[str, Any]:
        return {
            "valid": self.valid,
            "image_count": self.image_count,
            "annotation_count": self.annotation_count,
            "class_distribution": dict(sorted(self.class_distribution.items())),
            "errors": self.errors,
            "warnings": self.warnings,
            "leakage_pairs": self.leakage_pairs,
        }


def convert_voc_directory(
    images_dir: Path,
    annotations_dir: Path,
    output_dir: Path,
    config: DetectionDatasetConfig,
) -> DatasetCheckResult:
    """Convert valid VOC boxes to normalized YOLO labels and copy source images."""

    result = DatasetCheckResult()
    output_images = output_dir / "images"
    output_labels = output_dir / "labels"
    output_images.mkdir(parents=True, exist_ok=True)
    output_labels.mkdir(parents=True, exist_ok=True)
    class_to_id = {name: index for index, name in enumerate(config.class_names)}

    for xml_path in sorted(annotations_dir.glob("*.xml")):
        try:
            root = ET.parse(xml_path).getroot()
            filename = _required_text(root, "filename")
            width = int(_required_text(root, "size/width"))
            height = int(_required_text(root, "size/height"))
        except (ET.ParseError, ValueError) as error:
            result.errors.append(
                {"code": "INVALID_XML", "path": str(xml_path), "detail": str(error)}
            )
            continue
        image_path = images_dir / filename
        if not image_path.is_file():
            result.errors.append({"code": "IMAGE_NOT_FOUND", "path": str(image_path)})
            continue
        if width <= 0 or height <= 0:
            result.errors.append({"code": "INVALID_IMAGE_SIZE", "path": str(xml_path)})
            continue

        yolo_lines: list[str] = []
        for object_node in root.findall("object"):
            class_name = _required_text(object_node, "name")
            if class_name not in class_to_id:
                result.errors.append(
                    {"code": "UNKNOWN_CLASS", "path": str(xml_path), "class_name": class_name}
                )
                continue
            try:
                xmin = float(_required_text(object_node, "bndbox/xmin"))
                ymin = float(_required_text(object_node, "bndbox/ymin"))
                xmax = float(_required_text(object_node, "bndbox/xmax"))
                ymax = float(_required_text(object_node, "bndbox/ymax"))
            except ValueError as error:
                result.errors.append(
                    {"code": "INVALID_BOX", "path": str(xml_path), "detail": str(error)}
                )
                continue
            if (
                xmin < 0
                or ymin < 0
                or xmax > width
                or ymax > height
                or xmin >= xmax
                or ymin >= ymax
            ):
                result.errors.append(
                    {
                        "code": "OUT_OF_BOUNDS_BOX",
                        "path": str(xml_path),
                        "box": [xmin, ymin, xmax, ymax],
                    }
                )
                continue
            center_x = ((xmin + xmax) / 2) / width
            center_y = ((ymin + ymax) / 2) / height
            box_width = (xmax - xmin) / width
            box_height = (ymax - ymin) / height
            yolo_lines.append(
                f"{class_to_id[class_name]} {center_x:.8f} {center_y:.8f} "
                f"{box_width:.8f} {box_height:.8f}"
            )
            result.class_distribution[class_name] += 1
            result.annotation_count += 1
        if not yolo_lines:
            result.warnings.append({"code": "NO_VALID_BOXES", "path": str(xml_path)})
        shutil.copy2(image_path, output_images / image_path.name)
        (output_labels / f"{image_path.stem}.txt").write_text(
            "\n".join(yolo_lines) + ("\n" if yolo_lines else ""), encoding="utf-8"
        )
        result.image_count += 1
    return result


def split_yolo_dataset(
    source_dir: Path, output_dir: Path, validation_ratio: float, seed: int
) -> dict[str, int]:
    """Create a deterministic train/val copy from an all/images + all/labels source."""

    images = sorted(path for path in (source_dir / "images").iterdir() if path.is_file())
    if len(images) < 2:
        raise ValueError("At least two images are required for a train/validation split")
    shuffled = images.copy()
    random.Random(seed).shuffle(shuffled)
    validation_count = max(1, min(len(shuffled) - 1, round(len(shuffled) * validation_ratio)))
    validation_names = {path.name for path in shuffled[:validation_count]}
    counts = {"train": 0, "val": 0}
    for image_path in images:
        split = "val" if image_path.name in validation_names else "train"
        image_output = output_dir / split / "images"
        label_output = output_dir / split / "labels"
        image_output.mkdir(parents=True, exist_ok=True)
        label_output.mkdir(parents=True, exist_ok=True)
        label_path = source_dir / "labels" / f"{image_path.stem}.txt"
        if not label_path.is_file():
            raise ValueError(f"Missing YOLO label: {label_path}")
        shutil.copy2(image_path, image_output / image_path.name)
        shutil.copy2(label_path, label_output / label_path.name)
        counts[split] += 1
    return counts


def validate_yolo_dataset(root: Path, config: DetectionDatasetConfig) -> DatasetCheckResult:
    result = DatasetCheckResult()
    split_hashes: dict[str, dict[str, str]] = {"train": {}, "val": {}}
    for split in ("train", "val"):
        images_dir = root / split / "images"
        labels_dir = root / split / "labels"
        if not images_dir.is_dir() or not labels_dir.is_dir():
            result.errors.append({"code": "MISSING_SPLIT", "split": split})
            continue
        for image_path in sorted(path for path in images_dir.iterdir() if path.is_file()):
            if image_path.suffix.lower() not in config.allowed_extensions:
                result.errors.append({"code": "INVALID_IMAGE_FORMAT", "path": str(image_path)})
                continue
            result.image_count += 1
            split_hashes[split][image_path.name] = hashlib.sha256(
                image_path.read_bytes()
            ).hexdigest()
            label_path = labels_dir / f"{image_path.stem}.txt"
            if not label_path.is_file():
                result.errors.append({"code": "MISSING_LABEL", "path": str(image_path)})
                continue
            lines = [
                line.strip()
                for line in label_path.read_text(encoding="utf-8").splitlines()
                if line.strip()
            ]
            if not lines:
                result.warnings.append({"code": "EMPTY_LABEL", "path": str(label_path)})
            for line_number, line in enumerate(lines, start=1):
                parts = line.split()
                try:
                    if len(parts) != 5:
                        raise ValueError("expected five fields")
                    class_id = int(parts[0])
                    center_x, center_y, width, height = map(float, parts[1:])
                except ValueError as error:
                    result.errors.append(
                        {
                            "code": "MALFORMED_LABEL",
                            "path": str(label_path),
                            "line": line_number,
                            "detail": str(error),
                        }
                    )
                    continue
                if not 0 <= class_id < len(config.class_names):
                    result.errors.append(
                        {"code": "INVALID_CLASS", "path": str(label_path), "line": line_number}
                    )
                    continue
                if (
                    width <= 0
                    or height <= 0
                    or center_x - width / 2 < 0
                    or center_y - height / 2 < 0
                    or center_x + width / 2 > 1
                    or center_y + height / 2 > 1
                ):
                    result.errors.append(
                        {"code": "OUT_OF_BOUNDS_BOX", "path": str(label_path), "line": line_number}
                    )
                    continue
                result.class_distribution[config.class_names[class_id]] += 1
                result.annotation_count += 1
    validation_by_hash = {digest: name for name, digest in split_hashes["val"].items()}
    for train_name, digest in split_hashes["train"].items():
        if digest in validation_by_hash:
            result.leakage_pairs.append((train_name, validation_by_hash[digest]))
            result.errors.append(
                {
                    "code": "SPLIT_LEAKAGE",
                    "train": train_name,
                    "val": validation_by_hash[digest],
                }
            )
    return result


def _required_text(node: ET.Element, path: str) -> str:
    child = node.find(path)
    if child is None or child.text is None or not child.text.strip():
        raise ValueError(f"missing XML field: {path}")
    return child.text.strip()

import hashlib
from collections import Counter, defaultdict
from dataclasses import dataclass
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

import cv2
import numpy as np

from backend.app.data_quality.config import DataQualityConfig
from backend.app.data_quality.reporting import write_html_report, write_json_report

ImageArray = np.ndarray[Any, Any]


@dataclass(frozen=True)
class ScanArtifacts:
    report: dict[str, Any]
    json_path: Path
    html_path: Path


class DataQualityScanner:
    """Scan YOLO datasets without coupling analysis to API or persistence."""

    def __init__(self, config: DataQualityConfig) -> None:
        self.config = config

    def scan(self, dataset_path: Path, output_dir: Path) -> ScanArtifacts:
        dataset_path = dataset_path.resolve()
        if not dataset_path.is_dir():
            raise ValueError(f"Dataset directory does not exist: {dataset_path}")
        output_dir.mkdir(parents=True, exist_ok=True)
        thumbnail_dir = output_dir / "thumbnails"
        thumbnail_dir.mkdir(exist_ok=True)

        issues: list[dict[str, Any]] = []
        records: list[dict[str, Any]] = []
        class_distribution: Counter[str] = Counter()
        exact_hashes: dict[str, list[dict[str, Any]]] = defaultdict(list)
        perceptual_records: list[dict[str, Any]] = []

        for split in ("train", "val", "test"):
            legacy_images = dataset_path / split / "images"
            legacy_labels = dataset_path / split / "labels"
            images_dir = (
                legacy_images if legacy_images.is_dir() else dataset_path / "images" / split
            )
            labels_dir = (
                legacy_labels if legacy_labels.is_dir() else dataset_path / "labels" / split
            )
            if not images_dir.is_dir():
                self._issue(issues, "MISSING_IMAGES_DIRECTORY", images_dir, {"split": split})
                continue
            for image_path in sorted(path for path in images_dir.rglob("*") if path.is_file()):
                relative_path = image_path.relative_to(dataset_path).as_posix()
                if image_path.suffix.lower() not in self.config.image_extensions:
                    self._issue(
                        issues,
                        "UNSUPPORTED_IMAGE_FORMAT",
                        image_path,
                        {"extension": image_path.suffix.lower()},
                        relative_path,
                    )
                    continue
                image = self._read_image(image_path)
                if image is None:
                    self._issue(issues, "CORRUPT_IMAGE", image_path, {}, relative_path)
                    continue

                height, width = image.shape[:2]
                md5 = hashlib.md5(image_path.read_bytes()).hexdigest()  # noqa: S324
                perceptual_hash = self._difference_hash(image)
                record = {
                    "path": image_path,
                    "relative_path": relative_path,
                    "split": split,
                    "width": width,
                    "height": height,
                    "md5": md5,
                    "phash": perceptual_hash,
                }
                records.append(record)
                exact_hashes[md5].append(record)
                perceptual_records.append(record)

                gray = cv2.cvtColor(image, cv2.COLOR_BGR2GRAY)
                blur_variance = float(cv2.Laplacian(gray, cv2.CV_64F).var())
                bright_ratio = float(np.mean(gray >= self.config.overexposed_gray_threshold))
                dark_ratio = float(np.mean(gray <= self.config.underexposed_gray_threshold))
                if blur_variance < self.config.blur_variance_threshold:
                    self._issue(
                        issues,
                        "BLURRY_IMAGE",
                        image_path,
                        {"laplacian_variance": round(blur_variance, 4)},
                        relative_path,
                    )
                if bright_ratio >= self.config.overexposed_ratio_threshold:
                    self._issue(
                        issues,
                        "OVEREXPOSED_IMAGE",
                        image_path,
                        {"bright_ratio": round(bright_ratio, 4)},
                        relative_path,
                    )
                if dark_ratio >= self.config.underexposed_ratio_threshold:
                    self._issue(
                        issues,
                        "UNDEREXPOSED_IMAGE",
                        image_path,
                        {"dark_ratio": round(dark_ratio, 4)},
                        relative_path,
                    )

                label_path = labels_dir / image_path.relative_to(images_dir).with_suffix(".txt")
                self._check_yolo_label(
                    label_path, image_path, relative_path, width, height, issues, class_distribution
                )

        self._check_exact_duplicates(exact_hashes, issues)
        self._check_near_duplicates(perceptual_records, issues)
        self._check_split_leakage(exact_hashes, perceptual_records, issues)
        self._create_thumbnails(dataset_path, issues, thumbnail_dir)

        issue_counts = Counter(issue["code"] for issue in issues)
        report = {
            "schema_version": "1.0",
            "created_at": datetime.now(UTC).isoformat().replace("+00:00", "Z"),
            "dataset_path": str(dataset_path),
            "configuration": self.config.model_dump(mode="json"),
            "summary": {
                "total_images": len(records),
                "corrupt_count": issue_counts["CORRUPT_IMAGE"],
                "unsupported_format_count": issue_counts["UNSUPPORTED_IMAGE_FORMAT"],
                "duplicate_count": issue_counts["EXACT_DUPLICATE"],
                "near_duplicate_count": issue_counts["NEAR_DUPLICATE"],
                "blurry_count": issue_counts["BLURRY_IMAGE"],
                "overexposed_count": issue_counts["OVEREXPOSED_IMAGE"],
                "underexposed_count": issue_counts["UNDEREXPOSED_IMAGE"],
                "invalid_annotation_count": sum(
                    issue_counts[code]
                    for code in (
                        "MISSING_ANNOTATION",
                        "EMPTY_ANNOTATION",
                        "MALFORMED_ANNOTATION",
                        "INVALID_CLASS",
                        "OUT_OF_BOUNDS_BOX",
                        "TINY_BOX",
                    )
                ),
                "leakage_count": issue_counts["SPLIT_LEAKAGE"],
                "potential_near_leakage_count": issue_counts["POTENTIAL_SPLIT_LEAKAGE"],
                "issue_count": len(issues),
            },
            "image_size_statistics": self._size_statistics(records),
            "class_distribution": dict(sorted(class_distribution.items())),
            "issues": issues[: self.config.max_issue_samples],
        }
        json_path = output_dir / "data-quality-report.json"
        html_path = output_dir / "data-quality-report.html"
        write_json_report(report, json_path)
        write_html_report(report, html_path)
        return ScanArtifacts(report=report, json_path=json_path, html_path=html_path)

    def _check_yolo_label(
        self,
        label_path: Path,
        image_path: Path,
        relative_path: str,
        width: int,
        height: int,
        issues: list[dict[str, Any]],
        classes: Counter[str],
    ) -> None:
        if not label_path.exists():
            self._issue(issues, "MISSING_ANNOTATION", image_path, {}, relative_path)
            return
        lines = [
            line.strip()
            for line in label_path.read_text(encoding="utf-8").splitlines()
            if line.strip()
        ]
        if not lines:
            self._issue(issues, "EMPTY_ANNOTATION", image_path, {}, relative_path)
            return
        for line_number, line in enumerate(lines, start=1):
            parts = line.split()
            try:
                if len(parts) != 5:
                    raise ValueError
                class_id = int(parts[0])
                center_x, center_y, box_width, box_height = map(float, parts[1:])
            except ValueError:
                self._issue(
                    issues,
                    "MALFORMED_ANNOTATION",
                    image_path,
                    {"line": line_number, "value": line},
                    relative_path,
                )
                continue
            if not 0 <= class_id < len(self.config.class_names):
                self._issue(
                    issues,
                    "INVALID_CLASS",
                    image_path,
                    {"line": line_number, "class_id": class_id},
                    relative_path,
                )
            else:
                classes[self.config.class_names[class_id]] += 1
            x1, y1 = center_x - box_width / 2, center_y - box_height / 2
            x2, y2 = center_x + box_width / 2, center_y + box_height / 2
            if box_width <= 0 or box_height <= 0 or min(x1, y1) < 0 or max(x2, y2) > 1:
                self._issue(
                    issues,
                    "OUT_OF_BOUNDS_BOX",
                    image_path,
                    {"line": line_number, "box": [center_x, center_y, box_width, box_height]},
                    relative_path,
                )
                continue
            width_px, height_px = box_width * width, box_height * height
            if (
                width_px < self.config.tiny_box_min_width_px
                or height_px < self.config.tiny_box_min_height_px
                or width_px * height_px < self.config.tiny_box_min_area_px
            ):
                self._issue(
                    issues,
                    "TINY_BOX",
                    image_path,
                    {"line": line_number, "width_px": width_px, "height_px": height_px},
                    relative_path,
                )

    def _check_exact_duplicates(
        self, groups: dict[str, list[dict[str, Any]]], issues: list[dict[str, Any]]
    ) -> None:
        for md5, records in groups.items():
            for duplicate in records[1:]:
                self._issue(
                    issues,
                    "EXACT_DUPLICATE",
                    duplicate["path"],
                    {"duplicate_of": records[0]["relative_path"], "md5": md5},
                    duplicate["relative_path"],
                )

    def _check_near_duplicates(
        self, records: list[dict[str, Any]], issues: list[dict[str, Any]]
    ) -> None:
        for index, left in enumerate(records):
            for right in records[index + 1 :]:
                if left["md5"] == right["md5"]:
                    continue
                distance = (left["phash"] ^ right["phash"]).bit_count()
                if distance <= self.config.perceptual_hash_hamming_threshold:
                    self._issue(
                        issues,
                        "NEAR_DUPLICATE",
                        right["path"],
                        {"similar_to": left["relative_path"], "hamming_distance": distance},
                        right["relative_path"],
                    )

    def _check_split_leakage(
        self,
        exact_groups: dict[str, list[dict[str, Any]]],
        records: list[dict[str, Any]],
        issues: list[dict[str, Any]],
    ) -> None:
        leaked_pairs: set[tuple[str, str]] = set()
        for group in exact_groups.values():
            for index, left in enumerate(group):
                for right in group[index + 1 :]:
                    if left["split"] != right["split"]:
                        leaked_pairs.add((left["relative_path"], right["relative_path"]))
        potential_pairs: set[tuple[str, str]] = set()
        for index, left in enumerate(records):
            for right in records[index + 1 :]:
                if left["split"] == right["split"] or left["md5"] == right["md5"]:
                    continue
                distance = (left["phash"] ^ right["phash"]).bit_count()
                if distance <= self.config.perceptual_hash_hamming_threshold:
                    potential_pairs.add((left["relative_path"], right["relative_path"]))
        for left_path, right_path in sorted(leaked_pairs):
            self._issue(
                issues,
                "SPLIT_LEAKAGE",
                Path(right_path),
                {"left_path": left_path, "right_path": right_path, "method": "md5"},
                right_path,
            )
        for left_path, right_path in sorted(potential_pairs):
            self._issue(
                issues,
                "POTENTIAL_SPLIT_LEAKAGE",
                Path(right_path),
                {"left_path": left_path, "right_path": right_path, "method": "perceptual_hash"},
                right_path,
            )

    def _create_thumbnails(
        self, dataset_path: Path, issues: list[dict[str, Any]], output_dir: Path
    ) -> None:
        created: dict[str, str] = {}
        for issue in issues[: self.config.max_issue_samples]:
            relative = issue["path"]
            if relative in created:
                issue["thumbnail"] = created[relative]
                continue
            image_path = dataset_path / relative
            image = self._read_image(image_path)
            if image is None:
                continue
            thumbnail = image.copy()
            scale = min(
                self.config.thumbnail_width / thumbnail.shape[1],
                self.config.thumbnail_height / thumbnail.shape[0],
                1.0,
            )
            resized = cv2.resize(thumbnail, dsize=None, fx=scale, fy=scale)
            filename = f"{hashlib.sha1(relative.encode()).hexdigest()[:12]}.jpg"  # noqa: S324
            cv2.imwrite(str(output_dir / filename), resized)
            thumbnail_reference = f"thumbnails/{filename}"
            created[relative] = thumbnail_reference
            issue["thumbnail"] = thumbnail_reference

    @staticmethod
    def _read_image(path: Path) -> ImageArray | None:
        try:
            data = np.fromfile(path, dtype=np.uint8)
            image = cv2.imdecode(data, cv2.IMREAD_COLOR)
        except (OSError, cv2.error):
            return None
        return image

    @staticmethod
    def _difference_hash(image: ImageArray) -> int:
        gray = cv2.cvtColor(image, cv2.COLOR_BGR2GRAY)
        resized = cv2.resize(gray, (9, 8), interpolation=cv2.INTER_AREA)
        bits = resized[:, 1:] > resized[:, :-1]
        value = 0
        for bit in bits.flatten():
            value = (value << 1) | int(bit)
        return value

    @staticmethod
    def _size_statistics(records: list[dict[str, Any]]) -> dict[str, Any]:
        if not records:
            return {"count": 0}
        widths = np.array([record["width"] for record in records])
        heights = np.array([record["height"] for record in records])
        return {
            "count": len(records),
            "width": {
                "min": int(widths.min()),
                "max": int(widths.max()),
                "mean": round(float(widths.mean()), 2),
            },
            "height": {
                "min": int(heights.min()),
                "max": int(heights.max()),
                "mean": round(float(heights.mean()), 2),
            },
            "resolutions": dict(Counter(f"{r['width']}x{r['height']}" for r in records)),
        }

    @staticmethod
    def _issue(
        issues: list[dict[str, Any]],
        code: str,
        path: Path,
        details: dict[str, Any],
        relative_path: str | None = None,
    ) -> None:
        issues.append({"code": code, "path": relative_path or path.as_posix(), "details": details})

"""Convert real NEU-DET VOC annotations into a deterministic YOLO 70/20/10 split."""

import argparse
import hashlib
import json
import random
import shutil
from collections import Counter, defaultdict
from pathlib import Path
from typing import Any
from xml.etree import ElementTree

import cv2
import yaml

CLASS_NAMES = [
    "crazing",
    "inclusion",
    "patches",
    "pitted_surface",
    "rolled_in_scale",
    "scratches",
]
ALIASES = {"rolled-in_scale": "rolled_in_scale"}
IMAGE_EXTENSIONS = {".jpg", ".jpeg", ".png", ".bmp"}


def canonical_class(value: str) -> str:
    normalized = value.strip().lower().replace(" ", "_")
    return ALIASES.get(normalized, normalized)


def parse_annotation(path: Path) -> tuple[int, int, list[tuple[str, float, float, float, float]]]:
    root = ElementTree.parse(path).getroot()
    width = int(root.findtext("size/width", "0"))
    height = int(root.findtext("size/height", "0"))
    if width <= 0 or height <= 0:
        raise ValueError("invalid image size")
    boxes: list[tuple[str, float, float, float, float]] = []
    for node in root.findall("object"):
        class_name = canonical_class(node.findtext("name", ""))
        box = node.find("bndbox")
        if class_name not in CLASS_NAMES or box is None:
            raise ValueError(f"invalid class or box: {class_name}")
        xmin = float(box.findtext("xmin", ""))
        ymin = float(box.findtext("ymin", ""))
        xmax = float(box.findtext("xmax", ""))
        ymax = float(box.findtext("ymax", ""))
        if xmin < 0 or ymin < 0 or xmax > width or ymax > height or xmin >= xmax or ymin >= ymax:
            raise ValueError(f"out-of-bounds box: {[xmin, ymin, xmax, ymax]}")
        boxes.append((class_name, xmin, ymin, xmax, ymax))
    if not boxes:
        raise ValueError("empty annotation")
    return width, height, boxes


def main() -> None:
    parser = argparse.ArgumentParser(description="Prepare real NEU-DET as YOLO train/val/test")
    parser.add_argument("--raw", type=Path, default=Path("data/raw/neu-det/extracted"))
    parser.add_argument("--output", type=Path, default=Path("data/processed/neu-det-yolo"))
    parser.add_argument(
        "--manifest",
        type=Path,
        default=Path("artifacts/datasets/neu-det/split_manifest.json"),
    )
    parser.add_argument("--seed", type=int, default=42)
    args = parser.parse_args()

    images = {
        path.stem: path
        for path in args.raw.rglob("*")
        if path.is_file() and path.suffix.lower() in IMAGE_EXTENSIONS
    }
    annotations = {path.stem: path for path in args.raw.rglob("*.xml")}
    matched = sorted(set(images) & set(annotations))
    if len(matched) < 10:
        raise SystemExit("No usable real NEU-DET image/XML pairs found")

    parsed: dict[str, tuple[int, int, list[tuple[str, float, float, float, float]]]] = {}
    invalid: list[dict[str, str]] = []
    grouped: dict[str, list[str]] = defaultdict(list)
    hashes: dict[str, str] = {}
    for stem in matched:
        image = cv2.imread(str(images[stem]), cv2.IMREAD_GRAYSCALE)
        if image is None:
            invalid.append({"stem": stem, "error": "corrupt image"})
            continue
        try:
            parsed[stem] = parse_annotation(annotations[stem])
        except (ElementTree.ParseError, ValueError) as error:
            invalid.append({"stem": stem, "error": str(error)})
            continue
        primary_class = canonical_class(images[stem].parent.name)
        if primary_class not in CLASS_NAMES:
            primary_class = parsed[stem][2][0][0]
        grouped[primary_class].append(stem)
        hashes[stem] = hashlib.sha256(images[stem].read_bytes()).hexdigest()
    if invalid:
        raise SystemExit(f"Invalid real samples found: {invalid[:10]}")

    assignments: dict[str, str] = {}
    randomizer = random.Random(args.seed)
    for class_name in CLASS_NAMES:
        stems = sorted(grouped[class_name])
        randomizer.shuffle(stems)
        train_end = round(len(stems) * 0.7)
        val_end = train_end + round(len(stems) * 0.2)
        for stem in stems[:train_end]:
            assignments[stem] = "train"
        for stem in stems[train_end:val_end]:
            assignments[stem] = "val"
        for stem in stems[val_end:]:
            assignments[stem] = "test"

    stems_by_hash: dict[str, list[str]] = defaultdict(list)
    for stem, digest in hashes.items():
        stems_by_hash[digest].append(stem)
    for duplicate_stems in stems_by_hash.values():
        if len(duplicate_stems) > 1:
            target_split = assignments[sorted(duplicate_stems)[0]]
            for stem in duplicate_stems:
                assignments[stem] = target_split

    if args.output.exists():
        shutil.rmtree(args.output)

    split_counts: Counter[str] = Counter()
    split_classes: dict[str, Counter[str]] = {
        "train": Counter(),
        "val": Counter(),
        "test": Counter(),
    }
    content_locations: dict[str, list[tuple[str, str]]] = defaultdict(list)
    tiny_box_count = 0
    duplicate_box_count = 0
    for stem, split in assignments.items():
        image_output = args.output / "images" / split
        label_output = args.output / "labels" / split
        image_output.mkdir(parents=True, exist_ok=True)
        label_output.mkdir(parents=True, exist_ok=True)
        image_path = images[stem]
        shutil.copy2(image_path, image_output / image_path.name)
        width, height, boxes = parsed[stem]
        lines: list[str] = []
        seen_boxes: set[tuple[str, float, float, float, float]] = set()
        for class_name, xmin, ymin, xmax, ymax in boxes:
            box_key = (class_name, xmin, ymin, xmax, ymax)
            if box_key in seen_boxes:
                duplicate_box_count += 1
                continue
            seen_boxes.add(box_key)
            box_width, box_height = xmax - xmin, ymax - ymin
            if box_width < 4 or box_height < 4 or box_width * box_height < 24:
                tiny_box_count += 1
            center_x, center_y = (xmin + xmax) / 2 / width, (ymin + ymax) / 2 / height
            lines.append(
                f"{CLASS_NAMES.index(class_name)} {center_x:.8f} {center_y:.8f} "
                f"{box_width / width:.8f} {box_height / height:.8f}"
            )
            split_classes[split][class_name] += 1
        (label_output / f"{stem}.txt").write_text("\n".join(lines) + "\n", encoding="utf-8")
        split_counts[split] += 1
        content_locations[hashes[stem]].append((split, stem))

    leakage = [
        locations
        for locations in content_locations.values()
        if len({split for split, _ in locations}) > 1
    ]
    duplicates = [locations for locations in content_locations.values() if len(locations) > 1]
    dataset_yaml = {
        "path": str(args.output.resolve()),
        "train": "images/train",
        "val": "images/val",
        "test": "images/test",
        "names": {index: name for index, name in enumerate(CLASS_NAMES)},
    }
    dataset_yaml_path = args.output / "dataset.yaml"
    dataset_yaml_path.write_text(
        yaml.safe_dump(dataset_yaml, sort_keys=False, allow_unicode=True), encoding="utf-8"
    )
    manifest: dict[str, Any] = {
        "random_seed": args.seed,
        "source_pair_count": len(matched),
        "train_count": split_counts["train"],
        "val_count": split_counts["val"],
        "test_count": split_counts["test"],
        "split_class_distribution": {
            split: dict(sorted(distribution.items()))
            for split, distribution in split_classes.items()
        },
        "duplicate_content_groups": duplicates,
        "content_hash_leakage": leakage,
        "unmatched_images": sorted(set(images) - set(annotations)),
        "unmatched_annotations": sorted(set(annotations) - set(images)),
        "invalid_annotation_count": len(invalid),
        "tiny_box_count": tiny_box_count,
        "duplicate_box_count_removed": duplicate_box_count,
        "dataset_yaml": str(dataset_yaml_path.resolve()),
    }
    args.manifest.parent.mkdir(parents=True, exist_ok=True)
    args.manifest.write_text(json.dumps(manifest, ensure_ascii=False, indent=2), encoding="utf-8")
    print(json.dumps(manifest, ensure_ascii=False, indent=2))
    if not all(split_counts[split] for split in ("train", "val", "test")) or leakage:
        raise SystemExit(2)


if __name__ == "__main__":
    main()

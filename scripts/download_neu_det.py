"""Download and verify the real detection-labelled NEU-DET dataset."""

import argparse
import hashlib
import json
import shutil
import subprocess
import sys
import tarfile
import urllib.error
import urllib.request
import zipfile
from collections import Counter
from datetime import UTC, datetime
from pathlib import Path
from typing import Any
from xml.etree import ElementTree

import cv2

ZENODO_API = "https://zenodo.org/api/records/{record_id}"
GOOGLE_DRIVE_DOWNLOAD = (
    "https://drive.usercontent.google.com/download?id={file_id}&export=download&confirm=t"
)
IMAGE_EXTENSIONS = {".jpg", ".jpeg", ".png", ".bmp", ".tif", ".tiff"}
ARCHIVE_SUFFIXES = (".zip", ".tar", ".tar.gz", ".tgz")
EXPECTED_CLASSES = {
    "crazing",
    "inclusion",
    "patches",
    "pitted_surface",
    "rolled_in_scale",
    "scratches",
}


def _request_json(url: str) -> dict[str, Any]:
    request = urllib.request.Request(url, headers={"User-Agent": "factory-vision-quality-loop/1.0"})
    with urllib.request.urlopen(request, timeout=60) as response:
        return json.load(response)


def _download(url: str, destination: Path, expected_size: int | None) -> None:
    if destination.is_file() and (
        expected_size is None or destination.stat().st_size == expected_size
    ):
        print(f"Reusing completed archive: {destination}")
        return
    partial = destination.with_suffix(destination.suffix + ".part")
    offset = partial.stat().st_size if partial.exists() else 0
    headers = {"User-Agent": "factory-vision-quality-loop/1.0"}
    if offset:
        headers["Range"] = f"bytes={offset}-"
    request = urllib.request.Request(url, headers=headers)
    with urllib.request.urlopen(request, timeout=120) as response:
        append = offset > 0 and response.status == 206
        if offset and not append:
            offset = 0
        mode = "ab" if append else "wb"
        with partial.open(mode) as stream:
            shutil.copyfileobj(response, stream, length=1024 * 1024)
    if expected_size is not None and partial.stat().st_size != expected_size:
        raise RuntimeError(
            f"Incomplete download for {destination.name}: "
            f"expected {expected_size}, got {partial.stat().st_size}"
        )
    partial.replace(destination)


def _safe_extract(archive: Path, destination: Path) -> None:
    destination.mkdir(parents=True, exist_ok=True)
    destination_root = destination.resolve()
    if zipfile.is_zipfile(archive):
        with zipfile.ZipFile(archive) as bundle:
            for member in bundle.infolist():
                target = (destination / member.filename).resolve()
                if destination_root not in target.parents and target != destination_root:
                    raise RuntimeError(f"Unsafe archive member: {member.filename}")
            bundle.extractall(destination)
        return
    if tarfile.is_tarfile(archive):
        with tarfile.open(archive) as bundle:
            for member in bundle.getmembers():
                target = (destination / member.name).resolve()
                if destination_root not in target.parents and target != destination_root:
                    raise RuntimeError(f"Unsafe archive member: {member.name}")
            bundle.extractall(destination, filter="data")
        return
    raise RuntimeError(f"Unsupported or invalid archive: {archive}")


def _sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as stream:
        for chunk in iter(lambda: stream.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def _scan_dataset(
    root: Path, source: str, record_id: str, archives: list[dict[str, str]]
) -> dict[str, Any]:
    images = sorted(path for path in root.rglob("*") if path.suffix.lower() in IMAGE_EXTENSIONS)
    annotations = sorted(root.rglob("*.xml"))
    image_by_stem: dict[str, list[Path]] = {}
    annotation_by_stem: dict[str, list[Path]] = {}
    for image in images:
        image_by_stem.setdefault(image.stem, []).append(image)
    for annotation in annotations:
        annotation_by_stem.setdefault(annotation.stem, []).append(annotation)
    image_stems, annotation_stems = set(image_by_stem), set(annotation_by_stem)

    corrupt_images: list[str] = []
    width_distribution: Counter[str] = Counter()
    height_distribution: Counter[str] = Counter()
    for image in images:
        decoded = cv2.imread(str(image), cv2.IMREAD_GRAYSCALE)
        if decoded is None:
            corrupt_images.append(str(image.relative_to(root)))
        else:
            height, width = decoded.shape[:2]
            width_distribution[str(width)] += 1
            height_distribution[str(height)] += 1

    invalid_xml: list[str] = []
    class_distribution: Counter[str] = Counter()
    for annotation in annotations:
        try:
            parsed = ElementTree.parse(annotation).getroot()
            if parsed.find("size/width") is None or parsed.find("size/height") is None:
                raise ValueError("missing image size")
            for object_node in parsed.findall("object"):
                name = (
                    object_node.findtext("name", "")
                    .strip()
                    .lower()
                    .replace(" ", "_")
                    .replace("-", "_")
                )
                box = object_node.find("bndbox")
                if not name or box is None:
                    raise ValueError("missing class or bounding box")
                for key in ("xmin", "ymin", "xmax", "ymax"):
                    float(box.findtext(key, ""))
                class_distribution[name] += 1
        except (ElementTree.ParseError, ValueError):
            invalid_xml.append(str(annotation.relative_to(root)))

    unknown_classes = sorted(set(class_distribution) - EXPECTED_CLASSES)
    manifest = {
        "dataset_name": "NEU-DET",
        "dataset_source": source,
        "source_record": record_id,
        "download_time": datetime.now(UTC).isoformat().replace("+00:00", "Z"),
        "archives": archives,
        "archive_filename": archives[0]["filename"] if len(archives) == 1 else None,
        "archive_sha256": archives[0]["sha256"] if len(archives) == 1 else None,
        "image_count": len(images),
        "annotation_count": len(annotations),
        "matched_pair_count": len(image_stems & annotation_stems),
        "unmatched_images": sorted(image_stems - annotation_stems),
        "unmatched_annotations": sorted(annotation_stems - image_stems),
        "duplicate_image_stems": sorted(
            stem for stem, paths in image_by_stem.items() if len(paths) > 1
        ),
        "duplicate_annotation_stems": sorted(
            stem for stem, paths in annotation_by_stem.items() if len(paths) > 1
        ),
        "corrupt_image_count": len(corrupt_images),
        "corrupt_images": corrupt_images,
        "invalid_xml_count": len(invalid_xml),
        "invalid_xml": invalid_xml,
        "image_width_distribution": dict(sorted(width_distribution.items())),
        "image_height_distribution": dict(sorted(height_distribution.items())),
        "class_distribution": dict(sorted(class_distribution.items())),
        "class_names": sorted(class_distribution),
        "unknown_classes": unknown_classes,
    }
    if len(images) < 10 or len(annotations) < 10:
        raise RuntimeError(
            f"Downloaded content is not a usable detection dataset: "
            f"images={len(images)}, annotations={len(annotations)}"
        )
    if manifest["matched_pair_count"] < 10 or corrupt_images or invalid_xml or unknown_classes:
        raise RuntimeError("Dataset verification failed; inspect raw_manifest.json")
    return manifest


def main() -> None:
    parser = argparse.ArgumentParser(description="Download and verify real NEU-DET detection data")
    parser.add_argument("--source", choices=["zenodo", "google-drive", "kaggle"], default="zenodo")
    parser.add_argument("--record-id", default="16882077")
    parser.add_argument("--file-id", default="1qrdZlaDi272eA79b0uCwwqPrm2Q_WI3k")
    parser.add_argument("--kaggle-dataset", default="kaustubhdikshit/neu-surface-defect-database")
    parser.add_argument("--output", type=Path, default=Path("data/raw/neu-det"))
    parser.add_argument("--filename", help="Download one exact record filename")
    parser.add_argument(
        "--manifest",
        type=Path,
        default=Path("artifacts/datasets/neu-det/raw_manifest.json"),
    )
    args = parser.parse_args()
    try:
        if args.source == "kaggle":
            downloads = args.output / "downloads"
            extracted = args.output / "extracted"
            downloads.mkdir(parents=True, exist_ok=True)
            filename = args.filename or "neu-surface-defect-database.zip"
            destination = downloads / filename
            if destination.is_file() and zipfile.is_zipfile(destination):
                print(f"Reusing completed archive: {destination}")
            else:
                kaggle_executable = Path(sys.executable).parent / "Scripts" / "kaggle.exe"
                if not kaggle_executable.is_file():
                    raise RuntimeError(f"Kaggle CLI not found: {kaggle_executable}")
                subprocess.run(
                    [
                        str(kaggle_executable),
                        "datasets",
                        "download",
                        "-d",
                        args.kaggle_dataset,
                        "-p",
                        str(downloads),
                    ],
                    check=True,
                )
            if not destination.is_file() or not zipfile.is_zipfile(destination):
                raise RuntimeError(f"Kaggle did not produce a valid archive: {destination}")
            checksum = _sha256(destination)
            print(f"Downloaded: {destination} SHA256={checksum}")
            _safe_extract(destination, extracted)
            source_url = f"https://www.kaggle.com/datasets/{args.kaggle_dataset}"
            archives = [{"filename": filename, "sha256": checksum, "source_url": source_url}]
            manifest = _scan_dataset(extracted, args.source, args.kaggle_dataset, archives)
            args.manifest.parent.mkdir(parents=True, exist_ok=True)
            args.manifest.write_text(
                json.dumps(manifest, ensure_ascii=False, indent=2), encoding="utf-8"
            )
            print(json.dumps(manifest, ensure_ascii=False, indent=2))
            return
        if args.source == "google-drive":
            downloads = args.output / "downloads"
            extracted = args.output / "extracted"
            downloads.mkdir(parents=True, exist_ok=True)
            filename = args.filename or "NEU-DET.zip"
            destination = downloads / filename
            download_url = GOOGLE_DRIVE_DOWNLOAD.format(file_id=args.file_id)
            print(f"Source: Google Drive file {args.file_id}")
            print(f"Expected archive: {filename}")
            _download(download_url, destination, None)
            if not zipfile.is_zipfile(destination) and not tarfile.is_tarfile(destination):
                raise RuntimeError(
                    "Google Drive did not return a valid archive; "
                    "the file may require manual access"
                )
            checksum = _sha256(destination)
            print(f"Downloaded: {destination} SHA256={checksum}")
            _safe_extract(destination, extracted)
            archives = [{"filename": filename, "sha256": checksum, "source_url": download_url}]
            manifest = _scan_dataset(extracted, args.source, args.file_id, archives)
            args.manifest.parent.mkdir(parents=True, exist_ok=True)
            args.manifest.write_text(
                json.dumps(manifest, ensure_ascii=False, indent=2), encoding="utf-8"
            )
            print(json.dumps(manifest, ensure_ascii=False, indent=2))
            return
        record = _request_json(ZENODO_API.format(record_id=args.record_id))
        title = str(record.get("metadata", {}).get("title", ""))
        print(f"Source: {record.get('links', {}).get('html', ZENODO_API)}")
        print(f"Title: {title}")
        files = record.get("files", [])
        available_names = [item.get("key") for item in files]
        identity_text = f"{title} {' '.join(str(name) for name in available_names)}".lower()
        if "neu" not in identity_text or "det" not in identity_text:
            raise RuntimeError(
                "Zenodo record identity mismatch: expected NEU-DET, "
                f"found title={title!r}, files={available_names}"
            )
        selected = (
            [item for item in files if args.filename == item.get("key")]
            if args.filename
            else [
                item
                for item in files
                if str(item.get("key", "")).lower().endswith(ARCHIVE_SUFFIXES)
            ]
        )
        if not selected:
            raise RuntimeError(f"No matching archive. Available files: {available_names}")
        downloads = args.output / "downloads"
        extracted = args.output / "extracted"
        downloads.mkdir(parents=True, exist_ok=True)
        archive_records: list[dict[str, str]] = []
        for item in selected:
            filename = str(item["key"])
            destination = downloads / filename
            download_url = str(item.get("links", {}).get("content") or item["links"]["self"])
            _download(download_url, destination, int(item["size"]) if item.get("size") else None)
            checksum = _sha256(destination)
            print(f"Downloaded: {destination} SHA256={checksum}")
            _safe_extract(destination, extracted)
            archive_records.append(
                {"filename": filename, "sha256": checksum, "source_url": download_url}
            )
        manifest = _scan_dataset(extracted, args.source, args.record_id, archive_records)
        args.manifest.parent.mkdir(parents=True, exist_ok=True)
        args.manifest.write_text(
            json.dumps(manifest, ensure_ascii=False, indent=2), encoding="utf-8"
        )
        print(json.dumps(manifest, ensure_ascii=False, indent=2))
    except (
        OSError,
        urllib.error.URLError,
        subprocess.CalledProcessError,
        RuntimeError,
        KeyError,
        ValueError,
    ) as error:
        print(f"DOWNLOAD_FAILED: {type(error).__name__}: {error}")
        raise SystemExit(2) from error


if __name__ == "__main__":
    main()

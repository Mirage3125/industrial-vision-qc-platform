from __future__ import annotations

import hashlib
import json
import shutil
from collections import Counter
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

from fastapi import APIRouter, Depends, Request
from sqlalchemy import select
from sqlalchemy.orm import Session

from backend.app.core.errors import AppError
from backend.app.db.base import utc_now
from backend.app.db.session import get_db
from backend.app.models.domain import AuditLog, DatasetVersion, FeedbackSample
from backend.app.schemas.common import success_response
from backend.app.schemas.inspection import DatasetVersionManualRequest, FeedbackExportRequest

router = APIRouter(tags=["feedback"])
DB_SESSION = Depends(get_db)


def _hash(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as file:
        for chunk in iter(lambda: file.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def _write_yolo_label(path: Path, boxes: list[dict[str, Any]], class_names: list[str]) -> None:
    lines: list[str] = []
    for box in boxes:
        class_name = str(box.get("class_name") or box.get("label") or "unknown")
        if class_name == "normal":
            continue
        if class_name not in class_names:
            class_names.append(class_name)
        class_id = class_names.index(class_name)
        raw = box.get("bounding_box", box)
        x1, y1, x2, y2 = (float(raw.get(key, 0)) for key in ("x1", "y1", "x2", "y2"))
        width = max(float(box.get("image_width", 1)), x2, 1.0)
        height = max(float(box.get("image_height", 1)), y2, 1.0)
        bw, bh = max(x2 - x1, 1.0), max(y2 - y1, 1.0)
        cx, cy = x1 + bw / 2, y1 + bh / 2
        values = [class_id, cx / width, cy / height, bw / width, bh / height]
        if any(float(value) < 0 or float(value) > 1 for value in values[1:]):
            raise AppError("INVALID_ANNOTATION", f"Box out of bounds for {path}", 400)
        lines.append("{} {:.6f} {:.6f} {:.6f} {:.6f}".format(*values))
    path.write_text("\n".join(lines), encoding="utf-8")


@router.post("/feedback/export")
def export_feedback(
    payload: FeedbackExportRequest, request: Request, db: Session = DB_SESSION
) -> dict[str, object]:
    if db.scalar(select(DatasetVersion).where(DatasetVersion.version == payload.dataset_version)):
        raise AppError("DATASET_VERSION_EXISTS", "Dataset version already exists", 409)
    samples = db.scalars(
        select(FeedbackSample).where(FeedbackSample.export_status == "pending")
    ).all()
    if not samples:
        raise AppError("NO_FEEDBACK_TO_EXPORT", "No pending feedback samples", 400)
    output_root = Path(payload.output_root) / payload.dataset_version
    images_dir = output_root / "images" / "train"
    labels_dir = output_root / "labels" / "train"
    try:
        images_dir.mkdir(parents=True, exist_ok=False)
        labels_dir.mkdir(parents=True, exist_ok=True)
    except FileExistsError as error:
        raise AppError("EXPORT_TARGET_EXISTS", "Export target already exists", 409) from error
    class_names: list[str] = []
    sample_ids: list[str] = []
    image_hashes: dict[str, str] = {}
    model_versions: set[str] = set()
    distribution: Counter[str] = Counter()
    try:
        for sample in samples:
            source = Path(sample.image_path)
            if not source.is_file():
                raise AppError("SOURCE_IMAGE_MISSING", f"Image missing: {source}", 400)
            target_image = images_dir / f"{sample.id}{source.suffix.lower()}"
            shutil.copy2(source, target_image)
            boxes = sample.corrected_boxes
            if not boxes and sample.corrected_label != "normal":
                boxes = [{"label": sample.corrected_label, "x1": 0, "y1": 0, "x2": 1, "y2": 1}]
            _write_yolo_label(labels_dir / f"{sample.id}.txt", boxes, class_names)
            sample_ids.append(sample.id)
            image_hashes[str(target_image)] = _hash(target_image)
            distribution[sample.corrected_label] += 1
            if sample.source_model_version:
                model_versions.add(sample.source_model_version)
            sample.export_status = "exported"
        manifest = {
            "dataset_version": payload.dataset_version,
            "created_at": datetime.now(UTC).isoformat().replace("+00:00", "Z"),
            "source_dataset_version": payload.source_dataset_version,
            "sample_count": len(samples),
            "added_sample_count": len(samples),
            "class_distribution": dict(distribution),
            "sample_ids": sample_ids,
            "image_hashes": image_hashes,
            "export_operator": payload.export_operator,
            "source_model_versions": sorted(model_versions),
        }
        (output_root / "manifest.json").write_text(
            json.dumps(manifest, ensure_ascii=False, indent=2), encoding="utf-8"
        )
        dataset = DatasetVersion(
            version=payload.dataset_version,
            sample_count=len(samples),
            class_distribution=dict(distribution),
            source_description=f"feedback export by {payload.export_operator}",
        )
        db.add(dataset)
        db.flush()
        for sample in samples:
            sample.dataset_version_id = dataset.id
        db.add(
            AuditLog(
                action="feedback.exported",
                entity_type="dataset_version",
                entity_id=dataset.id,
                operator=payload.export_operator,
                details=manifest,
                created_at=utc_now(),
            )
        )
        db.commit()
    except Exception:
        db.rollback()
        if output_root.exists():
            shutil.rmtree(output_root, ignore_errors=True)
        raise
    return success_response(
        {"dataset_version_id": dataset.id, "manifest": manifest}, request.state.request_id
    )


@router.get("/datasets/versions")
def list_dataset_versions(request: Request, db: Session = DB_SESSION) -> dict[str, object]:
    rows = db.scalars(select(DatasetVersion).order_by(DatasetVersion.created_at.desc())).all()
    return success_response(
        {
            "versions": [
                {
                    "id": row.id,
                    "version": row.version,
                    "sample_count": row.sample_count,
                    "class_distribution": row.class_distribution,
                    "created_at": row.created_at.isoformat(),
                }
                for row in rows
            ]
        },
        request.state.request_id,
    )


@router.post("/datasets/versions")
def create_dataset_version(
    payload: DatasetVersionManualRequest, request: Request, db: Session = DB_SESSION
) -> dict[str, object]:
    if db.scalar(select(DatasetVersion).where(DatasetVersion.version == payload.version)):
        raise AppError("DATASET_VERSION_EXISTS", "Dataset version already exists", 409)
    row = DatasetVersion(
        version=payload.version,
        sample_count=payload.sample_count,
        class_distribution=payload.class_distribution,
        source_description=payload.source_description,
    )
    db.add(row)
    db.commit()
    return success_response({"id": row.id, "version": row.version}, request.state.request_id)

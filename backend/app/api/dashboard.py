from __future__ import annotations

import json
from collections import Counter
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

from fastapi import APIRouter, Depends, Request
from sqlalchemy import select
from sqlalchemy.orm import Session

from backend.app.db.session import get_db
from backend.app.models.domain import DataQualityReport, FeedbackSample, Inspection, ModelVersion
from backend.app.schemas.common import success_response

router = APIRouter(tags=["dashboard"])
DB_SESSION = Depends(get_db)


def _record(value: Any) -> dict[str, Any]:
    return value if isinstance(value, dict) else {}


def _number(value: Any) -> float | None:
    if isinstance(value, bool):
        return None
    if isinstance(value, int | float):
        return float(value)
    try:
        return float(value)
    except (TypeError, ValueError):
        return None


def _first_number(*values: Any) -> float | None:
    for value in values:
        number = _number(value)
        if number is not None:
            return number
    return None


def _benchmark_metrics(report: dict[str, Any]) -> dict[str, Any]:
    results = report.get("results")
    result_rows = (
        [row for row in results if isinstance(row, dict)] if isinstance(results, list) else []
    )
    selected = min(
        result_rows,
        key=lambda row: _first_number(row.get("average_latency_ms"), row.get("avg_ms"))
        or float("inf"),
        default={},
    )
    latency = _record(report.get("latency"))
    percentiles = _record(report.get("percentiles"))
    metrics = _record(report.get("metrics"))
    summary = _record(report.get("summary"))

    average_ms = _first_number(
        selected.get("average_latency_ms"),
        selected.get("avg_ms"),
        metrics.get("average_latency_ms"),
        summary.get("average_latency_ms"),
        report.get("average_latency_ms"),
        latency.get("average_ms"),
        latency.get("mean_ms"),
    )
    throughput = _first_number(
        selected.get("throughput_images_per_second"),
        selected.get("throughput"),
        selected.get("fps"),
        metrics.get("throughput_images_per_second"),
        metrics.get("throughput"),
        summary.get("throughput_images_per_second"),
        report.get("throughput_images_per_second"),
    )
    error_count = _first_number(
        metrics.get("error_count"), summary.get("error_count"), report.get("error_count")
    )
    success_count = _first_number(
        metrics.get("success_count"), summary.get("success_count"), report.get("success_count")
    )
    total_count = _first_number(
        metrics.get("total_count"),
        summary.get("total_count"),
        report.get("total_count"),
        report.get("image_count_used"),
        selected.get("measured_iterations"),
    )

    success_rate = _first_number(
        metrics.get("success_rate"), summary.get("success_rate"), report.get("success_rate")
    )
    error_rate = _first_number(
        metrics.get("error_rate"), summary.get("error_rate"), report.get("error_rate")
    )
    if (
        success_rate is None
        and success_count is not None
        and total_count is not None
        and total_count != 0
    ):
        success_rate = success_count / total_count
    if (
        error_rate is None
        and error_count is not None
        and total_count is not None
        and total_count != 0
    ):
        error_rate = error_count / total_count
    if result_rows and success_rate is None and error_rate is None:
        success_rate = 1.0
        error_rate = 0.0

    return {
        "average_latency_ms": average_ms,
        "p50_latency_ms": _first_number(
            selected.get("p50_latency_ms"),
            selected.get("p50_ms"),
            percentiles.get("p50"),
            percentiles.get("50"),
            latency.get("p50_ms"),
            metrics.get("p50_latency_ms"),
            report.get("p50_latency_ms"),
        ),
        "p95_latency_ms": _first_number(
            selected.get("p95_latency_ms"),
            selected.get("p95_ms"),
            percentiles.get("p95"),
            percentiles.get("95"),
            latency.get("p95_ms"),
            metrics.get("p95_latency_ms"),
            report.get("p95_latency_ms"),
        ),
        "throughput_images_per_second": throughput,
        "success_rate": success_rate,
        "error_rate": error_rate,
        "generated_at": report.get("created_at") or report.get("generated_at"),
        "selected_provider": selected.get("provider"),
        "selected_batch_size": selected.get("batch_size"),
    }


def _quality_metrics(report: dict[str, Any]) -> dict[str, Any]:
    summary = _record(report.get("summary"))
    size_stats = _record(report.get("image_size_statistics"))
    width_stats = _record(size_stats.get("width"))
    height_stats = _record(size_stats.get("height"))
    issues = report.get("issues")
    issue_rows = (
        [issue for issue in issues if isinstance(issue, dict)] if isinstance(issues, list) else []
    )
    issue_count = _first_number(summary.get("issue_count"), report.get("issue_count"))
    total_images = _first_number(
        summary.get("total_images"), report.get("total_images"), size_stats.get("count")
    )
    corrupt_count = _first_number(summary.get("corrupt_count"), 0) or 0
    unsupported_count = _first_number(summary.get("unsupported_format_count"), 0) or 0
    valid_images = (
        None if total_images is None else max(total_images - corrupt_count - unsupported_count, 0)
    )
    issues_truncated = issue_count is not None and len(issue_rows) < issue_count
    unique_issue_paths = {str(issue.get("path")) for issue in issue_rows if issue.get("path")}
    problem_image_count = None if issues_truncated else len(unique_issue_paths)
    overexposed_count = _first_number(summary.get("overexposed_count"), 0) or 0
    underexposed_count = _first_number(summary.get("underexposed_count"), 0) or 0
    bright_ratio = (
        None
        if total_images is None or total_images == 0
        else overexposed_count / total_images
    )
    dark_ratio = (
        None
        if total_images is None or total_images == 0
        else underexposed_count / total_images
    )

    return {
        "total_images": total_images,
        "valid_images": valid_images,
        "problem_image_count": problem_image_count,
        "issue_finding_count": issue_count,
        "issue_sample_count": len(issue_rows),
        "issues_truncated": issues_truncated,
        "width_min": _first_number(width_stats.get("min")),
        "width_mean": _first_number(width_stats.get("mean")),
        "width_max": _first_number(width_stats.get("max")),
        "height_min": _first_number(height_stats.get("min")),
        "height_mean": _first_number(height_stats.get("mean")),
        "height_max": _first_number(height_stats.get("max")),
        "blur_issue_count": _first_number(summary.get("blurry_count")),
        "bright_ratio": bright_ratio,
        "dark_ratio": dark_ratio,
        "generated_at": report.get("created_at") or report.get("generated_at"),
        "valid": issue_count == 0 if issue_count is not None else None,
    }


@router.get("/dashboard/overview")
def overview(request: Request, db: Session = DB_SESSION) -> dict[str, object]:
    today = datetime.now(UTC).date()
    inspections = db.scalars(select(Inspection)).all()
    today_rows = [row for row in inspections if row.created_at.date() == today]
    defect_rows = [row for row in today_rows if row.final_status in {"DEFECT", "ANOMALY"}]
    pending_reviews = [row for row in inspections if row.review_reasons]
    reviewed = [
        row
        for row in inspections
        if row.final_status == "REVIEW_REQUIRED" and not row.review_reasons
    ]
    latencies = [row.processing_time_ms or 0 for row in today_rows if row.processing_time_ms]
    models = db.scalars(select(ModelVersion).where(ModelVersion.active.is_(True))).all()
    class_distribution = Counter(row.predicted_class or "unknown" for row in inspections)
    return success_response(
        {
            "demo_data": False,
            "today_detection_count": len(today_rows),
            "defect_count": len(defect_rows),
            "defect_rate": len(defect_rows) / max(len(today_rows), 1),
            "auto_pass_count": len([row for row in today_rows if row.final_status == "PASS"]),
            "pending_review_count": len(pending_reviews),
            "reviewed_count": len(reviewed),
            "average_latency_ms": sum(latencies) / max(len(latencies), 1),
            "active_models": [
                {
                    "id": model.id,
                    "model_name": model.model_name,
                    "model_type": model.model_type,
                    "version": model.version,
                    "framework": model.framework,
                    "model_path": model.model_path,
                }
                for model in models
            ],
            "onnx_provider": "CPUExecutionProvider",
            "class_distribution": dict(class_distribution),
            "recent_records": [
                {
                    "id": row.id,
                    "image_path": row.image_path,
                    "final_status": row.final_status,
                    "predicted_class": row.predicted_class,
                    "created_at": row.created_at.isoformat(),
                }
                for row in sorted(inspections, key=lambda item: item.created_at, reverse=True)[:10]
            ],
        },
        request.state.request_id,
    )


@router.get("/feedback")
def feedback_pool(request: Request, db: Session = DB_SESSION) -> dict[str, object]:
    rows = db.scalars(select(FeedbackSample).order_by(FeedbackSample.created_at.desc())).all()
    return success_response(
        {
            "samples": [
                {
                    "id": row.id,
                    "inspection_id": row.inspection_id,
                    "image_path": row.image_path,
                    "original_label": row.original_label,
                    "corrected_label": row.corrected_label,
                    "original_boxes": row.original_boxes,
                    "corrected_boxes": row.corrected_boxes,
                    "feedback_type": row.feedback_type,
                    "export_status": row.export_status,
                    "dataset_version_id": row.dataset_version_id,
                    "source_model_version": row.source_model_version,
                    "created_at": row.created_at.isoformat(),
                }
                for row in rows
            ]
        },
        request.state.request_id,
    )


@router.get("/quality/reports")
def quality_reports(request: Request, db: Session = DB_SESSION) -> dict[str, object]:
    rows = db.scalars(select(DataQualityReport).order_by(DataQualityReport.created_at.desc())).all()
    file_reports: list[dict[str, Any]] = []
    for path in Path("artifacts").glob("**/data-quality-report.json"):
        try:
            data = json.loads(path.read_text(encoding="utf-8"))
            file_reports.append(
                {
                    "id": str(path),
                    "dataset_path": data.get("dataset_path"),
                    "summary": data.get("summary", {}),
                    "image_size_statistics": data.get("image_size_statistics", {}),
                    "class_distribution": data.get("class_distribution", {}),
                    "issues": data.get("issues", []),
                    "created_at": data.get("created_at"),
                    "metrics": _quality_metrics(data),
                    "report_path": str(path),
                    "html_path": str(path.with_suffix(".html")),
                }
            )
        except json.JSONDecodeError:
            continue
    return success_response(
        {
            "reports": [
                {
                    "id": row.id,
                    "dataset_path": row.dataset_path,
                    "summary": row.statistics,
                    "image_size_statistics": row.image_size_statistics,
                    "class_distribution": row.class_distribution,
                    "issues": row.issue_samples,
                    "metrics": _quality_metrics(
                        {
                            "summary": row.statistics,
                            "image_size_statistics": row.image_size_statistics,
                            "issues": row.issue_samples,
                            "created_at": row.created_at.isoformat(),
                        }
                    ),
                    "report_path": row.report_path,
                    "created_at": row.created_at.isoformat(),
                }
                for row in rows
            ]
            + file_reports
        },
        request.state.request_id,
    )


@router.get("/benchmarks")
def benchmarks(request: Request) -> dict[str, object]:
    reports = []
    for path in Path("artifacts/benchmarks").glob("*.json"):
        try:
            report = json.loads(path.read_text(encoding="utf-8"))
            reports.append(
                {
                    "path": str(path),
                    "name": path.name,
                    "report": report,
                    "metrics": _benchmark_metrics(report),
                    "created_at": report.get("created_at") or report.get("generated_at"),
                }
            )
        except json.JSONDecodeError:
            continue
    return success_response({"reports": reports}, request.state.request_id)

from __future__ import annotations

from fastapi import APIRouter, Depends, Request
from sqlalchemy import select
from sqlalchemy.orm import Session

from backend.app.core.errors import AppError
from backend.app.db.base import utc_now
from backend.app.db.session import get_db
from backend.app.inspection.service import create_feedback_from_review
from backend.app.models.domain import AuditLog, Inspection, ReviewTask
from backend.app.schemas.common import success_response
from backend.app.schemas.inspection import ReviewActionRequest

router = APIRouter(prefix="/reviews", tags=["reviews"])
DB_SESSION = Depends(get_db)


def _review_payload(
    review: ReviewTask, inspection: Inspection, logs: list[AuditLog]
) -> dict[str, object]:
    return {
        "id": review.id,
        "inspection_id": inspection.id,
        "image_path": inspection.image_path,
        "yolo_boxes": inspection.yolo_result.get("regions", []),
        "anomaly_heatmap": inspection.anomaly_result.get("heatmap_path"),
        "quality_result": inspection.quality_result,
        "original_prediction": review.original_prediction,
        "system_decision": inspection.system_decision,
        "final_status": inspection.final_status,
        "review_reasons": inspection.review_reasons,
        "model_versions": inspection.model_versions,
        "step_timings": inspection.step_timings,
        "review_status": review.review_status,
        "corrected_prediction": review.corrected_prediction,
        "reviewer": review.reviewer,
        "review_comment": review.review_comment,
        "history": [
            {
                "action": log.action,
                "operator": log.operator,
                "details": log.details,
                "created_at": log.created_at.isoformat(),
            }
            for log in logs
        ],
    }


@router.get("")
def list_reviews(request: Request, db: Session = DB_SESSION) -> dict[str, object]:
    rows = db.scalars(select(ReviewTask).order_by(ReviewTask.created_at.desc()).limit(100)).all()
    return success_response(
        {
            "reviews": [
                {
                    "id": row.id,
                    "inspection_id": row.inspection_id,
                    "review_status": row.review_status,
                    "review_reasons": row.system_decision.get("review_reasons", []),
                    "created_at": row.created_at.isoformat(),
                }
                for row in rows
            ]
        },
        request.state.request_id,
    )


@router.get("/{review_id}")
def get_review(review_id: str, request: Request, db: Session = DB_SESSION) -> dict[str, object]:
    review = db.get(ReviewTask, review_id)
    if review is None:
        raise AppError("REVIEW_NOT_FOUND", "Review task not found", 404)
    inspection = db.get(Inspection, review.inspection_id)
    if inspection is None:
        raise AppError("INSPECTION_NOT_FOUND", "Inspection not found", 404)
    logs = db.scalars(
        select(AuditLog).where(AuditLog.entity_id.in_([review.id, inspection.id]))
    ).all()
    return success_response(
        _review_payload(review, inspection, list(logs)), request.state.request_id
    )


def _finalize(
    db: Session,
    review_id: str,
    payload: ReviewActionRequest,
    status: str,
    create_feedback: bool,
) -> ReviewTask:
    review = db.get(ReviewTask, review_id)
    if review is None:
        raise AppError("REVIEW_NOT_FOUND", "Review task not found", 404)
    if review.review_status != "pending":
        raise AppError("REVIEW_STATE_CONFLICT", "Review task is already finalized", 409)
    inspection = db.get(Inspection, review.inspection_id)
    if inspection is None:
        raise AppError("INSPECTION_NOT_FOUND", "Inspection not found", 404)
    review.review_status = status
    review.reviewer = payload.reviewer
    review.review_comment = payload.review_comment
    review.reviewed_at = utc_now()
    review.corrected_prediction = payload.corrected_prediction or review.original_prediction
    if create_feedback:
        create_feedback_from_review(
            db,
            review,
            inspection,
            payload.reviewer,
            review.corrected_prediction or {},
            payload.corrected_label or inspection.predicted_class or "unknown",
            payload.feedback_type,
        )
    db.add(
        AuditLog(
            action=f"review.{status}",
            entity_type="review_task",
            entity_id=review.id,
            operator=payload.reviewer,
            details={"inspection_id": inspection.id, "create_feedback": create_feedback},
            created_at=utc_now(),
        )
    )
    return review


@router.post("/{review_id}/approve")
def approve(
    review_id: str, payload: ReviewActionRequest, request: Request, db: Session = DB_SESSION
) -> dict[str, object]:
    review = _finalize(db, review_id, payload, "approved", False)
    db.commit()
    return success_response(
        {"review_id": review.id, "status": review.review_status}, request.state.request_id
    )


@router.post("/{review_id}/correct")
def correct(
    review_id: str, payload: ReviewActionRequest, request: Request, db: Session = DB_SESSION
) -> dict[str, object]:
    review = _finalize(db, review_id, payload, "corrected", True)
    db.commit()
    return success_response(
        {"review_id": review.id, "status": review.review_status}, request.state.request_id
    )


@router.post("/{review_id}/reject")
def reject(
    review_id: str, payload: ReviewActionRequest, request: Request, db: Session = DB_SESSION
) -> dict[str, object]:
    review = _finalize(db, review_id, payload, "rejected", False)
    db.commit()
    return success_response(
        {"review_id": review.id, "status": review.review_status}, request.state.request_id
    )

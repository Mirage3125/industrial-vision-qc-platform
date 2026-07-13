from datetime import UTC

import pytest
from sqlalchemy import func, select
from sqlalchemy.orm import Session

from backend.app.core.errors import AppError
from backend.app.models.domain import AuditLog, FeedbackSample, Inspection, ModelVersion, ReviewTask
from backend.app.repositories import InspectionRepository
from backend.app.schemas.domain import (
    InspectionCreate,
    InspectionResponse,
    ModelVersionCreate,
    ReviewCorrection,
)
from backend.app.services import InspectionService, ModelService, ReviewService


def test_create_and_read_inspection_with_json_and_utc(db_session: Session) -> None:
    created = InspectionService(db_session).create(
        InspectionCreate(
            image_path="data/sample.jpg",
            source="line-a",
            prediction_type="hybrid",
            predicted_class="scratch",
            confidence=0.62,
            bounding_boxes=[{"x1": 1, "y1": 2, "x2": 10, "y2": 20}],
            requires_review=True,
            review_reason="low_confidence",
        ),
        operator="tester",
        request_id="request-1",
    )

    loaded = InspectionRepository(db_session).get(created.id)
    assert loaded is not None
    assert loaded.bounding_boxes[0]["x2"] == 10
    assert loaded.created_at.tzinfo is UTC
    assert len(loaded.id) == 36
    assert db_session.scalar(select(func.count()).select_from(ReviewTask)) == 1
    assert db_session.scalar(select(func.count()).select_from(AuditLog)) == 2

    response = InspectionResponse.model_validate(loaded)
    assert response.model_dump(mode="json")["created_at"].endswith("Z")


def test_review_correction_creates_feedback_and_audit_atomically(db_session: Session) -> None:
    inspection = InspectionService(db_session).create(
        InspectionCreate(
            image_path="data/review.jpg",
            source="line-b",
            prediction_type="detection",
            predicted_class="inclusion",
            confidence=0.4,
            requires_review=True,
            review_reason="low_confidence",
        ),
        operator="system",
    )
    review = db_session.scalar(select(ReviewTask).where(ReviewTask.inspection_id == inspection.id))
    assert review is not None
    review_id = review.id
    db_session.rollback()

    feedback = ReviewService(db_session).correct(
        review_id,
        ReviewCorrection(
            reviewer="quality-engineer",
            corrected_label="scratch",
            corrected_prediction={"class": "scratch", "boxes": []},
            review_comment="Corrected after checking the source image",
        ),
    )

    assert feedback.corrected_label == "scratch"
    assert db_session.get(FeedbackSample, feedback.id) is not None
    corrected_review = db_session.get(ReviewTask, review_id)
    assert corrected_review is not None
    assert corrected_review.review_status == "corrected"
    assert corrected_review.reviewed_at is not None
    assert corrected_review.reviewed_at.tzinfo is UTC

    db_session.rollback()
    with pytest.raises(AppError) as exc_info:
        ReviewService(db_session).correct(
            review_id,
            ReviewCorrection(
                reviewer="another-reviewer",
                corrected_label="normal",
                corrected_prediction={"class": "normal"},
            ),
        )
    assert exc_info.value.code == "REVIEW_STATE_CONFLICT"
    assert db_session.scalar(select(func.count()).select_from(FeedbackSample)) == 1


def test_model_activation_is_exclusive_per_model_type(db_session: Session) -> None:
    service = ModelService(db_session)
    first = service.register(
        ModelVersionCreate(
            model_name="steel-detector",
            model_type="detection",
            version="1.0.0",
            framework="onnx",
            model_path="models/detector-1.onnx",
            metrics={"status": "not_evaluated"},
            input_size=[640, 640],
        ),
        operator="admin",
    )
    service.activate(first.id, "admin")
    second = service.register(
        ModelVersionCreate(
            model_name="steel-detector",
            model_type="detection",
            version="1.1.0",
            framework="onnx",
            model_path="models/detector-2.onnx",
            metrics={"status": "not_evaluated"},
            input_size=[640, 640],
        ),
        operator="admin",
    )
    service.activate(second.id, "admin")

    db_session.refresh(first)
    db_session.refresh(second)
    assert first.active is False
    assert second.active is True
    active_count = db_session.scalar(
        select(func.count()).select_from(ModelVersion).where(ModelVersion.active.is_(True))
    )
    assert active_count == 1


def test_failed_service_operation_rolls_back_audit(db_session: Session) -> None:
    with pytest.raises(AppError):
        ReviewService(db_session).correct(
            "00000000-0000-0000-0000-000000000000",
            ReviewCorrection(
                reviewer="tester",
                corrected_label="normal",
                corrected_prediction={"class": "normal"},
            ),
        )

    assert db_session.scalar(select(func.count()).select_from(AuditLog)) == 0
    assert db_session.scalar(select(func.count()).select_from(Inspection)) == 0

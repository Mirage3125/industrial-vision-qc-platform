from sqlalchemy.orm import Session

from backend.app.core.errors import AppError
from backend.app.db.base import utc_now
from backend.app.models.domain import (
    DataQualityReport,
    DatasetVersion,
    FeedbackSample,
    Inspection,
    ModelVersion,
    ReviewTask,
)
from backend.app.repositories import (
    AuditRepository,
    DataQualityReportRepository,
    DatasetVersionRepository,
    FeedbackRepository,
    InspectionRepository,
    ModelVersionRepository,
    ReviewTaskRepository,
)
from backend.app.schemas.domain import (
    DataQualityReportCreate,
    DatasetVersionCreate,
    InspectionCreate,
    ModelVersionCreate,
    ReviewCorrection,
)


class InspectionService:
    def __init__(self, session: Session) -> None:
        self.session = session

    def create(
        self, data: InspectionCreate, operator: str, request_id: str | None = None
    ) -> Inspection:
        values = data.model_dump(exclude={"requires_review", "review_reason"})
        with self.session.begin():
            inspection = InspectionRepository(self.session).add(Inspection(**values))
            AuditRepository(self.session).record(
                "inspection.created",
                "inspection",
                inspection.id,
                operator,
                {"status": inspection.status, "source": inspection.source},
                request_id,
            )
            if data.requires_review:
                prediction = {
                    "class": data.predicted_class,
                    "confidence": data.confidence,
                    "bounding_boxes": data.bounding_boxes,
                    "reason": data.review_reason,
                }
                review = ReviewTaskRepository(self.session).add(
                    ReviewTask(inspection_id=inspection.id, original_prediction=prediction)
                )
                AuditRepository(self.session).record(
                    "review.created",
                    "review_task",
                    review.id,
                    operator,
                    {"inspection_id": inspection.id, "reason": data.review_reason},
                    request_id,
                )
        return inspection


class ReviewService:
    def __init__(self, session: Session) -> None:
        self.session = session

    def correct(self, review_id: str, data: ReviewCorrection) -> FeedbackSample:
        with self.session.begin():
            review = ReviewTaskRepository(self.session).get(review_id)
            if review is None:
                raise AppError("REVIEW_NOT_FOUND", "Review task was not found", 404)
            if review.review_status != "pending":
                raise AppError("REVIEW_STATE_CONFLICT", "Review task is already finalized", 409)
            inspection = InspectionRepository(self.session).get(review.inspection_id)
            if inspection is None:
                raise AppError("INSPECTION_NOT_FOUND", "Inspection was not found", 404)

            review.corrected_prediction = data.corrected_prediction
            review.review_status = "corrected"
            review.reviewer = data.reviewer
            review.review_comment = data.review_comment
            review.reviewed_at = utc_now()
            feedback = FeedbackRepository(self.session).add(
                FeedbackSample(
                    inspection_id=inspection.id,
                    review_task_id=review.id,
                    image_path=inspection.image_path,
                    original_label=inspection.predicted_class,
                    corrected_label=data.corrected_label,
                    corrected_annotation=data.corrected_prediction,
                )
            )
            AuditRepository(self.session).record(
                "review.corrected",
                "review_task",
                review.id,
                data.reviewer,
                {"inspection_id": inspection.id, "feedback_sample_id": feedback.id},
                data.request_id,
            )
        return feedback


class DatasetService:
    def __init__(self, session: Session) -> None:
        self.session = session

    def create_version(
        self, data: DatasetVersionCreate, operator: str, request_id: str | None = None
    ) -> DatasetVersion:
        with self.session.begin():
            repository = DatasetVersionRepository(self.session)
            if repository.get_by_version(data.version) is not None:
                raise AppError("DATASET_VERSION_EXISTS", "Dataset version already exists", 409)
            version = repository.add(DatasetVersion(**data.model_dump()))
            AuditRepository(self.session).record(
                "dataset_version.created",
                "dataset_version",
                version.id,
                operator,
                {"version": version.version, "sample_count": version.sample_count},
                request_id,
            )
        return version


class DataQualityService:
    def __init__(self, session: Session) -> None:
        self.session = session

    def save_report(
        self, data: DataQualityReportCreate, operator: str, request_id: str | None = None
    ) -> DataQualityReport:
        with self.session.begin():
            report = DataQualityReportRepository(self.session).add(
                DataQualityReport(**data.model_dump())
            )
            AuditRepository(self.session).record(
                "data_quality_report.created",
                "data_quality_report",
                report.id,
                operator,
                {"dataset_path": report.dataset_path, "total_images": report.total_images},
                request_id,
            )
        return report


class ModelService:
    def __init__(self, session: Session) -> None:
        self.session = session

    def register(
        self, data: ModelVersionCreate, operator: str, request_id: str | None = None
    ) -> ModelVersion:
        with self.session.begin():
            repository = ModelVersionRepository(self.session)
            if repository.get_by_name_version(data.model_name, data.version) is not None:
                raise AppError("MODEL_VERSION_EXISTS", "Model version already exists", 409)
            model = repository.add(ModelVersion(**data.model_dump()))
            AuditRepository(self.session).record(
                "model.registered",
                "model_version",
                model.id,
                operator,
                {"model_name": model.model_name, "version": model.version},
                request_id,
            )
        return model

    def activate(self, model_id: str, operator: str, request_id: str | None = None) -> ModelVersion:
        with self.session.begin():
            repository = ModelVersionRepository(self.session)
            model = repository.get(model_id)
            if model is None:
                raise AppError("MODEL_NOT_FOUND", "Model version was not found", 404)
            repository.deactivate_type(model.model_type)
            model.active = True
            AuditRepository(self.session).record(
                "model.activated",
                "model_version",
                model.id,
                operator,
                {"model_type": model.model_type, "version": model.version},
                request_id,
            )
        return model

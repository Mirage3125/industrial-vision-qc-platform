from collections.abc import Sequence
from typing import Any, Generic, TypeVar

from sqlalchemy import select, update
from sqlalchemy.orm import Session

from backend.app.db.base import Base, utc_now
from backend.app.models.domain import (
    AuditLog,
    DataQualityReport,
    DatasetVersion,
    FeedbackSample,
    Inspection,
    ModelVersion,
    ReviewTask,
)

ModelT = TypeVar("ModelT", bound=Base)


class Repository(Generic[ModelT]):
    """Small typed repository for shared persistence operations."""

    def __init__(self, session: Session, model: type[ModelT]) -> None:
        self.session = session
        self.model = model

    def add(self, entity: ModelT) -> ModelT:
        self.session.add(entity)
        self.session.flush()
        return entity

    def get(self, entity_id: str) -> ModelT | None:
        return self.session.get(self.model, entity_id)

    def list(self, limit: int = 100, offset: int = 0) -> Sequence[ModelT]:
        statement = select(self.model).offset(offset).limit(limit)
        return self.session.scalars(statement).all()


class InspectionRepository(Repository[Inspection]):
    def __init__(self, session: Session) -> None:
        super().__init__(session, Inspection)


class ReviewTaskRepository(Repository[ReviewTask]):
    def __init__(self, session: Session) -> None:
        super().__init__(session, ReviewTask)


class FeedbackRepository(Repository[FeedbackSample]):
    def __init__(self, session: Session) -> None:
        super().__init__(session, FeedbackSample)


class DataQualityReportRepository(Repository[DataQualityReport]):
    def __init__(self, session: Session) -> None:
        super().__init__(session, DataQualityReport)


class DatasetVersionRepository(Repository[DatasetVersion]):
    def __init__(self, session: Session) -> None:
        super().__init__(session, DatasetVersion)

    def get_by_version(self, version: str) -> DatasetVersion | None:
        return self.session.scalar(select(DatasetVersion).where(DatasetVersion.version == version))


class ModelVersionRepository(Repository[ModelVersion]):
    def __init__(self, session: Session) -> None:
        super().__init__(session, ModelVersion)

    def get_by_name_version(self, name: str, version: str) -> ModelVersion | None:
        return self.session.scalar(
            select(ModelVersion).where(
                ModelVersion.model_name == name,
                ModelVersion.version == version,
            )
        )

    def deactivate_type(self, model_type: str) -> None:
        self.session.execute(
            update(ModelVersion)
            .where(ModelVersion.model_type == model_type, ModelVersion.active.is_(True))
            .values(active=False, updated_at=utc_now())
        )


class AuditRepository(Repository[AuditLog]):
    def __init__(self, session: Session) -> None:
        super().__init__(session, AuditLog)

    def record(
        self,
        action: str,
        entity_type: str,
        entity_id: str,
        operator: str,
        details: dict[str, Any] | None = None,
        request_id: str | None = None,
    ) -> AuditLog:
        return self.add(
            AuditLog(
                action=action,
                entity_type=entity_type,
                entity_id=entity_id,
                operator=operator,
                details=details or {},
                request_id=request_id,
                created_at=utc_now(),
            )
        )

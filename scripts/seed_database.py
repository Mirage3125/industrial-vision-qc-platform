"""Insert clearly marked, idempotent development seed records."""

from sqlalchemy import select

from backend.app.db.session import SessionLocal
from backend.app.models.domain import DatasetVersion, Inspection, ModelVersion
from backend.app.schemas.domain import DatasetVersionCreate, InspectionCreate, ModelVersionCreate
from backend.app.services import DatasetService, InspectionService, ModelService


def seed() -> None:
    with SessionLocal() as session:
        dataset_exists = session.scalar(
            select(DatasetVersion.id).where(DatasetVersion.version == "demo-seed-v1")
        )
        session.rollback()
        if dataset_exists is None:
            DatasetService(session).create_version(
                DatasetVersionCreate(
                    version="demo-seed-v1",
                    sample_count=0,
                    class_distribution={},
                    source_description="Development seed only; not a trained dataset",
                ),
                operator="seed-script",
            )

    with SessionLocal() as session:
        model_exists = session.scalar(
            select(ModelVersion.id).where(
                ModelVersion.model_name == "demo-placeholder",
                ModelVersion.version == "0.0.0-seed",
            )
        )
        session.rollback()
        if model_exists is None:
            ModelService(session).register(
                ModelVersionCreate(
                    model_name="demo-placeholder",
                    model_type="detection",
                    version="0.0.0-seed",
                    framework="none",
                    model_path="models/README-no-model-installed",
                    metrics={"status": "not_evaluated"},
                    input_size=[],
                ),
                operator="seed-script",
            )

    with SessionLocal() as session:
        inspection_exists = session.scalar(
            select(Inspection.id).where(Inspection.source == "demo-seed")
        )
        session.rollback()
        if inspection_exists is None:
            InspectionService(session).create(
                InspectionCreate(
                    image_path="data/samples/not-installed.jpg",
                    source="demo-seed",
                    prediction_type="seed",
                    status="seed_only",
                    requires_review=True,
                    review_reason="Seed record for workflow verification",
                ),
                operator="seed-script",
            )


if __name__ == "__main__":
    seed()
    print("Development seed data is ready.")

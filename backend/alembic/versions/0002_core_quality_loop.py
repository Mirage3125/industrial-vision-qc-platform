"""Create the core quality-loop tables.

Revision ID: 0002
Revises: 0001
"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

from backend.app.db.base import UTCDateTime

revision: str = "0002"
down_revision: str | None = "0001"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def _identity_and_timestamps() -> list[sa.Column]:
    return [
        sa.Column("id", sa.String(36), primary_key=True),
        sa.Column("created_at", UTCDateTime(), nullable=False),
        sa.Column("updated_at", UTCDateTime(), nullable=False),
    ]


def upgrade() -> None:
    op.create_table(
        "dataset_versions",
        *_identity_and_timestamps(),
        sa.Column("version", sa.String(100), nullable=False),
        sa.Column("sample_count", sa.Integer(), nullable=False),
        sa.Column("class_distribution", sa.JSON(), nullable=False),
        sa.Column("source_description", sa.Text(), nullable=False),
        sa.Column("parent_version_id", sa.String(36), nullable=True),
        sa.ForeignKeyConstraint(
            ["parent_version_id"], ["dataset_versions.id"], ondelete="SET NULL"
        ),
        sa.UniqueConstraint("version", name="uq_dataset_versions_version"),
    )
    op.create_table(
        "model_versions",
        *_identity_and_timestamps(),
        sa.Column("model_name", sa.String(200), nullable=False),
        sa.Column("model_type", sa.String(50), nullable=False),
        sa.Column("version", sa.String(100), nullable=False),
        sa.Column("framework", sa.String(50), nullable=False),
        sa.Column("model_path", sa.String(1024), nullable=False),
        sa.Column("metrics", sa.JSON(), nullable=False),
        sa.Column("input_size", sa.JSON(), nullable=False),
        sa.Column("precision", sa.String(20), nullable=False),
        sa.Column("active", sa.Boolean(), nullable=False),
        sa.Column("dataset_version_id", sa.String(36), nullable=True),
        sa.ForeignKeyConstraint(
            ["dataset_version_id"], ["dataset_versions.id"], ondelete="SET NULL"
        ),
        sa.UniqueConstraint("model_name", "version", name="uq_model_versions_model_name"),
    )
    op.create_index("ix_model_versions_model_type", "model_versions", ["model_type"])
    op.create_index("ix_model_versions_type_active", "model_versions", ["model_type", "active"])
    op.create_table(
        "inspections",
        *_identity_and_timestamps(),
        sa.Column("image_path", sa.String(1024), nullable=False),
        sa.Column("source", sa.String(100), nullable=False),
        sa.Column("model_version_id", sa.String(36), nullable=True),
        sa.Column("prediction_type", sa.String(30), nullable=False),
        sa.Column("predicted_class", sa.String(100), nullable=True),
        sa.Column("confidence", sa.Float(), nullable=True),
        sa.Column("bounding_boxes", sa.JSON(), nullable=False),
        sa.Column("anomaly_score", sa.Float(), nullable=True),
        sa.Column("processing_time_ms", sa.Float(), nullable=True),
        sa.Column("status", sa.String(30), nullable=False),
        sa.ForeignKeyConstraint(["model_version_id"], ["model_versions.id"], ondelete="SET NULL"),
    )
    for name in ("source", "model_version_id", "predicted_class", "status"):
        op.create_index(f"ix_inspections_{name}", "inspections", [name])
    op.create_table(
        "review_tasks",
        *_identity_and_timestamps(),
        sa.Column("inspection_id", sa.String(36), nullable=False),
        sa.Column("original_prediction", sa.JSON(), nullable=False),
        sa.Column("corrected_prediction", sa.JSON(), nullable=True),
        sa.Column("review_status", sa.String(30), nullable=False),
        sa.Column("reviewer", sa.String(100), nullable=True),
        sa.Column("review_comment", sa.Text(), nullable=True),
        sa.Column("reviewed_at", UTCDateTime(), nullable=True),
        sa.ForeignKeyConstraint(["inspection_id"], ["inspections.id"], ondelete="CASCADE"),
    )
    op.create_index("ix_review_tasks_inspection_id", "review_tasks", ["inspection_id"])
    op.create_index("ix_review_tasks_review_status", "review_tasks", ["review_status"])
    op.create_table(
        "feedback_samples",
        *_identity_and_timestamps(),
        sa.Column("inspection_id", sa.String(36), nullable=False),
        sa.Column("review_task_id", sa.String(36), nullable=False),
        sa.Column("image_path", sa.String(1024), nullable=False),
        sa.Column("original_label", sa.String(100), nullable=True),
        sa.Column("corrected_label", sa.String(100), nullable=False),
        sa.Column("corrected_annotation", sa.JSON(), nullable=False),
        sa.Column("export_status", sa.String(30), nullable=False),
        sa.Column("dataset_version_id", sa.String(36), nullable=True),
        sa.ForeignKeyConstraint(["inspection_id"], ["inspections.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["review_task_id"], ["review_tasks.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(
            ["dataset_version_id"], ["dataset_versions.id"], ondelete="SET NULL"
        ),
        sa.UniqueConstraint("review_task_id", name="uq_feedback_samples_review_task_id"),
    )
    for name in ("inspection_id", "corrected_label", "export_status", "dataset_version_id"):
        op.create_index(f"ix_feedback_samples_{name}", "feedback_samples", [name])
    op.create_table(
        "data_quality_reports",
        *_identity_and_timestamps(),
        sa.Column("dataset_path", sa.String(1024), nullable=False),
        sa.Column("total_images", sa.Integer(), nullable=False),
        sa.Column("duplicate_count", sa.Integer(), nullable=False),
        sa.Column("blurry_count", sa.Integer(), nullable=False),
        sa.Column("overexposed_count", sa.Integer(), nullable=False),
        sa.Column("underexposed_count", sa.Integer(), nullable=False),
        sa.Column("invalid_annotation_count", sa.Integer(), nullable=False),
        sa.Column("leakage_count", sa.Integer(), nullable=False),
        sa.Column("image_size_statistics", sa.JSON(), nullable=False),
        sa.Column("class_distribution", sa.JSON(), nullable=False),
        sa.Column("issue_samples", sa.JSON(), nullable=False),
        sa.Column("report_path", sa.String(1024), nullable=True),
    )
    op.create_index(
        "ix_data_quality_reports_dataset_path", "data_quality_reports", ["dataset_path"]
    )
    op.create_table(
        "audit_logs",
        sa.Column("id", sa.String(36), primary_key=True),
        sa.Column("action", sa.String(100), nullable=False),
        sa.Column("entity_type", sa.String(100), nullable=False),
        sa.Column("entity_id", sa.String(36), nullable=False),
        sa.Column("operator", sa.String(100), nullable=False),
        sa.Column("details", sa.JSON(), nullable=False),
        sa.Column("request_id", sa.String(100), nullable=True),
        sa.Column("created_at", UTCDateTime(), nullable=False),
    )
    for name in ("action", "entity_type", "entity_id", "request_id"):
        op.create_index(f"ix_audit_logs_{name}", "audit_logs", [name])


def downgrade() -> None:
    for table in (
        "audit_logs",
        "data_quality_reports",
        "feedback_samples",
        "review_tasks",
        "inspections",
        "model_versions",
        "dataset_versions",
    ):
        op.drop_table(table)

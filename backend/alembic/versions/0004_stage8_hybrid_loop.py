"""stage8 hybrid inference review feedback loop

Revision ID: 0004
Revises: 0003
Create Date: 2026-07-13 11:30:00.000000
"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

revision: str = "0004"
down_revision: str | None = "0003"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def _json_column(name: str, default: str) -> sa.Column[str]:
    return sa.Column(name, sa.JSON(), nullable=False, server_default=default)


def upgrade() -> None:
    op.add_column("inspections", sa.Column("station_id", sa.String(length=100), nullable=True))
    op.add_column("inspections", sa.Column("batch_id", sa.String(length=100), nullable=True))
    op.add_column("inspections", sa.Column("idempotency_key", sa.String(length=200), nullable=True))
    op.add_column("inspections", sa.Column("final_status", sa.String(length=50), nullable=True))
    op.add_column("inspections", _json_column("review_reasons", "[]"))
    op.add_column(
        "inspections", sa.Column("decision_rule_version", sa.String(length=100), nullable=True)
    )
    op.add_column("inspections", _json_column("quality_result", "{}"))
    op.add_column("inspections", _json_column("yolo_result", "{}"))
    op.add_column("inspections", _json_column("anomaly_result", "{}"))
    op.add_column("inspections", _json_column("system_decision", "{}"))
    op.add_column("inspections", _json_column("step_timings", "{}"))
    op.add_column("inspections", _json_column("model_versions", "{}"))
    op.create_index("ix_inspections_station_id", "inspections", ["station_id"])
    op.create_index("ix_inspections_batch_id", "inspections", ["batch_id"])
    op.create_index(
        "uq_inspections_idempotency_key", "inspections", ["idempotency_key"], unique=True
    )

    op.add_column("review_tasks", _json_column("system_decision", "{}"))

    op.add_column("feedback_samples", _json_column("original_boxes", "[]"))
    op.add_column("feedback_samples", _json_column("corrected_boxes", "[]"))
    op.add_column(
        "feedback_samples",
        sa.Column(
            "feedback_type",
            sa.String(length=50),
            nullable=False,
            server_default="correction",
        ),
    )
    op.add_column(
        "feedback_samples",
        sa.Column("source_model_version", sa.String(length=100), nullable=True),
    )


def downgrade() -> None:
    op.drop_column("feedback_samples", "source_model_version")
    op.drop_column("feedback_samples", "feedback_type")
    op.drop_column("feedback_samples", "corrected_boxes")
    op.drop_column("feedback_samples", "original_boxes")
    op.drop_column("review_tasks", "system_decision")
    op.drop_index("uq_inspections_idempotency_key", table_name="inspections")
    op.drop_index("ix_inspections_batch_id", table_name="inspections")
    op.drop_index("ix_inspections_station_id", table_name="inspections")
    for column in (
        "model_versions",
        "step_timings",
        "system_decision",
        "anomaly_result",
        "yolo_result",
        "quality_result",
        "decision_rule_version",
        "review_reasons",
        "final_status",
        "idempotency_key",
        "batch_id",
        "station_id",
    ):
        op.drop_column("inspections", column)

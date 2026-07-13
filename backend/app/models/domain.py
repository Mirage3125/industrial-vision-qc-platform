from datetime import datetime
from typing import Any

from sqlalchemy import (
    JSON,
    Boolean,
    Float,
    ForeignKey,
    Index,
    Integer,
    String,
    Text,
    UniqueConstraint,
)
from sqlalchemy.orm import Mapped, mapped_column, relationship

from backend.app.db.base import Base, TimestampMixin, UTCDateTime, UUIDPrimaryKeyMixin


class Inspection(UUIDPrimaryKeyMixin, TimestampMixin, Base):
    __tablename__ = "inspections"

    image_path: Mapped[str] = mapped_column(String(1024), nullable=False)
    source: Mapped[str] = mapped_column(String(100), nullable=False, index=True)
    station_id: Mapped[str | None] = mapped_column(String(100), nullable=True, index=True)
    batch_id: Mapped[str | None] = mapped_column(String(100), nullable=True, index=True)
    idempotency_key: Mapped[str | None] = mapped_column(String(200), nullable=True, unique=True)
    model_version_id: Mapped[str | None] = mapped_column(
        ForeignKey("model_versions.id", ondelete="SET NULL"), nullable=True, index=True
    )
    prediction_type: Mapped[str] = mapped_column(String(30), nullable=False)
    predicted_class: Mapped[str | None] = mapped_column(String(100), nullable=True, index=True)
    confidence: Mapped[float | None] = mapped_column(Float, nullable=True)
    bounding_boxes: Mapped[list[dict[str, Any]]] = mapped_column(JSON, default=list, nullable=False)
    anomaly_score: Mapped[float | None] = mapped_column(Float, nullable=True)
    processing_time_ms: Mapped[float | None] = mapped_column(Float, nullable=True)
    status: Mapped[str] = mapped_column(String(30), default="completed", nullable=False, index=True)
    final_status: Mapped[str | None] = mapped_column(String(50), nullable=True, index=True)
    review_reasons: Mapped[list[str]] = mapped_column(JSON, default=list, nullable=False)
    decision_rule_version: Mapped[str | None] = mapped_column(String(100), nullable=True)
    quality_result: Mapped[dict[str, Any]] = mapped_column(JSON, default=dict, nullable=False)
    yolo_result: Mapped[dict[str, Any]] = mapped_column(JSON, default=dict, nullable=False)
    anomaly_result: Mapped[dict[str, Any]] = mapped_column(JSON, default=dict, nullable=False)
    system_decision: Mapped[dict[str, Any]] = mapped_column(JSON, default=dict, nullable=False)
    step_timings: Mapped[dict[str, float]] = mapped_column(JSON, default=dict, nullable=False)
    model_versions: Mapped[dict[str, str | None]] = mapped_column(
        JSON, default=dict, nullable=False
    )

    model_version: Mapped["ModelVersion | None"] = relationship(back_populates="inspections")
    review_tasks: Mapped[list["ReviewTask"]] = relationship(back_populates="inspection")


class ReviewTask(UUIDPrimaryKeyMixin, TimestampMixin, Base):
    __tablename__ = "review_tasks"

    inspection_id: Mapped[str] = mapped_column(
        ForeignKey("inspections.id", ondelete="CASCADE"), nullable=False, index=True
    )
    original_prediction: Mapped[dict[str, Any]] = mapped_column(JSON, nullable=False)
    corrected_prediction: Mapped[dict[str, Any] | None] = mapped_column(JSON, nullable=True)
    system_decision: Mapped[dict[str, Any]] = mapped_column(JSON, default=dict, nullable=False)
    review_status: Mapped[str] = mapped_column(
        String(30), default="pending", nullable=False, index=True
    )
    reviewer: Mapped[str | None] = mapped_column(String(100), nullable=True)
    review_comment: Mapped[str | None] = mapped_column(Text, nullable=True)
    reviewed_at: Mapped[datetime | None] = mapped_column(UTCDateTime(), nullable=True)

    inspection: Mapped[Inspection] = relationship(back_populates="review_tasks")
    feedback_samples: Mapped[list["FeedbackSample"]] = relationship(back_populates="review_task")


class FeedbackSample(UUIDPrimaryKeyMixin, TimestampMixin, Base):
    __tablename__ = "feedback_samples"

    inspection_id: Mapped[str] = mapped_column(
        ForeignKey("inspections.id", ondelete="CASCADE"), nullable=False, index=True
    )
    review_task_id: Mapped[str] = mapped_column(
        ForeignKey("review_tasks.id", ondelete="CASCADE"), nullable=False, unique=True
    )
    image_path: Mapped[str] = mapped_column(String(1024), nullable=False)
    original_label: Mapped[str | None] = mapped_column(String(100), nullable=True)
    corrected_label: Mapped[str] = mapped_column(String(100), nullable=False, index=True)
    original_boxes: Mapped[list[dict[str, Any]]] = mapped_column(JSON, default=list, nullable=False)
    corrected_boxes: Mapped[list[dict[str, Any]]] = mapped_column(
        JSON, default=list, nullable=False
    )
    feedback_type: Mapped[str] = mapped_column(String(50), default="correction", nullable=False)
    source_model_version: Mapped[str | None] = mapped_column(String(100), nullable=True)
    corrected_annotation: Mapped[dict[str, Any]] = mapped_column(JSON, default=dict, nullable=False)
    export_status: Mapped[str] = mapped_column(
        String(30), default="pending", nullable=False, index=True
    )
    dataset_version_id: Mapped[str | None] = mapped_column(
        ForeignKey("dataset_versions.id", ondelete="SET NULL"), nullable=True, index=True
    )

    review_task: Mapped[ReviewTask] = relationship(back_populates="feedback_samples")
    dataset_version: Mapped["DatasetVersion | None"] = relationship(back_populates="samples")


class DatasetVersion(UUIDPrimaryKeyMixin, TimestampMixin, Base):
    __tablename__ = "dataset_versions"
    __table_args__ = (UniqueConstraint("version"),)

    version: Mapped[str] = mapped_column(String(100), nullable=False)
    sample_count: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    class_distribution: Mapped[dict[str, int]] = mapped_column(JSON, default=dict, nullable=False)
    source_description: Mapped[str] = mapped_column(Text, nullable=False)
    parent_version_id: Mapped[str | None] = mapped_column(
        ForeignKey("dataset_versions.id", ondelete="SET NULL"), nullable=True
    )

    samples: Mapped[list[FeedbackSample]] = relationship(back_populates="dataset_version")


class ModelVersion(UUIDPrimaryKeyMixin, TimestampMixin, Base):
    __tablename__ = "model_versions"
    __table_args__ = (
        UniqueConstraint("model_name", "version"),
        Index("ix_model_versions_type_active", "model_type", "active"),
    )

    model_name: Mapped[str] = mapped_column(String(200), nullable=False)
    model_type: Mapped[str] = mapped_column(String(50), nullable=False, index=True)
    version: Mapped[str] = mapped_column(String(100), nullable=False)
    framework: Mapped[str] = mapped_column(String(50), nullable=False)
    model_path: Mapped[str] = mapped_column(String(1024), nullable=False)
    metrics: Mapped[dict[str, Any]] = mapped_column(JSON, default=dict, nullable=False)
    input_size: Mapped[list[int]] = mapped_column(JSON, default=list, nullable=False)
    precision: Mapped[str] = mapped_column(String(20), default="fp32", nullable=False)
    active: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)
    dataset_version_id: Mapped[str | None] = mapped_column(
        ForeignKey("dataset_versions.id", ondelete="SET NULL"), nullable=True
    )

    inspections: Mapped[list[Inspection]] = relationship(back_populates="model_version")


class DataQualityReport(UUIDPrimaryKeyMixin, TimestampMixin, Base):
    __tablename__ = "data_quality_reports"

    dataset_path: Mapped[str] = mapped_column(String(1024), nullable=False, index=True)
    total_images: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    duplicate_count: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    blurry_count: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    overexposed_count: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    underexposed_count: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    invalid_annotation_count: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    leakage_count: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    image_size_statistics: Mapped[dict[str, Any]] = mapped_column(
        JSON, default=dict, nullable=False
    )
    class_distribution: Mapped[dict[str, int]] = mapped_column(JSON, default=dict, nullable=False)
    issue_samples: Mapped[list[dict[str, Any]]] = mapped_column(JSON, default=list, nullable=False)
    statistics: Mapped[dict[str, Any]] = mapped_column(JSON, default=dict, nullable=False)
    report_path: Mapped[str | None] = mapped_column(String(1024), nullable=True)


class AuditLog(UUIDPrimaryKeyMixin, Base):
    __tablename__ = "audit_logs"

    action: Mapped[str] = mapped_column(String(100), nullable=False, index=True)
    entity_type: Mapped[str] = mapped_column(String(100), nullable=False, index=True)
    entity_id: Mapped[str] = mapped_column(String(36), nullable=False, index=True)
    operator: Mapped[str] = mapped_column(String(100), nullable=False)
    details: Mapped[dict[str, Any]] = mapped_column(JSON, default=dict, nullable=False)
    request_id: Mapped[str | None] = mapped_column(String(100), nullable=True, index=True)
    created_at: Mapped[datetime] = mapped_column(UTCDateTime(), nullable=False)

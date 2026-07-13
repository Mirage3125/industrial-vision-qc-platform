from __future__ import annotations

from typing import Any, Literal

from pydantic import BaseModel, Field


class InspectionPredictRequest(BaseModel):
    image_path: str = Field(min_length=1, max_length=1024)
    inference_mode: Literal["classical", "detection", "anomaly", "hybrid"] = "hybrid"
    model_version: str | None = None
    station_id: str | None = Field(default=None, max_length=100)
    batch_id: str | None = Field(default=None, max_length=100)
    idempotency_key: str | None = Field(default=None, max_length=200)
    force_review: bool = False


class InspectionUploadPredictRequest(BaseModel):
    filename: str = Field(min_length=1, max_length=255)
    content_base64: str = Field(min_length=1)
    inference_mode: Literal["classical", "detection", "anomaly", "hybrid"] = "hybrid"
    model_version: str | None = None
    station_id: str | None = Field(default=None, max_length=100)
    batch_id: str | None = Field(default=None, max_length=100)
    idempotency_key: str | None = Field(default=None, max_length=200)
    force_review: bool = False


class ReviewActionRequest(BaseModel):
    reviewer: str = Field(min_length=1, max_length=100)
    review_comment: str | None = None
    corrected_label: str | None = None
    corrected_prediction: dict[str, Any] = Field(default_factory=dict)
    feedback_type: str = "correction"


class FeedbackExportRequest(BaseModel):
    dataset_version: str = Field(min_length=1, max_length=100)
    export_operator: str = Field(min_length=1, max_length=100)
    output_root: str = Field(default="data/processed/feedback-yolo", max_length=1024)
    source_dataset_version: str | None = None


class DatasetVersionManualRequest(BaseModel):
    version: str = Field(min_length=1, max_length=100)
    source_description: str = Field(min_length=1)
    sample_count: int = Field(default=0, ge=0)
    class_distribution: dict[str, int] = Field(default_factory=dict)


class ModelActivateRequest(BaseModel):
    operator: str = Field(default="system", min_length=1)

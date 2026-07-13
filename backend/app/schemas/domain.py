from typing import Any, Literal

from pydantic import AwareDatetime, BaseModel, ConfigDict, Field


class ORMResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)


class InspectionCreate(BaseModel):
    image_path: str = Field(min_length=1, max_length=1024)
    source: str = Field(min_length=1, max_length=100)
    model_version_id: str | None = None
    prediction_type: Literal["rule", "detection", "hybrid", "seed"]
    predicted_class: str | None = Field(default=None, max_length=100)
    confidence: float | None = Field(default=None, ge=0, le=1)
    bounding_boxes: list[dict[str, Any]] = Field(default_factory=list)
    anomaly_score: float | None = Field(default=None, ge=0)
    processing_time_ms: float | None = Field(default=None, ge=0)
    status: str = Field(default="completed", min_length=1, max_length=30)
    requires_review: bool = False
    review_reason: str | None = None


class InspectionResponse(ORMResponse):
    id: str
    image_path: str
    source: str
    model_version_id: str | None
    prediction_type: str
    predicted_class: str | None
    confidence: float | None
    bounding_boxes: list[dict[str, Any]]
    anomaly_score: float | None
    processing_time_ms: float | None
    status: str
    created_at: AwareDatetime
    updated_at: AwareDatetime


class ReviewCorrection(BaseModel):
    reviewer: str = Field(min_length=1, max_length=100)
    corrected_label: str = Field(min_length=1, max_length=100)
    corrected_prediction: dict[str, Any]
    review_comment: str | None = None
    request_id: str | None = None


class ReviewTaskResponse(ORMResponse):
    id: str
    inspection_id: str
    original_prediction: dict[str, Any]
    corrected_prediction: dict[str, Any] | None
    review_status: str
    reviewer: str | None
    review_comment: str | None
    reviewed_at: AwareDatetime | None
    created_at: AwareDatetime
    updated_at: AwareDatetime


class FeedbackSampleResponse(ORMResponse):
    id: str
    inspection_id: str
    review_task_id: str
    image_path: str
    original_label: str | None
    corrected_label: str
    corrected_annotation: dict[str, Any]
    export_status: str
    dataset_version_id: str | None
    created_at: AwareDatetime
    updated_at: AwareDatetime


class DatasetVersionCreate(BaseModel):
    version: str = Field(min_length=1, max_length=100)
    sample_count: int = Field(default=0, ge=0)
    class_distribution: dict[str, int] = Field(default_factory=dict)
    source_description: str = Field(min_length=1)
    parent_version_id: str | None = None


class DatasetVersionResponse(ORMResponse):
    id: str
    version: str
    sample_count: int
    class_distribution: dict[str, int]
    source_description: str
    parent_version_id: str | None
    created_at: AwareDatetime
    updated_at: AwareDatetime


class ModelVersionCreate(BaseModel):
    model_name: str = Field(min_length=1, max_length=200)
    model_type: str = Field(min_length=1, max_length=50)
    version: str = Field(min_length=1, max_length=100)
    framework: str = Field(min_length=1, max_length=50)
    model_path: str = Field(min_length=1, max_length=1024)
    metrics: dict[str, Any] = Field(default_factory=dict)
    input_size: list[int] = Field(default_factory=list)
    precision: str = Field(default="fp32", max_length=20)
    dataset_version_id: str | None = None


class ModelVersionResponse(ORMResponse):
    id: str
    model_name: str
    model_type: str
    version: str
    framework: str
    model_path: str
    metrics: dict[str, Any]
    input_size: list[int]
    precision: str
    active: bool
    dataset_version_id: str | None
    created_at: AwareDatetime
    updated_at: AwareDatetime


class DataQualityReportCreate(BaseModel):
    dataset_path: str = Field(min_length=1, max_length=1024)
    total_images: int = Field(ge=0)
    duplicate_count: int = Field(default=0, ge=0)
    blurry_count: int = Field(default=0, ge=0)
    overexposed_count: int = Field(default=0, ge=0)
    underexposed_count: int = Field(default=0, ge=0)
    invalid_annotation_count: int = Field(default=0, ge=0)
    leakage_count: int = Field(default=0, ge=0)
    image_size_statistics: dict[str, Any] = Field(default_factory=dict)
    class_distribution: dict[str, int] = Field(default_factory=dict)
    issue_samples: list[dict[str, Any]] = Field(default_factory=list)
    statistics: dict[str, Any] = Field(default_factory=dict)
    report_path: str | None = None


class DataQualityReportResponse(DataQualityReportCreate, ORMResponse):
    id: str
    created_at: AwareDatetime
    updated_at: AwareDatetime


class AuditLogResponse(ORMResponse):
    id: str
    action: str
    entity_type: str
    entity_id: str
    operator: str
    details: dict[str, Any]
    request_id: str | None
    created_at: AwareDatetime

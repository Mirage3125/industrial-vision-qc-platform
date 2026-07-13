from __future__ import annotations

from pathlib import Path

import yaml
from pydantic import BaseModel, Field


class HybridInspectionConfig(BaseModel):
    decision_rule_version: str = "stage8.hybrid.v1"
    yolo_confidence_threshold: float = Field(default=0.25, ge=0, le=1)
    yolo_low_confidence_threshold: float = Field(default=0.5, ge=0, le=1)
    anomaly_threshold: float = Field(default=8.35, ge=0)
    blur_variance_threshold: float = Field(default=30.0, ge=0)
    overexposed_gray_threshold: int = Field(default=245, ge=0, le=255)
    overexposed_ratio_threshold: float = Field(default=0.85, ge=0, le=1)
    underexposed_gray_threshold: int = Field(default=15, ge=0, le=255)
    underexposed_ratio_threshold: float = Field(default=0.85, ge=0, le=1)
    min_width: int = Field(default=64, ge=1)
    min_height: int = Field(default=64, ge=1)
    force_review: bool = False
    high_risk_classes: list[str] = Field(default_factory=list)
    detection_class_names: list[str] = Field(default_factory=list)
    default_yolo_model_path: Path
    default_anomaly_model_path: Path


def load_hybrid_config(
    path: Path = Path("configs/inspection/hybrid.yaml"),
) -> HybridInspectionConfig:
    return HybridInspectionConfig.model_validate(yaml.safe_load(path.read_text(encoding="utf-8")))

from __future__ import annotations

from typing import Any

from pydantic import BaseModel, Field


class AnomalyPrediction(BaseModel):
    image_path: str
    is_anomaly: bool
    anomaly_score: float
    threshold: float
    anomaly_map: list[list[float]] | None = None
    heatmap_path: str | None = None
    overlay_path: str | None = None
    predicted_mask_path: str | None = None
    processing_time_ms: float = Field(ge=0)
    model_version: str
    runtime_provider: str
    metadata: dict[str, Any] = Field(default_factory=dict)

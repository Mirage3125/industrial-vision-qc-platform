from __future__ import annotations

from pydantic import BaseModel, Field


class AnomalyPredictRequest(BaseModel):
    image_path: str = Field(min_length=1, max_length=1024)
    model_path: str = Field(min_length=1, max_length=1024)
    output_dir: str = Field(default="artifacts/anomaly_predictions", max_length=1024)
    include_map: bool = False


class AnomalyBatchRequest(BaseModel):
    image_paths: list[str] = Field(min_length=1, max_length=100)
    model_path: str = Field(min_length=1, max_length=1024)
    output_dir: str = Field(default="artifacts/anomaly_predictions", max_length=1024)

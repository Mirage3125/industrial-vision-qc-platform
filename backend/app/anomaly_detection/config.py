from __future__ import annotations

from pathlib import Path

import yaml
from pydantic import BaseModel, Field


class AnomalyConfig(BaseModel):
    algorithm: str = "padim_statistical"
    category: str = "metal_nut"
    image_size: int = Field(default=256, ge=64, le=1024)
    threshold_quantile: float = Field(default=0.995, gt=0, lt=1)
    mask_threshold_quantile: float = Field(default=0.995, gt=0, lt=1)
    gaussian_blur_kernel: int = Field(default=9, ge=1)
    min_component_area: int = Field(default=16, ge=1)
    seed: int = 42
    data_root: Path = Path("data/raw/mvtec-ad")
    artifact_dir: Path = Path("artifacts/training/anomaly/padim_statistical_metal_nut")
    model_path: Path = Path("artifacts/training/anomaly/padim_statistical_metal_nut/model.npz")
    evaluation_dir: Path = Path("artifacts/anomaly_evaluation/padim_statistical_metal_nut")


def load_anomaly_config(path: Path) -> AnomalyConfig:
    data = yaml.safe_load(path.read_text(encoding="utf-8")) or {}
    return AnomalyConfig(**data)

from pathlib import Path

import yaml
from pydantic import BaseModel, Field, field_validator


class DataQualityConfig(BaseModel):
    """Validated thresholds for deterministic dataset scanning."""

    image_extensions: list[str]
    class_names: list[str]
    blur_variance_threshold: float = Field(gt=0)
    overexposed_gray_threshold: int = Field(ge=0, le=255)
    overexposed_ratio_threshold: float = Field(gt=0, le=1)
    underexposed_gray_threshold: int = Field(ge=0, le=255)
    underexposed_ratio_threshold: float = Field(gt=0, le=1)
    perceptual_hash_hamming_threshold: int = Field(ge=0, le=64)
    tiny_box_min_width_px: float = Field(ge=0)
    tiny_box_min_height_px: float = Field(ge=0)
    tiny_box_min_area_px: float = Field(ge=0)
    thumbnail_width: int = Field(gt=0)
    thumbnail_height: int = Field(gt=0)
    max_issue_samples: int = Field(gt=0)

    @field_validator("image_extensions")
    @classmethod
    def normalize_extensions(cls, values: list[str]) -> list[str]:
        return [value.lower() if value.startswith(".") else f".{value.lower()}" for value in values]


def load_config(path: Path) -> DataQualityConfig:
    """Load thresholds from YAML and fail fast on invalid configuration."""

    with path.open("r", encoding="utf-8") as stream:
        raw = yaml.safe_load(stream)
    return DataQualityConfig.model_validate(raw)

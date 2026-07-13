from pathlib import Path
from typing import Literal

import yaml
from pydantic import BaseModel, Field, field_validator, model_validator


class ClassicalVisionConfig(BaseModel):
    grayscale: bool = True
    blur_method: Literal["none", "gaussian", "median"] = "gaussian"
    gaussian_kernel_size: int = 5
    gaussian_sigma: float = Field(default=0.0, ge=0)
    median_kernel_size: int = 5
    clahe_enabled: bool = True
    clahe_clip_limit: float = Field(default=2.0, gt=0)
    clahe_tile_grid_size: int = Field(default=8, gt=0)
    segmentation_method: Literal["otsu", "adaptive", "canny"] = "otsu"
    invert_binary: bool = True
    adaptive_block_size: int = 21
    adaptive_c: float = 5.0
    canny_low_threshold: int = Field(default=50, ge=0, le=255)
    canny_high_threshold: int = Field(default=150, ge=0, le=255)
    opening_enabled: bool = True
    opening_kernel_size: int = 3
    opening_iterations: int = Field(default=1, ge=1)
    closing_enabled: bool = True
    closing_kernel_size: int = 5
    closing_iterations: int = Field(default=1, ge=1)
    analysis_method: Literal["contours", "connected_components"] = "contours"
    min_area: float = Field(default=30.0, ge=0)
    max_area: float = Field(default=1000000.0, gt=0)
    min_aspect_ratio: float = Field(default=0.05, ge=0)
    max_aspect_ratio: float = Field(default=20.0, gt=0)
    min_circularity: float = Field(default=0.0, ge=0, le=1)
    max_circularity: float = Field(default=1.0, ge=0, le=1)
    batch_extensions: list[str] = [".jpg", ".jpeg", ".png", ".bmp"]

    @field_validator(
        "gaussian_kernel_size",
        "median_kernel_size",
        "adaptive_block_size",
        "opening_kernel_size",
        "closing_kernel_size",
    )
    @classmethod
    def require_positive_odd_kernel(cls, value: int) -> int:
        if value <= 1 or value % 2 == 0:
            raise ValueError("kernel and block sizes must be odd integers greater than one")
        return value

    @field_validator("batch_extensions")
    @classmethod
    def normalize_extensions(cls, values: list[str]) -> list[str]:
        return [value.lower() if value.startswith(".") else f".{value.lower()}" for value in values]

    @model_validator(mode="after")
    def validate_ranges(self) -> "ClassicalVisionConfig":
        if self.max_area < self.min_area:
            raise ValueError("max_area must be greater than or equal to min_area")
        if self.max_aspect_ratio < self.min_aspect_ratio:
            raise ValueError("max_aspect_ratio must be greater than or equal to min_aspect_ratio")
        if self.max_circularity < self.min_circularity:
            raise ValueError("max_circularity must be greater than or equal to min_circularity")
        if self.canny_high_threshold <= self.canny_low_threshold:
            raise ValueError("canny_high_threshold must be greater than canny_low_threshold")
        return self


def load_classical_config(path: Path) -> ClassicalVisionConfig:
    with path.open("r", encoding="utf-8") as stream:
        return ClassicalVisionConfig.model_validate(yaml.safe_load(stream))

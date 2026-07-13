from pathlib import Path

import yaml
from pydantic import BaseModel, Field, field_validator


class DetectionDatasetConfig(BaseModel):
    dataset_name: str
    dataset_version: str
    dataset_root: Path
    class_names: list[str] = Field(min_length=1)
    seed: int = 42
    validation_ratio: float = Field(default=0.2, gt=0, lt=1)
    allowed_extensions: list[str]

    @field_validator("allowed_extensions")
    @classmethod
    def normalize_extensions(cls, values: list[str]) -> list[str]:
        return [value.lower() if value.startswith(".") else f".{value.lower()}" for value in values]


def load_detection_config(path: Path) -> DetectionDatasetConfig:
    with path.open("r", encoding="utf-8") as stream:
        return DetectionDatasetConfig.model_validate(yaml.safe_load(stream))


def load_yaml(path: Path) -> dict[str, object]:
    with path.open("r", encoding="utf-8") as stream:
        raw = yaml.safe_load(stream)
    if not isinstance(raw, dict):
        raise ValueError(f"YAML root must be a mapping: {path}")
    return raw

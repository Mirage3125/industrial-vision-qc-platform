from pathlib import Path

from pydantic import BaseModel, Field, field_validator


class YoloPredictRequest(BaseModel):
    image_path: str
    weights_path: str
    confidence: float = Field(default=0.25, ge=0, le=1)
    iou: float = Field(default=0.7, ge=0, le=1)
    device: str = "0"
    output_dir: str = "artifacts/detection/api"

    @field_validator("image_path")
    @classmethod
    def image_exists(cls, value: str) -> str:
        if not Path(value).is_file():
            raise ValueError("image_path does not exist")
        return value


class YoloBatchRequest(BaseModel):
    image_paths: list[str] = Field(min_length=1, max_length=200)
    weights_path: str
    confidence: float = Field(default=0.25, ge=0, le=1)
    iou: float = Field(default=0.7, ge=0, le=1)
    device: str = "0"
    output_dir: str = "artifacts/detection/api"

    @field_validator("image_paths")
    @classmethod
    def images_exist(cls, values: list[str]) -> list[str]:
        missing = [value for value in values if not Path(value).is_file()]
        if missing:
            raise ValueError(f"image paths do not exist: {missing[:3]}")
        return values

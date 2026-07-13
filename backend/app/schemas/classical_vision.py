from pathlib import Path

from pydantic import BaseModel, Field, field_validator

from backend.app.inference import InferenceResult


class ClassicalPredictRequest(BaseModel):
    image_path: str = Field(min_length=1)
    config_path: str = "configs/classical_vision/baseline.yaml"
    output_dir: str = "artifacts/classical_vision"

    @field_validator("image_path")
    @classmethod
    def image_must_exist(cls, value: str) -> str:
        if not Path(value).is_file():
            raise ValueError("image_path must point to an existing file")
        return value


class ClassicalBatchRequest(BaseModel):
    image_paths: list[str] = Field(min_length=1, max_length=500)
    config_path: str = "configs/classical_vision/baseline.yaml"
    output_dir: str = "artifacts/classical_vision"

    @field_validator("image_paths")
    @classmethod
    def images_must_exist(cls, values: list[str]) -> list[str]:
        missing = [value for value in values if not Path(value).is_file()]
        if missing:
            raise ValueError(f"image paths do not exist: {missing[:3]}")
        return values


class ClassicalPredictData(BaseModel):
    result: InferenceResult


class ClassicalBatchData(BaseModel):
    count: int
    results: list[InferenceResult]

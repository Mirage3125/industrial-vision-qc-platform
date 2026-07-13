from pathlib import Path
from typing import Any

import pytest
from fastapi.testclient import TestClient

from backend.app.detection import (
    DetectionDatasetConfig,
    YoloPyTorchDetector,
    convert_voc_directory,
    generate_voc_smoke_dataset,
    split_yolo_dataset,
    validate_yolo_dataset,
)


def _config(root: Path) -> DetectionDatasetConfig:
    return DetectionDatasetConfig(
        dataset_name="synthetic-smoke",
        dataset_version="test-only",
        dataset_root=root,
        class_names=["crazing", "inclusion"],
        seed=42,
        validation_ratio=0.25,
        allowed_extensions=[".jpg"],
    )


def test_voc_conversion_split_and_validation_smoke(tmp_path: Path) -> None:
    config = _config(tmp_path / "yolo")
    images, annotations = generate_voc_smoke_dataset(tmp_path / "voc", config.class_names)
    conversion = convert_voc_directory(images, annotations, tmp_path / "yolo" / "all", config)

    assert conversion.valid
    assert conversion.image_count == 8
    assert conversion.annotation_count == 8
    assert conversion.class_distribution == {"crazing": 4, "inclusion": 4}

    counts = split_yolo_dataset(tmp_path / "yolo" / "all", tmp_path / "yolo", 0.25, 42)
    assert counts == {"train": 6, "val": 2}
    validation = validate_yolo_dataset(tmp_path / "yolo", config)
    assert validation.valid
    assert validation.image_count == 8
    assert validation.annotation_count == 8
    assert not validation.leakage_pairs


def test_validator_detects_illegal_box_and_split_leakage(tmp_path: Path) -> None:
    config = _config(tmp_path)
    for split in ("train", "val"):
        (tmp_path / split / "images").mkdir(parents=True)
        (tmp_path / split / "labels").mkdir(parents=True)
    duplicate = b"same-image-content"
    (tmp_path / "train/images/a.jpg").write_bytes(duplicate)
    (tmp_path / "val/images/b.jpg").write_bytes(duplicate)
    (tmp_path / "train/labels/a.txt").write_text("0 0.5 0.5 1.2 0.2\n", encoding="utf-8")
    (tmp_path / "val/labels/b.txt").write_text("1 0.5 0.5 0.2 0.2\n", encoding="utf-8")

    result = validate_yolo_dataset(tmp_path, config)

    assert not result.valid
    assert any(error["code"] == "OUT_OF_BOUNDS_BOX" for error in result.errors)
    assert any(error["code"] == "SPLIT_LEAKAGE" for error in result.errors)


class _Scalar:
    def __init__(self, value: float) -> None:
        self.value = value

    def item(self) -> float:
        return self.value


class _Vector:
    def __init__(self, values: list[float]) -> None:
        self.values = values

    def tolist(self) -> list[float]:
        return self.values


class _Box:
    xyxy = [_Vector([10, 20, 50, 60])]
    cls = [_Scalar(1)]
    conf = [_Scalar(0.88)]


class _Result:
    names = {0: "crazing", 1: "inclusion"}
    boxes = [_Box()]
    orig_shape = (96, 128)


class _FakeModel:
    def predict(self, **_: Any) -> list[_Result]:
        return [_Result()]


def test_yolo_adapter_maps_provider_output_without_ultralytics(tmp_path: Path) -> None:
    image = tmp_path / "image.jpg"
    image.write_bytes(b"provider-does-not-read-in-fake-test")
    detector = YoloPyTorchDetector(Path("unused.pt"), device="cpu", model=_FakeModel())

    result = detector.predict(image)

    assert result.detector_type == "yolo_pytorch"
    assert result.defect_count == 1
    assert result.regions[0].class_name == "inclusion"
    assert result.regions[0].confidence == pytest.approx(0.88)
    assert result.regions[0].bounding_box.x2 == 50


def test_detection_api_reports_missing_model(client: TestClient, tmp_path: Path) -> None:
    image = tmp_path / "input.jpg"
    image.write_bytes(b"request-validation-only")
    response = client.post(
        "/api/v1/detection/predict",
        json={"image_path": str(image), "weights_path": str(tmp_path / "missing.pt")},
    )

    assert response.status_code == 503
    assert response.json()["error"]["code"] == "MODEL_NOT_READY"

from pathlib import Path

import cv2
import numpy as np
from fastapi.testclient import TestClient

from backend.app.classical_vision import ClassicalVisionConfig, ClassicalVisionDetector


def _write_test_image(path: Path) -> None:
    image = np.full((160, 200, 3), 220, dtype=np.uint8)
    cv2.rectangle(image, (30, 40), (90, 75), (20, 20, 20), thickness=-1)
    cv2.circle(image, (145, 110), 14, (25, 25, 25), thickness=-1)
    assert cv2.imwrite(str(path), image)


def _config(**overrides: object) -> ClassicalVisionConfig:
    values: dict[str, object] = {
        "blur_method": "none",
        "clahe_enabled": False,
        "segmentation_method": "otsu",
        "invert_binary": True,
        "opening_enabled": False,
        "closing_enabled": False,
        "analysis_method": "contours",
        "min_area": 100,
        "max_area": 5000,
    }
    values.update(overrides)
    return ClassicalVisionConfig.model_validate(values)


def test_contour_pipeline_detects_regions_and_writes_artifacts(tmp_path: Path) -> None:
    image_path = tmp_path / "defects.png"
    _write_test_image(image_path)
    detector = ClassicalVisionDetector(_config())

    result = detector.predict(image_path, tmp_path / "output")

    assert result.detector_type == "opencv_classical"
    assert result.defect_count == 2
    assert result.processing_time_ms >= 0
    assert all(region.area >= 100 for region in result.regions)
    assert all(0 <= region.circularity <= 1 for region in result.regions)
    assert Path(result.artifacts["binary_image"]).is_file()
    assert Path(result.artifacts["contour_image"]).is_file()
    assert Path(result.artifacts["json_result"]).is_file()


def test_connected_components_and_shape_filtering(tmp_path: Path) -> None:
    image_path = tmp_path / "components.png"
    _write_test_image(image_path)
    detector = ClassicalVisionDetector(
        _config(analysis_method="connected_components", min_aspect_ratio=1.2, max_aspect_ratio=2.0)
    )

    result = detector.predict(image_path)

    assert result.defect_count == 1
    assert result.regions[0].source == "connected_component"
    assert 1.2 <= result.regions[0].aspect_ratio <= 2.0


def test_all_segmentation_modes_produce_binary_images(tmp_path: Path) -> None:
    image_path = tmp_path / "modes.png"
    _write_test_image(image_path)
    image = cv2.imread(str(image_path))

    for method in ("otsu", "adaptive", "canny"):
        detector = ClassicalVisionDetector(_config(segmentation_method=method))
        binary = detector.segment(image)
        assert binary.dtype == np.uint8
        assert binary.shape == image.shape[:2]
        assert set(np.unique(binary)).issubset({0, 255})


def test_median_gaussian_clahe_and_morphology_paths(tmp_path: Path) -> None:
    image_path = tmp_path / "filters.png"
    _write_test_image(image_path)
    image = cv2.imread(str(image_path))

    for blur_method in ("gaussian", "median"):
        detector = ClassicalVisionDetector(
            _config(
                blur_method=blur_method,
                clahe_enabled=True,
                opening_enabled=True,
                closing_enabled=True,
            )
        )
        assert detector.segment(image).shape == image.shape[:2]


def test_batch_and_api_return_normalized_results(tmp_path: Path, client: TestClient) -> None:
    first = tmp_path / "first.png"
    second = tmp_path / "second.png"
    _write_test_image(first)
    _write_test_image(second)
    config_path = Path("configs/classical_vision/baseline.yaml").resolve()
    output_dir = tmp_path / "api-output"

    response = client.post(
        "/api/v1/classical-vision/batch",
        json={
            "image_paths": [str(first), str(second)],
            "config_path": str(config_path),
            "output_dir": str(output_dir),
        },
    )

    assert response.status_code == 200
    body = response.json()
    assert body["success"] is True
    assert body["data"]["count"] == 2
    assert all(item["detector_type"] == "opencv_classical" for item in body["data"]["results"])

    single_response = client.post(
        "/api/v1/classical-vision/predict",
        json={
            "image_path": str(first),
            "config_path": str(config_path),
            "output_dir": str(output_dir),
        },
    )
    assert single_response.status_code == 200
    assert single_response.json()["data"]["result"]["image_path"] == str(first.resolve())


def test_invalid_kernel_configuration_is_rejected() -> None:
    try:
        _config(gaussian_kernel_size=4)
    except ValueError as error:
        assert "odd integers" in str(error)
    else:
        raise AssertionError("Even kernel size must be rejected")

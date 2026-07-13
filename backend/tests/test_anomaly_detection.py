from __future__ import annotations

from pathlib import Path

import cv2
import numpy as np
from fastapi.testclient import TestClient

from backend.app.anomaly_detection.config import AnomalyConfig
from backend.app.anomaly_detection.dataset import build_manifest
from backend.app.anomaly_detection.evaluator import evaluate
from backend.app.anomaly_detection.predictor import PaDiMStyleAnomalyDetector
from backend.app.anomaly_detection.trainer import train_padim_statistical
from backend.app.main import create_app
from backend.app.models.domain import ModelVersion
from backend.app.repositories.core import AuditRepository, ModelVersionRepository


def _write_image(path: Path, value: int, defect: bool = False) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    image = np.full((64, 64, 3), value, dtype=np.uint8)
    if defect:
        image[20:36, 20:36] = 255
    cv2.imwrite(str(path), image)


def _dataset(root: Path) -> Path:
    category = root / "metal_nut"
    for index in range(4):
        _write_image(category / "train" / "good" / f"{index:03d}.png", 80 + index)
    _write_image(category / "test" / "good" / "000.png", 82)
    _write_image(category / "test" / "bent" / "000.png", 82, defect=True)
    mask = np.zeros((64, 64), dtype=np.uint8)
    mask[20:36, 20:36] = 255
    mask_path = category / "ground_truth" / "bent" / "000_mask.png"
    mask_path.parent.mkdir(parents=True, exist_ok=True)
    cv2.imwrite(str(mask_path), mask)
    return root


def test_anomaly_train_predict_evaluate(tmp_path: Path) -> None:
    data_root = _dataset(tmp_path / "mvtec-ad")
    config = AnomalyConfig(
        data_root=data_root,
        artifact_dir=tmp_path / "artifacts" / "train",
        model_path=tmp_path / "artifacts" / "train" / "model.npz",
        evaluation_dir=tmp_path / "artifacts" / "eval",
        image_size=64,
    )
    manifest = build_manifest(data_root, "metal_nut", "test", tmp_path / "manifest.json")
    assert manifest["train_good_count"] == 4

    metadata = train_padim_statistical(config)
    assert Path(str(metadata["model_path"])).is_file()

    detector = PaDiMStyleAnomalyDetector(config.model_path)
    result = detector.predict_anomaly(
        data_root / "metal_nut" / "test" / "bent" / "000.png", tmp_path / "predictions"
    )
    assert result.anomaly_score >= 0
    assert result.heatmap_path is not None and Path(result.heatmap_path).is_file()

    metrics = evaluate(config)
    assert metrics["sample_count"] == 2
    assert metrics["image_level_auroc"] is not None


def test_anomaly_api_model_not_loaded() -> None:
    client = TestClient(create_app())
    response = client.post(
        "/api/v1/anomaly/predict",
        json={"image_path": "missing.png", "model_path": "missing.npz"},
    )
    assert response.status_code == 400
    assert response.json()["error"]["code"] == "INVALID_IMAGE"


def test_anomaly_model_registration_repository(db_session) -> None:  # type: ignore[no-untyped-def]
    repo = ModelVersionRepository(db_session)
    model = repo.add(
        ModelVersion(
            model_name="padim_statistical_metal_nut",
            model_type="anomaly_detection",
            version="test",
            framework="opencv-numpy",
            model_path="model.npz",
            metrics={"image_level_auroc": 1.0},
            input_size=[64, 64],
            precision="fp32",
            active=True,
        )
    )
    AuditRepository(db_session).record(
        "register_anomaly_model", "model_versions", model.id, "test", {"version": "test"}
    )
    db_session.commit()
    assert repo.get_by_name_version("padim_statistical_metal_nut", "test") is not None

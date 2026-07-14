from __future__ import annotations

from pathlib import Path
from uuid import uuid4

import pytest
from fastapi.testclient import TestClient

from backend.app.db.base import Base
from backend.app.db.session import SessionLocal, engine
from backend.app.inspection.config import load_hybrid_config
from backend.app.inspection.decision import decide
from backend.app.main import create_app
from backend.app.models.domain import AuditLog, FeedbackSample, Inspection, ModelVersion, ReviewTask

YOLO_MODEL = "artifacts/training/neu_det_baseline/weights/best.onnx"
ANOMALY_MODEL = "artifacts/training/anomaly/padim_statistical_metal_nut/model.npz"
KNOWN_DEFECT_IMAGE = "data/processed/neu-det-yolo/images/test/scratches_13.jpg"
NORMALISH_IMAGE = "data/raw/mvtec-ad/metal_nut/test/good/000.png"


def _require_local_artifacts(*paths: str) -> None:
    missing = [path for path in paths if not Path(path).is_file()]
    if missing:
        pytest.skip(
            "Stage 8 integration test requires local model/data artifacts that are not "
            f"committed to Git: {missing}"
        )


def _reset_db() -> None:
    Base.metadata.drop_all(engine)
    Base.metadata.create_all(engine)


def _seed_models() -> tuple[str, str]:
    with SessionLocal() as session:
        yolo = ModelVersion(
            model_name="neu-det-yolo11n-onnx",
            model_type="detection",
            version=f"test-yolo-{uuid4()}",
            framework="onnxruntime",
            model_path=str(Path(YOLO_MODEL).resolve()),
            metrics={},
            input_size=[640, 640],
            precision="fp32",
            active=True,
        )
        anomaly = ModelVersion(
            model_name="padim_statistical_metal_nut",
            model_type="anomaly_detection",
            version=f"test-anomaly-{uuid4()}",
            framework="opencv-numpy",
            model_path=ANOMALY_MODEL,
            metrics={},
            input_size=[256, 256],
            precision="fp32",
            active=True,
        )
        session.add_all([yolo, anomaly])
        session.commit()
        return yolo.id, anomaly.id


def test_stage8_real_hybrid_review_feedback_export_and_idempotency(tmp_path: Path) -> None:
    _require_local_artifacts(YOLO_MODEL, ANOMALY_MODEL, KNOWN_DEFECT_IMAGE)
    _reset_db()
    _seed_models()
    client = TestClient(create_app())
    key = f"stage8-{uuid4()}"
    response = client.post(
        "/api/v1/inspection/predict",
        json={
            "image_path": KNOWN_DEFECT_IMAGE,
            "inference_mode": "hybrid",
            "idempotency_key": key,
            "station_id": "S1",
            "batch_id": "B1",
        },
    )
    assert response.status_code == 200
    payload = response.json()["data"]
    assert payload["inspection_id"]
    assert payload["review_id"]
    assert payload["model_versions"]["yolo"]
    assert payload["model_versions"]["anomaly"]

    duplicate = client.post(
        "/api/v1/inspection/predict",
        json={"image_path": KNOWN_DEFECT_IMAGE, "inference_mode": "hybrid", "idempotency_key": key},
    )
    assert duplicate.status_code == 200
    assert duplicate.json()["data"]["idempotent"] is True

    detail = client.get(f"/api/v1/reviews/{payload['review_id']}")
    assert detail.status_code == 200
    review_data = detail.json()["data"]
    assert review_data["original_prediction"]["yolo"]
    assert review_data["system_decision"]

    correction = {
        "reviewer": "qa",
        "review_comment": "box and class corrected",
        "corrected_label": "scratches",
        "feedback_type": "box_position_error",
        "corrected_prediction": {
            "label": "scratches",
            "boxes": [{"label": "scratches", "x1": 1, "y1": 1, "x2": 20, "y2": 20}],
        },
    }
    corrected = client.post(f"/api/v1/reviews/{payload['review_id']}/correct", json=correction)
    assert corrected.status_code == 200

    with SessionLocal() as session:
        inspection = session.get(Inspection, payload["inspection_id"])
        review = session.get(ReviewTask, payload["review_id"])
        feedback = session.query(FeedbackSample).one()
        assert inspection is not None
        assert review is not None
        assert review.original_prediction["yolo"]
        assert review.corrected_prediction is not None
        assert feedback.original_boxes
        assert session.query(AuditLog).count() >= 2

    version = f"feedback-{uuid4()}"
    exported = client.post(
        "/api/v1/feedback/export",
        json={
            "dataset_version": version,
            "export_operator": "qa",
            "output_root": str(tmp_path / "feedback-yolo"),
        },
    )
    assert exported.status_code == 200
    manifest = exported.json()["data"]["manifest"]
    assert manifest["added_sample_count"] == 1
    assert Path(tmp_path / "feedback-yolo" / version / "manifest.json").is_file()

    duplicate_export = client.post(
        "/api/v1/feedback/export",
        json={
            "dataset_version": version,
            "export_operator": "qa",
            "output_root": str(tmp_path / "feedback-yolo"),
        },
    )
    assert duplicate_export.status_code == 409


def test_stage8_review_approve_and_model_rollback() -> None:
    _require_local_artifacts(YOLO_MODEL, ANOMALY_MODEL, NORMALISH_IMAGE)
    _reset_db()
    anomaly_id = _seed_models()[1]
    client = TestClient(create_app())
    response = client.post(
        "/api/v1/inspection/predict",
        json={
            "image_path": NORMALISH_IMAGE,
            "inference_mode": "hybrid",
            "idempotency_key": f"stage8-{uuid4()}",
            "force_review": True,
        },
    )
    assert response.status_code == 200
    review_id = response.json()["data"]["review_id"]
    approved = client.post(
        f"/api/v1/reviews/{review_id}/approve",
        json={"reviewer": "qa", "review_comment": "approved original prediction"},
    )
    assert approved.status_code == 200
    rejected_again = client.post(
        f"/api/v1/reviews/{review_id}/reject",
        json={"reviewer": "qa", "review_comment": "late reject"},
    )
    assert rejected_again.status_code == 409

    models = client.get("/api/v1/models")
    assert models.status_code == 200
    rollback = client.post(f"/api/v1/models/{anomaly_id}/rollback", json={"operator": "qa"})
    assert rollback.status_code == 200


def test_stage8_decision_rules_cover_required_review_reasons() -> None:
    config = load_hybrid_config()
    blurry = decide(
        {"issues": ["BLURRY_IMAGE"]},
        {"regions": []},
        {"is_anomaly": False, "anomaly_score": 0},
        config,
    )
    assert blurry["requires_review"] is True
    assert "BLURRY_IMAGE" in blurry["review_reasons"]

    low_conf = decide(
        {"issues": []},
        {"regions": [{"class_name": "crazing", "confidence": 0.3}]},
        {"is_anomaly": False, "anomaly_score": 0},
        config,
    )
    assert "YOLO_LOW_CONFIDENCE" in low_conf["review_reasons"]

    conflict = decide(
        {"issues": []},
        {"regions": []},
        {"is_anomaly": True, "anomaly_score": 999},
        config,
    )
    assert "YOLO_NONE_ANOMALY_HIGH" in conflict["review_reasons"]

    failed = decide({"issues": []}, {"regions": []}, {}, config, inference_failed=True)
    assert failed["final_status"] == "INFERENCE_FAILED"

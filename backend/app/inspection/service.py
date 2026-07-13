from __future__ import annotations

import time
from pathlib import Path
from typing import Any, Literal

from sqlalchemy import select
from sqlalchemy.orm import Session

from backend.app.anomaly_detection.predictor import PaDiMStyleAnomalyDetector
from backend.app.db.base import utc_now
from backend.app.inference.onnx_runtime import OnnxYoloDetector
from backend.app.inspection.config import HybridInspectionConfig, load_hybrid_config
from backend.app.inspection.decision import decide
from backend.app.inspection.quality import inspect_image_quality
from backend.app.models.domain import AuditLog, FeedbackSample, Inspection, ModelVersion, ReviewTask

InferenceMode = Literal["classical", "detection", "anomaly", "hybrid"]


def _result_regions(result: Any) -> list[dict[str, Any]]:
    return [
        region.model_dump(mode="json") if hasattr(region, "model_dump") else dict(region)
        for region in getattr(result, "regions", [])
    ]


class InspectionPredictionService:
    def __init__(self, session: Session, config: HybridInspectionConfig | None = None) -> None:
        self.session = session
        self.config = config or load_hybrid_config()

    def predict(
        self,
        image_path: Path,
        inference_mode: InferenceMode,
        model_version: str | None,
        station_id: str | None,
        batch_id: str | None,
        idempotency_key: str | None,
        force_review: bool = False,
    ) -> dict[str, Any]:
        if idempotency_key:
            existing = self.session.scalar(
                select(Inspection).where(Inspection.idempotency_key == idempotency_key)
            )
            if existing is not None:
                return {"inspection": existing, "idempotent": True}

        started_total = time.perf_counter()
        timings: dict[str, float] = {}
        quality = inspect_image_quality(image_path, self.config)
        yolo_result: dict[str, Any] = {}
        anomaly_result: dict[str, Any] = {}
        inference_failed = False
        errors: list[str] = []
        yolo_model = self._select_model("detection", model_version)
        anomaly_model = self._select_model("anomaly_detection", None)

        if inference_mode in {"detection", "hybrid"}:
            step_started = time.perf_counter()
            try:
                yolo_path = Path(
                    yolo_model.model_path if yolo_model else self.config.default_yolo_model_path
                )
                yolo_detector = OnnxYoloDetector(
                    yolo_path,
                    self.config.detection_class_names,
                    provider="cpu",
                    confidence=self.config.yolo_confidence_threshold,
                )
                yolo_prediction = yolo_detector.predict(
                    image_path, Path("artifacts/inspection/yolo")
                )
                yolo_result = yolo_prediction.model_dump(mode="json")
            except Exception as error:
                inference_failed = True
                errors.append(f"YOLO_FAILED: {error}")
                yolo_result = {"error": str(error), "regions": []}
            timings["yolo_ms"] = round((time.perf_counter() - step_started) * 1000, 3)

        if inference_mode in {"anomaly", "hybrid"}:
            step_started = time.perf_counter()
            try:
                anomaly_detector = PaDiMStyleAnomalyDetector(
                    Path(
                        anomaly_model.model_path
                        if anomaly_model
                        else self.config.default_anomaly_model_path
                    )
                )
                anomaly_prediction = anomaly_detector.predict_anomaly(
                    image_path, Path("artifacts/inspection/anomaly"), include_map=False
                )
                anomaly_result = anomaly_prediction.model_dump(mode="json")
            except Exception as error:
                inference_failed = True
                errors.append(f"ANOMALY_FAILED: {error}")
                anomaly_result = {"error": str(error), "is_anomaly": False, "anomaly_score": 0}
            timings["anomaly_ms"] = round((time.perf_counter() - step_started) * 1000, 3)

        effective_config = self.config.model_copy(update={"force_review": force_review})
        if inference_mode == "detection":
            anomaly_for_decision: dict[str, Any] = {"is_anomaly": False, "anomaly_score": 0}
        else:
            anomaly_for_decision = anomaly_result
        decision = decide(
            quality, yolo_result, anomaly_for_decision, effective_config, inference_failed
        )
        if inference_mode == "anomaly" and not decision["requires_review"]:
            decision["final_status"] = "ANOMALY" if anomaly_result.get("is_anomaly") else "PASS"
        if inference_mode == "classical":
            decision["final_status"] = "REVIEW_REQUIRED"
            decision["requires_review"] = True
            decision["review_reasons"] = ["CLASSICAL_MODE_NOT_CONFIGURED_FOR_AUTO_PASS"]
        timings["total_ms"] = round((time.perf_counter() - started_total) * 1000, 3)
        original_prediction = {
            "quality": quality,
            "yolo": yolo_result,
            "anomaly": anomaly_result,
            "errors": errors,
        }
        inspection = Inspection(
            image_path=str(image_path),
            source="inspection_api",
            station_id=station_id,
            batch_id=batch_id,
            idempotency_key=idempotency_key,
            model_version_id=yolo_model.id if yolo_model else None,
            prediction_type=inference_mode,
            predicted_class=self._predicted_class(yolo_result, anomaly_result, decision),
            confidence=decision.get("max_yolo_confidence"),
            bounding_boxes=_result_regions(type("R", (), {"regions": []})())
            if not yolo_result
            else yolo_result.get("regions", []),
            anomaly_score=anomaly_result.get("anomaly_score"),
            processing_time_ms=timings["total_ms"],
            status="completed",
            final_status=decision["final_status"],
            review_reasons=decision["review_reasons"],
            decision_rule_version=decision["decision_rule_version"],
            quality_result=quality,
            yolo_result=yolo_result,
            anomaly_result=anomaly_result,
            system_decision=decision,
            step_timings=timings,
            model_versions={
                "yolo": None if yolo_model is None else yolo_model.id,
                "anomaly": None if anomaly_model is None else anomaly_model.id,
            },
        )
        self.session.add(inspection)
        self.session.flush()
        review: ReviewTask | None = None
        if decision["requires_review"]:
            review = ReviewTask(
                inspection_id=inspection.id,
                original_prediction=original_prediction,
                system_decision=decision,
                review_status="pending",
            )
            self.session.add(review)
            self.session.flush()
        self._audit(
            "inspection.predicted",
            "inspection",
            inspection.id,
            "system",
            {
                "final_status": decision["final_status"],
                "review_id": None if review is None else review.id,
            },
        )
        return {"inspection": inspection, "review": review, "idempotent": False}

    def _select_model(self, model_type: str, version: str | None) -> ModelVersion | None:
        statement = select(ModelVersion).where(ModelVersion.model_type == model_type)
        if version:
            statement = statement.where(ModelVersion.version == version)
        else:
            statement = statement.where(ModelVersion.active.is_(True))
        return self.session.scalar(statement)

    @staticmethod
    def _predicted_class(
        yolo: dict[str, Any], anomaly: dict[str, Any], decision: dict[str, Any]
    ) -> str | None:
        regions = yolo.get("regions", [])
        if regions:
            best = max(regions, key=lambda item: float(item.get("confidence") or 0))
            return str(best.get("class_name"))
        if decision["final_status"] == "ANOMALY" or anomaly.get("is_anomaly"):
            return "unknown_anomaly"
        if decision["final_status"] == "PASS":
            return "normal"
        return None

    def _audit(
        self, action: str, entity_type: str, entity_id: str, operator: str, details: dict[str, Any]
    ) -> None:
        self.session.add(
            AuditLog(
                action=action,
                entity_type=entity_type,
                entity_id=entity_id,
                operator=operator,
                details=details,
                created_at=utc_now(),
            )
        )


def create_feedback_from_review(
    session: Session,
    review: ReviewTask,
    inspection: Inspection,
    reviewer: str,
    corrected_prediction: dict[str, Any],
    corrected_label: str,
    feedback_type: str,
) -> FeedbackSample:
    original_boxes = inspection.yolo_result.get("regions", [])
    corrected_boxes = corrected_prediction.get("boxes", original_boxes)
    feedback = FeedbackSample(
        inspection_id=inspection.id,
        review_task_id=review.id,
        image_path=inspection.image_path,
        original_label=inspection.predicted_class,
        corrected_label=corrected_label,
        original_boxes=original_boxes,
        corrected_boxes=corrected_boxes,
        feedback_type=feedback_type,
        source_model_version=inspection.model_versions.get("yolo"),
        corrected_annotation=corrected_prediction,
    )
    session.add(feedback)
    session.add(
        AuditLog(
            action="feedback.created",
            entity_type="feedback_sample",
            entity_id="pending",
            operator=reviewer,
            details={"review_id": review.id, "inspection_id": inspection.id},
            created_at=utc_now(),
        )
    )
    return feedback

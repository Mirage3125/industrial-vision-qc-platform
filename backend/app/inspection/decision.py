from __future__ import annotations

from typing import Any

from backend.app.inspection.config import HybridInspectionConfig

TERMINAL_STATUSES = {
    "PASS",
    "DEFECT",
    "ANOMALY",
    "REVIEW_REQUIRED",
    "IMAGE_QUALITY_FAILED",
    "INFERENCE_FAILED",
}


def decide(
    quality: dict[str, Any],
    yolo: dict[str, Any],
    anomaly: dict[str, Any],
    config: HybridInspectionConfig,
    inference_failed: bool = False,
) -> dict[str, Any]:
    reasons: list[str] = []
    if inference_failed:
        reasons.append("INFERENCE_FAILED")
    for issue in quality.get("issues", []):
        reasons.append(str(issue))
    regions = yolo.get("regions", [])
    max_conf = max((float(region.get("confidence") or 0) for region in regions), default=0.0)
    high_risk = [
        region
        for region in regions
        if str(region.get("class_name")) in set(config.high_risk_classes)
        and float(region.get("confidence") or 0) >= config.yolo_low_confidence_threshold
    ]
    anomaly_score = float(anomaly.get("anomaly_score") or 0.0)
    anomaly_flag = (
        bool(anomaly.get("is_anomaly", False)) or anomaly_score >= config.anomaly_threshold
    )
    if regions and max_conf < config.yolo_low_confidence_threshold:
        reasons.append("YOLO_LOW_CONFIDENCE")
    if not regions and anomaly_flag:
        reasons.append("YOLO_NONE_ANOMALY_HIGH")
    if regions and anomaly_flag:
        reasons.append("MODEL_CONFLICT_OR_UNKNOWN_ANOMALY")
    if high_risk:
        reasons.append("HIGH_RISK_DEFECT")
    if anomaly_flag:
        reasons.append("UNKNOWN_ANOMALY")
    if config.force_review:
        reasons.append("FORCE_REVIEW")
    if any(reason in {"CORRUPT_IMAGE", "RESOLUTION_TOO_SMALL"} for reason in reasons):
        final_status = "IMAGE_QUALITY_FAILED"
    elif inference_failed:
        final_status = "INFERENCE_FAILED"
    elif reasons:
        final_status = "REVIEW_REQUIRED"
    elif regions:
        final_status = "DEFECT"
    elif anomaly_flag:
        final_status = "ANOMALY"
    else:
        final_status = "PASS"
    return {
        "requires_review": bool(reasons),
        "review_reasons": sorted(set(reasons)),
        "decision_rule_version": config.decision_rule_version,
        "final_status": final_status,
        "max_yolo_confidence": max_conf,
        "anomaly_score": anomaly_score,
        "rules": {
            "yolo_low_confidence_threshold": config.yolo_low_confidence_threshold,
            "anomaly_threshold": config.anomaly_threshold,
            "high_risk_classes": config.high_risk_classes,
        },
    }

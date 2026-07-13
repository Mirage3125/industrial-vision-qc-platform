from __future__ import annotations

import json
import shutil
import statistics
import time
from typing import Any

import cv2
import numpy as np

from backend.app.anomaly_detection.config import AnomalyConfig
from backend.app.anomaly_detection.dataset import mask_path_for, test_images
from backend.app.anomaly_detection.predictor import PaDiMStyleAnomalyDetector


def binary_auc(labels: list[int], scores: list[float]) -> float | None:
    label_array = np.asarray(labels, dtype=np.uint8)
    score_array = np.asarray(scores, dtype=np.float64)
    positive_count = int(label_array.sum())
    negative_count = int(label_array.size - positive_count)
    if positive_count == 0 or negative_count == 0:
        return None
    order = np.argsort(score_array, kind="mergesort")
    sorted_scores = score_array[order]
    ranks = np.empty_like(score_array, dtype=np.float64)
    start = 0
    one_based = np.arange(1, score_array.size + 1, dtype=np.float64)
    while start < score_array.size:
        end = start + 1
        while end < score_array.size and sorted_scores[end] == sorted_scores[start]:
            end += 1
        ranks[order[start:end]] = float(one_based[start:end].mean())
        start = end
    positive_rank_sum = float(ranks[label_array == 1].sum())
    return (positive_rank_sum - positive_count * (positive_count + 1) / 2) / (
        positive_count * negative_count
    )


def f1_at_threshold(labels: list[int], scores: list[float], threshold: float) -> dict[str, float]:
    tp = fp = tn = fn = 0
    for label, score in zip(labels, scores, strict=True):
        pred = score >= threshold
        if pred and label:
            tp += 1
        elif pred and not label:
            fp += 1
        elif not pred and label:
            fn += 1
        else:
            tn += 1
    precision = tp / max(tp + fp, 1)
    recall = tp / max(tp + fn, 1)
    f1 = 2 * precision * recall / max(precision + recall, 1e-12)
    return {
        "precision": precision,
        "recall": recall,
        "f1": f1,
        "false_positive_rate": fp / max(fp + tn, 1),
        "false_negative_rate": fn / max(fn + tp, 1),
    }


def evaluate(config: AnomalyConfig, max_pixel_samples: int = 2_000_000) -> dict[str, Any]:
    detector = PaDiMStyleAnomalyDetector(config.model_path)
    samples = test_images(config.data_root, config.category)
    if not samples:
        raise RuntimeError(f"No test images found for {config.category}")
    heatmap_dir = config.evaluation_dir / "heatmaps"
    overlay_dir = config.evaluation_dir / "overlays"
    mask_dir = config.evaluation_dir / "masks"
    for directory in [heatmap_dir, overlay_dir, mask_dir]:
        directory.mkdir(parents=True, exist_ok=True)

    image_labels: list[int] = []
    image_scores: list[float] = []
    pixel_labels: list[int] = []
    pixel_scores: list[float] = []
    false_positives: list[dict[str, Any]] = []
    false_negatives: list[dict[str, Any]] = []
    latencies: list[float] = []

    for image_path, label in samples:
        started = time.perf_counter()
        prediction = detector.predict_anomaly(
            image_path, config.evaluation_dir / "_predictions", include_map=True
        )
        prefix = f"{label}_{image_path.stem}"
        if prediction.heatmap_path is not None:
            target = heatmap_dir / f"{prefix}_heatmap.png"
            target.unlink(missing_ok=True)
            shutil.move(prediction.heatmap_path, target)
            prediction.heatmap_path = str(target)
        if prediction.overlay_path is not None:
            target = overlay_dir / f"{prefix}_overlay.png"
            target.unlink(missing_ok=True)
            shutil.move(prediction.overlay_path, target)
            prediction.overlay_path = str(target)
        if prediction.predicted_mask_path is not None:
            target = mask_dir / f"{prefix}_mask.png"
            target.unlink(missing_ok=True)
            shutil.move(prediction.predicted_mask_path, target)
            prediction.predicted_mask_path = str(target)
        latencies.append((time.perf_counter() - started) * 1000)
        actual = 0 if label == "good" else 1
        image_labels.append(actual)
        image_scores.append(prediction.anomaly_score)
        pred = int(prediction.is_anomaly)
        row = prediction.model_dump(mode="json") | {"label": label}
        if pred == 1 and actual == 0:
            false_positives.append(row)
        if pred == 0 and actual == 1:
            false_negatives.append(row)

        mask_path = mask_path_for(image_path, config.data_root, config.category, label)
        if mask_path is not None:
            gt = cv2.imread(str(mask_path), cv2.IMREAD_GRAYSCALE)
            pred_mask = cv2.imread(str(prediction.predicted_mask_path), cv2.IMREAD_GRAYSCALE)
            if gt is not None and pred_mask is not None:
                gt_small = cv2.resize(gt, (config.image_size, config.image_size)) > 0
                if prediction.anomaly_map is not None:
                    score_small = np.asarray(prediction.anomaly_map, dtype=np.float32)
                    pixel_labels.extend(gt_small.astype(np.uint8).ravel().tolist())
                    pixel_scores.extend(score_small.ravel().tolist())
                    if len(pixel_labels) > max_pixel_samples:
                        step = max(1, len(pixel_labels) // max_pixel_samples)
                        pixel_labels = pixel_labels[::step]
                        pixel_scores = pixel_scores[::step]

    image_auc = binary_auc(image_labels, image_scores)
    pixel_auc = binary_auc(pixel_labels, pixel_scores) if pixel_labels else None
    image_f1 = f1_at_threshold(image_labels, image_scores, detector.threshold)
    pixel_f1 = (
        f1_at_threshold(pixel_labels, pixel_scores, detector.mask_threshold)
        if pixel_labels
        else None
    )
    metrics: dict[str, Any] = {
        "algorithm": config.algorithm,
        "category": config.category,
        "model_path": str(config.model_path),
        "threshold": detector.threshold,
        "mask_threshold": detector.mask_threshold,
        "image_level_auroc": image_auc,
        "pixel_level_auroc": pixel_auc,
        "image_level_f1": image_f1["f1"],
        "pixel_level_f1": None if pixel_f1 is None else pixel_f1["f1"],
        "normal_false_positive_rate": image_f1["false_positive_rate"],
        "anomaly_false_negative_rate": image_f1["false_negative_rate"],
        "average_inference_time_ms": statistics.fmean(latencies),
        "p50_inference_time_ms": float(np.percentile(latencies, 50)),
        "p95_inference_time_ms": float(np.percentile(latencies, 95)),
        "p99_inference_time_ms": float(np.percentile(latencies, 99)),
        "sample_count": len(samples),
    }
    config.evaluation_dir.mkdir(parents=True, exist_ok=True)
    (config.evaluation_dir / "metrics.json").write_text(
        json.dumps(metrics, ensure_ascii=False, indent=2), encoding="utf-8"
    )
    (config.evaluation_dir / "false-positives.json").write_text(
        json.dumps(false_positives, ensure_ascii=False, indent=2), encoding="utf-8"
    )
    (config.evaluation_dir / "false-negatives.json").write_text(
        json.dumps(false_negatives, ensure_ascii=False, indent=2), encoding="utf-8"
    )
    (config.evaluation_dir / "metrics.md").write_text(
        "\n".join(f"- {key}: {value}" for key, value in metrics.items()), encoding="utf-8"
    )
    return metrics

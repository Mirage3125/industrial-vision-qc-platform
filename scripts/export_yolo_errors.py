import argparse
import json
from pathlib import Path
from typing import Any

from backend.app.detection import YoloPyTorchDetector


def _iou(left: list[float], right: list[float]) -> float:
    intersection_width = max(0.0, min(left[2], right[2]) - max(left[0], right[0]))
    intersection_height = max(0.0, min(left[3], right[3]) - max(left[1], right[1]))
    intersection = intersection_width * intersection_height
    union = (
        (left[2] - left[0]) * (left[3] - left[1])
        + (right[2] - right[0]) * (right[3] - right[1])
        - intersection
    )
    return intersection / union if union > 0 else 0.0


def _ground_truth(label_path: Path, width: int, height: int) -> list[dict[str, Any]]:
    boxes: list[dict[str, Any]] = []
    for line in label_path.read_text(encoding="utf-8").splitlines():
        class_id, center_x, center_y, box_width, box_height = map(float, line.split())
        boxes.append(
            {
                "class_id": int(class_id),
                "box": [
                    (center_x - box_width / 2) * width,
                    (center_y - box_height / 2) * height,
                    (center_x + box_width / 2) * width,
                    (center_y + box_height / 2) * height,
                ],
            }
        )
    return boxes


def main() -> None:
    parser = argparse.ArgumentParser(description="Export YOLO false-positive/missed/class errors")
    parser.add_argument("--weights", type=Path, required=True)
    parser.add_argument("--images", type=Path, required=True)
    parser.add_argument("--labels", type=Path, required=True)
    parser.add_argument("--output", type=Path, default=Path("artifacts/detection/errors"))
    parser.add_argument("--iou", type=float, default=0.5)
    parser.add_argument("--device", default="0")
    args = parser.parse_args()
    detector = YoloPyTorchDetector(args.weights, device=args.device)
    cases: list[dict[str, Any]] = []
    for image_path in sorted(args.images.glob("*")):
        label_path = args.labels / f"{image_path.stem}.txt"
        if not label_path.is_file():
            continue
        result = detector.predict(image_path, args.output / "visualizations")
        truth = _ground_truth(label_path, result.image_width, result.image_height)
        predicted = [
            {
                "class_id": region.class_id,
                "box": [
                    region.bounding_box.x1,
                    region.bounding_box.y1,
                    region.bounding_box.x2,
                    region.bounding_box.y2,
                ],
            }
            for region in result.regions
        ]
        matched_predictions: set[int] = set()
        errors: list[str] = []
        for target in truth:
            matches = [
                (index, _iou(target["box"], prediction["box"]))
                for index, prediction in enumerate(predicted)
                if index not in matched_predictions
            ]
            best = max(matches, key=lambda item: item[1], default=None)
            if best is None or best[1] < args.iou:
                errors.append("missed_detection")
            else:
                matched_predictions.add(best[0])
                if predicted[best[0]]["class_id"] != target["class_id"]:
                    errors.append("class_error")
        errors.extend(
            "false_positive" for i in range(len(predicted)) if i not in matched_predictions
        )
        if errors:
            cases.append(
                {"image": str(image_path), "errors": errors, "result": result.model_dump()}
            )
    args.output.mkdir(parents=True, exist_ok=True)
    output = args.output / "error-cases.json"
    output.write_text(json.dumps(cases, ensure_ascii=False, indent=2), encoding="utf-8")
    print(output)


if __name__ == "__main__":
    main()

"""Run diagnostic OpenCV stages on real NEU-DET samples from every class."""

import argparse
import json
import time
from pathlib import Path

import cv2

from backend.app.classical_vision import ClassicalVisionDetector, load_classical_config

CLASSES = [
    "crazing",
    "inclusion",
    "patches",
    "pitted_surface",
    "rolled-in_scale",
    "scratches",
]


def main() -> None:
    parser = argparse.ArgumentParser(description="Run OpenCV stages on real NEU-DET samples")
    parser.add_argument("--raw", type=Path, default=Path("data/raw/neu-det/extracted"))
    parser.add_argument(
        "--config", type=Path, default=Path("configs/classical_vision/baseline.yaml")
    )
    parser.add_argument("--output", type=Path, default=Path("artifacts/classical_vision/neu-det"))
    parser.add_argument("--per-class", type=int, default=2)
    args = parser.parse_args()
    detector = ClassicalVisionDetector(load_classical_config(args.config))
    args.output.mkdir(parents=True, exist_ok=True)
    summaries: list[dict[str, object]] = []
    for class_name in CLASSES:
        candidates = sorted(
            path for path in args.raw.rglob("*.jpg") if path.parent.name == class_name
        )[: args.per_class]
        if len(candidates) < args.per_class:
            raise SystemExit(f"Insufficient real samples for {class_name}")
        for image_path in candidates:
            output = args.output / class_name / image_path.stem
            output.mkdir(parents=True, exist_ok=True)
            image = cv2.imread(str(image_path))
            gray = cv2.cvtColor(image, cv2.COLOR_BGR2GRAY)
            enhanced = cv2.createCLAHE(clipLimit=2.0, tileGridSize=(8, 8)).apply(gray)
            _, binary = cv2.threshold(enhanced, 0, 255, cv2.THRESH_BINARY_INV | cv2.THRESH_OTSU)
            edges = cv2.Canny(enhanced, 50, 150)
            kernel = cv2.getStructuringElement(cv2.MORPH_ELLIPSE, (5, 5))
            morphology = cv2.morphologyEx(binary, cv2.MORPH_CLOSE, kernel)
            started = time.perf_counter()
            result = detector.predict(image_path, output)
            elapsed_ms = (time.perf_counter() - started) * 1000
            cv2.imwrite(str(output / "original.jpg"), image)
            cv2.imwrite(str(output / "gray-enhanced.png"), enhanced)
            cv2.imwrite(str(output / "binary.png"), binary)
            cv2.imwrite(str(output / "edges.png"), edges)
            cv2.imwrite(str(output / "morphology.png"), morphology)
            summaries.append(
                {
                    "class": class_name,
                    "image": str(image_path.resolve()),
                    "candidate_count": result.defect_count,
                    "detector_processing_time_ms": result.processing_time_ms,
                    "end_to_end_time_ms": round(elapsed_ms, 3),
                    "output_dir": str(output.resolve()),
                }
            )
    summary_path = args.output / "summary.json"
    summary_path.write_text(json.dumps(summaries, ensure_ascii=False, indent=2), encoding="utf-8")
    print(summary_path)


if __name__ == "__main__":
    main()
